import { createHash } from 'node:crypto';

/** Pure parts of the self-update from GitHub Releases: no network, no VS Code. */
export const RELEASES_API = 'https://api.github.com/repos/lksnext-ai-lab/spec2test/releases/latest';

export interface ReleaseInfo {
  version: string;
  assetName: string;
  downloadUrl: string;
  size?: number;
  /** `sha256:<hex>` as reported by GitHub, when it reports one. */
  digest?: string;
  pageUrl: string;
}

/** Numeric `major.minor.patch` (a leading `v` and anything after `-` or `+` are ignored). */
export function parseVersion(text: string): number[] | undefined {
  const match = /^v?(\d+)\.(\d+)\.(\d+)/.exec(text.trim());
  return match ? [Number(match[1]), Number(match[2]), Number(match[3])] : undefined;
}

/** Positive when `a` is newer than `b`; 0 when equal or when either is not a version. */
export function compareVersions(a: string, b: string): number {
  const left = parseVersion(a);
  const right = parseVersion(b);
  if (!left || !right) {
    return 0;
  }
  for (let index = 0; index < 3; index += 1) {
    if (left[index] !== right[index]) {
      return left[index] - right[index];
    }
  }
  return 0;
}

interface RawRelease {
  tag_name?: string;
  html_url?: string;
  draft?: boolean;
  prerelease?: boolean;
  assets?: { name?: string; browser_download_url?: string; size?: number; digest?: string }[];
}

/** The release's `.vsix`, or undefined for a draft, a prerelease or one without the extension attached. */
export function parseRelease(raw: unknown): ReleaseInfo | undefined {
  const release = raw as RawRelease;
  if (!release || release.draft || release.prerelease || !release.tag_name) {
    return undefined;
  }
  const version = release.tag_name.replace(/^v/, '');
  if (!parseVersion(version)) {
    return undefined;
  }
  const asset = release.assets?.find((item) => item.name === `spec2test-${version}.vsix` && item.browser_download_url);
  if (!asset?.name || !asset.browser_download_url) {
    return undefined;
  }
  return {
    version,
    assetName: asset.name,
    downloadUrl: asset.browser_download_url,
    size: asset.size,
    digest: asset.digest,
    pageUrl: release.html_url ?? `https://github.com/lksnext-ai-lab/spec2test/releases/tag/${release.tag_name}`,
  };
}

/** Does the downloaded file match what GitHub says it is? A missing digest cannot be checked and passes. */
export function matchesRelease(data: Uint8Array, release: Pick<ReleaseInfo, 'size' | 'digest'>): boolean {
  if (release.size !== undefined && data.byteLength !== release.size) {
    return false;
  }
  const expected = /^sha256:([0-9a-f]{64})$/i.exec(release.digest ?? '')?.[1];
  return !expected || createHash('sha256').update(data).digest('hex') === expected.toLowerCase();
}

export const DAY_MS = 24 * 60 * 60 * 1000;

export function isDue(lastCheck: number | undefined, now: number): boolean {
  return lastCheck === undefined || now - lastCheck >= DAY_MS;
}
