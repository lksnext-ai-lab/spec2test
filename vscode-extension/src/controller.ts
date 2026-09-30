import { execFile } from 'node:child_process';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import * as vscode from 'vscode';
import { DockerService } from './docker';
import { judgeProbe } from './core/health';
import { EnvStore } from './envstore';
import { FileIndex, copyIntoInputs, isSupported, outputsOf, ownedFiles } from './core/fileindex';
import { JobQueue } from './core/jobqueue';
import {
  ProjectError,
  addProject,
  readConfig,
  removeProject,
  resolveFeatures,
  resolvePaths,
  setModel,
  updateProject,
  validateName,
  writeConfig,
  type ProjectsConfig,
} from './core/projects';
import { readProviders } from './core/providers';
import { HF_TOKEN, TUNING } from './core/tuning';
import { McpService } from './mcp';
import { Traceability } from './traceability';
import { findRepo } from './repo';
import type { AppState, DockerState, FileOpenKind, ProjectFolder, ProjectView, ToHost } from './shared/messages';
import type { FileCard, Job, ProviderInfo, OrphanCard } from './shared/types';

const SELECTED_KEY = 'spec2test.selectedProject';
const PENDING_KEY = 'spec2test.envPending';
const FOLDER_LABEL: Record<ProjectFolder, string> = { inputs: 'Inputs', cache: 'Cache', preprocessed: 'Pre-processed', features: 'Features' };
const DOCKER_INSTALL_URL = 'https://docs.docker.com/get-docker/';

export class Controller implements vscode.Disposable {
  private readonly _onState = new vscode.EventEmitter<AppState>();
  readonly onState = this._onState.event;

  private repo?: string;
  private docker: AppState['docker'] = { state: 'no-repo' };
  private files: FileCard[] = [];
  private orphans: OrphanCard[] = [];
  private jobs: readonly Job[] = [];
  private providers: ProviderInfo[] = [];
  private index?: FileIndex;
  private watchers: vscode.Disposable[] = [];
  private timers: NodeJS.Timeout[] = [];
  private rescanTimer?: NodeJS.Timeout;
  private jobProject?: string;
  private unreachableSince?: number;

  private readonly dockerService: DockerService;
  private readonly env: EnvStore;
  private readonly mcp: McpService;
  private readonly queue: JobQueue;
  private readonly trace: Traceability;
  private highlight?: { name: string; nonce: number };
  readonly logs: vscode.OutputChannel;
  readonly activity: vscode.OutputChannel;

  constructor(private readonly context: vscode.ExtensionContext) {
    this.logs = vscode.window.createOutputChannel('Spec2Test: input-processor');
    this.activity = vscode.window.createOutputChannel('Spec2Test');
    this.dockerService = new DockerService(() => this.repo, () => this.port, this.logs);
    this.env = new EnvStore(context.secrets, () => this.repo);
    this.mcp = new McpService(() => this.port, (line) => this.activity.appendLine(line));
    this.queue = new JobQueue(
      (file, force, hooks) => this.mcp.processFile(this.jobProject ?? '', file, force, hooks),
      (jobs) => {
        this.jobs = jobs;
        this.post();
      },
    );
    this.trace = new Traceability(context.workspaceState, {
      selected: () => this.selected,
      featuresDir: () => this.featuresDirOf(this.selected),
      inputNames: () => this.files.map((file) => file.name),
      chooseFeaturesDir: () => this.changeFeaturesFolder(this.selected),
      changed: () => this.post(),
    });
    this.context.subscriptions.push(this._onState, this.logs, this.activity, this.trace, this);
  }

  // --- settings and paths ---------------------------------------------------

  private get port(): number {
    return vscode.workspace.getConfiguration('spec2test').get<number>('port', 8003);
  }

  private get configFile(): string | undefined {
    return this.repo ? path.join(this.repo, 'projects.json') : undefined;
  }

  private readConfig(): ProjectsConfig {
    const file = this.configFile;
    return file ? readConfig(file) : { projects: [] };
  }

  private get selected(): string | undefined {
    const config = this.readConfig();
    const stored = this.context.workspaceState.get<string>(SELECTED_KEY);
    return config.projects.find((project) => project.name === stored)?.name ?? config.projects[0]?.name;
  }

  private selectedPaths() {
    const name = this.selected;
    const file = this.configFile;
    const entry = this.readConfig().projects.find((project) => project.name === name);
    return entry && file ? resolvePaths(entry, path.dirname(file)) : undefined;
  }

