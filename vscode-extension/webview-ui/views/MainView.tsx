import type { AppState, ProjectFolder } from '../../src/shared/messages';
import { Dropdown } from '../ui/Dropdown';
import { Icon } from '../ui/Icon';
import { Menu } from '../ui/Menu';
import { jobFor, shortPath } from '../util';
import { send } from '../vscode';
import { DockerFooter, primaryAction } from './DockerFooter';
import { FileCard } from './FileCard';
import { GherkinSummary } from './GherkinSummary';

export function MainView({ state, openSettings }: { state: AppState; openSettings: () => void }) {
  const { projects, selected, files, jobs, orphans, docker, gherkin, highlight } = state;
  const project = projects.find((item) => item.name === selected);
  const running = jobs.some((job) => job.status === 'running' || job.status === 'queued');
  const pending = files.filter((file) => file.state !== 'cached').length;
  const canProcess = !docker.busy && docker.state !== 'no-repo' && docker.state !== 'not-installed' && docker.state !== 'daemon-down';
  const fix = primaryAction(state);
  const blocked = docker.state !== 'running' && docker.state !== 'starting' && !docker.busy;
  const newProject = () => send({ type: 'createProject' });
  const folder = (which: ProjectFolder, action: 'open' | 'change') => send({ type: 'projectFolder', name: selected ?? '', which, action });

  return (
    <div className="screen">
      <header className="topbar">
        <div className="topbar-project">
          <Dropdown
            ariaLabel="Project"
            value={selected ?? ''}
            placeholder="No projects yet"
            searchable
            disabled={projects.length === 0}
            leading={<Icon name="folder" />}
            options={projects.map((item) => ({ value: item.name, label: item.name, hint: shortPath(item.inputs, 2) }))}
            onChange={(name) => send({ type: 'selectProject', name })}
            actions={[{ label: 'New project…', icon: 'plus', onSelect: newProject }]}
            emptyText="No project matches"
          />
        </div>
        <button className="icon-btn" title="New project" aria-label="New project" onClick={newProject} disabled={state.docker.state === 'no-repo'}>
          <Icon name="plus" />
        </button>
        <button className="icon-btn" title="Settings" aria-label="Settings" onClick={openSettings}>
          <Icon name="settings" />
        </button>
      </header>

      <div className="scroll">
        {blocked && fix ? (
          <div className={`notice notice-${docker.state === 'stopped' ? 'info' : 'warn'}`}>
            <Icon name="alert" />
            <div className="notice-body">
              <strong>{docker.state === 'stopped' ? 'The input-processor is stopped' : docker.state === 'unhealthy' ? 'The input-processor is not responding' : docker.state === 'no-repo' ? 'spec2test folder not found' : docker.state === 'not-installed' ? 'Docker is not installed' : 'Docker is not running'}</strong>
              <span>{docker.detail ?? (docker.state === 'stopped' ? 'Start it to process your files.' : docker.state === 'no-repo' ? 'Point Spec2Test at your clone of the repository.' : docker.state === 'not-installed' ? 'Spec2Test runs its processor in Docker.' : 'Start Docker Desktop, then it connects on its own.')}</span>
              <button className="primary" onClick={fix.run}>
                {fix.label}
              </button>
            </div>
          </div>
        ) : null}

        {!project ? (
          docker.state === 'no-repo' ? null : (
            <div className="empty">
              <Icon name="folder" size={30} />
              <h3>Create your first project</h3>
              <p className="muted">A project holds the specs and recordings of one application, plus their processed results.</p>
              <button className="primary" onClick={newProject}>
                <Icon name="plus" /> New project
              </button>
            </div>
          )
        ) : (
          <>
            <div className="projectline">
              <Icon name="folder" size={14} />
              <span className="projectline-path" title={`Inputs: ${project.inputs}\nCache: ${project.cache}\nPre-processed: ${project.preprocessed}`}>
                {shortPath(project.inputs, 3)}
              </span>
              <button className="icon-btn danger" title="Remove project" aria-label="Remove project" disabled={Boolean(docker.busy)} onClick={() => send({ type: 'removeProject', name: project.name })}>
                <Icon name="trash" />
              </button>
              <Menu
                label="Project actions"
                items={[
                  { label: 'Open inputs folder', icon: 'folder', onSelect: () => folder('inputs', 'open') },
                  { label: 'Open cache folder', icon: 'folder', onSelect: () => folder('cache', 'open') },
                  { label: 'Open pre-processed folder', icon: 'folder', onSelect: () => folder('preprocessed', 'open') },
                  { label: project.features ? 'Open features folder' : 'Set features folder…', icon: 'folder', onSelect: () => folder('features', 'open') },
                  { label: 'Change inputs folder…', icon: 'settings', separatorBefore: true, disabled: Boolean(docker.busy), onSelect: () => folder('inputs', 'change') },
                  { label: 'Change cache folder…', icon: 'settings', disabled: Boolean(docker.busy), onSelect: () => folder('cache', 'change') },
                  { label: 'Change pre-processed folder…', icon: 'settings', disabled: Boolean(docker.busy), onSelect: () => folder('preprocessed', 'change') },
                  ...(project.features ? [{ label: 'Change features folder…', icon: 'settings' as const, onSelect: () => folder('features', 'change') }] : []),
                  { label: 'Use this project for agents', icon: 'external', separatorBefore: true, onSelect: () => send({ type: 'useInCopilot', name: project.name }) },
                  { label: 'Remove project', icon: 'trash', danger: true, separatorBefore: true, onSelect: () => send({ type: 'removeProject', name: project.name }) },
                ]}
              />
            </div>

            <div className="addfiles">
              <button onClick={() => send({ type: 'addFiles' })}>
                <Icon name="upload" size={14} /> Add files…
              </button>
              <span className="muted small">or drop them on “Drop files” above</span>
            </div>

            <div className="listhead">
              <h2>
                Files <span className="count">{files.length}</span>
              </h2>
              <div className="listhead-actions">
                <div className={`split ${gherkin.enabled ? 'is-on' : ''}`} role="group" aria-label="Gherkin traceability">
                  <button
                    className="split-main"
                    aria-pressed={gherkin.enabled}
                    title={gherkin.enabled ? 'Hide the features and scenarios under each input' : gherkin.folder ? 'Show which features and scenarios come from each input' : 'Choose the folder with your .feature files'}
                    onClick={() => send({ type: 'gherkin', action: 'toggle' })}
                  >
                    <Icon name="checklist" size={14} /> Gherkin
                  </button>
                  <button className="split-side" title="Reload: re-read every .feature file and update the traceability file" aria-label="Reload Gherkin traceability" disabled={!gherkin.folder || gherkin.scanning} onClick={() => send({ type: 'gherkin', action: 'reload' })}>
                    <Icon name="refresh" size={14} className={gherkin.scanning ? 'spin' : ''} />
                  </button>
                </div>
                {running ? (
                  <button className="primary" onClick={() => send({ type: 'cancel' })}>
                    <Icon name="stop" size={14} /> Cancel
                  </button>
                ) : (
                  <button className="primary" disabled={pending === 0 || !canProcess} onClick={() => send({ type: 'processPending' })} title="Process new and changed files">
                    <Icon name="play" size={14} /> Process{pending > 0 ? ` ${pending}` : ''}
                  </button>
                )}
              </div>
            </div>

            {gherkin.enabled ? <GherkinSummary state={state} /> : null}

            {orphans.length > 0 ? (
              <div className="orphans">
                <Icon name="archive" size={14} />
                <span>
                  {orphans.length} result{orphans.length > 1 ? 's' : ''} without a source file
                </span>
                <button className="link" onClick={() => send({ type: 'cleanOrphans' })}>
                  Archive
                </button>
              </div>
            ) : null}

            {files.length === 0 ? (
              <p className="muted center small">No files yet. Add PDFs, recordings, Markdown or text files.</p>
            ) : (
              <ul className="files">
                {files.map((file) => (
                  <FileCard key={file.name} file={file} job={jobFor(jobs, file.name)} canProcess={canProcess} gherkin={gherkin.enabled ? (gherkin.byInput[file.name] ?? []) : undefined} highlight={highlight?.name === file.name ? highlight.nonce : undefined} />
                ))}
              </ul>
            )}
          </>
        )}
      </div>

      <DockerFooter state={state} />
    </div>
  );
}
