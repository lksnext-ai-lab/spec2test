import type { AppState } from '../../src/shared/messages';
import { Icon } from '../ui/Icon';
import { send } from '../vscode';
import { TuningTab } from './TuningTab';

export function AdvancedTab(props: { state: AppState; draft: Record<string, string>; setValue: (key: string, value: string) => void; reset: (keys: string[]) => void }) {
  const { state } = props;
  return (
    <div className="stack">
      <h3 className="section-title">Logging</h3>
      <TuningTab state={state} group="Logging" draft={props.draft} setValue={props.setValue} reset={props.reset} intro="Higher levels write more detail to the container logs (Docker footer → Show logs)." />
      <h3 className="section-title">Container</h3>
      <section className="card">
        <div className="setting">
          <div className="setting-text">
            <div className="field-title">Update the image</div>
            <div className="field-help">Pulls the newest image and recreates the containers. Use it when the container does not respond.</div>
          </div>
          <button disabled={Boolean(state.docker.busy)} onClick={() => send({ type: 'docker', action: 'rebuild' })}>
            <Icon name="container" size={14} /> Update
          </button>
        </div>
        <div className="setting">
          <div className="setting-text">
            <div className="field-title">Container logs</div>
            <div className="field-help">Follow what the input-processor is doing.</div>
          </div>
          <button onClick={() => send({ type: 'docker', action: 'logs' })}>
            <Icon name="terminal" size={14} /> Show
          </button>
        </div>
      </section>
    </div>
  );
}
