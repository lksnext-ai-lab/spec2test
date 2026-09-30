import { describe, expect, it } from 'vitest';
import { formatValue, parseEnv, updateEnv } from '../src/core/envfile';

const SAMPLE = `# keys
# GOOGLE_API_KEY=
OPENAI_API_KEY=sk-old
# ANTHROPIC_API_KEY="sk-"
CUSTOM=keep me   # note

MAX_CRAWL_PAGES=50
`;

describe('parseEnv', () => {
  it('reads active assignments only, unquoting values', () => {
    expect(parseEnv('A=1\n# B=2\nC="x y"\nD=\'z\'\nE=v  # tail')).toEqual({ A: '1', C: 'x y', D: 'z', E: 'v' });
  });
});

describe('updateEnv', () => {
  it('rewrites an active line in place', () => {
    const out = updateEnv(SAMPLE, { OPENAI_API_KEY: 'sk-new' });
    expect(out).toContain('OPENAI_API_KEY=sk-new');
    expect(out).not.toContain('sk-old');
  });

  it('activates a commented template line where it is', () => {
    const lines = updateEnv(SAMPLE, { GOOGLE_API_KEY: 'g-key' }).split('\n');
    expect(lines[1]).toBe('GOOGLE_API_KEY=g-key');
  });

  it('appends unknown keys and keeps everything else untouched', () => {
    const out = updateEnv(SAMPLE, { HF_TOKEN: 'hf' });
    expect(out.endsWith('HF_TOKEN=hf\n')).toBe(true);
    expect(out).toContain('CUSTOM=keep me   # note');
    expect(out).toContain('MAX_CRAWL_PAGES=50');
  });

  it('comments out a cleared key and ignores clearing an absent one', () => {
    expect(updateEnv(SAMPLE, { OPENAI_API_KEY: null })).toContain('# OPENAI_API_KEY=');
    expect(updateEnv('A=1\n', { B: null })).toBe('A=1\n');
  });

  it('starts a new file', () => {
    expect(updateEnv('', { A: '1' })).toBe('A=1\n');
  });

  it('quotes values that need it, and survives a round trip', () => {
    expect(formatValue('plain')).toBe('plain');
    const tricky = 'a b#c"d$e';
    expect(parseEnv(updateEnv('', { K: tricky })).K).toBe(tricky);
  });
});
