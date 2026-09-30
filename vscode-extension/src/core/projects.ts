import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import type { LlmSettings } from '../shared/types';

export type { LlmSettings };

/** Same rule as input-processor/src/projects/model.py and scripts/sync_projects.py. */
export const NAME_RE = /^[a-z0-9][a-z0-9._-]*$/;

export interface ProjectEntry {
  name: string;
  inputs?: string;
  preprocessed?: string;
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

export class ProjectError extends Error {}

export function validateName(name: string): string | undefined {
  if (!NAME_RE.test(name)) {
    return 'Use lowercase letters, digits, dots, dashes or underscores, starting with a letter or digit.';
  }
  return undefined;
}

/** Host-side folders of a project: mirrors scripts/sync_projects.py `_project`. */
export function resolvePaths(entry: ProjectEntry, configDir: string): ProjectPaths {
  const fallback = path.join(configDir, '.spec2test-data', entry.name);
  return {
    inputs: resolve(entry.inputs, path.join(configDir, entry.name, 'inputs'), configDir),
    preprocessed: resolve(entry.preprocessed, path.join(fallback, 'preprocessed'), configDir),
    cache: resolve(entry.cache, path.join(fallback, 'cache'), configDir),
  };
}

/** The features folder, or undefined when the project has none (there is no default). */
export function resolveFeatures(entry: ProjectEntry, configDir: string): string | undefined {
  return (entry.features ?? '').trim() ? resolve(entry.features, '', configDir) : undefined;
}

function resolve(raw: string | undefined, fallback: string, base: string): string {
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
