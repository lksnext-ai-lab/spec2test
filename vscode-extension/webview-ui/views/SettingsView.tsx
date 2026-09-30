import { useState } from 'react';
import type { AppState } from '../../src/shared/messages';
import { Icon } from '../ui/Icon';
import { AdvancedTab } from '../settings/AdvancedTab';
import { EnvironmentTab } from '../settings/EnvironmentTab';
import { ModelsTab } from '../settings/ModelsTab';
import { TuningTab } from '../settings/TuningTab';
import { send } from '../vscode';
import { DockerFooter } from './DockerFooter';

export type Tab = 'models' | 'environment' | 'video' | 'advanced';

const TABS: { id: Tab; label: string }[] = [
  { id: 'models', label: 'Models' },
  { id: 'environment', label: 'Environment' },
  { id: 'video', label: 'Video' },
  { id: 'advanced', label: 'Advanced' },
];

export function SettingsView(props: { state: AppState; tab: Tab; setTab: (tab: Tab) => void; back: () => void }) {
  const { state, tab } = props;
  const [draft, setDraft] = useState<Record<string, string>>({});
  const dirty = Object.keys(draft).length > 0;
  const setValue = (key: string, value: string) => setDraft((current) => ({ ...current, [key]: value }));
  const reset = (keys: string[]) => setDraft((current) => ({ ...current, ...Object.fromEntries(keys.map((key) => [key, ''])) }));

  return (
    <div className="screen">
      <header className="topbar">
        <button className="icon-btn" title="Back to files" aria-label="Back to files" onClick={props.back}>
          <Icon name="chevron-left" />
        </button>
        <h1 className="topbar-title">Settings</h1>
      </header>

      <nav className="tabs" role="tablist" aria-label="Settings sections">
        {TABS.map((item) => (
          <button key={item.id} role="tab" id={`tab-${item.id}`} aria-selected={tab === item.id} aria-controls="tab-panel" className={tab === item.id ? 'tab is-on' : 'tab'} onClick={() => props.setTab(item.id)}>
            {item.label}
          </button>
        ))}
      </nav>

      <div className="scroll" role="tabpanel" id="tab-panel" aria-labelledby={`tab-${tab}`}>
        {tab === 'models' ? <ModelsTab state={state} /> : null}
        {tab === 'environment' ? <EnvironmentTab state={state} /> : null}
        {tab === 'video' ? <TuningTab state={state} group="Video" draft={draft} setValue={setValue} reset={reset} intro="How recordings are split and sent to the model." /> : null}
        {tab === 'advanced' ? <AdvancedTab state={state} draft={draft} setValue={setValue} reset={reset} /> : null}
      </div>

      {dirty || state.envPending ? (
        <div className="savebar" role="region" aria-label="Pending changes">
          {dirty ? (
            <>
              <span>Unsaved changes</span>
              <button onClick={() => setDraft({})}>Discard</button>
              <button
                className="primary"
                onClick={() => {
                  send({ type: 'saveTuning', values: draft });
                  setDraft({});
                }}
              >
                Save
              </button>
            </>
          ) : (
            <>
              <span>Restart the input-processor to use the new values.</span>
              <button className="primary" disabled={Boolean(state.docker.busy)} onClick={() => send({ type: 'applyEnv' })}>
                Apply and restart
              </button>
            </>
          )}
        </div>
      ) : null}
      <DockerFooter state={state} />
    </div>
  );
}
