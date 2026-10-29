import * as fs from 'node:fs';
import type * as vscode from 'vscode';
import { parseEnv } from './core/envfile';

const SECRET_PREFIX = 'spec2test.env.';
const TUNING_KEY = 'spec2test.tuning';

/**
 * API keys live in VS Code's SecretStorage (the OS keychain) and reach the container as
 * environment variables of the `docker run` process; no file ever holds them. Tuning values
 * are not secret and live in the extension's global state.
 */
export class EnvStore {
  private present = new Set<string>();

  constructor(
    private readonly secrets: vscode.SecretStorage,
    private readonly state: vscode.Memento,
  ) {}

  /** Learn which of `names` have a stored key (SecretStorage is async, the UI state is not). */
  async load(names: string[]): Promise<void> {
    const present = new Set<string>();
    for (const name of names) {
      if (await this.secrets.get(SECRET_PREFIX + name)) {
        present.add(name);
      }
    }
    this.present = present;
  }

  /** Tuning values currently set. */
  read(): Record<string, string> {
    return this.state.get<Record<string, string>>(TUNING_KEY, {});
  }

  async saveKey(name: string, value: string): Promise<void> {
    const trimmed = value.trim();
    if (trimmed) {
      await this.secrets.store(SECRET_PREFIX + name, trimmed);
      this.present.add(name);
    } else {
      await this.secrets.delete(SECRET_PREFIX + name);
      this.present.delete(name);
    }
  }

  async saveTuning(values: Record<string, string>): Promise<void> {
    const next = { ...this.read() };
    for (const [key, value] of Object.entries(values)) {
      if (value.trim()) {
        next[key] = value.trim();
      } else {
        delete next[key];
      }
    }
    await this.state.update(TUNING_KEY, next);
  }

  keyStatus(names: string[]): Record<string, boolean> {
    return Object.fromEntries(names.map((name) => [name, this.present.has(name)]));
  }

  /** The stored keys among `names`, ready to be placed in the environment of `docker run`. */
  async secretValues(names: string[]): Promise<Record<string, string>> {
    const values: Record<string, string> = {};
    for (const name of names) {
      const value = await this.secrets.get(SECRET_PREFIX + name);
      if (value) {
        values[name] = value;
      }
    }
    return values;
  }

  /**
   * One-time import from the `.env` of an old repository clone: keys and tuning values that
   * are set there and not yet stored here. The file itself is left alone.
   */
  async importLegacyEnv(file: string, keyNames: string[], tuningNames: string[]): Promise<string[]> {
    if (!fs.existsSync(file)) {
      return [];
    }
    const env = parseEnv(fs.readFileSync(file, 'utf8'));
    const imported: string[] = [];
    for (const name of keyNames) {
      const value = (env[name] ?? '').trim();
      if (value && !(await this.secrets.get(SECRET_PREFIX + name))) {
        await this.secrets.store(SECRET_PREFIX + name, value);
        imported.push(name);
      }
    }
    const tuning = this.read();
    const fresh = Object.fromEntries(tuningNames.filter((name) => (env[name] ?? '').trim() && !(name in tuning)).map((name) => [name, env[name].trim()]));
    if (Object.keys(fresh).length > 0) {
      await this.saveTuning(fresh);
      imported.push(...Object.keys(fresh));
    }
    return imported;
  }
}
