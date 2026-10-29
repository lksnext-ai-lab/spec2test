import * as fs from 'node:fs';
import * as path from 'node:path';
import type { GherkinFeatureRef, GherkinWarning } from '../shared/types';

/**
 * Traceability comments in `.feature` files (the contract the Gherkin agent writes):
 *
 *   # Inputs: SoA.md, QABAGE.md          before `Feature:`; the inputs of the whole file
 *   # Created: 2026-09-30
 *
 *   # Source: QABAGE.md | Created: 2026-09-30   directly above a Scenario
 *   Scenario: ...
 *
 * `# Source:` belongs to the next Scenario / Scenario Outline / Scenario Template / Example,
 * with blank lines, other comments and tags allowed in between.
 */

export const INDEX_FILE = '.spec2test-traceability.json';
export const INDEX_VERSION = 1;

export type RefKind = 'inputs' | 'source';

/** One input file name written in a comment, with where to find it in the line. */
export interface SourceRef {
  name: string;
  kind: RefKind;
  /** 1-based line. */
  line: number;
  /** 0-based columns of the name inside that line. */
  start: number;
  end: number;
}

export interface ParsedScenario {
  name: string;
  line: number;
  outline: boolean;
  sources: string[];
  created?: string;
}

export interface ParsedFeature {
  name?: string;
  line?: number;
  inputs: string[];
  created?: string;
  scenarios: ParsedScenario[];
  refs: SourceRef[];
}

