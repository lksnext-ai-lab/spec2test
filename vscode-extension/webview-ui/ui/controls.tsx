import type { ReactNode } from 'react';

export function Switch(props: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  return (
    <button type="button" role="switch" aria-checked={props.checked} aria-label={props.label} className={`switch ${props.checked ? 'on' : ''}`} onClick={() => props.onChange(!props.checked)}>
      <span className="switch-knob" />
    </button>
  );
}

export function Segmented<T extends string>(props: { value: T; options: { value: T; label: string }[]; onChange: (value: T) => void; label: string }) {
  return (
    <div className="segmented" role="radiogroup" aria-label={props.label}>
      {props.options.map((option) => (
        <button key={option.value} type="button" role="radio" aria-checked={props.value === option.value} className={props.value === option.value ? 'is-on' : ''} onClick={() => props.onChange(option.value)}>
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function Field(props: { title: string; help?: string; children: ReactNode; control?: ReactNode }) {
  return (
    <div className="field-row">
      <div className="field-head">
        <div className="field-text">
          <div className="field-title">{props.title}</div>
          {props.help ? <div className="field-help">{props.help}</div> : null}
        </div>
        {props.control}
      </div>
      {props.children}
    </div>
  );
}
