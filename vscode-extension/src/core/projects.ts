import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import type { LlmSettings } from '../shared/types';

export type { LlmSettings };

/** Same rule as input-processor/src/projects/model.py. */
export const NAME_RE = /^[a-z0-9][a-z0-9._-]*$/;

/** Folder inside a project's inputs folder that holds its results (`<inputs>/.spec2test/cache`). */
export const PROJECT_DATA_DIRNAME = '.spec2test';

let chosenRoot = '';

/** The folder from the `spec2test.dataFolder` setting; empty means the default. Relative paths are ignored. */
export function setDataRoot(value: string | undefined): void {
  const text = (value ?? '').trim();
  const expanded = text === '~' || text.startsWith('~/') || text.startsWith('~\\') ? path.join(os.homedir(), text.slice(1)) : text;
  chosenRoot = path.isAbsolute(expanded) ? path.resolve(expanded) : '';
}

export function defaultDataRoot(): string {
  return path.resolve(process.env.SPEC2TEST_HOME?.trim() || path.join(os.homedir(), '.spec2test'));
}

/** The one folder the container mounts: projects.json plus a work area per project. */
export function dataRoot(): string {
  return chosenRoot || defaultDataRoot();
}

export interface ProjectEntry {
  name: string;
  /** Host folder with the files to process. Left untouched; files are staged in the work area. */
  inputs?: string;
  /** Host folder for the processed results. Defaults to `<inputs>/.spec2test/cache`. */
  cache?: string;
  /** Host-only: where the .feature files are. Never mounted into Docker. */
  features?: string;
  llm?: LlmSettings;
  vision?: LlmSettings;
}

export interface ProjectsConfig {
  defaults?: { llm?: LlmSettings; vision?: LlmSettings };
  projects: ProjectEntry[];
}

export interface ProjectPaths {
  inputs: string;
  preprocessed: string;
  cache: string;
}

/** Where the container sees a project: `<root>/<name>/{inputs,preprocessed,cache}`. Disposable. */
export interface WorkArea {
  root: string;
  inputs: string;
  preprocessed: string;
  cache: string;
}

export class ProjectError extends Error {}

export function validateName(name: string): string | undefined {
  if (name === 'projects.json') {
    return 'That name is reserved for the configuration file.';
  }
  if (!NAME_RE.test(name)) {
    return 'Use lowercase letters, digits, dots, dashes or underscores, starting with a letter or digit.';
  }
  return undefined;
}

export function workAreaOf(root: string, name: string): WorkArea {
  const base = path.join(root, name);
  return {
    root: base,
    inputs: path.join(base, 'inputs'),
    preprocessed: path.join(base, 'preprocessed'),
    cache: path.join(base, 'cache'),
  };
}

/**
 * Host-side folders of a project, as the user sees them: `inputs` and `cache` are the user's
 * folders, `preprocessed` always lives in the work area. Without an inputs folder the project is
 * "managed": it lives entirely in the work area and nothing is staged or copied back.
 */
export function resolvePaths(entry: ProjectEntry, root: string): ProjectPaths {
  const work = workAreaOf(root, entry.name);
  const inputs = resolvePath(entry.inputs, work.inputs, root);
  const cacheFallback = inputs === path.resolve(work.inputs) ? work.cache : path.join(inputs, PROJECT_DATA_DIRNAME, 'cache');
  return { inputs, preprocessed: work.preprocessed, cache: resolvePath(entry.cache, cacheFallback, root) };
}

/** The features folder, or undefined when the project has none (there is no default). */
export function resolveFeatures(entry: ProjectEntry, configDir: string): string | undefined {
  return (entry.features ?? '').trim() ? resolvePath(entry.features, '', configDir) : undefined;
}

export function resolvePath(raw: string | undefined, fallback: string, base: string): string {
  const value = (raw ?? '').trim();
  if (!value) {
    return path.resolve(fallback);
  }
  const expanded = value === '~' || value.startsWith('~/') ? path.join(os.homedir(), value.slice(1)) : value;
  return path.resolve(path.isAbsolute(expanded) ? expanded : path.join(base, expanded));
}

export function readConfig(file: string): ProjectsConfig {
  if (!fs.existsSync(file)) {
    return { projects: [] };
  }
  let raw: unknown;
  try {
    raw = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    throw new ProjectError(`${file} is not valid JSON: ${(error as Error).message}`);
  }
  const config = raw as Partial<ProjectsConfig>;
  return { ...config, projects: Array.isArray(config.projects) ? config.projects : [] };
}

export function writeConfig(file: string, config: ProjectsConfig): void {
  fs.writeFileSync(file, JSON.stringify(config, null, 2) + '\n', 'utf8');
}

export function addProject(config: ProjectsConfig, entry: ProjectEntry): ProjectsConfig {
  const problem = validateName(entry.name);
  if (problem) {
    throw new ProjectError(`Invalid project name '${entry.name}'. ${problem}`);
  }
  if (config.projects.some((project) => project.name === entry.name)) {
    throw new ProjectError(`Project '${entry.name}' already exists.`);
  }
  return { ...config, projects: [...config.projects, entry] };
}

export function updateProject(
  config: ProjectsConfig,
  name: string,
  patch: Partial<Omit<ProjectEntry, 'name'>>,
): ProjectsConfig {
  if (!config.projects.some((project) => project.name === name)) {
    throw new ProjectError(`Unknown project '${name}'.`);
  }
  return {
    ...config,
    projects: config.projects.map((project) => (project.name === name ? { ...project, ...patch } : project)),
  };
}

export function removeProject(config: ProjectsConfig, name: string): ProjectsConfig {
  return { ...config, projects: config.projects.filter((project) => project.name !== name) };
}

/** Set (or clear, with `undefined`) one model block, for the defaults or for a project. */
export function setModel(
  config: ProjectsConfig,
  scope: { project?: string },
  kind: 'llm' | 'vision',
  value: LlmSettings | undefined,
): ProjectsConfig {
  const cleaned = value && (value.provider || value.model) ? value : undefined;
  if (scope.project) {
    return updateProject(config, scope.project, { [kind]: cleaned });
  }
  return { ...config, defaults: { ...config.defaults, [kind]: cleaned } };
}
