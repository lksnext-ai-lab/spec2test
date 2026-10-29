import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { Controller } from '../src/controller';
import { setDataRoot, writeConfig, type ProjectEntry } from '../src/core/projects';
import { Uri, fake, window } from './support/vscode';

/**
 * Regression tests for the parts of the Controller that are about to be refactored
 * (addUris, changeDataFolder, projectForFeature, buildState). They run against a fake `vscode`.
 */
const memento = () => {
  const values = new Map<string, unknown>();
  return {
    get: <T>(key: string, fallback?: T) => (values.has(key) ? (values.get(key) as T) : fallback),
    update: async (key: string, value: unknown) => {
      values.set(key, value);
    },
    keys: () => [...values.keys()],
  };
};

const makeContext = () => ({
  subscriptions: [] as { dispose(): void }[],
  secrets: { get: async () => undefined, store: async () => undefined, delete: async () => undefined },
  globalState: memento(),
  workspaceState: memento(),
  extensionPath: path.resolve(__dirname, '..'),
  extension: { packageJSON: { version: '0.1.0' } },
  globalStorageUri: { fsPath: os.tmpdir() },
});

let root: string;
let data: string;
let controller: Controller;
const originalHome = process.env.SPEC2TEST_HOME;

const write = (file: string, text = 'x') => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, text);
};

function save(projects: ProjectEntry[]): void {
  fs.mkdirSync(data, { recursive: true });
  writeConfig(path.join(data, 'projects.json'), { projects });
}

function make(): Controller {
  return new Controller(makeContext() as never);
}

beforeEach(() => {
  root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 's2t-ctl-')));
  data = path.join(root, 'data');
  process.env.SPEC2TEST_HOME = data;
  setDataRoot('');
  fake.reset();
});

afterEach(() => {
  controller?.dispose();
  setDataRoot('');
  if (originalHome === undefined) {
    delete process.env.SPEC2TEST_HOME;
  } else {
    process.env.SPEC2TEST_HOME = originalHome;
  }
});

describe('projectForFeature', () => {
  const inputs = () => path.join(root, 'specs');
  const features = () => path.join(root, 'features', 'shop');

  beforeEach(() => {
    write(path.join(inputs(), 'a.md'));
    write(path.join(inputs(), 'b.pdf'));
    write(path.join(inputs(), 'notes.docx'));
    write(path.join(inputs(), '.spec2test', 'cache', 'a.md.md'), '---\nsource: a.md\nsha256: 1\n---\n');
    write(path.join(features(), 'login.feature'));
    save([{ name: 'shop', inputs: inputs(), features: features() }]);
    controller = make();
  });

  it('describes the inputs of the project whose features folder holds the file', () => {
    const found = controller.projectForFeature(path.join(features(), 'login.feature'));
    expect(found?.project).toBe('shop');
    expect([...found!.inputs.entries()].sort()).toEqual([
      ['a.md', { processed: true }],
      ['b.pdf', { processed: false }],
    ]);
    expect(found!.cited.size).toBe(0);
  });

  it('finds files in subfolders and the folder itself', () => {
    expect(controller.projectForFeature(path.join(features(), 'deep', 'x.feature'))?.project).toBe('shop');
    expect(controller.projectForFeature(features())?.project).toBe('shop');
  });

  it('does not match a sibling folder that only shares the prefix', () => {
    expect(controller.projectForFeature(path.join(root, 'features', 'shop-other', 'x.feature'))).toBeUndefined();
    expect(controller.projectForFeature(path.join(root, 'elsewhere', 'x.feature'))).toBeUndefined();
  });

  it('picks the right project among several and ignores those without a features folder', () => {
    const other = path.join(root, 'features', 'admin');
    save([
      { name: 'plain', inputs: path.join(root, 'plain') },
      { name: 'shop', inputs: inputs(), features: features() },
      { name: 'admin', inputs: path.join(root, 'admin'), features: other },
    ]);
    expect(controller.projectForFeature(path.join(other, 'x.feature'))?.project).toBe('admin');
    expect(controller.projectForFeature(path.join(features(), 'x.feature'))?.project).toBe('shop');
  });

  it('reports no inputs when the inputs folder does not exist yet', () => {
    save([{ name: 'shop', inputs: path.join(root, 'missing'), features: features() }]);
    expect(controller.projectForFeature(path.join(features(), 'x.feature'))?.inputs.size).toBe(0);
  });
});

