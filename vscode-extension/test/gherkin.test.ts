import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { beforeEach, describe, expect, it } from 'vitest';
import { INDEX_FILE, buildIndex, parseFeature, scanFeatures, viewByInput, warningsOf, writeIndex } from '../src/core/gherkin';

const QABAGE = fs.readFileSync(path.join(__dirname, 'fixtures', 'qabage.feature'), 'utf8');
const lineOf = (text: string, needle: string): number => text.split('\n').findIndex((line) => line.includes(needle)) + 1;

describe('parseFeature: the example feature', () => {
  const parsed = parseFeature(QABAGE);

  it('reads the feature header', () => {
    expect(parsed.name).toBe('Assess Gherkin scenarios against the QABAGE quality attributes');
    expect(parsed.line).toBe(4);
    expect(parsed.inputs).toEqual(['SoA.md', 'QABAGE.md']);
    expect(parsed.created).toBe('2026-09-30');
  });

  it('finds the four scenarios with their lines, sources and dates', () => {
    expect(parsed.scenarios.map((s) => [s.name, s.line, s.sources, s.created])).toEqual([
      ['Flag a scenario that lacks a When step', lineOf(QABAGE, 'Flag a scenario'), ['QABAGE.md'], '2026-09-30'],
      ['Detect semantic duplicates within one feature file', lineOf(QABAGE, 'Detect semantic'), ['QABAGE.md'], '2026-09-30'],
      ['Detect a feature that lacks a prerequisite scenario', lineOf(QABAGE, 'lacks a prerequisite'), ['QABAGE.md'], '2026-09-30'],
      ['Route a low-confidence judgement to the LLM', lineOf(QABAGE, 'Route a low'), ['SoA.md'], '2026-09-30'],
    ]);
  });

  it('does not treat the Background or the steps as scenarios', () => {
    expect(parsed.scenarios).toHaveLength(4);
  });

  it('gives the exact columns of every input name, for editor links', () => {
    const lines = QABAGE.split('\n');
    expect(parsed.refs).toHaveLength(6); // 2 in the header + 4 sources
    for (const ref of parsed.refs) {
      expect(lines[ref.line - 1].slice(ref.start, ref.end)).toBe(ref.name);
    }
    expect(parsed.refs.filter((r) => r.kind === 'inputs').map((r) => r.name)).toEqual(['SoA.md', 'QABAGE.md']);
  });
});

describe('parseFeature: rules', () => {
  it('carries a Source across blank lines, other comments and tags', () => {
    const text = ['Feature: F', '', '  # Source: a.pdf', '', '  # a remark', '  @smoke @slow', '  Scenario: S', '    Given x'].join('\n');
    expect(parseFeature(text).scenarios[0].sources).toEqual(['a.pdf']);
  });

  it('drops a Source that is followed by something other than a scenario', () => {
    const text = ['Feature: F', '  Background:', '    # Source: a.pdf', '    Given a step', '  Scenario: S', '    Given x'].join('\n');
    expect(parseFeature(text).scenarios[0].sources).toEqual([]);
  });

  it('accepts several sources, keeps names with spaces and ignores duplicates and empty items', () => {
    const text = ['Feature: F', '  # Source: My Spec.pdf, login demo.mp4 , My Spec.pdf,, | Created: 2026-01-02', '  Scenario: S'].join('\n');
    const [scenario] = parseFeature(text).scenarios;
    expect(scenario.sources).toEqual(['My Spec.pdf', 'login demo.mp4']);
    expect(scenario.created).toBe('2026-01-02');
  });

  it('treats Scenario Outline, Scenario Template and Example as scenarios, but not Examples:', () => {
    const text = ['Feature: F', '  Scenario Outline: A', '    Given <x>', '    Examples:', '      | x |', '  Scenario Template: B', '  Example: C'].join('\n');
    const parsed = parseFeature(text);
    expect(parsed.scenarios.map((s) => [s.name, s.outline])).toEqual([
      ['A', true],
      ['B', true],
      ['C', false],
    ]);
  });

  it('reads # Inputs: only before Feature:', () => {
    const text = ['# Inputs: a.md', 'Feature: F', '  # Inputs: b.md', '  Scenario: S'].join('\n');
    const parsed = parseFeature(text);
    expect(parsed.inputs).toEqual(['a.md']);
    expect(parsed.refs.map((r) => r.name)).toEqual(['a.md']);
  });

  it('marks a scenario without a Source as untraced (no sources)', () => {
    expect(parseFeature('Feature: F\n  Scenario: S\n').scenarios[0].sources).toEqual([]);
  });

  it('ignores comments inside doc strings', () => {
    const text = ['Feature: F', '  # Source: real.md', '  Scenario: S', '    Given a text:', '      """', '      # Source: fake.md', '      Scenario: not one', '      """'].join('\n');
    const parsed = parseFeature(text);
    expect(parsed.scenarios).toHaveLength(1);
    expect(parsed.refs.map((r) => r.name)).toEqual(['real.md']);
  });

  it('handles Windows line endings and keeps columns right', () => {
    const text = 'Feature: F\r\n  # Source: a.md\r\n  Scenario: S\r\n';
    const parsed = parseFeature(text);
    expect(parsed.scenarios[0]).toMatchObject({ name: 'S', line: 3, sources: ['a.md'] });
    expect('  # Source: a.md'.slice(parsed.refs[0].start, parsed.refs[0].end)).toBe('a.md');
  });

  it('copes with an empty file and a file without a Feature', () => {
    expect(parseFeature('')).toMatchObject({ inputs: [], scenarios: [], refs: [] });
    expect(parseFeature('just text').name).toBeUndefined();
  });
});

