import * as crypto from 'node:crypto';
import * as fs from 'node:fs';
import * as fsp from 'node:fs/promises';
import * as path from 'node:path';
import { HISTORY_DIR, readCacheEntries } from './fileindex';
import type { WorkArea } from './projects';

/**
 * Staged processing. The user's folders are the source of truth; the work area is what the
 * container sees and can be deleted at any time.
 *
 *   mirror in  : project cache -> work cache   (before work, and whenever the cache changes)
 *   stage      : input -> work inputs          (only when it is not already processed)
 *   process    : the container writes work cache
 *   sync back  : work cache -> project cache   (only after a successful run), then unstage
 *
 * Every step copies one way and the job queue is the only writer, so there is no two-way merge.
 * The sync functions are synchronous on purpose: they cannot interleave with each other.
 */

export interface Layout {
  /** The user's inputs folder. */
  inputs: string;
  /** The user's folder for the processed results. */
  cache: string;
  /** The user's folder for the pre-processed files (also paid for: image descriptions). */
  preprocessed: string;
  work: WorkArea;
}

export interface Result {
  status: string;
  error?: string;
}

type Key = 'cache' | 'preprocessed';
type Baseline = Record<Key, string[]>;

const PENDING_FILE = '.pending-sync.json';
const ADOPTED_FILE = '.adopted-preprocessed';

export const needsStaging = (layout: Layout): boolean => path.resolve(layout.inputs) !== path.resolve(layout.work.inputs);

/** The folders that live outside the work area and so have to be kept in step with it. */
function pairs(layout: Layout): { key: Key; user: string; work: string }[] {
  return (['cache', 'preprocessed'] as const)
    .map((key) => ({ key, user: layout[key], work: layout.work[key] }))
    .filter((pair) => path.resolve(pair.user) !== path.resolve(pair.work));
}

export const needsSync = (layout: Layout): boolean => pairs(layout).length > 0;

/**
 * What counts as a result in a folder: `<input>.md` files in the cache (its `_segments` scratch folder
 * is not a result), and anything not hidden in the pre-processed folder (`<input>.md`, `<input>_images/`).
 */
export function entryNames(dir: string, key: Key): string[] {
  if (!fs.existsSync(dir)) {
    return [];
  }
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((item) => !item.name.startsWith('.') && (key === 'preprocessed' || (item.isFile() && item.name.endsWith('.md'))))
    .map((item) => item.name);
}

const SMALL_FILE = 256 * 1024;

/** Small files are compared by content; big ones (images) by size and modification time, which a copy preserves. */
function sameFile(a: string, b: string): boolean {
  if (!fs.existsSync(a) || !fs.existsSync(b)) {
    return false;
  }
  const left = fs.statSync(a);
  const right = fs.statSync(b);
  if (left.size !== right.size) {
    return false;
  }
  return left.size <= SMALL_FILE ? fs.readFileSync(a).equals(fs.readFileSync(b)) : Math.abs(left.mtimeMs - right.mtimeMs) < 2;
}

function copyFile(from: string, to: string): void {
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.copyFileSync(from, to);
  const time = fs.statSync(from);
  fs.utimesSync(to, time.atime, time.mtime);
}

/** Make `to` equal `from`, file by file, leaving what is already equal alone. */
function syncTree(from: string, to: string): void {
  if (fs.statSync(from).isDirectory()) {
    fs.mkdirSync(to, { recursive: true });
    const names = new Set(fs.readdirSync(from));
    for (const name of names) {
      syncTree(path.join(from, name), path.join(to, name));
    }
    for (const name of fs.readdirSync(to)) {
      if (!names.has(name)) {
        fs.rmSync(path.join(to, name), { recursive: true, force: true });
      }
    }
  } else if (!sameFile(from, to)) {
    fs.rmSync(to, { recursive: true, force: true });
    copyFile(from, to);
  }
}

function copyMissingHistory(fromDir: string, toDir: string): void {
  const from = path.join(fromDir, HISTORY_DIR);
  if (!fs.existsSync(from)) {
    return;
  }
  for (const name of fs.readdirSync(from)) {
    const target = path.join(toDir, HISTORY_DIR, name);
    if (!fs.existsSync(target)) {
      copyFile(path.join(from, name), target);
    }
  }
}

