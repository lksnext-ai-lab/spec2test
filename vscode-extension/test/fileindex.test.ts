import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import * as crypto from 'node:crypto';
import { beforeEach, describe, expect, it } from 'vitest';
import { FileIndex, copyIntoInputs, isSupported, listHistory, outputsOf, ownedFiles, parseFrontMatter } from '../src/core/fileindex';

let root: string;
let paths: { inputs: string; cache: string; preprocessed: string };

const sha = (text: string) => crypto.createHash('sha256').update(text).digest('hex');

function cacheFile(name: string, content: string, extra: Partial<Record<string, string>> = {}) {
  const meta = { source: name, format: path.extname(name), size: String(content.length), sha256: sha(content), processed_at: '2026-09-29T10:00:00Z', provider: 'google_genai', model: 'gemini', ...extra };
  const front = Object.entries(meta).map(([key, value]) => `${key}: "${value}"`).join('\n');
  fs.writeFileSync(path.join(paths.cache, `${name}.md`), `---\n${front}\n---\nbody\n`);
}

beforeEach(() => {
  root = fs.mkdtempSync(path.join(os.tmpdir(), 's2t-'));
  paths = { inputs: path.join(root, 'inputs'), cache: path.join(root, 'cache'), preprocessed: path.join(root, 'pre') };
  Object.values(paths).forEach((dir) => fs.mkdirSync(dir, { recursive: true }));
});

describe('mapping', () => {
  it('maps an input to its outputs by full name plus .md', () => {
    expect(outputsOf(paths, 'login.mp4')).toEqual({
      original: path.join(paths.inputs, 'login.mp4'),
      cache: path.join(paths.cache, 'login.mp4.md'),
      preprocessed: path.join(paths.preprocessed, 'login.mp4.md'),
      images: path.join(paths.preprocessed, 'login.mp4_images'),
    });
  });

  it('supports exactly the formats the server handles', () => {
    expect(['a.MP4', 'a.pdf', 'a.md', 'a.txt'].every(isSupported)).toBe(true);
    expect(['a.docx', 'a.png', 'a'].some(isSupported)).toBe(false);
  });

  it('parses front matter', () => {
    expect(parseFrontMatter('---\nsource: "a.txt"\nsize: 5\n---\nbody')).toEqual({ source: 'a.txt', size: '5' });
    expect(parseFrontMatter('no front matter')).toEqual({});
  });
});

describe('scan', () => {
  it('classifies new, cached, changed, renamed and orphaned files', async () => {
    fs.writeFileSync(path.join(paths.inputs, 'new.txt'), 'brand new');
    fs.writeFileSync(path.join(paths.inputs, 'same.txt'), 'same');
    fs.writeFileSync(path.join(paths.inputs, 'edited.txt'), 'after');
    fs.writeFileSync(path.join(paths.inputs, 'moved.txt'), 'twin');
    fs.writeFileSync(path.join(paths.inputs, 'ignore.docx'), 'x');
    cacheFile('same.txt', 'same');
    cacheFile('edited.txt', 'before');
    cacheFile('old-name.txt', 'twin');
    cacheFile('gone.txt', 'vanished');

    const { files, orphans } = await new FileIndex(paths).scan();

    expect(Object.fromEntries(files.map((f) => [f.name, f.state]))).toEqual({
      'edited.txt': 'stale',
      'moved.txt': 'renamed',
      'new.txt': 'new',
      'same.txt': 'cached',
    });
    expect(orphans.map((o) => o.name).sort()).toEqual(['gone.txt']);
    const same = files.find((f) => f.name === 'same.txt')!;
    expect(same).toMatchObject({ hasCache: true, hasPreprocessed: false, provider: 'google_genai', model: 'gemini' });
  });

  it('memoises hashes by size and mtime', async () => {
    const file = path.join(paths.inputs, 'a.txt');
    fs.writeFileSync(file, 'one');
    const index = new FileIndex(paths);
    const first = await index.sha256(file);
    expect(await index.sha256(file)).toBe(first);
    fs.writeFileSync(file, 'two!');
    expect(await index.sha256(file)).not.toBe(first);
  });

  it('copes with folders that do not exist yet', async () => {
    fs.rmSync(paths.inputs, { recursive: true });
    fs.rmSync(paths.cache, { recursive: true });
    expect(await new FileIndex(paths).scan()).toEqual({ files: [], orphans: [] });
  });
});