describe('addUris', () => {
  const inputs = () => path.join(root, 'specs');
  const quickPick = (value: 'replace' | 'keep-both' | 'skip' | undefined) =>
    window.showQuickPick.mockResolvedValue(value ? { value } : undefined);
  const names = () => fs.readdirSync(inputs()).filter((name) => !name.startsWith('.')).sort();

  beforeEach(() => {
    fs.mkdirSync(inputs(), { recursive: true });
    save([{ name: 'shop', inputs: inputs() }]);
    controller = make();
  });

  it('asks for a project first when there is none', async () => {
    save([]);
    await controller.addUris([Uri.file(path.join(root, 'a.md')) as never]);
    expect(window.showWarningMessage).toHaveBeenCalledWith('Create or select a project before adding files.');
  });

  it('copies supported files and reports the unsupported ones', async () => {
    write(path.join(root, 'in', 'a.md'));
    write(path.join(root, 'in', 'b.docx'));
    await controller.addUris([Uri.file(path.join(root, 'in', 'a.md')), Uri.file(path.join(root, 'in', 'b.docx'))] as never);
    expect(names()).toEqual(['a.md']);
    expect(window.showWarningMessage).toHaveBeenCalledWith(expect.stringContaining('b.docx'));
    expect(window.showInformationMessage).toHaveBeenCalledWith("Added 1 file(s) to 'shop'.", 'Process now');
  });

  it('takes the files of a dropped folder, not its subfolders', async () => {
    write(path.join(root, 'in', 'a.pdf'));
    write(path.join(root, 'in', 'sub', 'deep.pdf'));
    write(path.join(root, 'in', 'c.zip'));
    await controller.addUris([Uri.file(path.join(root, 'in'))] as never);
    expect(names()).toEqual(['a.pdf']);
    expect(window.showWarningMessage).toHaveBeenCalledWith(expect.stringContaining('c.zip'));
  });

  it('rejects things that are not local files and paths that do not exist', async () => {
    await controller.addUris([Uri.parse('https://example.com/x.pdf'), Uri.file(path.join(root, 'ghost.md'))] as never);
    expect(names()).toEqual([]);
    expect(window.showWarningMessage).toHaveBeenCalledWith(expect.stringContaining('https://example.com/x.pdf'));
    expect(window.showQuickPick).not.toHaveBeenCalled();
  });

  it('does nothing, and does not prompt, when no file is supported', async () => {
    write(path.join(root, 'in', 'x.exe'));
    await controller.addUris([Uri.file(path.join(root, 'in', 'x.exe'))] as never);
    expect(names()).toEqual([]);
    expect(window.showInformationMessage).not.toHaveBeenCalled();
  });

  describe('when a file of the same name is already there', () => {
    beforeEach(() => {
      write(path.join(inputs(), 'a.md'), 'old');
      write(path.join(root, 'in', 'a.md'), 'new');
    });
    const add = () => controller.addUris([Uri.file(path.join(root, 'in', 'a.md'))] as never);

    it('replaces it when asked to', async () => {
      quickPick('replace');
      await add();
      expect(fs.readFileSync(path.join(inputs(), 'a.md'), 'utf8')).toBe('new');
    });

    it('keeps both under a numbered name', async () => {
      quickPick('keep-both');
      await add();
      expect(names()).toEqual(['a (2).md', 'a.md']);
      expect(fs.readFileSync(path.join(inputs(), 'a.md'), 'utf8')).toBe('old');
    });

    it('leaves the existing file when told to skip, and says nothing was added', async () => {
      quickPick('skip');
      await add();
      expect(fs.readFileSync(path.join(inputs(), 'a.md'), 'utf8')).toBe('old');
      expect(window.showInformationMessage).not.toHaveBeenCalled();
    });

    it('does nothing when the question is dismissed', async () => {
      quickPick(undefined);
      await add();
      expect(fs.readFileSync(path.join(inputs(), 'a.md'), 'utf8')).toBe('old');
      expect(names()).toEqual(['a.md']);
    });
  });
});

