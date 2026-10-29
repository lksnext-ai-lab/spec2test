import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { DAY_MS, compareVersions, isDue, matchesRelease, parseRelease } from '../src/core/updates';

describe('compareVersions', () => {
  it('orders numerically, not as text, and ignores a leading v', () => {
    expect(compareVersions('0.10.0', '0.9.5')).toBeGreaterThan(0);
    expect(compareVersions('v1.0.0', '0.99.99')).toBeGreaterThan(0);
    expect(compareVersions('0.2.5', '0.2.57')).toBeLessThan(0);
    expect(compareVersions('0.2.57', 'v0.2.57')).toBe(0);
  });

  it('treats anything that is not a version as equal, so it never offers an update', () => {
    expect(compareVersions('latest', '0.1.0')).toBe(0);
    expect(compareVersions('0.1.0', '')).toBe(0);
  });
});

describe('parseRelease', () => {
  const release = {
    tag_name: 'v0.2.57',
    html_url: 'https://github.com/lksnext-ai-lab/spec2test/releases/tag/v0.2.57',
    assets: [
      { name: 'notes.txt', browser_download_url: 'https://x/notes.txt' },
      { name: 'spec2test-0.2.57.vsix', browser_download_url: 'https://x/spec2test-0.2.57.vsix', size: 10, digest: 'sha256:abc' },
    ],
  };

  it('finds the .vsix that matches the tag', () => {
    expect(parseRelease(release)).toMatchObject({ version: '0.2.57', assetName: 'spec2test-0.2.57.vsix', downloadUrl: 'https://x/spec2test-0.2.57.vsix', size: 10 });
  });

  it('ignores drafts, prereleases, odd tags and releases without the extension', () => {
    expect(parseRelease({ ...release, draft: true })).toBeUndefined();
    expect(parseRelease({ ...release, prerelease: true })).toBeUndefined();
    expect(parseRelease({ ...release, tag_name: 'nightly' })).toBeUndefined();
    expect(parseRelease({ ...release, assets: [] })).toBeUndefined();
    expect(parseRelease({ ...release, assets: [{ name: 'spec2test-9.9.9.vsix', browser_download_url: 'u' }] })).toBeUndefined();
    expect(parseRelease(null)).toBeUndefined();
  });
});

describe('matchesRelease', () => {
  const data = new TextEncoder().encode('vsix bytes');
  const digest = `sha256:${createHash('sha256').update(data).digest('hex')}`;

  it('accepts the right size and hash and rejects a changed file', () => {
    expect(matchesRelease(data, { size: data.byteLength, digest })).toBe(true);
    expect(matchesRelease(new TextEncoder().encode('tampered!!'), { size: data.byteLength, digest })).toBe(false);
    expect(matchesRelease(data, { size: data.byteLength + 1, digest })).toBe(false);
  });

  it('passes what it cannot check', () => {
    expect(matchesRelease(data, {})).toBe(true);
  });
});

describe('isDue', () => {
  it('checks at most once a day', () => {
    expect(isDue(undefined, 1)).toBe(true);
    expect(isDue(1000, 1000 + DAY_MS - 1)).toBe(false);
    expect(isDue(1000, 1000 + DAY_MS)).toBe(true);
  });
});
