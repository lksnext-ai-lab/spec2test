import * as fs from 'node:fs';
import * as vscode from 'vscode';
import { buildIndex, viewByInput, warningsOf, writeIndex, type TraceIndex } from './core/gherkin';
import type { GherkinState } from './shared/types';

export interface TraceabilityHost {
  selected(): string | undefined;
  /** Host path of the selected project's features folder, if it has one. */
  featuresDir(): string | undefined;
  /** File names of the selected project's inputs. */
  inputNames(): string[];
  /** Ask for the features folder (and save it); undefined when the user cancels. */
  chooseFeaturesDir(): Promise<string | undefined>;
  changed(): void;
}

const key = (project: string) => `spec2test.gherkin.${project}`;

/**
 * Keeps the link between inputs and the scenarios that cite them. The `# Source:` comments in the
 * `.feature` files are the only source of truth; the JSON written next to the features is an index
 * rebuilt from them whenever the user reloads (or a feature file changes while the view is on).
 */
export class Traceability implements vscode.Disposable {
  private index?: TraceIndex;
  private scanning = false;
  private error?: string;
  private watcher?: vscode.FileSystemWatcher;
  private watched?: string;
  private timer?: NodeJS.Timeout;

  constructor(
    private readonly memento: vscode.Memento,
    private readonly host: TraceabilityHost,
  ) {}

  get enabled(): boolean {
    const project = this.host.selected();
    return Boolean(project && this.memento.get<boolean>(key(project), false));
  }

  /** The index of the selected project, when it has been built. */
  get current(): TraceIndex | undefined {
    return this.index?.project === this.host.selected() ? this.index : undefined;
  }

  get state(): GherkinState {
    const index = this.current;
    const names = this.host.inputNames();
    return {
      enabled: this.enabled,
      folder: this.host.featuresDir(),
      scanning: this.scanning,
      features: index?.features.length ?? 0,
      scenarios: index?.features.reduce((sum, feature) => sum + feature.scenarios.length, 0) ?? 0,
      generatedAt: index?.generatedAt,
      byInput: index ? viewByInput(index, names) : {},
      warnings: index ? warningsOf(index) : [],
      error: this.error,
    };
  }

  async toggle(): Promise<void> {
    const project = this.host.selected();
    if (!project) {
      return;
    }
    if (this.enabled) {
      await this.memento.update(key(project), false);
      this.sync();
      this.host.changed();
      return;
    }
    if (!this.host.featuresDir() && !(await this.host.chooseFeaturesDir())) {
      return;
    }
    await this.memento.update(key(project), true);
    await this.reload();
  }

  /** Rescan the features folder, rebuild the index and write the JSON. */
  async reload(): Promise<void> {
    if (!this.host.selected()) {
      return;
    }
    this.scanning = true;
    this.host.changed();
    await new Promise((resolve) => setTimeout(resolve, 0)); // let the spinner paint
    try {
      this.rebuild();
    } finally {
      this.scanning = false;
      this.sync();
      this.host.changed();
    }
  }

  private rebuild(): void {
    const project = this.host.selected();
    const dir = this.host.featuresDir();
    this.error = undefined;
    if (!project || !dir) {
      this.index = undefined;
      this.error = 'Choose the folder with your .feature files first.';
      return;
    }
    if (!fs.existsSync(dir)) {
      this.index = undefined;
      this.error = `The features folder does not exist: ${dir}`;
      return;
    }
    this.index = buildIndex(project, dir, this.host.inputNames());
    try {
      writeIndex(dir, this.index);
    } catch (error) {
      this.error = `Could not write the traceability file: ${(error as Error).message}`;
    }
  }

  /** Called when the project, its folders or its inputs may have changed. */
  refresh(): void {
    if (this.enabled) {
      this.rebuild();
    }
    this.sync();
  }

  /** Watch the features folder while the view is on, and only then. */
  private sync(): void {
    const dir = this.enabled ? this.host.featuresDir() : undefined;
    if (dir === this.watched) {
      return;
    }
    this.watcher?.dispose();
    this.watcher = undefined;
    this.watched = dir;
    if (!dir) {
      return;
    }
    const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(dir), '**/*.feature'));
    const later = () => {
      clearTimeout(this.timer);
      this.timer = setTimeout(() => void this.reload(), 500);
    };
    this.watcher = watcher;
    watcher.onDidCreate(later);
    watcher.onDidChange(later);
    watcher.onDidDelete(later);
  }

  dispose(): void {
    clearTimeout(this.timer);
    this.watcher?.dispose();
  }
}
