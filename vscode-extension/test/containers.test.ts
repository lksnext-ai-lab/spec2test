import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  buildRunArgs,
  inputProcessorSpec,
  isCurrent,
  parseInspect,
  shouldMapUser,
  webCrawlerSpec,
  wantedImage,
} from '../src/core/containers';

describe('wantedImage', () => {
  it('is the registry image of this extension version unless overridden', () => {
    expect(wantedImage('inputProcessor', '0.2.5', '')).toBe('ghcr.io/lksnext-ai-lab/spec2test-input-processor:0.2.5');
    expect(wantedImage('webCrawler', '0.2.5', '  ')).toBe('ghcr.io/lksnext-ai-lab/spec2test-web-crawler:0.2.5');
    expect(wantedImage('webCrawler', '0.2.5', 'spec2test-web-crawler:dev')).toBe('spec2test-web-crawler:dev');
  });
});

describe('buildRunArgs', () => {
  const spec = inputProcessorSpec({
    image: 'img:1',
    port: 8003,
    dataRoot: path.resolve('/home/me/.spec2test'),
    tuning: { INPUT_PROCESSOR_LOG_LEVEL: 'DEBUG', INPUT_PROCESSOR_VIDEO_MAX_FRAMES: '  ' },
    secrets: ['GOOGLE_API_KEY'],
    gpu: true,
  });
  const args = buildRunArgs(spec);

  it('publishes on loopback only and mounts the data folder once', () => {
    expect(args.slice(0, 6)).toEqual(['run', '-d', '--name', 'spec2test-input-processor', '-p', '127.0.0.1:8003:8000']);
    expect(args).toContain(`${path.resolve('/home/me/.spec2test')}:/projects`);
    expect(args.filter((arg) => arg.endsWith(':/projects'))).toHaveLength(1);
    expect(args).toContain('INPUT_PROCESSOR_PROJECTS_CONFIG=/projects/projects.json');
  });

  it('passes secrets as bare names, never with a value', () => {
    expect(args).toContain('GOOGLE_API_KEY');
    expect(args.some((arg) => arg.startsWith('GOOGLE_API_KEY='))).toBe(false);
  });

  it('skips empty tuning values, adds the GPU flag and ends with the image', () => {
    expect(args).toContain('INPUT_PROCESSOR_LOG_LEVEL=DEBUG');
    expect(args.some((arg) => arg.startsWith('INPUT_PROCESSOR_VIDEO_MAX_FRAMES'))).toBe(false);
    expect(args.join(' ')).toContain('--gpus all');
    expect(args.at(-1)).toBe('img:1');
  });

  it('mounts the saved crawler login only when there is one', () => {
    const without = buildRunArgs(webCrawlerSpec({ image: 'c:1', port: 8000 }));
    expect(without).not.toContain('-v');
    const login = path.resolve('/home/me/.spec2test/auth_actions.json');
    const withLogin = buildRunArgs(webCrawlerSpec({ image: 'c:1', port: 8000, authActionsFile: login }));
    expect(withLogin).toContain(`${login}:/app/auth_actions.json:ro`);
    expect(withLogin).toContain('CRAWLER_AUTH_ACTIONS_FILE=/app/auth_actions.json');
  });
});

describe('container inspection', () => {
  it('parses the inspect format and rejects empty output', () => {
    expect(parseInspect('running|img:1|sha256:abc\n')).toEqual({ status: 'running', image: 'img:1', imageId: 'sha256:abc' });
    expect(parseInspect('')).toBeUndefined();
  });

  it('is current only for the same tag and, when known, the same image id', () => {
    const running = { status: 'running', image: 'img:dev', imageId: 'sha256:old' };
    expect(isCurrent(running, 'img:dev', 'sha256:old')).toBe(true);
    expect(isCurrent(running, 'img:dev', 'sha256:new')).toBe(false);
    expect(isCurrent(running, 'img:dev', undefined)).toBe(true);
    expect(isCurrent(running, 'img:0.3', 'sha256:old')).toBe(false);
  });
});

describe('running as the user (native Docker on Linux)', () => {
  const root = path.resolve('/home/me/.spec2test');
  const base = { image: 'img:1', port: 8003, dataRoot: root, tuning: {}, secrets: [], gpu: false };

  it('adds --user, keeps the model cache in the data folder and gives the process a writable home', () => {
    const args = buildRunArgs(inputProcessorSpec({ ...base, user: { uid: 1000, gid: 1001 } }));
    expect(args.join(' ')).toContain('--user 1000:1001');
    expect(args).toContain('HF_HOME=/projects/.hf-cache');
    expect(args).toContain('HOME=/tmp');
    expect(args.some((arg) => arg.includes('spec2test-hf-cache'))).toBe(false);
  });

  it('keeps the named volume and root when no mapping is needed', () => {
    const args = buildRunArgs(inputProcessorSpec(base));
    expect(args).not.toContain('--user');
    expect(args).toContain('spec2test-hf-cache:/root/.cache/huggingface');
    expect(args).toContain('HF_HOME=/root/.cache/huggingface');
  });

  it('maps the user only for native Docker Engine on Linux', () => {
    const engine = { operatingSystem: 'Ubuntu 24.04 LTS', securityOptions: '[name=seccomp,profile=builtin name=cgroupns]' };
    expect(shouldMapUser('linux', engine)).toBe(true);
    expect(shouldMapUser('linux', { ...engine, securityOptions: '[name=seccomp name=rootless]' })).toBe(false);
    expect(shouldMapUser('linux', { ...engine, operatingSystem: 'Docker Desktop' })).toBe(false);
    expect(shouldMapUser('darwin', engine)).toBe(false);
    expect(shouldMapUser('win32', engine)).toBe(false);
  });
});
