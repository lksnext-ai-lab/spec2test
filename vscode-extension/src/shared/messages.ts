import type {
  FileCard,
  GherkinState,
  Job,
  LlmSettings,
  OrphanCard,
  ProviderInfo,
  TuningVariable,
} from './types';

export type DockerState =
  | 'no-repo'
  | 'not-installed'
  | 'daemon-down'
  | 'stopped'
  | 'starting'
  | 'running'
  | 'unhealthy';

export interface ProjectView {
  name: string;
  inputs: string;
  preprocessed: string;
  cache: string;
  features?: string;
  llm?: LlmSettings;
  vision?: LlmSettings;
}

export interface AppState {
  repo?: string;
  docker: { state: DockerState; detail?: string; busy?: string };
  projects: ProjectView[];
  selected?: string;
  defaults: { llm?: LlmSettings; vision?: LlmSettings };
  files: FileCard[];
  orphans: OrphanCard[];
  jobs: Job[];
  providers: ProviderInfo[];
  /** Which provider key variables have a value (never the value itself). */
  keys: Record<string, boolean>;
  tuning: TuningVariable[];
  tuningValues: Record<string, string>;
  /** Keys or tuning changed since the container last started. */
  envPending: boolean;
  gherkin: GherkinState;
  /** Set to make one input card scroll into view and flash; `nonce` repeats the effect. */
  highlight?: { name: string; nonce: number };
  /** The server's built-in default provider, used when nothing is configured. */
  fallbackProvider: string;
}

export type ProjectFolder = 'inputs' | 'cache' | 'preprocessed' | 'features';

export type FileOpenKind = 'original' | 'cache' | 'cache-preview' | 'preprocessed' | 'images';

export type ToHost =
  | { type: 'ready' }
  | { type: 'chooseRepo' }
  | { type: 'selectProject'; name: string }
  | { type: 'createProject' }
  | { type: 'removeProject'; name: string }
  | { type: 'projectFolder'; name: string; which: ProjectFolder; action: 'open' | 'change' }
  | { type: 'useInCopilot'; name: string }
  | { type: 'docker'; action: 'install' | 'startDocker' | 'start' | 'stop' | 'restart' | 'rebuild' | 'logs' }
  | { type: 'addFiles' }
  | { type: 'process'; files: string[]; force: boolean }
  | { type: 'processPending' }
  | { type: 'cancel' }
  | { type: 'open'; file: string; kind: FileOpenKind }
  | { type: 'history'; file: string }
  | { type: 'removeFile'; file: string }
  | { type: 'cleanOrphans' }
  | { type: 'saveModel'; scope: 'defaults' | 'project'; kind: 'llm' | 'vision'; value?: LlmSettings }
  | { type: 'saveKey'; env: string; value: string }
  | { type: 'saveTuning'; values: Record<string, string> }
  | { type: 'gherkin'; action: 'toggle' | 'reload' }
  | { type: 'openScenario'; file: string; line: number }
  | { type: 'applyEnv' };

export type ToWebview = { type: 'state'; state: AppState };
