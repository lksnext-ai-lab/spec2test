import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { ProjectError, addProject, readConfig, removeProject, resolveFeatures, resolvePaths, setModel, updateProject, validateName, workAreaOf, writeConfig } from '../src/core/projects';

describe('validateName', () => {
  it.each(['shop-app', 'a', 'app.v2', 'x_1'])('accepts %s', (name) => expect(validateName(name)).toBeUndefined());
  it.each(['', 'Shop', '-x', 'has space', '.hidden', 'a/b', 'projects.json'])('rejects %j', (name) => expect(validateName(name)).toBeDefined());
});

describe('resolvePaths', () => {
  const root = path.resolve('/cfg');

  it('a project without folders is managed: everything lives in the work area', () => {
    expect(resolvePaths({ name: 'shop' }, root)).toEqual({
      inputs: path.join(root, 'shop', 'inputs'),
      preprocessed: path.join(root, 'shop', 'preprocessed'),
      cache: path.join(root, 'shop', 'cache'),
    });
  });

  it('puts the cache of an outside inputs folder next to it, and pre-processed files in the work area', () => {
    expect(resolvePaths({ name: 'a', inputs: '/abs/specs' }, root)).toEqual({
      inputs: path.resolve('/abs/specs'),
      preprocessed: path.join(root, 'a', 'preprocessed'),
      cache: path.join(path.resolve('/abs/specs'), '.spec2test', 'cache'),
    });
  });

  it('keeps absolute paths and resolves relative ones against the data folder', () => {
    const resolved = resolvePaths({ name: 'a', inputs: '/abs/specs', cache: 'data/cache' }, root);
    expect(resolved.cache).toBe(path.join(root, 'data', 'cache'));
  });

  it('expands ~', () => {
    expect(resolvePaths({ name: 'a', inputs: '~/specs' }, root).inputs).toBe(path.join(os.homedir(), 'specs'));
  });

  it('lays out the work area under the data folder', () => {
    expect(workAreaOf(root, 'a')).toEqual({
      root: path.join(root, 'a'),
      inputs: path.join(root, 'a', 'inputs'),
      preprocessed: path.join(root, 'a', 'preprocessed'),
      cache: path.join(root, 'a', 'cache'),
    });
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
