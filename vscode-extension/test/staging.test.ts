import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { createHash } from 'node:crypto';
import { beforeEach, describe, expect, it } from 'vitest';
import { migrateLegacy } from '../src/core/migrate';
import { readConfig, resolvePaths, workAreaOf } from '../src/core/projects';
import { entryNames, hasPending, isUpToDate, mirrorIn, refreshWork, runStaged, snapshot, syncBack, type Layout } from '../src/core/staging';

const sha = (text: string) => createHash('sha256').update(text).digest('hex');
const entry = (source: string, text: string) => `---\nsource: "${source}"\nsha256: ${sha(text)}\n---\nbody of ${source}\n`;

let root: string;
let layout: Layout;

const write = (file: string, text: string) => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, text);
};

beforeEach(() => {
  root = fs.mkdtempSync(path.join(os.tmpdir(), 's2t-stage-'));
  const project = path.join(root, 'user', 'specs');
  layout = { inputs: project, cache: path.join(project, '.spec2test', 'cache'), preprocessed: path.join(project, '.spec2test', 'preprocessed'), work: workAreaOf(path.join(root, 'data'), 'shop') };
  fs.mkdirSync(project, { recursive: true });
});

const never = new AbortController().signal;

function run(name: string, options: { force?: boolean; process?: () => Promise<{ status: string; error?: string }>; reports?: string[] } = {}) {
  return runStaged({
    layout,
    name,
    force: options.force ?? false,
    signal: never,
    sha256: async () => sha(fs.readFileSync(path.join(layout.inputs, name), 'utf8')),
    process: options.process ?? (async () => ({ status: 'new' })),
    report: (message) => options.reports?.push(message),
  });
}

describe('mirrorIn / syncBack', () => {
  it('mirrors the project cache into the work cache and drops entries the project does not have', () => {
    write(path.join(layout.cache, 'a.pdf.md'), 'A');
    write(path.join(layout.work.cache, 'gone.pdf.md'), 'old');
    mirrorIn(layout);
    expect(entryNames(layout.work.cache, 'cache')).toEqual(['a.pdf.md']);
    expect(fs.readFileSync(path.join(layout.work.cache, 'a.pdf.md'), 'utf8')).toBe('A');
  });

  it('copies new and changed results back and history files that are missing', () => {
    write(path.join(layout.cache, 'a.pdf.md'), 'old');
    write(path.join(layout.work.cache, 'a.pdf.md'), 'new');
    write(path.join(layout.work.cache, '.history', 'a.pdf.12345678.20260101T000000Z.md'), 'archived');
    syncBack(layout, { cache: ['a.pdf.md'], preprocessed: [] });
    expect(fs.readFileSync(path.join(layout.cache, 'a.pdf.md'), 'utf8')).toBe('new');
    expect(fs.existsSync(path.join(layout.cache, '.history', 'a.pdf.12345678.20260101T000000Z.md'))).toBe(true);
  });

  it('deletes only results the server removed, never ones the project gained meanwhile', () => {
    write(path.join(layout.cache, 'old-name.pdf.md'), 'x');
    write(path.join(layout.cache, 'pulled.pdf.md'), 'from git');
    write(path.join(layout.work.cache, 'new-name.pdf.md'), 'x');
    syncBack(layout, { cache: ['old-name.pdf.md'], preprocessed: [] });
    expect(entryNames(layout.cache, 'cache').sort()).toEqual(['new-name.pdf.md', 'pulled.pdf.md']);
  });
});