describe('changeDataFolder', () => {
  const pick = (target: string | undefined) => window.showOpenDialog.mockResolvedValue(target ? [Uri.file(target)] : undefined);
  const answer = (button: string | undefined) => window.showWarningMessage.mockResolvedValue(button);

  beforeEach(() => {
    save([{ name: 'shop' }]);
    write(path.join(data, 'shop', 'cache', 'a.md.md'), 'cached');
    controller = make();
  });

  it('does nothing when the folder dialog is dismissed', async () => {
    pick(undefined);
    await controller.changeDataFolder();
    expect(fake.updates).toEqual([]);
  });

  it('does nothing when the chosen folder is the current one', async () => {
    pick(data);
    await controller.changeDataFolder();
    expect(fake.updates).toEqual([]);
    expect(window.showWarningMessage).not.toHaveBeenCalled();
  });

  it.each([
    ['inside the current folder', () => path.join(data, 'sub')],
    ['around the current folder', () => root],
  ])('refuses a folder %s', async (_label, target) => {
    pick(target());
    await controller.changeDataFolder();
    expect(window.showErrorMessage).toHaveBeenCalledWith(expect.stringContaining('inside each other'));
    expect(fake.updates).toEqual([]);
  });

  it('copies the projects along when asked, then saves the setting', async () => {
    const target = path.join(root, 'moved');
    pick(target);
    answer('Copy and switch');
    await controller.changeDataFolder();
    expect(fs.existsSync(path.join(target, 'projects.json'))).toBe(true);
    expect(fs.readFileSync(path.join(target, 'shop', 'cache', 'a.md.md'), 'utf8')).toBe('cached');
    expect(fs.existsSync(path.join(data, 'projects.json'))).toBe(true);
    expect(fake.updates).toEqual([{ key: 'dataFolder', value: target }]);
  });

  it('switches to an empty folder without copying', async () => {
    const target = path.join(root, 'fresh');
    pick(target);
    answer('Switch without copying');
    await controller.changeDataFolder();
    expect(fs.existsSync(target)).toBe(true);
    expect(fs.existsSync(path.join(target, 'projects.json'))).toBe(false);
    expect(fake.updates).toEqual([{ key: 'dataFolder', value: target }]);
  });

  it('warns that a non-empty folder will receive files', async () => {
    const target = path.join(root, 'busy');
    write(path.join(target, 'unrelated.txt'));
    pick(target);
    answer('Copy and switch');
    await controller.changeDataFolder();
    expect(window.showWarningMessage.mock.calls[0][1].detail).toContain('not empty');
  });

  it('uses the projects already in the chosen folder and copies nothing', async () => {
    const target = path.join(root, 'existing');
    write(path.join(target, 'projects.json'), '{"projects":[]}');
    pick(target);
    answer('Use it');
    await controller.changeDataFolder();
    expect(fs.readFileSync(path.join(target, 'projects.json'), 'utf8')).toBe('{"projects":[]}');
    expect(fs.existsSync(path.join(target, 'shop'))).toBe(false);
    expect(fake.updates).toEqual([{ key: 'dataFolder', value: target }]);
  });

  it('changes nothing when the confirmation is dismissed', async () => {
    const target = path.join(root, 'never');
    pick(target);
    answer(undefined);
    await controller.changeDataFolder();
    expect(fs.existsSync(target)).toBe(false);
    expect(fake.updates).toEqual([]);
  });

  it('goes back to the default by clearing the setting', async () => {
    const custom = path.join(root, 'custom');
    write(path.join(custom, 'projects.json'), '{"projects":[]}');
    fake.settings.set('dataFolder', custom);
    setDataRoot(custom);
    answer('Copy and switch');
    await controller.changeDataFolder(true);
    expect(fake.updates).toEqual([{ key: 'dataFolder', value: undefined }]);
    expect(fs.existsSync(path.join(data, 'projects.json'))).toBe(true);
  });

  it('refuses while a job is running', async () => {
    (controller as unknown as { queue: { busy: boolean; cancel(): void } }).queue = { busy: true, cancel: () => undefined };
    pick(path.join(root, 'later'));
    await controller.changeDataFolder();
    expect(window.showWarningMessage).toHaveBeenCalledWith(expect.stringContaining('running job'));
    expect(window.showOpenDialog).not.toHaveBeenCalled();
  });
});

describe('buildState', () => {
  it('lists projects with their display names and picks the first when none is stored', () => {
    save([
      { name: 'shop-app', title: 'Shop App', inputs: path.join(root, 's') },
      { name: 'admin', inputs: path.join(root, 'a') },
    ]);
    controller = make();
    const state = controller.buildState();
    expect(state.projects.map((project) => [project.name, project.title])).toEqual([
      ['shop-app', 'Shop App'],
      ['admin', 'admin'],
    ]);
    expect(state.selected).toBe('shop-app');
    expect(state.dataFolder).toEqual({ path: data, isDefault: true });
    expect(state.docker.state).toBe('stopped');
  });

  it('flags a custom data folder', () => {
    setDataRoot(path.join(root, 'elsewhere'));
    controller = make();
    expect(controller.buildState().dataFolder).toEqual({ path: path.join(root, 'elsewhere'), isDefault: false });
  });
});
