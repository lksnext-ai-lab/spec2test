import { execFile } from 'node:child_process';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import * as vscode from 'vscode';
import { DockerService, engineInfo, type ServiceConfig } from './docker';
import { CONTAINER_NAME, HF_CACHE_DIRNAME, inputProcessorSpec, shouldMapUser, toDockerPath, webCrawlerSpec, wantedImage } from './core/containers';
import { hasForeignOwner } from './core/ownership';
import { judgeProbe } from './core/health';
import { EnvStore } from './envstore';
import { FileIndex, copyIntoInputs, isSupported, outputsOf, ownedFiles } from './core/fileindex';
import { JobQueue, type RunHooks } from './core/jobqueue';
import { TARGETS, McpFileError, applyPlan, installedMcpFiles, loadBundle, planInstall, retargetProject, type AgentTarget, type McpSettings } from './core/agents';
import { migrateLegacy } from './core/migrate';
import {
  ProjectError,
  addProject,
  dataRoot,
  defaultDataRoot,
  setDataRoot,
  workAreaOf,
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
import { hashFile, refreshWork, runStaged, type Layout } from './core/staging';
import { Traceability } from './traceability';
import { findRepo } from './repo';
import type { AppState, DockerState, FileOpenKind, ProjectFolder, ProjectView, ToHost } from './shared/messages';
import type { FileCard, Job, ProviderInfo, OrphanCard } from './shared/types';

const SELECTED_KEY = 'spec2test.selectedProject';
const PENDING_KEY = 'spec2test.envPending';
const FOLDER_LABEL: Record<ProjectFolder, string> = { inputs: 'Inputs', cache: 'Cache', preprocessed: 'Pre-processed', features: 'Features' };
const AGENTS_KEY = 'spec2test.agents';
const AGENTS_PROMPT_KEY = 'spec2test.agentsPrompt';
const DOCKER_INSTALL_URL = 'https://docs.docker.com/get-docker/';

export class Controller implements vscode.Disposable {
  private readonly _onState = new vscode.EventEmitter<AppState>();
  readonly onState = this._onState.event;

  private docker: AppState['docker'] = { state: 'stopped' };
  private crawler: AppState['crawler'];
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
  private readonly crawlerService: DockerService;
  private readonly env: EnvStore;
  private readonly mcp: McpService;
  private readonly queue: JobQueue;
  private readonly trace: Traceability;
  private highlight?: { name: string; nonce: number };
  readonly logs: vscode.OutputChannel;
  private readonly crawlerLogs: vscode.OutputChannel;
  readonly activity: vscode.OutputChannel;

  constructor(private readonly context: vscode.ExtensionContext) {
    this.logs = vscode.window.createOutputChannel('Spec2Test: input-processor');
    this.activity = vscode.window.createOutputChannel('Spec2Test');
    this.crawlerLogs = vscode.window.createOutputChannel('Spec2Test: web-crawler');
    this.dockerService = new DockerService(() => this.inputProcessorConfig(), this.logs);
    this.crawlerService = new DockerService(() => this.crawlerConfig(), this.crawlerLogs);
    this.env = new EnvStore(context.secrets, context.globalState);
    this.mcp = new McpService(() => this.port, (line) => this.activity.appendLine(line));
    this.queue = new JobQueue(
      (file, force, hooks) => this.runJob(file, force, hooks),
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
    this.context.subscriptions.push(this._onState, this.logs, this.crawlerLogs, this.activity, this.trace, this);
  }

  // --- settings and paths ---------------------------------------------------

  private get port(): number {
    return vscode.workspace.getConfiguration('spec2test').get<number>('port', 8003);
  }

  private get configFile(): string | undefined {
    return path.join(dataRoot(), 'projects.json');
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

  /** The user's folders and the container's work area for one project. */
  private layoutOf(name: string): Layout | undefined {
    const file = this.configFile;
    const entry = this.readConfig().projects.find((project) => project.name === name);
    if (!entry || !file) {
      return undefined;
    }
    const paths = resolvePaths(entry, path.dirname(file));
    return { inputs: paths.inputs, cache: paths.cache, work: workAreaOf(path.dirname(file), name) };
  }

  private runJob(file: string, force: boolean, hooks: RunHooks): Promise<{ status: string; error?: string }> {
    const project = this.jobProject ?? '';
    const layout = this.layoutOf(project);
    const process = () => this.mcp.processFile(project, file, force, hooks);
    if (!layout) {
      return process();
    }
    return runStaged({
      layout,
      name: file,
      force,
      signal: hooks.signal,
      sha256: () => this.index?.sha256(path.join(layout.inputs, file)) ?? hashFile(path.join(layout.inputs, file)),
      process,
      report: hooks.onStage,
    });
  }

  /** Keep every project's work cache in step with its cache folder (agents read it through the container). */
  private refreshWorkAreas(): void {
    if (this.queue.busy) {
      return;
    }
    for (const entry of this.readConfig().projects) {
      const layout = this.layoutOf(entry.name);
      try {
        if (layout) {
          refreshWork(layout);
        }
      } catch (error) {
        this.activity.appendLine(`Could not update the work area of '${entry.name}': ${(error as Error).message}`);
      }
    }
  }

  get selectedName(): string | undefined {
    return this.selected;
  }

  // --- lifecycle --------------------------------------------------------------

  async init(): Promise<void> {
    setDataRoot(this.settings.get<string>('dataFolder', ''));
    await this.importFromRepository();
    this.providers = readProviders(path.join(this.context.extensionPath, 'dist', 'providers'));
    await this.env.load(this.keyNames());
    this.watchProject();
    await this.rescan();
    await this.probeDocker();
    this.timers.push(setInterval(() => void this.probeDocker(), 5000));
    this.context.subscriptions.push(
      vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration('spec2test.dataFolder')) {
          void this.applyDataFolder();
        } else if (event.affectsConfiguration('spec2test')) {
          void this.probeDocker();
        }
      }),
    );
    if (vscode.workspace.getConfiguration('spec2test').get<boolean>('autoStartService')) {
      void this.startService();
    }
    setTimeout(() => void this.offerAgents(), 4000);
  }

  dispose(): void {
    this.timers.forEach(clearInterval);
    this.watchers.forEach((watcher) => watcher.dispose());
    this.dockerService.dispose();
    this.crawlerService.dispose();
    this.queue.cancel();
  }

  /** Bring projects, keys and the saved crawler login over from an old clone of the repository, once. */
  private async importFromRepository(): Promise<void> {
    const configured = vscode.workspace.getConfiguration('spec2test').get<string>('repoPath', '');
    const folders = (vscode.workspace.workspaceFolders ?? []).map((folder) => folder.uri.fsPath);
    const repo = findRepo(configured, folders);
    if (!repo) {
      return;
    }
    try {
      migrateLegacy(repo, dataRoot()).forEach((note) => this.activity.appendLine(note));
      const names = Array.from(new Set([...readProviders(path.join(this.context.extensionPath, 'dist', 'providers')).map((provider) => provider.apiKeyEnv), HF_TOKEN]));
      const imported = await this.env.importLegacyEnv(path.join(repo, '.env'), names, TUNING.map((variable) => variable.key));
      if (imported.length > 0) {
        this.activity.appendLine(`Imported from ${path.join(repo, '.env')}: ${imported.join(', ')}.`);
      }
      const login = path.join(repo, 'auth_actions.json');
      const target = path.join(dataRoot(), 'auth_actions.json');
      if (fs.existsSync(login) && !fs.existsSync(target)) {
        fs.mkdirSync(dataRoot(), { recursive: true });
        fs.copyFileSync(login, target);
      }
    } catch (error) {
      this.activity.appendLine(`Could not import from ${repo}: ${(error as Error).message}`);
    }
  }

  // --- data folder -------------------------------------------------------------------------------

  /** Pick (or reset) the data folder, offer to bring the projects along, then let the setting change do the switch. */
  async changeDataFolder(reset = false): Promise<void> {
    if (this.queue.busy) {
      void vscode.window.showWarningMessage('Wait for the running job to finish, or cancel it, before moving the data folder.');
      return;
    }
    const current = dataRoot();
    let target = defaultDataRoot();
    if (!reset) {
      const picked = await vscode.window.showOpenDialog({
        canSelectFiles: false,
        canSelectFolders: true,
        canSelectMany: false,
        title: 'Choose the Spec2Test data folder',
        defaultUri: vscode.Uri.file(path.dirname(current)),
        openLabel: 'Use this folder',
      });
      if (!picked?.[0]) {
        return;
      }
      target = path.resolve(picked[0].fsPath);
    }
    if (target === current) {
      return;
    }
    const inside = (child: string, parent: string) => child.startsWith(parent + path.sep);
    if (inside(target, current) || inside(current, target)) {
      void vscode.window.showErrorMessage('The new folder and the current one cannot be inside each other.');
      return;
    }
    const hasProjects = fs.existsSync(path.join(target, 'projects.json'));
    const isEmpty = !fs.existsSync(target) || fs.readdirSync(target).length === 0;
    let copy = false;
    if (hasProjects) {
      const answer = await vscode.window.showWarningMessage(`${target} already holds Spec2Test projects.`, { modal: true, detail: 'Spec2Test will use them as they are; your current projects are not copied.' }, 'Use it');
      if (!answer) {
        return;
      }
    } else {
      const hasCurrent = fs.existsSync(path.join(current, 'projects.json'));
      const detail = [
        isEmpty ? '' : `The folder is not empty: Spec2Test will add its files inside it.`,
        hasCurrent ? 'Copy brings projects.json and the work areas along. Your input folders and their results are not touched, and the old folder is left in place for you to delete.' : '',
      ].filter(Boolean).join('\n\n');
      const answer = await vscode.window.showWarningMessage(
        `Use ${target} as the data folder?`,
        { modal: true, detail: detail || undefined },
        ...(hasCurrent ? ['Copy and switch', 'Switch without copying'] : ['Switch']),
      );
      if (!answer) {
        return;
      }
      copy = answer === 'Copy and switch';
    }
    try {
      if (copy) {
        fs.cpSync(current, target, { recursive: true, force: false, errorOnExist: false });
      } else {
        fs.mkdirSync(target, { recursive: true });
      }
    } catch (error) {
      void vscode.window.showErrorMessage(`Could not prepare ${target}: ${(error as Error).message}`);
      return;
    }
    await this.settings.update('dataFolder', target === defaultDataRoot() ? undefined : target, vscode.ConfigurationTarget.Global);
  }

  /** The setting changed (from the command or by hand): follow it. */
  private async applyDataFolder(): Promise<void> {
    const before = dataRoot();
    setDataRoot(this.settings.get<string>('dataFolder', ''));
    if (dataRoot() === before) {
      return;
    }
    fs.mkdirSync(dataRoot(), { recursive: true });
    this.watchProject();
    await this.rescan();
    const state = (await this.dockerService.probe()).state;
    if (state === 'running' || state === 'starting' || state === 'outdated') {
      // The container mounts the folder, so it has to be recreated to see the new one.
      await this.startService();
    }
    this.post();
  }

  // --- what each container needs ----------------------------------------------------------------

  private get settings(): vscode.WorkspaceConfiguration {
    return vscode.workspace.getConfiguration('spec2test');
  }

  private get version(): string {
    return String(this.context.extension.packageJSON.version);
  }

  private inputProcessorConfig(): ServiceConfig {
    const image = wantedImage('inputProcessor', this.version, this.settings.get<string>('image.inputProcessor', ''));
    return {
      container: CONTAINER_NAME.inputProcessor,
      image,
      port: this.port,
      spec: async (resolved) =>
        inputProcessorSpec({
          image: resolved,
          port: this.port,
          dataRoot: dataRoot(),
          tuning: this.env.read(),
          secrets: Object.keys(await this.env.secretValues(this.keyNames())),
          gpu: this.settings.get<boolean>('gpu', false),
          user: await this.runAsUser(),
        }),
      prepare: async (spec) => {
        if (!spec.user) {
          return undefined;
        }
        const root = dataRoot();
        fs.mkdirSync(path.join(root, HF_CACHE_DIRNAME), { recursive: true });
        if (!hasForeignOwner(root, spec.user.uid)) {
          return undefined;
        }
        this.logs.appendLine('Giving you back the files an earlier run left owned by root…');
        const { uid, gid } = spec.user;
        return this.dockerService.runOnce(['run', '--rm', '--user', '0', '--entrypoint', 'chown', '-v', `${toDockerPath(root)}:/projects`, spec.image, '-R', `${uid}:${gid}`, '/projects']);
      },
      secretValues: () => this.env.secretValues(this.keyNames()),
    };
  }

  /** On native Docker Engine for Linux the container runs as you, so the files it writes stay yours. */
  private async runAsUser(): Promise<{ uid: number; gid: number } | undefined> {
    if (typeof process.getuid !== 'function' || typeof process.getgid !== 'function') {
      return undefined;
    }
    return shouldMapUser(os.platform(), await engineInfo()) ? { uid: process.getuid(), gid: process.getgid() } : undefined;
  }

  private get crawlerEnabled(): boolean {
    return this.settings.get<boolean>('webCrawler.enabled', true);
  }

  private get crawlerPort(): number {
    return this.settings.get<number>('webCrawler.port', 8000);
  }

  private crawlerConfig(): ServiceConfig {
    const image = wantedImage('webCrawler', this.version, this.settings.get<string>('image.webCrawler', ''));
    const login = path.join(dataRoot(), 'auth_actions.json');
    return {
      container: CONTAINER_NAME.webCrawler,
      image,
      port: this.crawlerPort,
      spec: async (resolved) => webCrawlerSpec({ image: resolved, port: this.crawlerPort, authActionsFile: fs.existsSync(login) ? login : undefined }),
      secretValues: async () => ({}),
    };
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
    this.refreshWorkAreas();
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
    const crawlerBefore = JSON.stringify(this.crawler);
    const engineUp = this.docker.state !== 'not-installed' && this.docker.state !== 'daemon-down';
    this.crawler = this.crawlerEnabled && engineUp ? await this.crawlerService.probeContainer() : undefined;
    if (JSON.stringify(this.docker) !== before || JSON.stringify(this.crawler) !== crawlerBefore) {
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
    const docker = problem ? { ...this.docker, detail: problem } : this.docker;
    return {
      docker,
      dataFolder: { path: dataRoot(), isDefault: dataRoot() === defaultDataRoot() },
      crawler: this.crawler,
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
      case 'installAgents':
        return this.installAgents();
      case 'changeDataFolder':
        return this.changeDataFolder(message.reset);
      case 'selectProject':
        await this.context.workspaceState.update(SELECTED_KEY, message.name);
        this.watchProject();
        await this.useInCopilot(message.name, false);
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
        await this.env.saveTuning(message.values);
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
    const start = this.featuresDirOf(name) ?? vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? os.homedir();
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
    if (which === 'preprocessed') {
      void vscode.window.showInformationMessage('Pre-processed files live in the Spec2Test work area and cannot be moved.');
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
    await this.rescan();
  }

  // --- agents (Gherkin-Generator for Copilot, Claude Code and Codex) -------------------------------

  private agentSettings(project: string | undefined): McpSettings {
    return {
      project,
      inputProcessorPort: this.port,
      webCrawler: this.crawlerEnabled ? { port: this.crawlerPort } : undefined,
    };
  }

  private async pickWorkspace(): Promise<string | undefined> {
    const folders = vscode.workspace.workspaceFolders ?? [];
    if (folders.length <= 1) {
      return folders[0]?.uri.fsPath;
    }
    const picked = await vscode.window.showQuickPick(
      folders.map((folder) => ({ label: folder.name, description: folder.uri.fsPath, value: folder.uri.fsPath })),
      { title: 'Add the Gherkin-Generator to which folder?' },
    );
    return picked?.value;
  }

  /** Copy the agent, skill and MCP settings into the open workspace for the tools the user picks. */
  async installAgents(): Promise<void> {
    const workspace = await this.pickWorkspace();
    if (!workspace) {
      void vscode.window.showWarningMessage('Open a folder first: the Gherkin-Generator is added to your project.');
      return;
    }
    const previous = this.context.workspaceState.get<{ targets: AgentTarget[] }>(AGENTS_KEY);
    const picks = await vscode.window.showQuickPick(
      TARGETS.map((target) => ({
        label: target.label,
        description: target.detail,
        target: target.id,
        picked: previous ? previous.targets.includes(target.id) : target.id !== 'codex' || fs.existsSync(path.join(workspace, '.codex')),
      })),
      { canPickMany: true, title: 'Add the Gherkin-Generator for…', placeHolder: 'Choose the tools you use in this project' },
    );
    if (!picks || picks.length === 0) {
      return;
    }
    const targets = picks.map((pick) => pick.target);
    const project = this.selected;
    try {
      const bundle = loadBundle(path.join(this.context.extensionPath, 'dist', 'agents'));
      const plan = planInstall(workspace, targets, bundle, this.agentSettings(project));
      const changed = plan.filter((item) => item.status === 'differs' && !item.merged);
      let overwrite = false;
      if (changed.length > 0) {
        const list = changed.map((item) => path.relative(workspace, item.file)).join('\n');
        const answer = await vscode.window.showWarningMessage(
          `${changed.length} file(s) in your project differ from the ones shipped with Spec2Test.`,
          { modal: true, detail: `${list}\n\nOverwrite replaces them; Keep mine leaves them as they are.` },
          'Overwrite',
          'Keep mine',
        );
        if (!answer) {
          return;
        }
        overwrite = answer === 'Overwrite';
      }
      const { written, skipped } = applyPlan(plan, overwrite);
      await this.context.workspaceState.update(AGENTS_KEY, { version: this.version, targets });
      const notes = [
        `${written.length} file(s) written${skipped.length ? `, ${skipped.length} kept` : ''}.`,
        project ? `The agents use project '${project}'.` : 'Create a project, then run this again so the agents know which one to use.',
        targets.includes('copilot') ? 'Copilot: start the servers from .vscode/mcp.json.' : '',
        targets.includes('claude') ? 'Claude Code: approve the project servers on first use.' : '',
        targets.includes('codex') ? 'Codex: trust the project so it reads .codex/config.toml.' : '',
        'The web-crawler agent also needs Node.js (npx) for the Playwright server.',
      ].filter(Boolean);
      void vscode.window.showInformationMessage(notes.join(' '));
    } catch (error) {
      void vscode.window.showErrorMessage(error instanceof McpFileError || error instanceof Error ? `Could not add the Gherkin-Generator: ${error.message}` : String(error));
    }
  }

  /** Point the installed agent configs at `name`. Quiet when nothing is installed unless `report` is set. */
  private async useInCopilot(name: string, report = true): Promise<void> {
    const workspace = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!workspace) {
      return;
    }
    if (installedMcpFiles(workspace).length === 0) {
      if (report) {
        const answer = await vscode.window.showInformationMessage('The Gherkin-Generator is not in this project yet.', 'Add it');
        if (answer) {
          await this.installAgents();
        }
      }
      return;
    }
    try {
      const changed = retargetProject(workspace, this.agentSettings(name));
      if (report || changed.length > 0) {
        void vscode.window.showInformationMessage(`Agents now use project '${name}' (${changed.map((file) => path.relative(workspace, file)).join(', ') || 'already set'}).`);
      }
    } catch (error) {
      throw new Error(`Could not update the agent settings: ${(error as Error).message}`);
    }
  }

  /** Once per workspace: offer the agent, or an update after the extension changed. */
  private async offerAgents(): Promise<void> {
    const workspace = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!workspace || this.context.workspaceState.get<string>(AGENTS_PROMPT_KEY) === 'never') {
      return;
    }
    const installed = this.context.workspaceState.get<{ version: string }>(AGENTS_KEY);
    if (installed?.version === this.version) {
      return;
    }
    const answer = await vscode.window.showInformationMessage(
      installed ? 'A newer Gherkin-Generator is available for this project.' : 'Add the Gherkin-Generator agent to this project?',
      installed ? 'Update' : 'Add',
      'Not now',
      'Never for this project',
    );
    if (answer === 'Update' || answer === 'Add') {
      await this.installAgents();
    } else if (answer === 'Never for this project') {
      await this.context.workspaceState.update(AGENTS_PROMPT_KEY, 'never');
    }
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
      case 'restart':
        return this.startService();
      case 'stop':
        await this.withBusy('Stopping…', async () => {
          await this.dockerService.down();
          if (this.crawler) {
            await this.crawlerService.down();
          }
        });
        return;
      case 'rebuild':
        return this.startService({ refresh: true });
      case 'logs':
        this.dockerService.showLogs();
        return;
      case 'crawlerLogs':
        this.crawlerService.showLogs();
        return;
    }
  }

  /** (Re)create the containers from the image this version wants. `refresh` pulls the newest copy first. */
  async startService(options: { refresh?: boolean } = {}): Promise<void> {
    const label = options.refresh ? 'Updating the image…' : 'Starting the input-processor…';
    await this.withBusy(label, async () => {
      // Docker would create a missing bind-mount source as root.
      fs.mkdirSync(dataRoot(), { recursive: true });
      const result = await this.dockerService.up(options);
      if (result.code !== 0) {
        this.dockerService.showLogs();
        throw new Error(`Docker could not start the service:\n${tail(result.stderr)}`);
      }
      this.setDocker('starting', label);
      if (!(await this.dockerService.waitUntilReachable())) {
        this.dockerService.showLogs();
        throw new Error('The input-processor did not answer within two minutes. Check the logs.');
      }
      await this.context.globalState.update(PENDING_KEY, false);
      if (this.crawlerEnabled) {
        // The crawler is optional: a failure here must not hide that the input-processor works.
        const crawled = await this.crawlerService.up(options);
        if (crawled.code !== 0) {
          void vscode.window.showWarningMessage(`The web crawler could not start: ${tail(crawled.stderr, 3)}`);
        }
      }
    });
  }

  private async applyEnv(): Promise<void> {
    const state = (await this.dockerService.probe()).state;
    if (state === 'running' || state === 'starting' || state === 'outdated') {
      await this.startService();
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