describe('pre-processed files', () => {
  const pre = () => path.join(layout.preprocessed);

  it('copies the pre-processed file and its images back next to the results, and mirrors them in again', async () => {
    write(path.join(layout.inputs, 'a.pdf'), 'pdf');
    await run('a.pdf', {
      process: async () => {
        write(path.join(layout.work.cache, 'a.pdf.md'), entry('a.pdf', 'pdf'));
        write(path.join(layout.work.preprocessed, 'a.pdf.md'), 'pre');
        write(path.join(layout.work.preprocessed, 'a.pdf_images', 'img-1.png'), 'png');
        return { status: 'new' };
      },
    });
    expect(fs.readFileSync(path.join(pre(), 'a.pdf.md'), 'utf8')).toBe('pre');
    expect(fs.existsSync(path.join(pre(), 'a.pdf_images', 'img-1.png'))).toBe(true);

    fs.rmSync(layout.work.root, { recursive: true, force: true });
    refreshWork(layout);
    expect(fs.existsSync(path.join(layout.work.preprocessed, 'a.pdf_images', 'img-1.png'))).toBe(true);
  });

  it('does not treat scratch folders of the cache as results', () => {
    write(path.join(layout.work.cache, '_segments', 'big.mp4'), 'x');
    expect(entryNames(layout.work.cache, 'cache')).toEqual([]);
    expect(snapshot(layout).cache).toEqual([]);
  });

  it('adopts pre-processed files that only the work area had, once, instead of dropping them', () => {
    write(path.join(layout.work.preprocessed, 'old.pdf.md'), 'paid');
    refreshWork(layout);
    expect(fs.readFileSync(path.join(pre(), 'old.pdf.md'), 'utf8')).toBe('paid');
    // After that the user's folder is authoritative: what is removed there goes from the work area too.
    fs.rmSync(path.join(pre(), 'old.pdf.md'));
    refreshWork(layout);
    expect(fs.existsSync(path.join(layout.work.preprocessed, 'old.pdf.md'))).toBe(false);
  });

  it('leaves big unchanged images alone and replaces a changed one', () => {
    const big = 'x'.repeat(300 * 1024);
    write(path.join(pre(), 'a.pdf_images', 'big.png'), big);
    refreshWork(layout);
    const copy = path.join(layout.work.preprocessed, 'a.pdf_images', 'big.png');
    const before = fs.statSync(copy).ino;
    refreshWork(layout);
    expect(fs.statSync(copy).ino).toBe(before);
    const changed = path.join(pre(), 'a.pdf_images', 'big.png');
    write(changed, 'y'.repeat(300 * 1024));
    const later = new Date(Date.now() + 60_000);
    fs.utimesSync(changed, later, later);
    refreshWork(layout);
    expect(fs.readFileSync(copy, 'utf8')[0]).toBe('y');
  });
});

describe('isUpToDate', () => {
  it('needs the same name and hash, and never when forced', () => {
    write(path.join(layout.cache, 'a.md.md'), entry('a.md', 'hello'));
    expect(isUpToDate(layout.cache, 'a.md', sha('hello'), false)).toBe(true);
    expect(isUpToDate(layout.cache, 'a.md', sha('changed'), false)).toBe(false);
    expect(isUpToDate(layout.cache, 'a.md', sha('hello'), true)).toBe(false);
    expect(isUpToDate(layout.cache, 'b.md', sha('hello'), false)).toBe(false);
  });
});

