import * as path from 'node:path';

/** The two containers the extension runs. Pure helpers: no Docker, no VS Code, so they are testable. */
export type ServiceKey = 'inputProcessor' | 'webCrawler';

export const REGISTRY = 'ghcr.io/lksnext-ai-lab';
export const IMAGE_NAME: Record<ServiceKey, string> = {
  inputProcessor: 'spec2test-input-processor',
  webCrawler: 'spec2test-web-crawler',
};
export const CONTAINER_NAME: Record<ServiceKey, string> = {
  inputProcessor: 'spec2test-input-processor',
  webCrawler: 'spec2test-web-crawler',
};

/** The image this extension version is built for, unless the user pointed the setting at another. */
export function wantedImage(service: ServiceKey, version: string, override: string): string {
  return override.trim() || `${REGISTRY}/${IMAGE_NAME[service]}:${version}`;
}

export interface RunSpec {
  container: string;
  image: string;
  hostPort: number;
  /** `host:container` bind mounts or `volume:container` named volumes. */
  volumes: string[];
  /** Non-secret variables, passed as `NAME=value`. */
  env: Record<string, string>;
  /** Secret variables, passed as a bare `NAME`: the value travels in the process environment, not in the command line. */
  secrets: string[];
  gpu?: boolean;
}

/** Arguments of `docker run`. Published on 127.0.0.1 only: the services have no authentication. */
export function buildRunArgs(spec: RunSpec): string[] {
  const args = ['run', '-d', '--name', spec.container, '-p', `127.0.0.1:${spec.hostPort}:8000`];
  for (const volume of spec.volumes) {
    args.push('-v', volume);
  }
  for (const [name, value] of Object.entries(spec.env)) {
    args.push('-e', `${name}=${value}`);
  }
  for (const name of spec.secrets) {
    args.push('-e', name);
  }
  if (spec.gpu) {
    args.push('--gpus', 'all');
  }
  args.push(spec.image);
  return args;
}

/** Variables for the input-processor. Docker bind-mount paths use forward slashes on every OS. */
export function inputProcessorSpec(options: {
  image: string;
  port: number;
  dataRoot: string;
  tuning: Record<string, string>;
  secrets: string[];
  gpu: boolean;
}): RunSpec {
  const tuning = Object.fromEntries(Object.entries(options.tuning).filter(([, value]) => value.trim() !== ''));
  return {
    container: CONTAINER_NAME.inputProcessor,
    image: options.image,
    hostPort: options.port,
    volumes: [`${toDockerPath(options.dataRoot)}:/projects`, 'spec2test-hf-cache:/root/.cache/huggingface'],
    env: {
      PYTHONUNBUFFERED: '1',
      HOST: '0.0.0.0',
      HF_HOME: '/root/.cache/huggingface',
      HF_HUB_ENABLE_HF_TRANSFER: '1',
      INPUT_PROCESSOR_PROJECTS_CONFIG: '/projects/projects.json',
      ...tuning,
    },
    secrets: options.secrets,
    gpu: options.gpu,
  };
}

/** The crawler needs the saved login only when that file exists: Docker would otherwise create a folder in its place. */
export function webCrawlerSpec(options: { image: string; port: number; authActionsFile?: string }): RunSpec {
  return {
    container: CONTAINER_NAME.webCrawler,
    image: options.image,
    hostPort: options.port,
    volumes: options.authActionsFile ? [`${toDockerPath(options.authActionsFile)}:/app/auth_actions.json:ro`] : [],
    env: {
      PYTHONUNBUFFERED: '1',
      ...(options.authActionsFile ? { CRAWLER_AUTH_ACTIONS_FILE: '/app/auth_actions.json' } : {}),
    },
    secrets: [],
  };
}

export function toDockerPath(host: string): string {
  return path.sep === '\\' ? host.replace(/\\/g, '/') : host;
}

export interface Inspected {
  status: string;
  image: string;
  imageId: string;
}

/** Output of `docker container inspect --format '{{.State.Status}}|{{.Config.Image}}|{{.Image}}'`. */
export function parseInspect(output: string): Inspected | undefined {
  const [status, image, imageId] = output.trim().split('|');
  return status && image ? { status, image, imageId: imageId ?? '' } : undefined;
}

/**
 * Is the container running what we want? Same tag is not enough: a `:dev` tag that was
 * rebuilt, or a `:latest` that was pulled again, points at a new image id.
 */
export function isCurrent(container: Inspected, wanted: string, wantedId: string | undefined): boolean {
  if (container.image !== wanted) {
    return false;
  }
  return wantedId === undefined || container.imageId === wantedId;
}

/** Last non-empty line of a command's stderr, for short messages. */
export function lastLine(text: string): string {
  return text.trim().split(/\r?\n/).filter(Boolean).pop() ?? '';
}