const FEATURE = /^\s*Feature\s*:\s*(.*?)\s*$/;
const SCENARIO = /^\s*(Scenario Outline|Scenario Template|Scenario|Example)\s*:\s*(.*?)\s*$/;
const INPUTS = /^(\s*#\s*Inputs\s*:)(.*)$/i;
const SOURCE = /^(\s*#\s*Source\s*:)([^|]*)(\|.*)?$/i;
const CREATED = /^\s*#\s*Created\s*:\s*(.*?)\s*$/i;
const CREATED_INLINE = /\|\s*Created\s*:\s*(.*?)\s*$/i;
const DOC_STRING = /^\s*("""|```)/;

/** Split "A.md, B.md" into names, remembering where each starts in the original line. */
function splitNames(list: string, offset: number): { name: string; start: number; end: number }[] {
  const names: { name: string; start: number; end: number }[] = [];
  let cursor = 0;
  for (const piece of list.split(',')) {
    const name = piece.trim();
    if (name) {
      const start = offset + cursor + (piece.length - piece.trimStart().length);
      names.push({ name, start, end: start + name.length });
    }
    cursor += piece.length + 1;
  }
  return names;
}

const unique = (values: string[]): string[] => [...new Set(values)];

export function parseFeature(text: string): ParsedFeature {
  const result: ParsedFeature = { inputs: [], scenarios: [], refs: [] };
  let pending: { sources: string[]; created?: string } | undefined;
  let inDocString = false;

  text.split(/\r?\n/).forEach((line, index) => {
    const number = index + 1;

    if (DOC_STRING.test(line)) {
      inDocString = !inDocString;
      pending = undefined;
      return;
    }
    if (inDocString) {
      return;
    }

    const inHeader = result.line === undefined;

    const inputs = INPUTS.exec(line);
    if (inputs) {
      if (inHeader) {
        const found = splitNames(inputs[2], inputs[1].length);
        result.inputs = unique([...result.inputs, ...found.map((item) => item.name)]);
        found.forEach((item) => result.refs.push({ ...item, kind: 'inputs', line: number }));
      }
      return;
    }

    const source = SOURCE.exec(line);
    if (source) {
      const found = splitNames(source[2], source[1].length);
      found.forEach((item) => result.refs.push({ ...item, kind: 'source', line: number }));
      pending = {
        sources: unique(found.map((item) => item.name)),
        created: CREATED_INLINE.exec(source[3] ?? '')?.[1],
      };
      return;
    }

    if (inHeader) {
      const created = CREATED.exec(line);
      if (created) {
        result.created = created[1];
        return;
      }
    }

    const feature = FEATURE.exec(line);
    if (feature && inHeader) {
      result.name = feature[1];
      result.line = number;
      pending = undefined;
      return;
    }

    const scenario = SCENARIO.exec(line);
    if (scenario) {
      result.scenarios.push({
        name: scenario[2],
        line: number,
        outline: scenario[1] !== 'Scenario' && scenario[1] !== 'Example',
        sources: pending?.sources ?? [],
        created: pending?.created,
      });
      pending = undefined;
      return;
    }

    // Blank lines, other comments and tags keep the pending Source; anything else drops it.
    const trimmed = line.trim();
    if (trimmed !== '' && !trimmed.startsWith('#') && !trimmed.startsWith('@')) {
      pending = undefined;
    }
  });

  return result;
}

/** `*.feature` files under `dir`, skipping dot-folders, node_modules and symlinked folders. */
export function scanFeatures(dir: string, maxDepth = 12): string[] {
  const found: string[] = [];
  const walk = (current: string, depth: number) => {
    let items: fs.Dirent[];
    try {
      items = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      return;
    }
    for (const item of items) {
      const full = path.join(current, item.name);
      if (item.isDirectory()) {
        if (depth < maxDepth && !item.name.startsWith('.') && item.name !== 'node_modules') {
          walk(full, depth + 1);
        }
      } else if (item.isFile() && item.name.endsWith('.feature')) {
        found.push(full);
      }
    }
  };
  if (fs.existsSync(dir)) {
    walk(dir, 0);
  }
  return found.sort();
}

export interface IndexedScenario {
  name: string;
  line: number;
  sources: string[];
  created?: string;
}

export interface IndexedFeature {
  file: string;
  name: string;
  line: number;
  inputs: string[];
  scenarios: IndexedScenario[];
}

export interface TraceIndex {
  version: number;
  generatedAt: string;
  project: string;
  features: IndexedFeature[];
  byInput: Record<string, { file: string; line: number; scenario: string }[]>;
  unknownSources: { file: string; line: number; name: string; suggestion?: string }[];
  untraced: { file: string; line: number; scenario: string }[];
}

const posix = (value: string): string => value.split(path.sep).join('/');

export function buildIndex(project: string, featuresDir: string, inputNames: string[], now: Date = new Date()): TraceIndex {
  const known = new Set(inputNames);
  const lower = new Map(inputNames.map((name) => [name.toLowerCase(), name]));
  const index: TraceIndex = {
    version: INDEX_VERSION,
    generatedAt: now.toISOString(),
    project,
    features: [],
    byInput: Object.fromEntries(inputNames.map((name) => [name, []])),
    unknownSources: [],
    untraced: [],
  };

  for (const full of scanFeatures(featuresDir)) {
    const file = posix(path.relative(featuresDir, full));
    const parsed = parseFeature(fs.readFileSync(full, 'utf8'));
    index.features.push({
      file,
      name: parsed.name ?? path.basename(full, '.feature'),
      line: parsed.line ?? 1,
      inputs: parsed.inputs,
      scenarios: parsed.scenarios.map(({ name, line, sources, created }) => ({ name, line, sources, created })),
    });

    for (const scenario of parsed.scenarios) {
      if (scenario.sources.length === 0) {
        index.untraced.push({ file, line: scenario.line, scenario: scenario.name });
      }
      for (const name of scenario.sources) {
        if (known.has(name)) {
          index.byInput[name].push({ file, line: scenario.line, scenario: scenario.name });
        }
      }
    }
    for (const ref of parsed.refs) {
      if (!known.has(ref.name)) {
        const suggestion = lower.get(ref.name.toLowerCase());
        index.unknownSources.push({ file, line: ref.line, name: ref.name, ...(suggestion ? { suggestion } : {}) });
      }
    }
  }
  return index;
}

/** What each input card needs: the features that cite it, with the scenarios that do. */
export function viewByInput(index: TraceIndex, inputNames: string[]): Record<string, GherkinFeatureRef[]> {
  const view: Record<string, GherkinFeatureRef[]> = {};
  for (const name of inputNames) {
    view[name] = index.features
      .filter((feature) => feature.inputs.includes(name) || feature.scenarios.some((scenario) => scenario.sources.includes(name)))
      .map((feature) => ({
        file: feature.file,
        name: feature.name,
        line: feature.line,
        scenarios: feature.scenarios.filter((scenario) => scenario.sources.includes(name)).map(({ name: scenario, line }) => ({ name: scenario, line })),
      }));
  }
  return view;
}

export function warningsOf(index: TraceIndex): GherkinWarning[] {
  return [
    ...index.unknownSources.map((item): GherkinWarning => ({
      kind: 'unknown-source',
      file: item.file,
      line: item.line,
      text: item.suggestion ? `Unknown input '${item.name}'. Did you mean '${item.suggestion}'?` : `Unknown input '${item.name}'`,
    })),
    ...index.untraced.map((item): GherkinWarning => ({ kind: 'untraced', file: item.file, line: item.line, text: `No # Source: for '${item.scenario}'` })),
  ];
}

/** Write the index next to the features, but only when something other than the timestamp changed. */
export function writeIndex(featuresDir: string, index: TraceIndex): boolean {
  const target = path.join(featuresDir, INDEX_FILE);
  if (fs.existsSync(target)) {
    try {
      const previous = JSON.parse(fs.readFileSync(target, 'utf8')) as TraceIndex;
      if (JSON.stringify({ ...previous, generatedAt: '' }) === JSON.stringify({ ...index, generatedAt: '' })) {
        return false;
      }
    } catch {
      // Unreadable or hand-edited: overwrite it.
    }
  }
  fs.mkdirSync(featuresDir, { recursive: true });
  const temporary = `${target}.tmp`;
  fs.writeFileSync(temporary, JSON.stringify(index, null, 2) + '\n', 'utf8');
  fs.renameSync(temporary, target);
  return true;
}
