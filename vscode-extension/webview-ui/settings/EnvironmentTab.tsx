import { useState } from 'react';
import type { AppState } from '../../src/shared/messages';
import { Icon } from '../ui/Icon';
import { titleCase } from '../util';
import { send } from '../vscode';

export function KeyRow(props: { env: string; title: string; isSet: boolean }) {
  const [value, setValue] = useState('');
  const [shown, setShown] = useState(false);
  return (
    <div className="keyrow">
      <div className="keyrow-head">
        <Icon name="key" size={14} />
        <span className="keyrow-title">{props.title}</span>
        <code className="muted">{props.env}</code>
        <span className={`status status-${props.isSet ? 'ok' : 'error'}`}>
          <span className="status-dot" />
          {props.isSet ? 'Set' : 'Missing'}
        </span>
      </div>
      <form
        className="keyrow-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (value.trim()) {
            send({ type: 'saveKey', env: props.env, value });
            setValue('');
          }
        }}
      >
        <input
          type={shown ? 'text' : 'password'}
          autoComplete="off"
          spellCheck={false}
          aria-label={`${props.title} API key`}
          placeholder={props.isSet ? 'Paste a new key to replace it' : 'Paste your API key'}
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        <button type="button" className="icon-btn" title={shown ? 'Hide key' : 'Show key'} aria-label={shown ? 'Hide key' : 'Show key'} onClick={() => setShown(!shown)}>
          <Icon name="eye" />
        </button>
        <button type="submit" className="primary" disabled={!value.trim()}>
          Save
        </button>
        {props.isSet ? (
          <button type="button" className="icon-btn danger" title="Remove key" aria-label="Remove key" onClick={() => send({ type: 'saveKey', env: props.env, value: '' })}>
            <Icon name="trash" />
          </button>
        ) : null}
      </form>
    </div>
  );
}

export function EnvironmentTab({ state }: { state: AppState }) {
  const envs = Array.from(new Set(state.providers.map((provider) => provider.apiKeyEnv)));
  const providerOf = (env: string) =>
    state.providers
      .filter((provider) => provider.apiKeyEnv === env)
      .map((provider) => titleCase(provider.name))
      .join(' / ');
  return (
    <div className="stack">
      <p className="muted small">Keys are stored in your operating system’s keychain and copied to the repository’s <code>.env</code> so the container can read them.</p>
      <section className="card">
        <h3>LLM providers</h3>
        {envs.map((env) => (
          <KeyRow key={env} env={env} title={providerOf(env)} isSet={Boolean(state.keys[env])} />
        ))}
      </section>
      <section className="card">
        <h3>Optional</h3>
        <KeyRow env="HF_TOKEN" title="Hugging Face" isSet={Boolean(state.keys.HF_TOKEN)} />
      </section>
    </div>
  );
}
