import { vi } from 'vitest';

/**
 * A just-enough stand-in for the `vscode` module so the Controller can run under vitest.
 * Tests drive it through `fake`: preset the answers of dialogs, read back what was shown or saved.
 */
export const fake = {
  settings: new Map<string, unknown>(),
  workspaceFolders: undefined as { uri: { fsPath: string }; name: string }[] | undefined,
  updates: [] as { key: string; value: unknown }[],
  reset(): void {
    this.settings.clear();
    this.updates.length = 0;
    this.workspaceFolders = undefined;
    for (const fn of [window.showInformationMessage, window.showWarningMessage, window.showErrorMessage, window.showQuickPick, window.showOpenDialog, window.showInputBox, commands.executeCommand]) {
      fn.mockReset();
    }
  },
};

export class EventEmitter<T> {
  private listeners: ((value: T) => void)[] = [];
  event = (listener: (value: T) => void) => {
    this.listeners.push(listener);
    return { dispose: () => undefined };
  };
  fire(value: T): void {
    this.listeners.forEach((listener) => listener(value));
  }
  dispose(): void {}
}

export const Uri = {
  file: (fsPath: string) => ({ scheme: 'file', fsPath, toString: () => `file://${fsPath}` }),
  parse: (text: string) => ({ scheme: text.split(':')[0], fsPath: text, toString: () => text }),
};

class Position {
  constructor(
    public line: number,
    public character: number,
  ) {}
}
class Range {
  constructor(
    public start: Position,
    public end: Position,
  ) {}
}
class RelativePattern {
  constructor(
    public base: unknown,
    public pattern: string,
  ) {}
}
class Disposable {
  constructor(private readonly fn: () => void = () => undefined) {}
  dispose(): void {
    this.fn();
  }
}

const channel = () => ({ appendLine: vi.fn(), append: vi.fn(), show: vi.fn(), dispose: vi.fn() });

export const window = {
  createOutputChannel: vi.fn(channel),
  showInformationMessage: vi.fn(),
  showWarningMessage: vi.fn(),
  showErrorMessage: vi.fn(),
  showQuickPick: vi.fn(),
  showOpenDialog: vi.fn(),
  showInputBox: vi.fn(),
  withProgress: vi.fn((_options: unknown, task: () => unknown) => task()),
};

export const commands = { executeCommand: vi.fn() };
export const env = { openExternal: vi.fn() };
export const extensions = { getExtension: vi.fn() };

export const workspace = {
  get workspaceFolders() {
    return fake.workspaceFolders;
  },
  getConfiguration: (_section?: string) => ({
    get: <T>(key: string, fallback?: T): T => (fake.settings.has(key) ? (fake.settings.get(key) as T) : (fallback as T)),
    update: async (key: string, value: unknown) => {
      fake.updates.push({ key, value });
      if (value === undefined) {
        fake.settings.delete(key);
      } else {
        fake.settings.set(key, value);
      }
    },
  }),
  onDidChangeConfiguration: () => new Disposable(),
  createFileSystemWatcher: () => ({
    onDidCreate: () => new Disposable(),
    onDidChange: () => new Disposable(),
    onDidDelete: () => new Disposable(),
    dispose: () => undefined,
  }),
  fs: { delete: vi.fn(async () => undefined) },
};

export const ConfigurationTarget = { Global: 1, Workspace: 2, WorkspaceFolder: 3 };
export const ExtensionMode = { Production: 1, Development: 2, Test: 3 };
export const ProgressLocation = { Notification: 15 };
export { Position, Range, RelativePattern, Disposable };