describe('runStaged', () => {
  it('stages the input, lets the server write the work cache, copies the result back and unstages', async () => {
    write(path.join(layout.inputs, 'a.md'), 'hello');
    const reports: string[] = [];
    let seenStaged = false;
    const result = await run('a.md', {
      reports,
      process: async () => {
        seenStaged = fs.existsSync(path.join(layout.work.inputs, 'a.md'));
        write(path.join(layout.work.cache, 'a.md.md'), entry('a.md', 'hello'));
        return { status: 'new' };
      },
    });
    expect(result.status).toBe('new');
    expect(seenStaged).toBe(true);
    expect(fs.existsSync(path.join(layout.work.inputs, 'a.md'))).toBe(false);
    expect(fs.existsSync(path.join(layout.cache, 'a.md.md'))).toBe(true);
    expect(fs.existsSync(path.join(layout.inputs, 'a.md'))).toBe(true);
    expect(reports.some((message) => message.startsWith('Copying a.md'))).toBe(true);
  });

  it('skips the copy and the server when the file is already processed', async () => {
    write(path.join(layout.inputs, 'a.md'), 'hello');
    write(path.join(layout.cache, 'a.md.md'), entry('a.md', 'hello'));
    let called = false;
    const result = await run('a.md', { process: async () => ((called = true), { status: 'new' }) });
    expect(result.status).toBe('cached');
    expect(called).toBe(false);
    expect(fs.existsSync(path.join(layout.work.inputs, 'a.md'))).toBe(false);
  });

  it('processes a forced file even when it is cached', async () => {
    write(path.join(layout.inputs, 'a.md'), 'hello');
    write(path.join(layout.cache, 'a.md.md'), entry('a.md', 'hello'));
    const result = await run('a.md', { force: true, process: async () => ({ status: 'updated' }) });
    expect(result.status).toBe('updated');
  });

  it('copies nothing back after an error and unstages the input', async () => {
    write(path.join(layout.inputs, 'a.md'), 'hello');
    await run('a.md', {
      process: async () => {
        write(path.join(layout.work.cache, 'half.md.md'), 'partial');
        return { status: 'error', error: 'boom' };
      },
    });
    expect(fs.existsSync(path.join(layout.cache, 'half.md.md'))).toBe(false);
    expect(fs.existsSync(path.join(layout.work.inputs, 'a.md'))).toBe(false);
  });

  it('keeps the result pending when the copy-back fails and delivers it on the next refresh', async () => {
    write(path.join(layout.inputs, 'a.md'), 'hello');
    // A file where the cache folder should be makes the copy-back fail.
    write(path.join(layout.inputs, '.spec2test'), 'in the way');
    await expect(
      run('a.md', {
        process: async () => {
          write(path.join(layout.work.cache, 'a.md.md'), entry('a.md', 'hello'));
          return { status: 'new' };
        },
      }),
    ).rejects.toThrow(/could not be copied/);
    expect(hasPending(layout)).toBe(true);

    fs.rmSync(path.join(layout.inputs, '.spec2test'));
    refreshWork(layout);
    expect(hasPending(layout)).toBe(false);
    expect(fs.existsSync(path.join(layout.cache, 'a.md.md'))).toBe(true);
    expect(fs.existsSync(path.join(layout.work.cache, 'a.md.md'))).toBe(true);
  });

  it('re-keys a renamed file: the old result leaves the project cache', async () => {
    write(path.join(layout.inputs, 'new.md'), 'hello');
    write(path.join(layout.cache, 'old.md.md'), entry('old.md', 'hello'));
    await run('new.md', {
      process: async () => {
        fs.renameSync(path.join(layout.work.cache, 'old.md.md'), path.join(layout.work.cache, 'new.md.md'));
        return { status: 'renamed' };
      },
    });
    expect(entryNames(layout.cache, 'cache')).toEqual(['new.md.md']);
  });

  it('does not stage or copy for a managed project (inputs and cache in the work area)', async () => {
    layout = { inputs: layout.work.inputs, cache: layout.work.cache, preprocessed: layout.work.preprocessed, work: layout.work };
    write(path.join(layout.inputs, 'a.md'), 'hello');
    const result = await run('a.md');
    expect(result.status).toBe('new');
    expect(fs.existsSync(path.join(layout.inputs, 'a.md'))).toBe(true);
  });

  it('rebuilds a wiped work area from the project cache', () => {
    write(path.join(layout.cache, 'a.md.md'), entry('a.md', 'hello'));
    refreshWork(layout);
    fs.rmSync(layout.work.root, { recursive: true, force: true });
    refreshWork(layout);
    expect(entryNames(layout.work.cache, 'cache')).toEqual(['a.md.md']);
  });
});

describe('migrateLegacy', () => {
  it('imports the old projects.json and moves default results to their new place', () => {
    const repo = path.join(root, 'repo');
    write(path.join(repo, '.spec2test-data', 'shop', 'cache', 'a.md.md'), 'A');
    write(path.join(repo, '.spec2test-data', 'shop', 'preprocessed', 'a.md.md'), 'P');
    write(path.join(repo, 'projects.json'), JSON.stringify({ projects: [{ name: 'shop', inputs: path.join(root, 'user', 'specs') }, { name: 'plain' }] }));
    const data = path.join(root, 'data');

    expect(migrateLegacy(repo, data)).toHaveLength(2);

    const config = readConfig(path.join(data, 'projects.json'));
    expect(config.projects.map((project) => project.name)).toEqual(['shop', 'plain']);
    const paths = resolvePaths(config.projects[0], data);
    expect(fs.readFileSync(path.join(paths.cache, 'a.md.md'), 'utf8')).toBe('A');
    expect(fs.readFileSync(path.join(paths.preprocessed, 'a.md.md'), 'utf8')).toBe('P');
    expect(migrateLegacy(repo, data)).toEqual([]);
  });
});