describe('history and archiving', () => {
  it('lists server-written history newest first, ignoring lookalikes', () => {
    const dir = path.join(paths.cache, '.history');
    fs.mkdirSync(dir);
    for (const file of ['a.txt.1234abcd.20260101T100000Z.md', 'a.txt.1234abcd.20260202T100000Z-1.md', 'a.txt.b.5678abcd.20260303T100000Z.md', 'a.txt.notes.md']) {
      fs.writeFileSync(path.join(dir, file), 'x');
    }
    expect(listHistory(paths.cache, 'a.txt').map((h) => h.label)).toEqual(['2026-02-02 10:00:00', '2026-01-01 10:00:00']);
  });

  it('archives a cache entry into .history using the server naming, never deleting', () => {
    cacheFile('a.txt', 'content');
    const target = new FileIndex(paths).archiveCache('a.txt', new Date('2026-09-30T12:34:56Z'))!;
    expect(path.basename(target)).toBe(`a.txt.${sha('content').slice(0, 8)}.20260930T123456Z.md`);
    expect(fs.existsSync(target)).toBe(true);
    expect(fs.existsSync(path.join(paths.cache, 'a.txt.md'))).toBe(false);
    expect(listHistory(paths.cache, 'a.txt')).toHaveLength(1);
    expect(new FileIndex(paths).archiveCache('missing.txt')).toBeUndefined();
  });
});

describe('copyIntoInputs', () => {
  it('copies, and resolves name clashes as asked', () => {
    const source = path.join(root, 'spec.pdf');
    fs.writeFileSync(source, 'v1');
    expect(copyIntoInputs(source, paths.inputs, 'replace').copied).toBe(true);
    fs.writeFileSync(source, 'v2');
    expect(copyIntoInputs(source, paths.inputs, 'skip').copied).toBe(false);
    expect(fs.readFileSync(path.join(paths.inputs, 'spec.pdf'), 'utf8')).toBe('v1');
    expect(path.basename(copyIntoInputs(source, paths.inputs, 'keep-both').target)).toBe('spec (2).pdf');
    copyIntoInputs(source, paths.inputs, 'replace');
    expect(fs.readFileSync(path.join(paths.inputs, 'spec.pdf'), 'utf8')).toBe('v2');
    expect(fs.existsSync(source)).toBe(true);
  });
});

describe('ownedFiles (what "detach and trash" may delete)', () => {
  it('lists inputs, their results and the processor folders, and leaves everything else alone', () => {
    fs.writeFileSync(path.join(paths.inputs, 'spec.pdf'), 'pdf');
    fs.writeFileSync(path.join(paths.inputs, 'notes.docx'), 'someone else\'s file');
    fs.mkdirSync(path.join(paths.inputs, 'subfolder'));
    cacheFile('spec.pdf', 'pdf');
    cacheFile('gone.txt', 'orphan');
    fs.mkdirSync(path.join(paths.cache, '.history'));
    fs.mkdirSync(path.join(paths.cache, '_segments'));
    fs.writeFileSync(path.join(paths.cache, 'unrelated.log'), 'x');
    fs.writeFileSync(path.join(paths.preprocessed, 'spec.pdf.md'), 'md');
    fs.mkdirSync(path.join(paths.preprocessed, 'spec.pdf_images'));
    fs.writeFileSync(path.join(paths.preprocessed, 'readme.txt'), 'x');

    const rel = ownedFiles(paths).map((file) => path.relative(root, file)).sort();

    expect(rel).toEqual(
      [
        'cache/.history',
        'cache/_segments',
        'cache/gone.txt.md',
        'cache/spec.pdf.md',
        'inputs/spec.pdf',
        'pre/spec.pdf.md',
        'pre/spec.pdf_images',
      ].sort(),
    );
  });

  it('is empty for folders that do not exist', () => {
    expect(ownedFiles({ inputs: path.join(root, 'no'), cache: path.join(root, 'no2'), preprocessed: path.join(root, 'no3') })).toEqual([]);
  });
});
