import { useState } from 'react';
import type { AppState } from '../../src/shared/messages';
import type { LlmSettings, ProviderInfo } from '../../src/shared/types';
import { Dropdown, type Option } from '../ui/Dropdown';
import { Segmented } from '../ui/controls';
import { CAPABILITY_LABEL, capabilitiesOf, effectiveModel, titleCase } from '../util';
import { send } from '../vscode';
import { KeyRow } from './EnvironmentTab';

const tags = (caps: string[]) => caps.map((cap) => CAPABILITY_LABEL[cap] ?? cap);

function ModelPicker(props: { title: string; help: string; value?: LlmSettings; providers: ProviderInfo[]; inheritLabel: string; onChange: (value: LlmSettings | undefined) => void }) {
  const provider = props.providers.find((item) => item.name === props.value?.provider);
  const providerOptions: Option[] = [{ value: '', label: props.inheritLabel }, ...props.providers.map((item) => ({ value: item.name, label: titleCase(item.name), hint: item.name, badges: tags(item.capabilities) }))];
  const modelOptions: Option[] = provider
    ? [{ value: '', label: `Provider default`, hint: provider.defaultModel }, ...provider.models.map((model) => ({ value: model.id, label: model.id, badges: tags(model.capabilities) }))]
    : [];

  return (
    <section className="card">
      <h3>{props.title}</h3>
      <p className="muted small">{props.help}</p>
      <label className="label">Provider</label>
      <Dropdown ariaLabel={`${props.title}: provider`} value={props.value?.provider ?? ''} options={providerOptions} searchable onChange={(name) => props.onChange(name ? { provider: name } : undefined)} />
      {provider ? (
        <>
          <label className="label">Model</label>
          <Dropdown
            ariaLabel={`${props.title}: model`}
            value={props.value?.model ?? ''}
            options={modelOptions}
            searchable
            customLabel={(query) => `Use “${query}”`}
            onChange={(model) => props.onChange({ provider: provider.name, model: model || undefined })}
          />
        </>
      ) : null}
    </section>
  );
}

export function ModelsTab({ state }: { state: AppState }) {
  const [scope, setScope] = useState<'project' | 'defaults'>(state.selected ? 'project' : 'defaults');
  const project = state.projects.find((item) => item.name === state.selected);
  const source = scope === 'project' ? project : state.defaults;
  const save = (kind: 'llm' | 'vision') => (value: LlmSettings | undefined) => send({ type: 'saveModel', scope, kind, value });

  const text = effectiveModel(project?.llm, state.defaults.llm, state.providers, state.fallbackProvider);
  const hasVision = Boolean(project?.vision?.provider || state.defaults.vision?.provider);
  const vision = hasVision ? effectiveModel(project?.vision, state.defaults.vision, state.providers, state.fallbackProvider) : text;
  const visionCaps = capabilitiesOf(state.providers, vision.provider, vision.model);
  const missing = Array.from(new Set([text.provider, vision.provider]))
    .map((name) => state.providers.find((item) => item.name === name))
    .filter((item): item is ProviderInfo => Boolean(item) && !state.keys[item!.apiKeyEnv]);

  return (
    <div className="stack">
      {state.selected ? (
        <Segmented
          label="Where the choice applies"
          value={scope}
          onChange={setScope}
          options={[
            { value: 'project', label: `Project: ${state.selected}` },
            { value: 'defaults', label: 'All projects' },
          ]}
        />
      ) : null}
      <ModelPicker
        key={`llm-${scope}-${state.selected}`}
        title="Text model"
        help="Summarises documents and analyses videos."
        value={source?.llm}
        providers={state.providers}
        inheritLabel={scope === 'project' ? 'Same as all projects' : 'Server default'}
        onChange={save('llm')}
      />
      <ModelPicker
        key={`vision-${scope}-${state.selected}`}
        title="Vision model"
        help="Describes the images inside PDFs and Markdown."
        value={source?.vision}
        providers={state.providers}
        inheritLabel="Same as the text model"
        onChange={save('vision')}
      />

      {state.selected ? (
        <p className="summary small">
          <strong>{state.selected}</strong> uses <code>{text.provider}</code> / <code>{text.model || 'default'}</code>
          {vision.provider !== text.provider || vision.model !== text.model ? (
            <>
              {' '}
              and <code>{vision.provider}</code> / <code>{vision.model || 'default'}</code> for images
            </>
          ) : null}
          .
        </p>
      ) : null}
      {!visionCaps.includes('images') ? <p className="callout warn">The vision model cannot read images, so pictures in documents will not be described.</p> : null}
      {missing.map((item) => (
        <div className="callout warn" key={item.name}>
          <p>
            No API key for <strong>{titleCase(item.name)}</strong>. Processing will fail until you add one.
          </p>
          <KeyRow env={item.apiKeyEnv} title={titleCase(item.name)} isSet={false} />
        </div>
      ))}
      <p className="muted small">Model changes apply to the next run. No restart needed.</p>
    </div>
  );
}
