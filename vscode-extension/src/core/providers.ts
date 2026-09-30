import * as fs from 'node:fs';
import * as path from 'node:path';
import type { Capability, ProviderInfo } from '../shared/types';

export type { Capability, ProviderInfo };

interface Raw {
  name: string;
  api_key_env: string;
  default_model: string;
  capabilities: Capability[];
  models?: string[];
  model_capabilities?: Record<string, Capability[]>;
}

/** Providers straight from the repo files, so the UI works while the container is stopped. */
export function readProviders(repo: string): ProviderInfo[] {
  const dir = path.join(repo, 'input-processor', 'src', 'providers');
  const files = ['native.json', 'catalog.json'];
  const providers: ProviderInfo[] = [];
  for (const file of files) {
    const full = path.join(dir, file);
    if (!fs.existsSync(full)) {
      continue;
    }
    const raw = JSON.parse(fs.readFileSync(full, 'utf8')) as { providers: Raw[] };
    for (const item of raw.providers) {
      const ids = Array.from(new Set([item.default_model, ...(item.models ?? [])]));
      providers.push({
        name: item.name,
        apiKeyEnv: item.api_key_env,
        defaultModel: item.default_model,
        capabilities: item.capabilities,
        models: ids.map((id) => ({ id, capabilities: item.model_capabilities?.[id] ?? item.capabilities })),
      });
    }
  }
  return providers.sort((a, b) => a.name.localeCompare(b.name));
}
