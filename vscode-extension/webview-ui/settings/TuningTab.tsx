import type { AppState } from '../../src/shared/messages';
import type { TuningVariable } from '../../src/shared/types';
import { Segmented, Switch } from '../ui/controls';

export function TuningField(props: { variable: TuningVariable; value: string; onChange: (value: string) => void }) {
  const { variable, value } = props;
  const effective = value || variable.default;
  return (
    <div className={`setting ${variable.type === 'select' ? 'setting-stack' : ''}`}>
      <div className="setting-text">
        <div className="field-title">{variable.label}</div>
        <div className="field-help">{variable.help}</div>
      </div>
      {variable.type === 'boolean' ? (
        <Switch label={variable.label} checked={effective === 'true'} onChange={(on) => props.onChange(on ? 'true' : 'false')} />
      ) : variable.type === 'select' ? (
        <Segmented label={variable.label} value={effective} options={(variable.options ?? []).map((option) => ({ value: option, label: option.charAt(0) + option.slice(1).toLowerCase() }))} onChange={props.onChange} />
      ) : (
        <input className="num" type="number" min={0} inputMode="numeric" aria-label={variable.label} placeholder={variable.default} value={value} onChange={(event) => props.onChange(event.target.value)} />
      )}
    </div>
  );
}

export function TuningTab(props: { state: AppState; group: TuningVariable['group']; draft: Record<string, string>; setValue: (key: string, value: string) => void; reset: (keys: string[]) => void; intro?: string }) {
  const variables = props.state.tuning.filter((variable) => variable.group === props.group);
  return (
    <div className="stack">
      {props.intro ? <p className="muted small">{props.intro}</p> : null}
      <section className="card">
        {variables.map((variable) => (
          <TuningField key={variable.key} variable={variable} value={props.draft[variable.key] ?? props.state.tuningValues[variable.key] ?? ''} onChange={(value) => props.setValue(variable.key, value)} />
        ))}
      </section>
      <button className="link" onClick={() => props.reset(variables.map((variable) => variable.key))}>
        Reset to defaults
      </button>
    </div>
  );
}
