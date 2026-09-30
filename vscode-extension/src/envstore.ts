import * as fs from 'node:fs';
import * as path from 'node:path';
import type * as vscode from 'vscode';
import { parseEnv, updateEnv } from './core/envfile';

const SECRET_PREFIX = 'spec2test.env.';

/** API keys live in VS Code's SecretStorage (OS keychain) and are mirrored into the repo's .env for the container. */
export class EnvStore {
  constructor(
    private readonly secrets: vscode.SecretStorage,
    private readonly repo: () => string | undefined,
  ) {}

  get file(): string | undefined {
    const repo = this.repo();
    return repo ? path.join(repo, '.env') : undefined;
  }

  /** docker compose refuses to start when `env_file: .env` is missing. */
  ensureFile(): void {
    const file = this.file;
    if (file && !fs.existsSync(file)) {
      const example = path.join(path.dirname(file), '.env.example');
      fs.writeFileSync(file, fs.existsSync(example) ? fs.readFileSync(example, 'utf8') : '', 'utf8');
    }
  }

  read(): Record<string, string> {
    const file = this.file;
    return file && fs.existsSync(file) ? parseEnv(fs.readFileSync(file, 'utf8')) : {};
  }

  private write(updates: Record<string, string | null>): void {
    const file = this.file;
    if (!file) {
      return;
    }
    const current = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '';
    fs.writeFileSync(file, updateEnv(current, updates), 'utf8');
  }

  async saveKey(name: string, value: string): Promise<void> {
    const trimmed = value.trim();
    if (trimmed) {
      await this.secrets.store(SECRET_PREFIX + name, trimmed);
    } else {
      await this.secrets.delete(SECRET_PREFIX + name);
    }
    this.write({ [name]: trimmed || null });
  }

  saveTuning(values: Record<string, string>): void {
    this.write(Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value.trim() || null])));
  }

  /**
   * Make SecretStorage and .env agree: keys that are only in .env (set by hand)
   * are imported; keys only in SecretStorage (a fresh clone, a deleted .env) are written back.
   */
  async syncKeys(names: string[]): Promise<void> {
    const env = this.read();
    const missingInEnv: Record<string, string> = {};
    for (const name of names) {
      const stored = await this.secrets.get(SECRET_PREFIX + name);
      const inEnv = (env[name] ?? '').trim();
      if (inEnv && !stored) {
        await this.secrets.store(SECRET_PREFIX + name, inEnv);
      } else if (stored && !inEnv) {
        missingInEnv[name] = stored;
      }
    }
    if (Object.keys(missingInEnv).length > 0) {
      this.write(missingInEnv);
    }
  }

  keyStatus(names: string[]): Record<string, boolean> {
    const env = this.read();
    return Object.fromEntries(names.map((name) => [name, Boolean((env[name] ?? '').trim())]));
  }
}