/** Make the work folders equal to the user's. Results the user's folders do not have are dropped. */
export function mirrorIn(layout: Layout): void {
  for (const { key, user, work } of pairs(layout)) {
    fs.mkdirSync(work, { recursive: true });
    const wanted = new Set(entryNames(user, key));
    for (const name of wanted) {
      syncTree(path.join(user, name), path.join(work, name));
    }
    for (const name of entryNames(work, key)) {
      if (!wanted.has(name)) {
        fs.rmSync(path.join(work, name), { recursive: true, force: true });
      }
    }
  }
}

/** What the work folders hold right now: the baseline for a later {@link syncBack}. */
export function snapshot(layout: Layout): Baseline {
  return { cache: entryNames(layout.work.cache, 'cache'), preprocessed: entryNames(layout.work.preprocessed, 'preprocessed') };
}

/**
 * Copy the results of a run into the user's folders. `baseline` is what the work folders held
 * before the run: an entry that is gone now was moved or re-keyed by the server, so it goes from
 * the user's folder too. Anything else in the user's folders is never deleted.
 */
export function syncBack(layout: Layout, baseline: Baseline): void {
  for (const { key, user, work } of pairs(layout)) {
    fs.mkdirSync(user, { recursive: true });
    copyMissingHistory(work, user);
    const now = new Set(entryNames(work, key));
    for (const name of now) {
      syncTree(path.join(work, name), path.join(user, name));
    }
    for (const name of baseline[key]) {
      if (!now.has(name)) {
        fs.rmSync(path.join(user, name), { recursive: true, force: true });
      }
    }
  }
}

const pendingPath = (layout: Layout) => path.join(layout.work.root, PENDING_FILE);

export function hasPending(layout: Layout): boolean {
  return fs.existsSync(pendingPath(layout));
}

function markPending(layout: Layout, baseline: Baseline): void {
  fs.mkdirSync(layout.work.root, { recursive: true });
  fs.writeFileSync(pendingPath(layout), JSON.stringify({ baseline }), 'utf8');
}

/** Retry a copy-back that failed earlier. Returns false when it still cannot be done. */
export function retryPending(layout: Layout): boolean {
  if (!hasPending(layout)) {
    return true;
  }
  let baseline: Baseline = { cache: [], preprocessed: [] };
  try {
    const stored = (JSON.parse(fs.readFileSync(pendingPath(layout), 'utf8')) as { baseline?: Baseline | string[] }).baseline;
    // The first version stored only the cache entries, as a list.
    baseline = Array.isArray(stored) ? { cache: stored, preprocessed: [] } : { cache: stored?.cache ?? [], preprocessed: stored?.preprocessed ?? [] };
  } catch {
    // An unreadable marker still means "results are waiting": copy without deleting anything.
  }
  try {
    syncBack(layout, baseline);
    fs.rmSync(pendingPath(layout), { force: true });
    return true;
  } catch {
    return false;
  }
}

/**
 * Before pre-processed files lived in the user's folder they were only in the work area. Once,
 * copy them over so the first mirror does not throw away what was paid for.
 */
function adoptPreprocessed(layout: Layout): void {
  const marker = path.join(layout.work.root, ADOPTED_FILE);
  const pair = pairs(layout).find((item) => item.key === 'preprocessed');
  if (!pair || fs.existsSync(marker)) {
    return;
  }
  for (const name of entryNames(pair.work, 'preprocessed')) {
    if (!fs.existsSync(path.join(pair.user, name))) {
      syncTree(path.join(pair.work, name), path.join(pair.user, name));
    }
  }
  fs.mkdirSync(layout.work.root, { recursive: true });
  fs.writeFileSync(marker, '', 'utf8');
}

/** Bring the work area up to date with the user's folders; a no-op for managed projects. */
export function refreshWork(layout: Layout): void {
  if (!needsSync(layout) || !retryPending(layout)) {
    return;
  }
  adoptPreprocessed(layout);
  mirrorIn(layout);
}

