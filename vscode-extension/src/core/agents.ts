import * as fs from 'node:fs';
import * as path from 'node:path';
import { unzipSync } from 'fflate';

/**
 * Puts the Gherkin-Generator agent into a user's project, for the three tools that read it:
 * GitHub Copilot (custom agents + .vscode/mcp.json), Claude Code (skill + subagent + .mcp.json)
 * and Codex (Agent Skills + .codex/config.toml). Pure file logic: no VS Code, so it is testable.
 */
export type AgentTarget = 'copilot' | 'claude' | 'codex';

export const TARGETS: { id: AgentTarget; label: string; detail: string }[] = [
  { id: 'copilot', label: 'GitHub Copilot', detail: '.github/agents, .vscode/mcp.json' },
  { id: 'claude', label: 'Claude Code', detail: '.claude/skills, .claude/agents, .mcp.json' },
  { id: 'codex', label: 'Codex', detail: '.agents/skills, .codex/config.toml' },
];

export const SKILL_NAME = 'gherkin-generator';
const SKILL_ARCHIVE = `${SKILL_NAME}.skill`;
const PLAYWRIGHT = { command: 'npx', args: ['@playwright/mcp@latest'] };
const BLOCK_START = '# >>> spec2test (managed by the Spec2Test extension) >>>';
const BLOCK_END = '# <<< spec2test <<<';

/** Everything the extension ships: the Copilot agent files and the unpacked skill. */
export interface Bundle {
  /** `<name>.agent.md` -> content. */
  copilot: Map<string, Buffer>;
  /** Path inside the skill folder -> content. */
  skill: Map<string, Buffer>;
}

export function loadBundle(dir: string): Bundle {
  const copilot = new Map<string, Buffer>();
  for (const name of fs.readdirSync(dir)) {
    if (name.endsWith('.agent.md')) {
      copilot.set(name, fs.readFileSync(path.join(dir, name)));
    }
  }
  const skill = new Map<string, Buffer>();
  const files = unzipSync(new Uint8Array(fs.readFileSync(path.join(dir, SKILL_ARCHIVE))));
  for (const [entry, data] of Object.entries(files)) {
    const relative = entry.startsWith(`${SKILL_NAME}/`) ? entry.slice(SKILL_NAME.length + 1) : entry;
    if (!entry.endsWith('/') && relative) {
      skill.set(relative, Buffer.from(data));
    }
  }
  if (!skill.has('SKILL.md')) {
    throw new Error(`${SKILL_ARCHIVE} has no SKILL.md.`);
  }
  return { copilot, skill };
}

export interface McpSettings {
  /** Selected Spec2Test project; the header is left out when there is none. */
  project?: string;
  inputProcessorPort: number;
  webCrawler?: { port: number };
}

export class McpFileError extends Error {}

export type FileStatus = 'new' | 'same' | 'differs';

export interface PlannedFile {
  target: AgentTarget;
  file: string;
  content: Buffer;
  status: FileStatus;
  /** Configuration files are merged, so they never need the user's go-ahead. */
  merged: boolean;
}

function inputProcessorEntry(settings: McpSettings): Record<string, unknown> {
  return {
    type: 'http',
    url: `http://localhost:${settings.inputProcessorPort}/mcp`,
    ...(settings.project ? { headers: { 'X-Spec2Test-Project': settings.project } } : {}),
  };
}

function jsonServers(settings: McpSettings, stdioType: boolean): Record<string, unknown> {
  return {
    'input-processor': inputProcessorEntry(settings),
    ...(settings.webCrawler ? { 'web-crawler': { type: 'http', url: `http://localhost:${settings.webCrawler.port}/mcp` } } : {}),
    playwright: stdioType ? { type: 'stdio', ...PLAYWRIGHT } : { ...PLAYWRIGHT },
  };
}

/** Our servers replace the old ones; `playwright` is only added, because the user may have set it up their way. */
export function mergeMcpJson(existing: string | undefined, key: 'servers' | 'mcpServers', ours: Record<string, unknown>, indent: string | number): string {
  let root: Record<string, unknown> = {};
  if (existing?.trim()) {
    try {
      root = JSON.parse(existing) as Record<string, unknown>;
    } catch {
      throw new McpFileError('It is not valid JSON (comments are not supported). Add the servers by hand.');
    }
  }
  const servers = { ...((root[key] as Record<string, unknown> | undefined) ?? {}) };
  for (const [name, entry] of Object.entries(ours)) {
    if (name !== 'playwright' || !(name in servers)) {
      servers[name] = entry;
    }
  }
  return JSON.stringify({ ...root, [key]: servers }, null, indent) + '\n';
}

function tomlTables(text: string): Set<string> {
  return new Set(Array.from(text.matchAll(/^\s*\[mcp_servers\.([\w-]+)\]/gm)).map((match) => match[1]));
}

function withoutBlock(text: string): string {
  const start = text.indexOf(BLOCK_START);
  const end = text.indexOf(BLOCK_END);
  if (start < 0 || end < start) {
    return text;
  }
  return text.slice(0, start).replace(/\n+$/, '\n') + text.slice(end + BLOCK_END.length).replace(/^\n+/, '');
}

