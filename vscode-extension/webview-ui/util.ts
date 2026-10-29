import type { Job, LlmSettings, ProviderInfo } from '../src/shared/types';

export function formatSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ['KB', 'MB', 'GB'];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value < 10 ? 1 : 0)} ${units[unit]}`;
}

export function relativeTime(iso?: string, now: number = Date.now()): string {
  if (!iso) {
    return '';
  }
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) {
    return iso;
  }
  const seconds = Math.max(0, Math.round((now - then) / 1000));
  if (seconds < 60) {
    return 'just now';
  }
  if (seconds < 3600) {
    return `${Math.floor(seconds / 60)} min ago`;
  }
  if (seconds < 86400) {
    return `${Math.floor(seconds / 3600)} h ago`;
  }
  if (seconds < 86400 * 30) {
    return `${Math.floor(seconds / 86400)} d ago`;
  }
  return new Date(then).toLocaleDateString();
}

const BRAND: Record<string, string> = {
  google_genai: 'Google Gemini',
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  deepseek: 'DeepSeek',
  openrouter: 'OpenRouter',
  qwen: 'Qwen',
};

/** Provider ids as people write them; unknown providers fall back to Title Case. */
export function titleCase(name: string): string {
  return (
    BRAND[name] ??
    name
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
  );
}

/** Keep the last `keep` folders of a path: `/Users/a/b/c/specs` -> `…/b/c/specs`. */
export function shortPath(full: string, keep = 2): string {
  const parts = full.split(/[\\/]/).filter(Boolean);
  return parts.length <= keep ? full : `…/${parts.slice(-keep).join('/')}`;
}

/** What the server will actually use: project override, else defaults, else the built-in default. */
export function effectiveModel(
  project: LlmSettings | undefined,
  defaults: LlmSettings | undefined,
  providers: ProviderInfo[],
  fallbackProvider: string,
): { provider: string; model: string } {
  const provider = project?.provider || defaults?.provider || fallbackProvider;
  const info = providers.find((item) => item.name === provider);
  const model = project?.model || (project?.provider ? '' : defaults?.model) || info?.defaultModel || '';
  return { provider, model: model || info?.defaultModel || '' };
}

export function capabilitiesOf(providers: ProviderInfo[], provider: string, model: string): string[] {
  const info = providers.find((item) => item.name === provider);
  return info?.models.find((item) => item.id === model)?.capabilities ?? info?.capabilities ?? [];
}

export const CAPABILITY_LABEL: Record<string, string> = {
  text: 'Text',
  images: 'Images',
  video_inline: 'Video',
  video_upload: 'Video upload',
};

export function jobFor(jobs: Job[], file: string): Job | undefined {
  return [...jobs].reverse().find((job) => job.file === file);
}
