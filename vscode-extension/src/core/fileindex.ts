import * as crypto from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';
import type { CacheState, FileCard, HistoryItem, OrphanCard } from '../shared/types';
import type { ProjectPaths } from './projects';

export type { CacheState, FileCard, HistoryItem, OrphanCard };

export const SUPPORTED = ['.mp4', '.pdf', '.md', '.txt'];
export const HISTORY_DIR = '.history';

export interface CacheEntry {
  source: string;
  sha256: string;
  processedAt?: string;
  provider?: string;
  model?: string;
}

export interface Outputs {
  original: string;
  cache: string;
  preprocessed: string;
  images: string;
}

export function isSupported(name: string): boolean {
  return SUPPORTED.includes(path.extname(name).toLowerCase());
}

/** Where every artefact of `name` lives on the host: inputs/X -> cache/X.md, preprocessed/X.md, preprocessed/X_images/. */
export function outputsOf(paths: ProjectPaths, name: string): Outputs {
  return {
    original: path.join(paths.inputs, name),
    cache: path.join(paths.cache, `${name}.md`),
    preprocessed: path.join(paths.preprocessed, `${name}.md`),
    images: path.join(paths.preprocessed, `${name}_images`),
  };
}

/** Read the YAML front-matter the input-processor writes at the top of every cache file. */
export function parseFrontMatter(text: string): Record<string, string> {
  const lines = text.split(/\r?\n/);
  if (lines[0]?.trim() !== '---') {
    return {};
  }
  const values: Record<string, string> = {};
  for (const line of lines.slice(1)) {
    if (line.trim() === '---') {
      break;
    }
    const match = /^([A-Za-z_][\w-]*):\s*(\S.*)?$/.exec(line);
    if (match) {
      values[match[1]] = (match[2] ?? '').trim().replace(/^(["'])(.*)\1$/, '$2');
    }
  }
  return values;
}

function readHead(file: string, bytes = 4096): string {
  const fd = fs.openSync(file, 'r');
  try {
    const buffer = Buffer.alloc(bytes);
    const read = fs.readSync(fd, buffer, 0, bytes, 0);
    return buffer.toString('utf8', 0, read);
  } finally {
    fs.closeSync(fd);
  }
}

export function readCacheEntries(cacheDir: string): CacheEntry[] {
  if (!fs.existsSync(cacheDir)) {
    return [];
  }
  const entries: CacheEntry[] = [];
  for (const item of fs.readdirSync(cacheDir, { withFileTypes: true })) {
    if (!item.isFile() || item.name.startsWith('.') || !item.name.endsWith('.md')) {
      continue;
    }
    const source = item.name.slice(0, -3);
    if (!isSupported(source)) {
      continue;
    }
    const meta = parseFrontMatter(readHead(path.join(cacheDir, item.name)));
    if (meta.sha256) {
      entries.push({
        source: meta.source || source,
        sha256: meta.sha256,
        processedAt: meta.processed_at,
        provider: meta.provider,
        model: meta.model,
      });
    }
  }
  return entries;
}

export function listHistory(cacheDir: string, name: string): HistoryItem[] {
  const dir = path.join(cacheDir, HISTORY_DIR);
  if (!fs.existsSync(dir)) {
    return [];
  }
  const pattern = /^[0-9a-f]{8}\.(\d{8}T\d{6}Z)(?:-\d+)?\.md$/;
  return fs
    .readdirSync(dir)
    .filter((file) => file.startsWith(`${name}.`) && pattern.test(file.slice(name.length + 1)))
    .sort((a, b) => a.localeCompare(b))
    .reverse()
    .map((file) => {
      const stamp = pattern.exec(file.slice(name.length + 1))![1];
      const label = `${stamp.slice(0, 4)}-${stamp.slice(4, 6)}-${stamp.slice(6, 8)} ${stamp.slice(9, 11)}:${stamp.slice(11, 13)}:${stamp.slice(13, 15)}`;
      return { path: path.join(dir, file), label };
    });
}

/** The supported input file names directly inside `inputs`, sorted with localeCompare. */
export function listInputNames(inputs: string): string[] {
  if (!fs.existsSync(inputs)) {
    return [];
  }
  return fs
    .readdirSync(inputs, { withFileTypes: true })
    .filter((item) => item.isFile() && isSupported(item.name))
    .map((item) => item.name)
    .sort((a, b) => a.localeCompare(b));
}

export interface InputMatch {
  state: CacheState;
  /** The cache entry supplying the metadata: the input's own entry, or the twin it renames. */
  entry?: CacheEntry;
  /** The twin entry that a renamed input takes over, so its source is re-keyed. */
  rekeyed?: CacheEntry;
}

/** Relate one input to the cache: its own entry, a renamed twin (same hash and extension), or nothing. */
export function classifyInput(
  name: string,
  sha: string,
  bySource: Map<string, CacheEntry>,
  bySha: Map<string, CacheEntry>,
): InputMatch {
  const own = bySource.get(name);
  if (own) {
    return { state: own.sha256 === sha ? 'cached' : 'stale', entry: own };
  }
  const twin = bySha.get(sha);
  if (twin && path.extname(twin.source).toLowerCase() === path.extname(name).toLowerCase()) {
    return { state: 'renamed', entry: twin, rekeyed: twin };
  }
  return { state: 'new' };
}

function buildFileCard(
  paths: ProjectPaths,
  name: string,
  outputs: Outputs,
  size: number,
  match: InputMatch,
): FileCard {
  return {
    name,
    format: path.extname(name).toLowerCase(),
    size,
    state: match.state,
    processedAt: match.entry?.processedAt,
    provider: match.entry?.provider,
    model: match.entry?.model,
    hasCache: fs.existsSync(outputs.cache),
    hasPreprocessed: fs.existsSync(outputs.preprocessed),
    hasImages: fs.existsSync(outputs.images),
    history: listHistory(paths.cache, name),
  };
}

function findOrphans(entries: CacheEntry[], names: string[], rekeyed: Set<string>): OrphanCard[] {
  const present = new Set(names);
  return (
    entries
      // A result that a renamed file will take over on the next run is not abandoned.
      .filter((entry) => !present.has(entry.source) && !rekeyed.has(entry.source))
      .map((entry) => ({ name: entry.source, processedAt: entry.processedAt }))
  );
}

export class FileIndex {
  private readonly hashes = new Map<string, { size: number; mtimeMs: number; sha: string }>();

  constructor(private paths: ProjectPaths) {}

  setPaths(paths: ProjectPaths): void {
    this.paths = paths;
  }

  async sha256(file: string): Promise<string> {
    const stat = fs.statSync(file);
    const known = this.hashes.get(file);
    if (known?.size === stat.size && known.mtimeMs === stat.mtimeMs) {
      return known.sha;
    }
    const sha = await new Promise<string>((resolve, reject) => {
      const hash = crypto.createHash('sha256');
      fs.createReadStream(file)
        .on('data', (chunk) => hash.update(chunk))
        .on('end', () => resolve(hash.digest('hex')))
        .on('error', reject);
    });
    this.hashes.set(file, { size: stat.size, mtimeMs: stat.mtimeMs, sha });
    return sha;
  }

  /** The input files with their cache state, plus cache entries whose source is gone. */
  async scan(): Promise<{ files: FileCard[]; orphans: OrphanCard[] }> {
    const { inputs, cache } = this.paths;
    const names = listInputNames(inputs);

    const entries = readCacheEntries(cache);
    const bySource = new Map(entries.map((entry) => [entry.source, entry]));
    const bySha = new Map(entries.map((entry) => [entry.sha256, entry]));

    const files: FileCard[] = [];
    const rekeyed = new Set<string>();
    for (const name of names) {
      const outputs = outputsOf(this.paths, name);
      const size = fs.statSync(outputs.original).size;
      const sha = await this.sha256(outputs.original);
      const match = classifyInput(name, sha, bySource, bySha);
      if (match.rekeyed) {
        rekeyed.add(match.rekeyed.source);
      }
      files.push(buildFileCard(this.paths, name, outputs, size, match));
    }

    return { files, orphans: findOrphans(entries, names, rekeyed) };
  }

  /** Move a cache entry to `.history` (never deletes it). Returns the archive path. */
  archiveCache(name: string, now: Date = new Date()): string | undefined {
    const { cache } = this.paths;
    const file = outputsOf(this.paths, name).cache;
    if (!fs.existsSync(file)) {
      return undefined;
    }
    const meta = parseFrontMatter(readHead(file));
    const sha8 = (meta.sha256 ?? '00000000').slice(0, 8);
    const stamp = now.toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
    const dir = path.join(cache, HISTORY_DIR);
    fs.mkdirSync(dir, { recursive: true });
    let target = path.join(dir, `${name}.${sha8}.${stamp}.md`);
    for (let n = 1; fs.existsSync(target); n += 1) {
      target = path.join(dir, `${name}.${sha8}.${stamp}-${n}.md`);
    }
    fs.renameSync(file, target);
    return target;
  }
}

/** Copy `source` into `inputsDir`; `mode` decides what happens when the name is taken. */
export function copyIntoInputs(
  source: string,
  inputsDir: string,
  mode: 'replace' | 'keep-both' | 'skip',
): { target: string; copied: boolean } {
  fs.mkdirSync(inputsDir, { recursive: true });
  const name = path.basename(source);
  let target = path.join(inputsDir, name);
  if (fs.existsSync(target)) {
    if (mode === 'skip') {
      return { target, copied: false };
    }
    if (mode === 'keep-both') {
      const { name: stem, ext } = path.parse(name);
      for (let n = 2; fs.existsSync(target); n += 1) {
        target = path.join(inputsDir, `${stem} (${n})${ext}`);
      }
    }
  }
  fs.copyFileSync(source, target);
  return { target, copied: true };
}