/** Cached means: same name, same hash, and not forced. Then neither the file nor the server is needed. */
export function isUpToDate(cacheDir: string, name: string, sha256: string, force: boolean): boolean {
  if (force) {
    return false;
  }
  return readCacheEntries(cacheDir).some((entry) => entry.source === name && entry.sha256 === sha256);
}

export function hashFile(file: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    fs.createReadStream(file)
      .on('data', (chunk) => hash.update(chunk))
      .on('end', () => resolve(hash.digest('hex')))
      .on('error', reject);
  });
}

export function formatSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${unit === 0 ? value : value.toFixed(1)} ${units[unit]}`;
}

/** Copy `from` to `to`: an instant copy-on-write clone where the filesystem has one, else a streamed copy. */
export async function copyWithProgress(
  from: string,
  to: string,
  signal: AbortSignal,
  onProgress: (done: number, total: number) => void,
): Promise<void> {
  await fsp.rm(to, { force: true });
  try {
    await fsp.copyFile(from, to, fs.constants.COPYFILE_FICLONE_FORCE);
    return;
  } catch {
    // No clone support here: copy the bytes.
  }
  const total = fs.statSync(from).size;
  let done = 0;
  let last = 0;
  const source = fs.createReadStream(from);
  const target = fs.createWriteStream(to);
  const abort = () => {
    source.destroy(new Error('Cancelled'));
    target.destroy();
  };
  signal.addEventListener('abort', abort, { once: true });
  source.on('data', (chunk) => {
    done += chunk.length;
    const now = Date.now();
    if (now - last > 250) {
      last = now;
      onProgress(done, total);
    }
  });
  try {
    await new Promise<void>((resolve, reject) => {
      source.on('error', reject);
      target.on('error', reject);
      target.on('finish', resolve);
      source.pipe(target);
    });
    onProgress(total, total);
  } catch (error) {
    await fsp.rm(to, { force: true });
    throw error;
  } finally {
    signal.removeEventListener('abort', abort);
  }
}

export interface StagedRun {
  layout: Layout;
  name: string;
  force: boolean;
  signal: AbortSignal;
  sha256: () => Promise<string>;
  process: () => Promise<Result>;
  report: (message: string) => void;
}

/** Process one input through the work area; the user's input is never modified. */
export async function runStaged(run: StagedRun): Promise<Result> {
  const { layout, name, signal, report } = run;
  const sync = needsSync(layout);
  const stage = needsStaging(layout);

  let baseline: Baseline = { cache: [], preprocessed: [] };
  if (sync) {
    if (!retryPending(layout)) {
      throw new Error(`Earlier results are waiting to be copied to ${layout.cache}, but that folder cannot be written.`);
    }
    mirrorIn(layout);
    baseline = snapshot(layout);
  }

  const staged = path.join(layout.work.inputs, name);
  if (stage) {
    report(`Checking ${name}…`);
    if (isUpToDate(layout.cache, name, await run.sha256(), run.force)) {
      return { status: 'cached' };
    }
    const source = path.join(layout.inputs, name);
    const label = formatSize(fs.statSync(source).size);
    fs.mkdirSync(layout.work.inputs, { recursive: true });
    report(`Copying ${name} (${label}) to the Spec2Test work area…`);
    await copyWithProgress(source, staged, signal, (done, total) =>
      report(`Copying ${name} (${label}) to the Spec2Test work area… ${Math.floor((done / total) * 100)}%`),
    );
  }

  // The server reports steps only for PDFs and videos; without this a text file would keep showing the copy.
  report(`Processing ${name}…`);
  let result: Result;
  try {
    result = await run.process();
  } finally {
    if (stage) {
      await fsp.rm(staged, { force: true });
    }
  }

  if (sync && result.status !== 'error' && !signal.aborted) {
    try {
      syncBack(layout, baseline);
    } catch (error) {
      markPending(layout, baseline);
      throw new Error(`Processed, but the result could not be copied to ${layout.cache} (${(error as Error).message}). It will be retried.`);
    }
  }
  return result;
}