describe('scanning and indexing a features folder', () => {
  let root: string;
  beforeEach(() => {
    root = fs.mkdtempSync(path.join(os.tmpdir(), 's2t-gherkin-'));
    fs.mkdirSync(path.join(root, 'qabage', 'deep'), { recursive: true });
    fs.mkdirSync(path.join(root, '.hidden'));
    fs.mkdirSync(path.join(root, 'node_modules'));
    fs.writeFileSync(path.join(root, 'qabage', 'assess.feature'), QABAGE);
    fs.writeFileSync(
      path.join(root, 'qabage', 'deep', 'other.feature'),
      ['Feature: Other', '  # Source: soa.md, Typo.pdf', '  Scenario: Typos', '  Scenario: Loose end'].join('\n'),
    );
    fs.writeFileSync(path.join(root, '.hidden', 'skip.feature'), 'Feature: hidden');
    fs.writeFileSync(path.join(root, 'node_modules', 'skip.feature'), 'Feature: modules');
    fs.writeFileSync(path.join(root, 'notes.txt'), 'not a feature');
  });

  it('finds .feature files in subfolders and skips dot-folders and node_modules', () => {
    expect(scanFeatures(root).map((file) => path.relative(root, file))).toEqual([path.join('qabage', 'assess.feature'), path.join('qabage', 'deep', 'other.feature')]);
    expect(scanFeatures(path.join(root, 'missing'))).toEqual([]);
  });

  it('builds the index with relative posix paths, by-input references, unknown sources and untraced scenarios', () => {
    const index = buildIndex('demo', root, ['SoA.md', 'QABAGE.md'], new Date('2026-09-30T10:00:00Z'));

    expect(index.project).toBe('demo');
    expect(index.features.map((f) => f.file)).toEqual(['qabage/assess.feature', 'qabage/deep/other.feature']);
    expect(index.byInput['QABAGE.md'].map((r) => r.scenario)).toEqual([
      'Flag a scenario that lacks a When step',
      'Detect semantic duplicates within one feature file',
      'Detect a feature that lacks a prerequisite scenario',
    ]);
    expect(index.byInput['SoA.md']).toHaveLength(1);
    expect(index.unknownSources).toEqual([
      { file: 'qabage/deep/other.feature', line: 2, name: 'soa.md', suggestion: 'SoA.md' },
      { file: 'qabage/deep/other.feature', line: 2, name: 'Typo.pdf' },
    ]);
    // 'Typos' has a Source comment (with unknown names); only 'Loose end' has none at all.
    expect(index.untraced).toEqual([{ file: 'qabage/deep/other.feature', line: 4, scenario: 'Loose end' }]);
  });

  it('projects the index to what each input card shows', () => {
    const index = buildIndex('demo', root, ['SoA.md', 'QABAGE.md', 'Lonely.pdf']);
    const view = viewByInput(index, ['SoA.md', 'QABAGE.md', 'Lonely.pdf']);

    expect(view['QABAGE.md']).toHaveLength(1);
    expect(view['QABAGE.md'][0]).toMatchObject({ file: 'qabage/assess.feature', name: expect.stringContaining('Assess') });
    expect(view['QABAGE.md'][0].scenarios).toHaveLength(3);
    // The header lists SoA.md too, so the feature shows up even for scenarios that cite only QABAGE.md.
    expect(view['SoA.md'][0].scenarios.map((s) => s.name)).toEqual(['Route a low-confidence judgement to the LLM']);
    expect(view['Lonely.pdf']).toEqual([]);
  });

  it('turns unknown sources and untraced scenarios into warnings, with a hint for case slips', () => {
    const warnings = warningsOf(buildIndex('demo', root, ['SoA.md', 'QABAGE.md']));
    expect(warnings.map((w) => w.text)).toEqual([
      "Unknown input 'soa.md'. Did you mean 'SoA.md'?",
      "Unknown input 'Typo.pdf'",
      "No # Source: for 'Loose end'",
    ]);
  });

  it('writes the index once and does not rewrite it when only the timestamp would change', () => {
    const first = buildIndex('demo', root, ['SoA.md'], new Date('2026-09-30T10:00:00Z'));
    expect(writeIndex(root, first)).toBe(true);
    const file = path.join(root, INDEX_FILE);
    const written = fs.readFileSync(file, 'utf8');
    expect(JSON.parse(written).byInput['SoA.md']).toHaveLength(1);
    expect(fs.existsSync(`${file}.tmp`)).toBe(false);

    expect(writeIndex(root, buildIndex('demo', root, ['SoA.md'], new Date('2027-01-01T00:00:00Z')))).toBe(false);
    expect(fs.readFileSync(file, 'utf8')).toBe(written);

    fs.appendFileSync(path.join(root, 'qabage', 'assess.feature'), '\n  # Source: SoA.md\n  Scenario: Added later\n');
    expect(writeIndex(root, buildIndex('demo', root, ['SoA.md']))).toBe(true);
  });
});
