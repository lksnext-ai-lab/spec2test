import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { beforeAll, beforeEach, describe, expect, it } from 'vitest';
import {
  McpFileError,
  applyPlan,
  installedMcpFiles,
  loadBundle,
  mergeCodexToml,
  mergeMcpJson,
  planInstall,
  retargetProject,
  type Bundle,
  type McpSettings,
} from '../src/core/agents';

const REPO = path.resolve(__dirname, '..', '..');
const settings: McpSettings = { project: 'demo', inputProcessorPort: 8003, webCrawler: { port: 8000 } };

let bundle: Bundle;
let workspace: string;

beforeAll(() => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 's2t-bundle-'));
  for (const name of fs.readdirSync(path.join(REPO, '.github', 'agents'))) {
    fs.copyFileSync(path.join(REPO, '.github', 'agents', name), path.join(dir, name.toLowerCase()));
  }
  fs.copyFileSync(path.join(REPO, 'gherkin-generator.skill'), path.join(dir, 'gherkin-generator.skill'));
  bundle = loadBundle(dir);
});

beforeEach(() => {
  workspace = fs.mkdtempSync(path.join(os.tmpdir(), 's2t-ws-'));
});

const json = (relative: string) => JSON.parse(fs.readFileSync(path.join(workspace, relative), 'utf8'));
const install = (targets: Parameters<typeof planInstall>[1], overwrite = false) => applyPlan(planInstall(workspace, targets, bundle, settings), overwrite);

describe('loadBundle', () => {
  it('reads both Copilot agents and unpacks the skill without its top folder', () => {
    expect([...bundle.copilot.keys()].sort()).toEqual(['gherkin-generator.agent.md', 'web-crawler.agent.md']);
    expect(bundle.skill.has('SKILL.md')).toBe(true);
    expect(bundle.skill.has('agents/web-crawler.md')).toBe(true);
    expect(bundle.skill.has('scripts/run_lint.py')).toBe(true);
  });
});

describe('install', () => {
  it('writes the Copilot agents and a merged .vscode/mcp.json', () => {
    install(['copilot']);
    expect(fs.existsSync(path.join(workspace, '.github/agents/gherkin-generator.agent.md'))).toBe(true);
    const servers = json('.vscode/mcp.json').servers;
    expect(servers['input-processor']).toEqual({ type: 'http', url: 'http://localhost:8003/mcp', headers: { 'X-Spec2Test-Project': 'demo' } });
    expect(servers['web-crawler'].url).toBe('http://localhost:8000/mcp');
    expect(servers.playwright).toEqual({ type: 'stdio', command: 'npx', args: ['@playwright/mcp@latest'] });
  });

  it('writes the Claude Code skill, subagent and .mcp.json', () => {
    install(['claude']);
    expect(fs.existsSync(path.join(workspace, '.claude/skills/gherkin-generator/SKILL.md'))).toBe(true);
    expect(fs.existsSync(path.join(workspace, '.claude/agents/web-crawler.md'))).toBe(true);
    expect(json('.mcp.json').mcpServers['input-processor'].headers).toEqual({ 'X-Spec2Test-Project': 'demo' });
  });

  it('writes the Codex skill and a managed block in .codex/config.toml', () => {
    install(['codex']);
    expect(fs.existsSync(path.join(workspace, '.agents/skills/gherkin-generator/SKILL.md'))).toBe(true);
    const toml = fs.readFileSync(path.join(workspace, '.codex/config.toml'), 'utf8');
    expect(toml).toContain('[mcp_servers.input-processor]');
    expect(toml).toContain('http_headers = { "X-Spec2Test-Project" = "demo" }');
    expect(toml).toContain('[mcp_servers.playwright]');
  });

  it('is idempotent: a second run writes nothing', () => {
    install(['copilot', 'claude', 'codex']);
    const again = install(['copilot', 'claude', 'codex']);
    expect(again).toEqual({ written: [], skipped: [] });
  });

  it('does not overwrite a changed agent file unless asked, but always updates the config', () => {
    install(['copilot']);
    const agent = path.join(workspace, '.github/agents/web-crawler.agent.md');
    fs.writeFileSync(agent, 'my edits');
    const plan = planInstall(workspace, ['copilot'], bundle, { ...settings, project: 'other' });
    expect(plan.find((item) => item.file === agent)!.status).toBe('differs');
    const kept = applyPlan(plan, false);
    expect(kept.skipped).toEqual([agent]);
    expect(fs.readFileSync(agent, 'utf8')).toBe('my edits');
    expect(json('.vscode/mcp.json').servers['input-processor'].headers['X-Spec2Test-Project']).toBe('other');
    applyPlan(plan, true);
    expect(fs.readFileSync(agent, 'utf8')).not.toBe('my edits');
  });
});

describe('mergeMcpJson', () => {
  const ours = { 'input-processor': { type: 'http', url: 'u' }, playwright: { command: 'npx' } };

  it('keeps other servers and keys, replaces ours and never replaces an existing playwright', () => {
    const existing = JSON.stringify({ inputs: [], servers: { mine: { url: 'x' }, playwright: { command: 'custom' }, 'input-processor': { url: 'old' } } });
    const merged = JSON.parse(mergeMcpJson(existing, 'servers', ours, 2));
    expect(merged.inputs).toEqual([]);
    expect(merged.servers.mine).toEqual({ url: 'x' });
    expect(merged.servers.playwright).toEqual({ command: 'custom' });
    expect(merged.servers['input-processor']).toEqual({ type: 'http', url: 'u' });
  });

  it('refuses a file with comments instead of damaging it', () => {
    expect(() => mergeMcpJson('{ // note\n}', 'servers', ours, 2)).toThrow(McpFileError);
  });
});

describe('mergeCodexToml', () => {
  it('keeps the user content, replaces its own block on update and drops the header without a project', () => {
    const first = mergeCodexToml('model = "x"\n', settings);
    expect(first.startsWith('model = "x"\n\n')).toBe(true);
    const second = mergeCodexToml(first, { ...settings, project: 'other' });
    expect(second.match(/managed by the Spec2Test extension/g)).toHaveLength(1);
    expect(second).toContain('"other"');
    expect(second).not.toContain('"demo"');
    expect(mergeCodexToml(undefined, { inputProcessorPort: 8003 })).not.toContain('http_headers');
  });

  it('refuses when the user defined the same server outside the block, and respects their playwright', () => {
    expect(() => mergeCodexToml('[mcp_servers.input-processor]\nurl = "x"\n', settings)).toThrow(McpFileError);
    expect(mergeCodexToml('[mcp_servers.playwright]\ncommand = "mine"\n', settings).match(/\[mcp_servers\.playwright\]/g)).toHaveLength(1);
  });
});

describe('retargetProject', () => {
  it('switches the project in every installed config and only those', () => {
    install(['copilot', 'codex']);
    const changed = retargetProject(workspace, { ...settings, project: 'second' });
    expect(changed).toHaveLength(2);
    expect(json('.vscode/mcp.json').servers['input-processor'].headers['X-Spec2Test-Project']).toBe('second');
    expect(fs.existsSync(path.join(workspace, '.mcp.json'))).toBe(false);
    expect(installedMcpFiles(workspace).map((item) => item.target).sort()).toEqual(['codex', 'copilot']);
    expect(retargetProject(workspace, { ...settings, project: 'second' })).toEqual([]);
  });
});
