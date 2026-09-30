import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { ProjectError, addProject, readConfig, removeProject, resolveFeatures, resolvePaths, setModel, updateProject, validateName, writeConfig } from '../src/core/projects';

describe('validateName', () => {
  it.each(['shop-app', 'a', 'app.v2', 'x_1'])('accepts %s', (name) => expect(validateName(name)).toBeUndefined());
  it.each(['', 'Shop', '-x', 'has space', '.hidden', 'a/b'])('rejects %j', (name) => expect(validateName(name)).toBeDefined());
});

describe('resolvePaths (mirrors scripts/sync_projects.py)', () => {
  const dir = path.resolve('/cfg');

  it('defaults inputs next to the config and outputs under .spec2test-data', () => {
    expect(resolvePaths({ name: 'shop' }, dir)).toEqual({
      inputs: path.join(dir, 'shop', 'inputs'),
      preprocessed: path.join(dir, '.spec2test-data', 'shop', 'preprocessed'),
      cache: path.join(dir, '.spec2test-data', 'shop', 'cache'),
    });
  });

  it('keeps absolute paths and resolves relative ones against the config folder', () => {
    const resolved = resolvePaths({ name: 'a', inputs: '/abs/specs', cache: 'data/cache' }, dir);
    expect(resolved.inputs).toBe(path.resolve('/abs/specs'));
    expect(resolved.cache).toBe(path.join(dir, 'data', 'cache'));
  });

  it('expands ~', () => {
    expect(resolvePaths({ name: 'a', inputs: '~/specs' }, dir).inputs).toBe(path.join(os.homedir(), 'specs'));
  });
});

describe('config editing', () => {
  const base = { projects: [{ name: 'a' }] };

  it('adds, updates and removes without mutating the input', () => {
    const added = addProject(base, { name: 'b', inputs: '/x' });
    expect(added.projects.map((p) => p.name)).toEqual(['a', 'b']);
    expect(base.projects).toHaveLength(1);
    expect(updateProject(added, 'b', { cache: '/c' }).projects[1]).toMatchObject({ name: 'b', cache: '/c' });
    expect(removeProject(added, 'a').projects.map((p) => p.name)).toEqual(['b']);
  });

  it('refuses duplicates, bad names and unknown projects', () => {
    expect(() => addProject(base, { name: 'a' })).toThrow(ProjectError);
    expect(() => addProject(base, { name: 'Bad Name' })).toThrow(/Invalid project name/);
    expect(() => updateProject(base, 'zzz', {})).toThrow(/Unknown project/);
  });

  it('sets and clears model blocks for a project or the defaults', () => {
    const project = setModel(base, { project: 'a' }, 'llm', { provider: 'openai', model: 'gpt-4o' });
    expect(project.projects[0].llm).toEqual({ provider: 'openai', model: 'gpt-4o' });
    expect(setModel(project, { project: 'a' }, 'llm', undefined).projects[0].llm).toBeUndefined();
    expect(setModel(base, {}, 'vision', { provider: 'google_genai' }).defaults?.vision).toEqual({ provider: 'google_genai' });
    expect(setModel(base, {}, 'vision', {}).defaults?.vision).toBeUndefined();
  });
});

describe('config files', () => {
  it('reads a missing file as empty and round-trips', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 's2t-'));
    const file = path.join(dir, 'projects.json');
    expect(readConfig(file)).toEqual({ projects: [] });
    writeConfig(file, { defaults: { llm: { provider: 'openai' } }, projects: [{ name: 'a' }] });
    expect(readConfig(file).projects[0].name).toBe('a');
    fs.writeFileSync(file, '{ nope');
    expect(() => readConfig(file)).toThrow(/not valid JSON/);
  });
});

describe('resolveFeatures', () => {
  const dir = path.resolve('/cfg');

  it('has no default: a project without a features folder has none', () => {
    expect(resolveFeatures({ name: 'a' }, dir)).toBeUndefined();
    expect(resolveFeatures({ name: 'a', features: '  ' }, dir)).toBeUndefined();
  });

  it('resolves like the other folders', () => {
    expect(resolveFeatures({ name: 'a', features: '/abs/features' }, dir)).toBe(path.resolve('/abs/features'));
    expect(resolveFeatures({ name: 'a', features: 'gherkin' }, dir)).toBe(path.join(dir, 'gherkin'));
    expect(resolveFeatures({ name: 'a', features: '~/f' }, dir)).toBe(path.join(os.homedir(), 'f'));
  });

  it('is kept when other fields of the project change', () => {
    const config = updateProject({ projects: [{ name: 'a', features: '/f' }] }, 'a', { cache: '/c' });
    expect(config.projects[0].features).toBe('/f');
  });
});
