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
  /** The user's cache folder. */
  cache: string;
  work: WorkArea;
}

export interface Result {
  status: string;
  error?: string;
}

const PENDING_FILE = '.pending-sync.json';

export const needsStaging = (layout: Layout): boolean => path.resolve(layout.inputs) !== path.resolve(layout.work.inputs);
export const needsCacheSync = (layout: Layout): boolean => path.resolve(layout.cache) !== path.resolve(layout.work.cache);

/** Top-level result files of a cache folder (`<input>.md`); history and dot-files are not entries. */
export function entryFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) {
    return [];
  }
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((item) => item.isFile() && item.name.endsWith('.md') && !item.name.startsWith('.'))
    .map((item) => item.name);
}

function sameContent(a: string, b: string): boolean {
  if (!fs.existsSync(a) || !fs.existsSync(b)) {
    return false;
  }
  return fs.statSync(a).size === fs.statSync(b).size && fs.readFileSync(a).equals(fs.readFileSync(b));
}

function copyIfDifferent(from: string, to: string): boolean {
  if (sameContent(from, to)) {
    return false;
  }
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.copyFileSync(from, to);
  return true;
}

function copyMissingHistory(fromCache: string, toCache: string): void {
  const from = path.join(fromCache, HISTORY_DIR);
  if (!fs.existsSync(from)) {
    return;
  }
  for (const name of fs.readdirSync(from)) {
    const target = path.join(toCache, HISTORY_DIR, name);
    if (!fs.existsSync(target)) {
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.copyFileSync(path.join(from, name), target);
    }
  }
}

/** Make the work cache equal to the project cache. Results the project does not have are dropped. */
export function mirrorIn(layout: Layout): void {
  const { cache, work } = layout;
  fs.mkdirSync(work.cache, { recursive: true });
  const wanted = new Set(entryFiles(cache));
  for (const name of wanted) {
    copyIfDifferent(path.join(cache, name), path.join(work.cache, name));
  }
  for (const name of entryFiles(work.cache)) {
    if (!wanted.has(name)) {
      fs.rmSync(path.join(work.cache, name), { force: true });
    }
  }
}

/**
 * Copy the results of a run into the project cache. `baseline` is what the work cache held
 * before the run: a baseline entry that is gone now was moved or re-keyed by the server, so it
 * goes from the project too. Anything else in the project cache is never deleted.
 */
export function syncBack(layout: Layout, baseline: readonly string[]): void {
  const { cache, work } = layout;
  fs.mkdirSync(cache, { recursive: true });
  copyMissingHistory(work.cache, cache);
  const now = new Set(entryFiles(work.cache));
  for (const name of now) {
    copyIfDifferent(path.join(work.cache, name), path.join(cache, name));
  }
  for (const name of baseline) {
    if (!now.has(name)) {
      fs.rmSync(path.join(cache, name), { force: true });
    }
  }
}

const pendingPath = (layout: Layout) => path.join(layout.work.root, PENDING_FILE);

export function hasPending(layout: Layout): boolean {
  return fs.existsSync(pendingPath(layout));
}

function markPending(layout: Layout, baseline: readonly string[]): void {
  fs.mkdirSync(layout.work.root, { recursive: true });
  fs.writeFileSync(pendingPath(layout), JSON.stringify({ baseline }), 'utf8');
}

/** Retry a copy-back that failed earlier. Returns false when it still cannot be done. */
export function retryPending(layout: Layout): boolean {
  if (!hasPending(layout)) {
    return true;
  }
  let baseline: string[] = [];
  try {
    baseline = (JSON.parse(fs.readFileSync(pendingPath(layout), 'utf8')) as { baseline?: string[] }).baseline ?? [];
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

/** Bring the work cache up to date with the project; a no-op for managed projects. */
export function refreshWork(layout: Layout): void {
  if (!needsCacheSync(layout) || !retryPending(layout)) {
    return;
  }
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
  const sync = needsCacheSync(layout);
  const stage = needsStaging(layout);

  let baseline: string[] = [];
  if (sync) {
    if (!retryPending(layout)) {
      throw new Error(`Earlier results are waiting to be copied to ${layout.cache}, but that folder cannot be written.`);
    }
    mirrorIn(layout);
    baseline = entryFiles(layout.work.cache);
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