  get selectedName(): string | undefined {
    return this.selected;
  }

  // --- lifecycle --------------------------------------------------------------

  async init(): Promise<void> {
    this.locateRepo();
    await this.afterRepoChange();
    this.timers.push(setInterval(() => void this.probeDocker(), 5000));
    this.context.subscriptions.push(
      vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration('spec2test')) {
          void this.locateRepoAndRefresh();
        }
      }),
      vscode.workspace.onDidChangeWorkspaceFolders(() => void this.locateRepoAndRefresh()),
    );
    if (vscode.workspace.getConfiguration('spec2test').get<boolean>('autoStartService')) {
      void this.startService();
    }
  }

  dispose(): void {
    this.timers.forEach(clearInterval);
    this.watchers.forEach((watcher) => watcher.dispose());
    this.dockerService.dispose();
    this.queue.cancel();
  }

  private locateRepo(): void {
    const configured = vscode.workspace.getConfiguration('spec2test').get<string>('repoPath', '');
    const folders = (vscode.workspace.workspaceFolders ?? []).map((folder) => folder.uri.fsPath);
    this.repo = findRepo(configured, folders);
  }

  private async locateRepoAndRefresh(): Promise<void> {
    this.locateRepo();
    await this.afterRepoChange();
  }

  private async afterRepoChange(): Promise<void> {
    if (this.repo) {
      this.env.ensureFile();
      this.providers = readProviders(this.repo);
      await this.env.syncKeys(this.keyNames());
    } else {
      this.providers = [];
    }
    this.watchProject();
    await this.rescan();
    await this.probeDocker();
  }

  private keyNames(): string[] {
    return Array.from(new Set([...this.providers.map((provider) => provider.apiKeyEnv), HF_TOKEN]));
  }

  private watchProject(): void {
    this.watchers.forEach((watcher) => watcher.dispose());
    this.watchers = [];
    const paths = this.selectedPaths();
    this.index = paths ? new FileIndex(paths) : undefined;
    if (!paths) {
      return;
    }
    const watch = (dir: string) => {
      const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(vscode.Uri.file(dir), '**'));
      const schedule = () => this.scheduleRescan();
      this.watchers.push(watcher, watcher.onDidCreate(schedule), watcher.onDidChange(schedule), watcher.onDidDelete(schedule));
    };
    [paths.inputs, paths.cache, paths.preprocessed].forEach(watch);
  }

  private scheduleRescan(): void {
    clearTimeout(this.rescanTimer);
    this.rescanTimer = setTimeout(() => void this.rescan(), 400);
  }

  async rescan(): Promise<void> {
    try {
      const scan = (await this.index?.scan()) ?? { files: [], orphans: [] };
      this.files = scan.files;
      this.orphans = scan.orphans;
      this.trace.refresh();
    } catch (error) {
      this.activity.appendLine(`Could not read the project folders: ${(error as Error).message}`);
    }
    this.post();
  }

  async probeDocker(): Promise<void> {
    if (this.docker.busy) {
      return;
    }
    const before = JSON.stringify(this.docker);
    const judged = judgeProbe(await this.dockerService.probe(), this.unreachableSince, Date.now(), this.port);
    this.unreachableSince = judged.since;
    this.docker = judged.docker;
    if (JSON.stringify(this.docker) !== before) {
      this.post();
    }
  }

  // --- state ---------------------------------------------------------------------

  buildState(): AppState {
    let config: ProjectsConfig = { projects: [] };
    let problem: string | undefined;
    try {
      config = this.readConfig();
    } catch (error) {
      problem = (error as Error).message;
    }
    const base = this.configFile ? path.dirname(this.configFile) : '';
    const projects: ProjectView[] = config.projects.map((entry) => ({
      name: entry.name,
      ...resolvePaths(entry, base),
      features: resolveFeatures(entry, base),
      llm: entry.llm,
      vision: entry.vision,
    }));
    const env = this.env.read();
    const docker = problem && this.docker.state !== 'no-repo' ? { ...this.docker, detail: problem } : this.docker;
    return {
      repo: this.repo,
      docker,
      projects,
      selected: this.selected,
      defaults: config.defaults ?? {},
      files: this.files,
      orphans: this.orphans,
      jobs: [...this.jobs],
      providers: this.providers,
      keys: this.env.keyStatus(this.keyNames()),
      tuning: TUNING,
      tuningValues: Object.fromEntries(TUNING.map((variable) => [variable.key, env[variable.key] ?? ''])),
      envPending: this.context.globalState.get<boolean>(PENDING_KEY, false),
      gherkin: this.trace.state,
      highlight: this.highlight,
      fallbackProvider: 'google_genai',
    };
  }

  private post(): void {
    this._onState.fire(this.buildState());
  }

  /** Read through a method so TypeScript does not narrow a field that changes across awaits. */
  private currentDockerState(): DockerState {
    return this.docker.state;
  }

  private setDocker(state: DockerState, busy?: string, detail?: string): void {
    this.docker = { state, busy, detail };
    this.post();
  }

  private async withBusy<T>(label: string, work: () => Promise<T>): Promise<T | undefined> {
    this.setDocker(this.docker.state, label);
    try {
      return await work();
    } catch (error) {
      void vscode.window.showErrorMessage(error instanceof Error ? error.message : String(error));
      return undefined;
    } finally {
      this.docker = { ...this.docker, busy: undefined };
      await this.probeDocker();
      this.post();
    }
  }

  // --- messages from the webview --------------------------------------------------

  async handle(message: ToHost): Promise<void> {
    try {
      await this.dispatch(message);
    } catch (error) {
      void vscode.window.showErrorMessage(error instanceof Error ? error.message : String(error));
    }
  }

  private async dispatch(message: ToHost): Promise<void> {
    switch (message.type) {
      case 'ready':
        this.post();
        return;
      case 'chooseRepo':
        return this.chooseRepo();
      case 'selectProject':
        await this.context.workspaceState.update(SELECTED_KEY, message.name);
        this.watchProject();
        return this.rescan();
      case 'createProject':
        return this.createProject();
      case 'removeProject':
        return this.removeProjectFlow(message.name);
      case 'gherkin':
        return message.action === 'toggle' ? this.trace.toggle() : this.trace.reload();
      case 'openScenario':
        return this.openScenario(message.file, message.line);
      case 'projectFolder':
        return message.action === 'open' ? this.openProjectFolder(message.name, message.which) : this.changeProjectFolder(message.name, message.which);
      case 'useInCopilot':
        return this.useInCopilot(message.name);
      case 'docker':
        return this.dockerAction(message.action);
      case 'addFiles':
        return this.addFilesDialog();
      case 'process':
        return this.process(message.files, message.force);
      case 'processPending':
        return this.process(
          this.files.filter((file) => file.state !== 'cached').map((file) => file.name),
          false,
        );
      case 'cancel':
        this.queue.cancel();
        return;
      case 'open':
        return this.open(message.file, message.kind);
      case 'history':
        return this.history(message.file);
      case 'removeFile':
        return this.removeFile(message.file);
      case 'cleanOrphans':
        return this.cleanOrphans();
      case 'saveModel': {
        const config = setModel(this.readConfig(), message.scope === 'project' ? { project: this.selected } : {}, message.kind, message.value);
        writeConfig(this.requireConfigFile(), config);
        this.post();
        return;
      }
      case 'saveKey':
        await this.env.saveKey(message.env, message.value);
        return this.markEnvPending();
      case 'saveTuning':
        this.env.saveTuning(message.values);
        return this.markEnvPending();
      case 'applyEnv':
        return this.applyEnv();
    }
  }

  private requireConfigFile(): string {
    const file = this.configFile;
    if (!file) {
      throw new Error('Choose the spec2test repository folder first.');
    }
    return file;
  }

  private async markEnvPending(): Promise<void> {
    await this.context.globalState.update(PENDING_KEY, true);
    this.post();
  }

  // --- repository ------------------------------------------------------------------

  async chooseRepo(): Promise<void> {
    const picked = await vscode.window.showOpenDialog({
      canSelectFiles: false,
      canSelectFolders: true,
      canSelectMany: false,
      title: 'Choose the spec2test repository folder',
      openLabel: 'Use this folder',
    });
    if (!picked?.[0]) {
      return;
    }
    const folder = picked[0].fsPath;
    if (!findRepo(folder, [])) {
      void vscode.window.showErrorMessage(
        'That folder does not look like the spec2test repository (docker-compose.yaml, scripts/sync_projects.py and input-processor/ are expected).',
      );
      return;
    }
    await vscode.workspace.getConfiguration('spec2test').update('repoPath', folder, vscode.ConfigurationTarget.Global);
  }

  // --- projects ----------------------------------------------------------------------

  private async createProject(): Promise<void> {
    const file = this.requireConfigFile();
    const config = readConfig(file);
    const name = await vscode.window.showInputBox({
      title: 'New Spec2Test project',
      prompt: 'Project name',
      placeHolder: 'shop-app',
      validateInput: (value) =>
        validateName(value) ?? (config.projects.some((project) => project.name === value) ? 'That project already exists.' : undefined),
    });
    if (!name) {
      return;
    }
    const defaults = resolvePaths({ name }, path.dirname(file));
    const choice = await vscode.window.showQuickPick(
      [
        { label: '$(folder) Use the default folder', description: defaults.inputs, value: 'default' as const },
        { label: '$(folder-opened) Choose the folder with my specs…', description: 'an existing folder of PDFs, recordings, Markdown or text', value: 'choose' as const },
      ],
      { title: `Inputs folder for '${name}'`, placeHolder: 'Where are the files to process?' },
    );
    if (!choice) {
      return;
    }
    let inputs = defaults.inputs;
    if (choice.value === 'choose') {
      const picked = await this.pickFolder(`Inputs folder for '${name}'`, defaults.inputs);
      if (!picked) {
        return;
      }
      inputs = picked;
    }
    fs.mkdirSync(inputs, { recursive: true });
    // The cache and pre-processed folders keep their defaults; each can be changed later from the project menu.
    writeConfig(file, addProject(config, { name, inputs }));
    await this.context.workspaceState.update(SELECTED_KEY, name);
    this.watchProject();
    await this.syncAndRestart(`Creating project '${name}'…`);
    await this.rescan();
  }

  private async pickFolder(title: string, current: string): Promise<string | undefined> {
    const picked = await vscode.window.showOpenDialog({
      canSelectFiles: false,
      canSelectFolders: true,
      canSelectMany: false,
      title,
      defaultUri: vscode.Uri.file(fs.existsSync(current) ? current : path.dirname(current)),
      openLabel: 'Select folder',
    });
    return picked?.[0]?.fsPath;
  }

  private projectPaths(name: string): { entry: NonNullable<ProjectsConfig['projects'][number]>; paths: ReturnType<typeof resolvePaths> } {
    const file = this.requireConfigFile();
    const entry = readConfig(file).projects.find((project) => project.name === name);
    if (!entry) {
      throw new ProjectError(`Unknown project '${name}'.`);
    }
    return { entry, paths: resolvePaths(entry, path.dirname(file)) };
  }

  private featuresDirOf(name: string | undefined): string | undefined {
    if (!name || !this.configFile) {
      return undefined;
    }
    const entry = this.readConfig().projects.find((project) => project.name === name);
    return entry ? resolveFeatures(entry, path.dirname(this.configFile)) : undefined;
  }

  /** Ask for the folder with the .feature files and remember it in projects.json (host-only, never mounted). */
  private async changeFeaturesFolder(name: string | undefined): Promise<string | undefined> {
    if (!name) {
      return undefined;
    }
    const start = this.featuresDirOf(name) ?? vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? this.repo ?? os.homedir();
    const picked = await this.pickFolder(`Folder with the .feature files of '${name}' (subfolders are included)`, start);
    if (!picked) {
      return undefined;
    }
    const file = this.requireConfigFile();
    writeConfig(file, updateProject(readConfig(file), name, { features: picked }));
    this.trace.refresh();
    this.post();
    return picked;
  }

  private async openScenario(relative: string, line: number): Promise<void> {
    const root = this.featuresDirOf(this.selected);
    if (!root) {
      return;
    }
    const target = path.resolve(root, relative);
    if (target !== root && !target.startsWith(root + path.sep)) {
      throw new Error('That file is outside the features folder.');
    }
    const position = new vscode.Position(Math.max(0, line - 1), 0);
    await vscode.commands.executeCommand('vscode.open', vscode.Uri.file(target), { selection: new vscode.Range(position, position), preview: false });
  }

  /** Select an input's card in the sidebar (used by the links inside .feature files). */
  async revealInput(project: string, name: string): Promise<void> {
    if (this.selected !== project && this.readConfig().projects.some((item) => item.name === project)) {
      await this.context.workspaceState.update(SELECTED_KEY, project);
      this.watchProject();
      await this.rescan();
    }
    if (!this.files.some((file) => file.name === name)) {
      void vscode.window.showWarningMessage(`'${name}' is not an input file of project '${project}'.`);
      return;
    }
    await vscode.commands.executeCommand('spec2test.main.focus');
    this.highlight = { name, nonce: (this.highlight?.nonce ?? 0) + 1 };
    this.post();
  }

  /** The project whose features folder holds `fsPath`, with what the editor links need to know. */
  projectForFeature(fsPath: string): { project: string; inputs: Map<string, { processed: boolean }>; cited: Map<string, number> } | undefined {
    const file = this.configFile;
    if (!file) {
      return undefined;
    }
    for (const entry of this.readConfig().projects) {
      const root = resolveFeatures(entry, path.dirname(file));
      if (!root || !(fsPath === root || fsPath.startsWith(root + path.sep))) {
        continue;
      }
      const paths = resolvePaths(entry, path.dirname(file));
      const inputs = new Map<string, { processed: boolean }>();
      if (fs.existsSync(paths.inputs)) {
        for (const item of fs.readdirSync(paths.inputs, { withFileTypes: true })) {
          if (item.isFile() && isSupported(item.name)) {
            inputs.set(item.name, { processed: fs.existsSync(outputsOf(paths, item.name).cache) });
          }
        }
      }
      const index = this.trace.current?.project === entry.name ? this.trace.current : undefined;
      const cited = new Map(Object.entries(index?.byInput ?? {}).map(([name, refs]) => [name, refs.length]));
      return { project: entry.name, inputs, cited };
    }
    return undefined;
  }

  private async openProjectFolder(name: string, which: ProjectFolder): Promise<void> {
    if (which === 'features') {
      const dir = this.featuresDirOf(name);
      if (!dir) {
        await this.changeFeaturesFolder(name);
      } else if (fs.existsSync(dir)) {
        await vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(dir));
      } else {
        void vscode.window.showWarningMessage(`The features folder does not exist: ${dir}`);
      }
      return;
    }
    const folder = this.projectPaths(name).paths[which];
    fs.mkdirSync(folder, { recursive: true });
    await vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(folder));
  }

  /** Change one folder of a project. The three folders are independent and each has its own menu entry. */
  private async changeProjectFolder(name: string, which: ProjectFolder): Promise<void> {
    if (which === 'features') {
      await this.changeFeaturesFolder(name);
      return;
    }
    const { paths } = this.projectPaths(name);
    const label = FOLDER_LABEL[which];
    const picked = await this.pickFolder(`${label} folder for '${name}'. Files already in the old folder are not moved.`, paths[which]);
    if (!picked || path.resolve(picked) === path.resolve(paths[which])) {
      return;
    }
    fs.mkdirSync(picked, { recursive: true });
    const file = this.requireConfigFile();
    writeConfig(file, updateProject(readConfig(file), name, { [which]: picked }));
    this.watchProject();
    await this.syncAndRestart(`Changing the ${label.toLowerCase()} folder…`);
    await this.rescan();
  }

  private async removeProjectFlow(name: string): Promise<void> {
    const { paths } = this.projectPaths(name);
    const owned = ownedFiles(paths);
    const inputs = owned.filter((file) => path.dirname(file) === paths.inputs).length;
    const trashLabel = owned.length > 0 ? `Detach and move ${owned.length} item(s) to the trash` : undefined;
    const detach = 'Detach only';

    const answer = await vscode.window.showWarningMessage(
      `Remove project '${name}'?`,
      {
        modal: true,
        detail: [
          `Detach only: '${name}' disappears from Spec2Test. Nothing is deleted from your disk.`,
          owned.length > 0
            ? `Detach and trash: also moves to the trash ${inputs} input file(s) from ${paths.inputs} and all their results (cache and pre-processed). Other files in those folders are not touched.`
            : 'There are no input files or results to delete.',
        ].join('\n\n'),
      },
      ...(trashLabel ? [detach, trashLabel] : [detach]),
    );
    if (!answer) {
      return;
    }
    if (answer === trashLabel) {
      for (const target of owned) {
        await vscode.workspace.fs.delete(vscode.Uri.file(target), { recursive: true, useTrash: true });
      }
    }
    const file = this.requireConfigFile();
    const config = removeProject(readConfig(file), name);
    writeConfig(file, config);
    this.watchProject();
    if (config.projects.length > 0) {
      await this.syncAndRestart(`Removing project '${name}'…`);
    }
    await this.rescan();
  }

  /** Regenerate docker-compose.override.yaml, then recreate the container if it is running. */
  private async syncAndRestart(label: string): Promise<void> {
    await this.withBusy(label, async () => {
      await this.runSync();
      const running = (await this.dockerService.probe()).state;
      if (running === 'running' || running === 'starting') {
        const result = await this.dockerService.up({ recreate: true });
        if (result.code !== 0) {
          throw new Error(`Docker could not restart the service:\n${tail(result.stderr)}`);
        }
        await this.dockerService.waitUntilReachable();
        await this.context.globalState.update(PENDING_KEY, false);
      }
    });
  }

  private runSync(): Promise<void> {
    const repo = this.repo;
    if (!repo) {
      return Promise.reject(new Error('Choose the spec2test repository folder first.'));
    }
    if (this.readConfig().projects.length === 0) {
      return Promise.resolve();
    }
    const python = vscode.workspace.getConfiguration('spec2test').get<string>('pythonPath', 'python3');
    return new Promise((resolve, reject) => {
      execFile(python, [path.join('scripts', 'sync_projects.py'), '--quiet'], { cwd: repo }, (error, _stdout, stderr) => {
        if (error) {
          reject(new Error(`scripts/sync_projects.py failed:\n${tail(stderr || error.message)}`));
        } else {
          resolve();
        }
      });
    });
  }

  private async useInCopilot(name: string): Promise<void> {
    const folder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? this.repo;
    if (!folder) {
      return;
    }
    const file = path.join(folder, '.vscode', 'mcp.json');
    if (!fs.existsSync(file)) {
      void vscode.window.showInformationMessage(`No .vscode/mcp.json found in ${folder}.`);
      return;
    }
    let json: { servers?: Record<string, { headers?: Record<string, string> }> };
    try {
      json = JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch {
      throw new Error(`${file} could not be parsed (comments are not supported here). Edit the X-Spec2Test-Project header by hand.`);
    }
    const server = json.servers?.['input-processor'];
    if (!server) {
      throw new Error(`${file} has no 'input-processor' server.`);
    }
    server.headers = { ...server.headers, 'X-Spec2Test-Project': name };
    fs.writeFileSync(file, JSON.stringify(json, null, '\t') + '\n', 'utf8');
    void vscode.window.showInformationMessage(`Agents now use project '${name}' (${path.relative(folder, file)}).`);
  }

  // --- docker ------------------------------------------------------------------------------

  async dockerAction(action: Extract<ToHost, { type: 'docker' }>['action']): Promise<void> {
    switch (action) {
      case 'install':
        await vscode.env.openExternal(vscode.Uri.parse(DOCKER_INSTALL_URL));
        return;
      case 'startDocker':
        return this.startDockerDesktop();
      case 'start':
        // Building is a cached no-op when nothing changed, and it repairs a stale image.
        return this.startService({ build: true });
      case 'stop':
        await this.withBusy('Stopping…', async () => {
          await this.dockerService.down();
        });
        return;
      case 'restart':
        return this.startService({ recreate: true });
      case 'rebuild':
        return this.startService({ recreate: true, build: true });
      case 'logs':
        this.dockerService.showLogs();
        return;
    }
  }

  async startService(options: { recreate?: boolean; build?: boolean } = {}): Promise<void> {
    if (!this.repo) {
      await this.chooseRepo();
      return;
    }
    await this.withBusy(options.build ? 'Building and starting…' : 'Starting the input-processor…', async () => {
      this.env.ensureFile();
      await this.runSync();
      if (options.build) {
        this.logs.show(true);
      }
      const result = await this.dockerService.up(options);
      if (result.code !== 0) {
        this.dockerService.showLogs();
        throw new Error(`Docker could not start the service:\n${tail(result.stderr)}`);
      }
      this.setDocker('starting', options.build ? 'Building and starting…' : 'Starting the input-processor…');
      if (!(await this.dockerService.waitUntilReachable())) {
        this.dockerService.showLogs();
        throw new Error('The input-processor did not answer within two minutes. Check the logs.');
      }
      await this.context.globalState.update(PENDING_KEY, false);
    });
  }

  private async applyEnv(): Promise<void> {
    const state = (await this.dockerService.probe()).state;
    if (state === 'running' || state === 'starting') {
      await this.startService({ recreate: true });
    } else {
      await this.context.globalState.update(PENDING_KEY, false);
      this.post();
      void vscode.window.showInformationMessage('Saved. The new values are used the next time the input-processor starts.');
    }
  }

  private async startDockerDesktop(): Promise<void> {
    if (os.platform() === 'darwin') {
      execFile('open', ['-a', 'Docker']);
      this.setDocker('daemon-down', 'Starting Docker Desktop…');
      for (let attempt = 0; attempt < 60; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        if ((await this.dockerService.probe()).state !== 'daemon-down') {
          break;
        }
      }
      this.docker = { ...this.docker, busy: undefined };
      await this.probeDocker();
      this.post();
    } else if (os.platform() === 'win32') {
      void vscode.window.showInformationMessage('Start Docker Desktop from the Start menu, then come back here.');
    } else {
      void vscode.window.showInformationMessage('Start the Docker daemon (for example: sudo systemctl start docker), then come back here.');
    }
  }

  // --- files ----------------------------------------------------------------------------------

  async addFilesDialog(): Promise<void> {
    const picked = await vscode.window.showOpenDialog({
      canSelectMany: true,
      canSelectFiles: true,
      canSelectFolders: false,
      title: 'Add files to the project',
      filters: { 'Specs and recordings': ['mp4', 'pdf', 'md', 'txt'] },
    });
    if (picked?.length) {
      await this.addUris(picked);
    }
  }

  async addUris(uris: vscode.Uri[]): Promise<void> {
    const paths = this.selectedPaths();
    if (!paths) {
      void vscode.window.showWarningMessage('Create or select a project before adding files.');
      return;
    }
    const sources: string[] = [];
    const rejected: string[] = [];
    for (const uri of uris) {
      if (uri.scheme !== 'file') {
        rejected.push(uri.toString());
        continue;
      }
      const stat = fs.existsSync(uri.fsPath) ? fs.statSync(uri.fsPath) : undefined;
      const candidates = stat?.isDirectory()
        ? fs.readdirSync(uri.fsPath).map((name) => path.join(uri.fsPath, name)).filter((file) => fs.statSync(file).isFile())
        : stat
          ? [uri.fsPath]
          : [];
      for (const file of candidates) {
        (isSupported(file) ? sources : rejected).push(isSupported(file) ? file : path.basename(file));
      }
    }
    if (rejected.length > 0) {
      void vscode.window.showWarningMessage(`Skipped unsupported files (only .mp4, .pdf, .md and .txt): ${rejected.join(', ')}`);
    }
    if (sources.length === 0) {
      return;
    }

    const taken = sources.filter((source) => fs.existsSync(path.join(paths.inputs, path.basename(source))));
    let mode: 'replace' | 'keep-both' | 'skip' = 'replace';
    if (taken.length > 0) {
      const answer = await vscode.window.showQuickPick(
        [
          { label: 'Replace', description: 'Overwrite the files already in the project', value: 'replace' as const },
          { label: 'Keep both', description: 'Add the new ones as “name (2).ext”', value: 'keep-both' as const },
          { label: 'Skip', description: 'Leave the existing files alone', value: 'skip' as const },
        ],
        { title: `${taken.length} file(s) already exist in the project`, placeHolder: taken.map((file) => path.basename(file)).join(', ') },
      );
      if (!answer) {
        return;
      }
      mode = answer.value;
    }
    let copied = 0;
    for (const source of sources) {
      const isConflict = taken.includes(source);
      if (copyIntoInputs(source, paths.inputs, isConflict ? mode : 'replace').copied) {
        copied += 1;
      }
    }
    await this.rescan();
    if (copied > 0) {
      const next = await vscode.window.showInformationMessage(`Added ${copied} file(s) to '${this.selected}'.`, 'Process now');
      if (next === 'Process now') {
        await this.dispatch({ type: 'processPending' });
      }
    }
  }

  private async process(files: string[], force: boolean): Promise<void> {
    if (files.length === 0) {
      void vscode.window.showInformationMessage('Everything is up to date.');
      return;
    }
    const project = this.selected;
    if (!project) {
      return;
    }
    if (this.queue.busy && this.jobProject !== project) {
      void vscode.window.showWarningMessage(`Still processing '${this.jobProject}'. Wait for it or cancel first.`);
      return;
    }
    if (this.docker.state !== 'running') {
      const answer = await vscode.window.showWarningMessage('The input-processor is not running.', 'Start it and process');
      if (answer !== 'Start it and process') {
        return;
      }
      await this.startService();
      if (this.currentDockerState() !== 'running') {
        return;
      }
    }
    this.jobProject = project;
    const done = await this.queue.enqueue(files, force).then(() => true);
    await this.rescan();
    const failed = this.jobs.filter((job) => job.status === 'error');
    if (done && failed.length > 0) {
      void vscode.window.showErrorMessage(`${failed.length} file(s) failed: ${failed.map((job) => `${job.file} (${job.error})`).join('; ')}`);
    }
  }

  private async open(file: string, kind: FileOpenKind): Promise<void> {
    const paths = this.selectedPaths();
    if (!paths) {
      return;
    }
    const outputs = outputsOf(paths, file);
    const target = { original: outputs.original, cache: outputs.cache, 'cache-preview': outputs.cache, preprocessed: outputs.preprocessed, images: outputs.images }[kind];
    if (!fs.existsSync(target)) {
      void vscode.window.showInformationMessage(`${path.basename(target)} does not exist yet. Process the file first.`);
      return;
    }
    const uri = vscode.Uri.file(target);
    if (kind === 'images') {
      await vscode.commands.executeCommand('revealFileInOS', uri);
    } else if (kind === 'cache-preview') {
      await vscode.commands.executeCommand('markdown.showPreviewToSide', uri);
    } else if (kind === 'original' && file.toLowerCase().endsWith('.pdf')) {
      await this.openPdf(uri);
    } else {
      await vscode.commands.executeCommand('vscode.open', uri, { preview: false });
    }
  }

  /** VS Code has no built-in PDF viewer: use the popular extension if present, else offer it. */
  private async openPdf(uri: vscode.Uri): Promise<void> {
    if (vscode.extensions.getExtension('tomoki1207.pdf')) {
      await vscode.commands.executeCommand('vscode.openWith', uri, 'pdf.preview');
      return;
    }
    const answer = await vscode.window.showInformationMessage(
      'VS Code cannot show PDFs by itself. Install a PDF viewer extension to open them here.',
      'Install PDF viewer',
      'Open with system viewer',
    );
    if (answer === 'Install PDF viewer') {
      await vscode.commands.executeCommand('workbench.extensions.installExtension', 'tomoki1207.pdf');
    } else if (answer === 'Open with system viewer') {
      await vscode.env.openExternal(uri);
    }
  }

  private async history(file: string): Promise<void> {
    const card = this.files.find((item) => item.name === file);
    if (!card || card.history.length === 0) {
      void vscode.window.showInformationMessage(`No earlier versions of ${file}.`);
      return;
    }
    const paths = this.selectedPaths();
    if (!paths) {
      return;
    }
    const picked = await vscode.window.showQuickPick(
      card.history.map((item) => ({ label: item.label, description: 'compare with the current result', item })),
      { title: `Earlier versions of ${file}` },
    );
    if (!picked) {
      return;
    }
    const current = vscode.Uri.file(outputsOf(paths, file).cache);
    const older = vscode.Uri.file(picked.item.path);
    if (fs.existsSync(current.fsPath)) {
      await vscode.commands.executeCommand('vscode.diff', older, current, `${file}: ${picked.label} ↔ current`);
    } else {
      await vscode.commands.executeCommand('vscode.open', older);
    }
  }

  private async removeFile(file: string): Promise<void> {
    const paths = this.selectedPaths();
    if (!paths) {
      return;
    }
    const answer = await vscode.window.showWarningMessage(
      `Remove ${file} from the project?`,
      { modal: true, detail: 'Files go to the trash. Cached results are kept in the history when you also remove the outputs.' },
      'Remove input only',
      'Remove input and outputs',
    );
    if (!answer) {
      return;
    }
    const outputs = outputsOf(paths, file);
    const trash = (target: string) =>
      fs.existsSync(target) ? vscode.workspace.fs.delete(vscode.Uri.file(target), { recursive: true, useTrash: true }) : Promise.resolve();
    await trash(outputs.original);
    if (answer === 'Remove input and outputs') {
      this.index?.archiveCache(file);
      await trash(outputs.preprocessed);
      await trash(outputs.images);
    }
    await this.rescan();
  }

  private async cleanOrphans(): Promise<void> {
    if (this.orphans.length === 0) {
      void vscode.window.showInformationMessage('No orphaned results.');
      return;
    }
    const answer = await vscode.window.showWarningMessage(
      `Archive ${this.orphans.length} orphaned result(s)?`,
      { modal: true, detail: `${this.orphans.map((orphan) => orphan.name).join(', ')}\n\nTheir source files are gone. The results are moved to the cache history, not deleted.` },
      'Archive',
    );
    if (answer !== 'Archive') {
      return;
    }
    for (const orphan of this.orphans) {
      this.index?.archiveCache(orphan.name);
    }
    await this.rescan();
  }
}

function tail(text: string, lines = 12): string {
  return text.trim().split(/\r?\n/).slice(-lines).join('\n');
}
