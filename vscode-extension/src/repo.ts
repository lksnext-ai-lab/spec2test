import * as fs from 'node:fs';
import * as path from 'node:path';

const MARKERS = ['docker-compose.yaml', path.join('scripts', 'sync_projects.py'), 'input-processor'];

export function isRepo(dir: string): boolean {
  return MARKERS.every((marker) => fs.existsSync(path.join(dir, marker)));
}

/** The configured folder if valid, else the first of `candidates` (or its parents) that looks like the repo. */
export function findRepo(configured: string, candidates: string[]): string | undefined {
  if (configured.trim() && isRepo(configured.trim())) {
    return path.resolve(configured.trim());
  }
  for (const candidate of candidates) {
    let dir = path.resolve(candidate);
    for (let depth = 0; depth < 4; depth += 1) {
      if (isRepo(dir)) {
        return dir;
      }
      const parent = path.dirname(dir);
      if (parent === dir) {
        break;
      }
      dir = parent;
    }
    // A workspace that contains the repo as a direct child (a monorepo of projects).
    const nested = path.join(candidate, 'spec2test');
    if (isRepo(nested)) {
      return nested;
    }
  }
  return undefined;
}
