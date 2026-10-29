import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { AppState } from '../../src/shared/messages';
import type { FileCard, Job } from '../../src/shared/types';

// The webview talks to the editor through acquireVsCodeApi(), which only exists inside a webview.
vi.mock('../vscode', () => ({ send: vi.fn(), vscode: { postMessage: vi.fn(), getState: vi.fn(), setState: vi.fn() } }));

import { MainView } from '../views/MainView';

/**
 * Regression tests for MainView, which is about to be split into smaller components: they pin what
 * each state of the sidebar shows, as rendered text, not how the component is built.
 */
const card = (name: string, state: FileCard['state'] = 'new'): FileCard => ({
  name,
  format: name.slice(name.lastIndexOf('.')),
  size: 2048,
  state,
  hasCache: state === 'cached',
  hasPreprocessed: false,
  hasImages: false,
  history: [],
});

function makeState(overrides: Partial<AppState> = {}): AppState {
  return {
    docker: { state: 'running' },
    dataFolder: { path: '/home/me/.spec2test', isDefault: true },
    projects: [{ name: 'shop-app', title: 'Shop App', inputs: '/home/me/specs', preprocessed: '/p', cache: '/c' }],
    selected: 'shop-app',
    defaults: {},
    files: [],
    orphans: [],
    jobs: [],
    providers: [],
    keys: {},
    tuning: [],
    tuningValues: {},
    envPending: false,
    gherkin: { enabled: false, scanning: false, features: 0, scenarios: 0, byInput: {}, warnings: [] },
    fallbackProvider: 'google_genai',
    ...overrides,
  };
}

const render = (state: AppState) => renderToStaticMarkup(<MainView state={state} openSettings={() => undefined} />);
const text = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
const job = (file: string, status: Job['status'], extra: Partial<Job> = {}): Job => ({ file, force: false, status, ...extra });

describe('MainView without a project', () => {
  const html = render(makeState({ projects: [], selected: undefined }));

  it('invites the user to create the first project', () => {
    expect(text(html)).toContain('Create your first project');
    expect(text(html)).toContain('New project');
  });

  it('shows no file list and a disabled project dropdown placeholder', () => {
    expect(text(html)).not.toContain('Add files');
    expect(html).toContain('No projects yet');
  });
});

describe('MainView when the container is not usable', () => {
  it.each([
    ['stopped', 'The input-processor is stopped', 'Start input-processor'],
    ['unhealthy', 'The input-processor is not responding', 'Update image and restart'],
    ['not-installed', 'Docker is not installed', 'Get Docker'],
    ['daemon-down', 'Docker is not running', 'Start Docker'],
  ] as const)('explains %s and offers the one fix', (docker, title, action) => {
    const out = text(render(makeState({ docker: { state: docker } })));
    expect(out).toContain(title);
    expect(out).toContain(action);
  });

  it('shows the detail the host gives instead of the default sentence', () => {
    const out = text(render(makeState({ docker: { state: 'stopped', detail: 'exited (1)' } })));
    expect(out).toContain('exited (1)');
    expect(out).not.toContain('Start it to process your files.');
  });

  it('tells the user that a newer image is available, without calling Docker broken', () => {
    const out = text(render(makeState({ docker: { state: 'outdated' } })));
    expect(out).toContain('A newer image is available');
    expect(out).toContain('Update image and restart');
    expect(out).not.toContain('Docker is not running');
  });

  it.each(['running', 'starting'] as const)('shows no banner while %s', (docker) => {
    const out = text(render(makeState({ docker: { state: docker } })));
    expect(out).not.toContain('is stopped');
    expect(out).not.toContain('is not responding');
    expect(out).not.toContain('Docker is not');
  });

  it('shows no banner while a start or stop is in progress', () => {
    expect(text(render(makeState({ docker: { state: 'stopped', busy: 'Starting…' } })))).not.toContain('The input-processor is stopped');
  });
});

describe('MainView with a project', () => {
  it('shows the project by its display name, with the file count and an empty list message', () => {
    const out = text(render(makeState()));
    expect(out).toContain('Shop App');
    expect(out).toContain('Files 0');
    expect(out).toContain('No files yet.');
  });

  it('lists the files and counts the ones that still need processing on the button', () => {
    const out = text(render(makeState({ files: [card('a.md', 'cached'), card('b.pdf', 'new'), card('c.mp4', 'stale')] })));
    expect(out).toContain('Files 3');
    expect(out).toContain('a.md');
    expect(out).toContain('b.pdf');
    expect(out).toContain('Process 2');
    expect(out).not.toContain('No files yet.');
  });

  it('disables Process when everything is cached', () => {
    const html = render(makeState({ files: [card('a.md', 'cached')] }));
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>(?:(?!<\/button>).)*Process/s);
  });

  it('disables Process while Docker cannot be used', () => {
    const html = render(makeState({ docker: { state: 'daemon-down' }, files: [card('a.md')] }));
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>(?:(?!<\/button>).)*Process 1/s);
  });

  it('turns Process into Cancel while a job is queued or running', () => {
    for (const status of ['queued', 'running'] as const) {
      const out = text(render(makeState({ files: [card('a.md')], jobs: [job('a.md', status)] })));
      expect(out).toContain('Cancel');
      expect(out).not.toMatch(/Process \d/);
    }
  });

  it('shows the live stage of the file being processed', () => {
    const out = text(render(makeState({ files: [card('a.md')], jobs: [job('a.md', 'running', { stage: 'Processing a.md…' })] })));
    expect(out).toContain('Processing a.md…');
  });

  it('counts results without a source file, in the singular and the plural', () => {
    expect(text(render(makeState({ orphans: [{ name: 'x.md' }] })))).toContain('1 result without a source file');
    expect(text(render(makeState({ orphans: [{ name: 'x.md' }, { name: 'y.md' }] })))).toContain('2 results without a source file');
    expect(text(render(makeState()))).not.toContain('without a source file');
  });

  it('shows the Gherkin summary only when the view is switched on', () => {
    const off = text(render(makeState({ files: [card('a.md')] })));
    const on = text(render(makeState({ files: [card('a.md')], gherkin: { enabled: true, folder: '/f', scanning: false, features: 2, scenarios: 5, byInput: {}, warnings: [] } })));
    expect(off).not.toContain('5 scenarios');
    expect(on).toContain('5');
  });

  it('keeps the Gherkin reload button disabled until a features folder is set', () => {
    const none = render(makeState());
    expect(none).toMatch(/aria-label="Reload Gherkin traceability"[^>]*disabled=""|disabled=""[^>]*aria-label="Reload Gherkin traceability"/);
    const set = render(makeState({ gherkin: { enabled: false, folder: '/f', scanning: false, features: 0, scenarios: 0, byInput: {}, warnings: [] } }));
    expect(set).not.toMatch(/aria-label="Reload Gherkin traceability"[^>]*disabled=""|disabled=""[^>]*aria-label="Reload Gherkin traceability"/);
  });
});
