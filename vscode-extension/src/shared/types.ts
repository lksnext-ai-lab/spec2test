/** Plain data shared by the extension host and the webview (no Node or VS Code imports). */

export type CacheState = 'new' | 'cached' | 'stale' | 'renamed';

export interface HistoryItem {
  path: string;
  label: string;
}

export interface FileCard {
  name: string;
  format: string;
  size: number;
  state: CacheState;
  processedAt?: string;
  provider?: string;
  model?: string;
  hasCache: boolean;
  hasPreprocessed: boolean;
  hasImages: boolean;
  history: HistoryItem[];
}

export interface OrphanCard {
  name: string;
  processedAt?: string;
}

export interface LlmSettings {
  provider?: string;
  model?: string;
}

export type Capability = 'text' | 'images' | 'video_inline' | 'video_upload';

export interface ProviderInfo {
  name: string;
  apiKeyEnv: string;
  defaultModel: string;
  capabilities: Capability[];
  models: { id: string; capabilities: Capability[] }[];
}

export interface TuningVariable {
  key: string;
  label: string;
  group: 'Video' | 'Logging';
  type: 'number' | 'boolean' | 'select';
  default: string;
  help: string;
  options?: string[];
}

export type JobStatus = 'queued' | 'running' | 'done' | 'error' | 'cancelled';

export interface Job {
  file: string;
  force: boolean;
  status: JobStatus;
  stage?: string;
  step?: { index: number; total: number };
  outcome?: string;
  error?: string;
}

/** A scenario that cites an input, as shown under the input's card. */
export interface GherkinScenarioRef {
  name: string;
  line: number;
}

/** A feature file that cites an input, with the scenarios that do. */
export interface GherkinFeatureRef {
  /** Path relative to the features folder, with forward slashes. */
  file: string;
  name: string;
  line: number;
  scenarios: GherkinScenarioRef[];
}

export interface GherkinWarning {
  kind: 'unknown-source' | 'untraced';
  file: string;
  line: number;
  text: string;
}

export interface GherkinState {
  /** The "Gherkin" view is switched on for the selected project. */
  enabled: boolean;
  /** Host path of the features folder, when one is set. */
  folder?: string;
  scanning: boolean;
  features: number;
  scenarios: number;
  generatedAt?: string;
  byInput: Record<string, GherkinFeatureRef[]>;
  warnings: GherkinWarning[];
  error?: string;
}
