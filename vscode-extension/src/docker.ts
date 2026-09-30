import { execFile, spawn, type ChildProcess } from 'node:child_process';
import * as os from 'node:os';
import type * as vscode from 'vscode';
import { UNREACHABLE } from './core/health';
import type { DockerState } from './shared/messages';

const SERVICE = 'input-processor';


/** VS Code started from the Dock does not always see Docker's install folders. */
function dockerEnv(): NodeJS.ProcessEnv {
  const extra =
    os.platform() === 'win32'
      ? []
      : ['/usr/local/bin', '/opt/homebrew/bin', '/Applications/Docker.app/Contents/Resources/bin'];
  const separator = os.platform() === 'win32' ? ';' : ':';
  return { ...process.env, PATH: [process.env.PATH ?? '', ...extra].join(separator) };
}

interface Result {
  code: number | null;
  stdout: string;
  stderr: string;
  missing?: boolean;
}

function run(args: string[], cwd: string | undefined, timeoutMs = 60_000): Promise<Result> {
  return new Promise((resolve) => {
    execFile('docker', args, { cwd, env: dockerEnv(), timeout: timeoutMs, maxBuffer: 16 * 1024 * 1024 }, (error, stdout, stderr) => {
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

/** `docker compose ps --format json` prints one object per line or a JSON array, depending on the version. */
export function parseComposePs(output: string): { State?: string; Health?: string }[] {
  const text = output.trim();
  if (!text) {
    return [];
  }
  if (text.startsWith('[')) {
    return JSON.parse(text);
  }
  return text.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
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

export class DockerService {
  private logs?: ChildProcess;

  constructor(
    private readonly repo: () => string | undefined,
    private readonly port: () => number,
    private readonly output: vscode.OutputChannel,
  ) {}

  async probe(): Promise<{ state: DockerState; detail?: string }> {
    const repo = this.repo();
    if (!repo) {
      return { state: 'no-repo' };
    }
    const version = await run(['--version'], repo, 10_000);
    if (version.missing) {
      return { state: 'not-installed' };
    }
    const info = await run(['info', '--format', '{{.ServerVersion}}'], repo, 10_000);
    if (info.code !== 0) {
      return { state: 'daemon-down', detail: info.stderr.trim().split('\n').pop() };
    }
    const ps = await run(['compose', 'ps', '--all', '--format', 'json', SERVICE], repo, 15_000);
    if (ps.code !== 0) {
      return { state: 'stopped', detail: ps.stderr.trim().split('\n').pop() };
    }
    const container = parseComposePs(ps.stdout)[0];
    if (!container) {
      return { state: 'stopped' };
    }
    if (container.State === 'running') {
      return (await isReachable(this.port())) ? { state: 'running' } : { state: 'starting', detail: UNREACHABLE };
    }
    if (container.State === 'restarting' || container.State === 'created') {
      return { state: 'starting' };
    }
    return { state: 'stopped', detail: container.State };
  }

  /** Wait until the MCP endpoint answers; false on timeout. */
  async waitUntilReachable(timeoutMs = 120_000): Promise<boolean> {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (await isReachable(this.port())) {
        return true;
      }
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    return false;
  }

  up(options: { build?: boolean; recreate?: boolean } = {}): Promise<Result> {
    const args = ['compose', 'up', '-d'];
    if (options.build) {
      args.push('--build');
    }
    if (options.recreate) {
      args.push('--force-recreate');
    }
    args.push(SERVICE);
    return this.stream(args);
  }

  down(): Promise<Result> {
    return this.stream(['compose', 'stop', SERVICE]);
  }

  /** Follow the container logs in the output channel until disposed. */
  showLogs(): void {
    this.output.show(true);
    if (this.logs && !this.logs.killed) {
      return;
    }
    const repo = this.repo();
    if (!repo) {
      return;
    }
    this.logs = spawn('docker', ['compose', 'logs', '-f', '--tail', '200', '--no-color', SERVICE], {
      cwd: repo,
      env: dockerEnv(),
    });
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

  private stream(args: string[]): Promise<Result> {
    const repo = this.repo();
    this.output.appendLine(`$ docker ${args.join(' ')}`);
    return new Promise((resolve) => {
      const child = spawn('docker', args, { cwd: repo, env: dockerEnv() });
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