/** Codex keeps its servers in TOML tables. We own one marked block and never touch anything outside it. */
export function mergeCodexToml(existing: string | undefined, settings: McpSettings): string {
  const outside = withoutBlock(existing ?? '');
  const taken = tomlTables(outside);
  const ours = ['input-processor', ...(settings.webCrawler ? ['web-crawler'] : [])];
  const clash = ours.find((name) => taken.has(name));
  if (clash) {
    throw new McpFileError(`It already defines [mcp_servers.${clash}] outside the Spec2Test block. Edit that table by hand.`);
  }
  const lines = [BLOCK_START, '[mcp_servers.input-processor]', `url = "http://localhost:${settings.inputProcessorPort}/mcp"`];
  if (settings.project) {
    lines.push(`http_headers = { "X-Spec2Test-Project" = "${settings.project}" }`);
  }
  if (settings.webCrawler) {
    lines.push('', '[mcp_servers.web-crawler]', `url = "http://localhost:${settings.webCrawler.port}/mcp"`);
  }
  if (!taken.has('playwright')) {
    lines.push('', '[mcp_servers.playwright]', `command = "${PLAYWRIGHT.command}"`, `args = ["${PLAYWRIGHT.args[0]}"]`);
  }
  lines.push(BLOCK_END, '');
  const head = outside.trim() ? outside.replace(/\n*$/, '\n\n') : '';
  return head + lines.join('\n');
}

function read(file: string): string | undefined {
  return fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : undefined;
}

function statusOf(file: string, content: Buffer): FileStatus {
  if (!fs.existsSync(file)) {
    return 'new';
  }
  return fs.readFileSync(file).equals(content) ? 'same' : 'differs';
}

/** What installing `targets` would write into `workspace`. Throws McpFileError when a config file cannot be merged. */
export function planInstall(workspace: string, targets: AgentTarget[], bundle: Bundle, settings: McpSettings): PlannedFile[] {
  const planned: PlannedFile[] = [];
  const add = (target: AgentTarget, relative: string, content: Buffer | string, merged = false) => {
    const file = path.join(workspace, ...relative.split('/'));
    const buffer = Buffer.isBuffer(content) ? content : Buffer.from(content, 'utf8');
    planned.push({ target, file, content: buffer, status: statusOf(file, buffer), merged });
  };
  const mcp = (target: AgentTarget, relative: string, build: (existing: string | undefined) => string) => {
    try {
      add(target, relative, build(read(path.join(workspace, ...relative.split('/')))), true);
    } catch (error) {
      if (error instanceof McpFileError) {
        throw new McpFileError(`${relative}: ${error.message}`);
      }
      throw error;
    }
  };

  for (const target of targets) {
    if (target === 'copilot') {
      for (const [name, content] of bundle.copilot) {
        add(target, `.github/agents/${name}`, content);
      }
      mcp(target, '.vscode/mcp.json', (existing) => mergeMcpJson(existing, 'servers', jsonServers(settings, true), '\t'));
    } else if (target === 'claude') {
      for (const [name, content] of bundle.skill) {
        add(target, `.claude/skills/${SKILL_NAME}/${name}`, content);
      }
      const crawler = bundle.skill.get('agents/web-crawler.md');
      if (crawler) {
        add(target, '.claude/agents/web-crawler.md', crawler);
      }
      mcp(target, '.mcp.json', (existing) => mergeMcpJson(existing, 'mcpServers', jsonServers(settings, false), 2));
    } else {
      for (const [name, content] of bundle.skill) {
        add(target, `.agents/skills/${SKILL_NAME}/${name}`, content);
      }
      mcp(target, '.codex/config.toml', (existing) => mergeCodexToml(existing, settings));
    }
  }
  return planned;
}

/** Write the files; `overwrite` decides what happens to existing files that differ (merged configs are always written). */
export function applyPlan(planned: PlannedFile[], overwrite: boolean): { written: string[]; skipped: string[] } {
  const written: string[] = [];
  const skipped: string[] = [];
  for (const item of planned) {
    if (item.status === 'same') {
      continue;
    }
    if (item.status === 'differs' && !item.merged && !overwrite) {
      skipped.push(item.file);
      continue;
    }
    fs.mkdirSync(path.dirname(item.file), { recursive: true });
    fs.writeFileSync(item.file, item.content);
    written.push(item.file);
  }
  return { written, skipped };
}

/** The MCP config files of `workspace` that already hold our `input-processor` server. */
export function installedMcpFiles(workspace: string): { target: AgentTarget; file: string }[] {
  const found: { target: AgentTarget; file: string }[] = [];
  const json = (target: AgentTarget, relative: string, key: string) => {
    try {
      const root = JSON.parse(read(path.join(workspace, relative)) ?? '{}') as Record<string, Record<string, unknown> | undefined>;
      if (root[key]?.['input-processor']) {
        found.push({ target, file: path.join(workspace, relative) });
      }
    } catch {
      // A file we cannot read is not one we manage.
    }
  };
  json('copilot', '.vscode/mcp.json', 'servers');
  json('claude', '.mcp.json', 'mcpServers');
  const toml = path.join(workspace, '.codex', 'config.toml');
  if (read(toml)?.includes(BLOCK_START)) {
    found.push({ target: 'codex', file: toml });
  }
  return found;
}

/** Point every installed config at `settings.project` (and the current ports) without touching the agent files. */
export function retargetProject(workspace: string, settings: McpSettings): string[] {
  const changed: string[] = [];
  for (const { target, file } of installedMcpFiles(workspace)) {
    const existing = fs.readFileSync(file, 'utf8');
    let next: string;
    if (target === 'codex') {
      next = mergeCodexToml(existing, settings);
    } else {
      const key = target === 'copilot' ? 'servers' : 'mcpServers';
      next = mergeMcpJson(existing, key, jsonServers(settings, target === 'copilot'), target === 'copilot' ? '\t' : 2);
    }
    if (next !== existing) {
      fs.writeFileSync(file, next, 'utf8');
      changed.push(file);
    }
  }
  return changed;
}
