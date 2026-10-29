import * as fs from 'node:fs';
import * as path from 'node:path';
import { readConfig, resolvePaths, resolvePath, writeConfig, type ProjectEntry } from './projects';

/**
 * Before the single mount, projects.json lived in the repository clone and every project had its
 * own mounted folders, defaulting to `<repo>/<name>/inputs` and `<repo>/.spec2test-data/<name>/…`.
 * Import it once: the inputs stay where they are, the old results move to where they live now.
 */
export function migrateLegacy(repoDir: string, root: string): string[] {
  const legacy = path.join(repoDir, 'projects.json');
  const target = path.join(root, 'projects.json');
  if (fs.existsSync(target) || !fs.existsSync(legacy)) {
    return [];
  }
  const old = readConfig(legacy);
  const notes: string[] = [];
  const projects = old.projects.map((entry): ProjectEntry => {
    const data = path.join(repoDir, '.spec2test-data', entry.name);
    const legacyInputs = resolvePath(entry.inputs, path.join(repoDir, entry.name, 'inputs'), repoDir);
    const legacyCache = resolvePath(entry.cache, path.join(data, 'cache'), repoDir);
    const legacyPre = resolvePath((entry as { preprocessed?: string }).preprocessed, path.join(data, 'preprocessed'), repoDir);

    const { preprocessed: _dropped, ...rest } = entry as ProjectEntry & { preprocessed?: string };
    const migrated: ProjectEntry = { ...rest };
    if (entry.inputs || fs.existsSync(legacyInputs)) {
      migrated.inputs = legacyInputs;
    }
    const paths = resolvePaths(migrated, root);
    if (!entry.cache) {
      copyMissing(legacyCache, paths.cache);
    }
    copyMissing(legacyPre, paths.preprocessed);
    notes.push(`Imported project '${entry.name}'.`);
    return migrated;
  });
  fs.mkdirSync(root, { recursive: true });
  writeConfig(target, { ...old, projects });
  return notes;
}

function copyMissing(from: string, to: string): void {
  if (!fs.existsSync(from) || path.resolve(from) === path.resolve(to)) {
    return;
  }
  fs.cpSync(from, to, { recursive: true, force: false, errorOnExist: false });
}
