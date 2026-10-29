import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { parseProcessResult, toolText } from '../src/mcp';
import { readProviders } from '../src/core/providers';
import { findRepo, isRepo } from '../src/repo';
import { TUNING } from '../src/core/tuning';

const REPO = path.resolve(__dirname, '..', '..');

describe('MCP results', () => {
  it('extracts text and interprets process_file answers', () => {
    expect(toolText({ content: [{ type: 'text', text: 'hi' }] })).toBe('hi');
    expect(toolText({})).toBe('');
    expect(parseProcessResult('{"name":"a","status":"new"}')).toEqual({ status: 'new', error: undefined });
    expect(parseProcessResult('{"error":"nope"}')).toEqual({ status: 'error', error: 'nope' });
    expect(parseProcessResult('not json').status).toBe('error');
  });
});

describe('repository detection', () => {
  it('recognises this repository and walks up from a sub folder', () => {
    expect(isRepo(REPO)).toBe(true);
    expect(findRepo('', [path.join(REPO, 'input-processor', 'src')])).toBe(REPO);
    expect(findRepo(REPO, [])).toBe(REPO);
  });

  it('returns nothing for unrelated folders', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 's2t-'));
    expect(findRepo('', [dir])).toBeUndefined();
  });
});

describe('provider metadata read from the catalog files', () => {
  const providers = readProviders(path.join(REPO, 'input-processor', 'src', 'providers'));

  it('lists native and catalog providers with their key variables', () => {
    expect(providers.map((p) => p.name)).toEqual(['anthropic', 'deepseek', 'google_genai', 'openai', 'openrouter', 'qwen']);
    expect(providers.find((p) => p.name === 'google_genai')).toMatchObject({ apiKeyEnv: 'GOOGLE_API_KEY', defaultModel: 'gemini-2.0-flash' });
  });

  it('applies per-model capability overrides', () => {
    const openrouter = providers.find((p) => p.name === 'openrouter')!;
    expect(openrouter.models.find((m) => m.id === 'deepseek/deepseek-chat')!.capabilities).toEqual(['text']);
    expect(providers.every((p) => p.models.some((m) => m.id === p.defaultModel))).toBe(true);
  });
});

describe('tuning variables', () => {
  it('cover every INPUT_PROCESSOR_* knob of .env.example', () => {
    const example = fs.readFileSync(path.join(REPO, '.env.example'), 'utf8');
    const documented = Array.from(example.matchAll(/^#\s*(INPUT_PROCESSOR_[A-Z_]+)=/gm)).map((m) => m[1]);
    const ours = TUNING.map((t) => t.key);
    // The two path settings are wired by docker-compose, not user tuning.
    const expected = documented.filter((key) => !/PROJECTS_(CONFIG|ROOT)$/.test(key));
    expect(ours.sort()).toEqual(expected.sort());
  });
});
