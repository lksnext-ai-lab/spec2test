import { execFile, spawn, type ChildProcess } from 'node:child_process';
import * as os from 'node:os';
import type * as vscode from 'vscode';
import { buildRunArgs, isCurrent, lastLine, parseInspect, type RunSpec } from './core/containers';
import { UNREACHABLE } from './core/health';
import { dataRoot } from './core/projects';
import type { DockerState } from './shared/messages';

/** VS Code started from the Dock does not always see Docker's install folders. */
function dockerEnv(extra: Record<string, string> = {}): NodeJS.ProcessEnv {
  const folders =
    os.platform() === 'win32'
      ? []
      : ['/usr/local/bin', '/opt/homebrew/bin', '/Applications/Docker.app/Contents/Resources/bin'];
  const separator = os.platform() === 'win32' ? ';' : ':';
  return { ...process.env, PATH: [process.env.PATH ?? '', ...folders].join(separator), SPEC2TEST_HOME: dataRoot(), ...extra };
}

export interface Result {
  code: number | null;
  stdout: string;
  stderr: string;
  missing?: boolean;
}

function run(args: string[], timeoutMs = 60_000): Promise<Result> {
  return new Promise((resolve) => {
    execFile('docker', args, { env: dockerEnv(), timeout: timeoutMs, maxBuffer: 16 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (!error) {
        resolve({ code: 0, stdout, stderr });
        return;
      }
      const failure = error as NodeJS.ErrnoException & { code?: number | string };
      resolve({
        code: typeof failure.code === 'number' ? failure.code : 1,
        stdout,
        stderr: stderr || failure.message,
        missing: failure.code === 'ENOENT',
      });
    });
  });
}

export async function isReachable(port: number, timeoutMs = 2000): Promise<boolean> {
  try {
    // Any HTTP answer (even 4xx) proves the server is listening.
    await fetch(`http://127.0.0.1:${port}/mcp`, { method: 'GET', signal: AbortSignal.timeout(timeoutMs) });
    return true;
  } catch {
    return false;
  }
}

/** What a service needs to start; read fresh every time because keys and settings change. */
export interface ServiceConfig {
  container: string;
  /** The image this version of the extension wants. */
  image: string;
  port: number;
  spec(image: string): Promise<RunSpec>;
  /** Secret values for the bare `-e NAME` arguments. */
  secretValues(): Promise<Record<string, string>>;
}

export class DockerService {
  private logs?: ChildProcess;

  constructor(
    private readonly config: () => ServiceConfig,
    private readonly output: vscode.OutputChannel,
  ) {}

  private get container(): string {
    return this.config().container;
  }

  async probe(): Promise<{ state: DockerState; detail?: string }> {
    const version = await run(['--version'], 10_000);
    if (version.missing) {
      return { state: 'not-installed' };
    }
    const info = await run(['info', '--format', '{{.ServerVersion}}'], 10_000);
    if (info.code !== 0) {
      return { state: 'daemon-down', detail: lastLine(info.stderr) };
    }
    return this.probeContainer();
  }

  /** Container state only; the caller already knows Docker itself is up. */
  async probeContainer(): Promise<{ state: DockerState; detail?: string }> {
    const { image, port } = this.config();
    const inspected = await run(['container', 'inspect', this.container, '--format', '{{.State.Status}}|{{.Config.Image}}|{{.Image}}'], 15_000);
    const container = inspected.code === 0 ? parseInspect(inspected.stdout) : undefined;
    if (!container) {
      return { state: 'stopped' };
    }
    if (container.status === 'running') {
      if (!(await isReachable(port))) {
        return { state: 'starting', detail: UNREACHABLE };
      }
      const wantedId = await this.imageId(image);
      return isCurrent(container, image, wantedId) ? { state: 'running' } : { state: 'outdated', detail: `Running ${container.image}; this version wants ${image}.` };
    }
    if (container.status === 'restarting' || container.status === 'created') {
      return { state: 'starting' };
    }
    return { state: 'stopped', detail: container.status };
  }

  /** Wait until the MCP endpoint answers; false on timeout. */
  async waitUntilReachable(timeoutMs = 120_000): Promise<boolean> {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (await isReachable(this.config().port)) {
        return true;
      }
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    return false;
  }

  private async imageId(image: string): Promise<string | undefined> {
    const result = await run(['image', 'inspect', image, '--format', '{{.Id}}'], 15_000);
    return result.code === 0 ? result.stdout.trim() || undefined : undefined;
  }

  /**
   * Make sure the image is on this machine. A tag that exists locally is kept unless `refresh`
   * asks for the newest one; if the registry cannot be reached the local copy is used.
   */
  async ensureImage(refresh: boolean): Promise<Result> {
    const { image } = this.config();
    const local = await this.imageId(image);
    if (local && !refresh) {
      return { code: 0, stdout: '', stderr: '' };
    }
    this.output.show(true);
    const pulled = await this.stream(['pull', image]);
    if (pulled.code === 0 || local) {
      return { code: 0, stdout: pulled.stdout, stderr: pulled.stderr };
    }
    return {
      ...pulled,
      stderr: `${lastLine(pulled.stderr)}\nThe image ${image} is not available. Build it locally and point the Spec2Test image setting at it, or check your network.`,
    };
  }

  /** Always creates a fresh container, so changed keys, settings and mounts are picked up. */
  async up(options: { refresh?: boolean } = {}): Promise<Result> {
    const image = await this.ensureImage(Boolean(options.refresh));
    if (image.code !== 0) {
      return image;
    }
    const config = this.config();
    const spec = await config.spec(config.image);
    await this.stream(['rm', '-f', spec.container]);
    return this.stream(buildRunArgs(spec), await config.secretValues());
  }

  down(): Promise<Result> {
    return this.stream(['stop', this.container]);
  }

  /** Follow the container logs in the output channel until disposed. */
  showLogs(): void {
    this.output.show(true);
    if (this.logs && !this.logs.killed) {
      return;
    }
    this.logs = spawn('docker', ['logs', '-f', '--tail', '200', this.container], { env: dockerEnv() });
    const write = (chunk: Buffer) => this.output.append(chunk.toString());
    this.logs.stdout?.on('data', write);
    this.logs.stderr?.on('data', write);
    this.logs.on('exit', () => {
      this.logs = undefined;
    });
  }

  dispose(): void {
    this.logs?.kill();
  }

  private stream(args: string[], secrets: Record<string, string> = {}): Promise<Result> {
    // Only the argument names are logged: secrets are never on the command line.
    this.output.appendLine(`$ docker ${args.join(' ')}`);
    return new Promise((resolve) => {
      const child = spawn('docker', args, { env: dockerEnv(secrets) });
      let stdout = '';
      let stderr = '';
      child.stdout.on('data', (chunk: Buffer) => {
        stdout += chunk.toString();
        this.output.append(chunk.toString());
      });
      child.stderr.on('data', (chunk: Buffer) => {
        stderr += chunk.toString();
        this.output.append(chunk.toString());
      });
      child.on('error', (error) => resolve({ code: 1, stdout, stderr: error.message, missing: (error as NodeJS.ErrnoException).code === 'ENOENT' }));
      child.on('close', (code) => resolve({ code, stdout, stderr }));
    });
  }
}
