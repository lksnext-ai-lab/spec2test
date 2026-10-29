import * as fs from 'node:fs';
import * as path from 'node:path';
import * as vscode from 'vscode';
import { RELEASES_API, compareVersions, isDue, matchesRelease, parseRelease, type ReleaseInfo } from './core/updates';

const LAST_CHECK_KEY = 'spec2test.update.lastCheck';
const SKIPPED_KEY = 'spec2test.update.skipped';

/** Looks for a newer release on GitHub and installs its .vsix, so people do not have to come back to the Releases page. */
export class UpdateChecker {
  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly output: vscode.OutputChannel,
  ) {}

  private get current(): string {
    return String(this.context.extension.packageJSON.version);
  }

  /** At most once a day, never in a development host, and only when the setting allows it. */
  async checkOnStartup(): Promise<void> {
    const enabled = vscode.workspace.getConfiguration('spec2test').get<boolean>('checkForUpdates', true);
    if (!enabled || this.context.extensionMode !== vscode.ExtensionMode.Production) {
      return;
    }
    if (!isDue(this.context.globalState.get<number>(LAST_CHECK_KEY), Date.now())) {
      return;
    }
    await this.check(false);
  }

  /** `manual`: report every outcome, ignore the "skip this version" choice. */
  async check(manual: boolean): Promise<void> {
    let release: ReleaseInfo | undefined;
    try {
      release = await this.latest();
    } catch (error) {
      this.output.appendLine(`Update check failed: ${(error as Error).message}`);
      if (manual) {
        void vscode.window.showWarningMessage(`Could not check for updates: ${(error as Error).message}`);
      }
      return;
    }
    await this.context.globalState.update(LAST_CHECK_KEY, Date.now());
    if (!release || compareVersions(release.version, this.current) <= 0) {
      if (manual) {
        void vscode.window.showInformationMessage(`Spec2Test ${this.current} is up to date.`);
      }
      return;
    }
    if (!manual && this.context.globalState.get<string>(SKIPPED_KEY) === release.version) {
      return;
    }
    const answer = await vscode.window.showInformationMessage(
      `Spec2Test ${release.version} is available (you have ${this.current}).`,
      'Update',
      'Release notes',
      'Skip this version',
    );
    if (answer === 'Release notes') {
      await vscode.env.openExternal(vscode.Uri.parse(release.pageUrl));
    } else if (answer === 'Skip this version') {
      await this.context.globalState.update(SKIPPED_KEY, release.version);
    } else if (answer === 'Update') {
      await this.install(release);
    }
  }

  private async latest(): Promise<ReleaseInfo | undefined> {
    const response = await fetch(RELEASES_API, {
      headers: { Accept: 'application/vnd.github+json', 'User-Agent': 'spec2test-vscode' },
      signal: AbortSignal.timeout(10_000),
    });
    if (response.status === 404) {
      // No release yet, or a private repository that anonymous requests cannot see.
      throw new Error('no public release found (GitHub answered 404)');
    }
    if (!response.ok) {
      throw new Error(`GitHub answered ${response.status}`);
    }
    return parseRelease(await response.json());
  }

  private async install(release: ReleaseInfo): Promise<void> {
    try {
      const file = await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: `Downloading Spec2Test ${release.version}…` },
        () => this.download(release),
      );
      await vscode.commands.executeCommand('workbench.extensions.installExtension', vscode.Uri.file(file));
      const answer = await vscode.window.showInformationMessage(
        `Spec2Test ${release.version} is installed. Reload the window to use it; the containers are updated on the next start.`,
        'Reload Window',
      );
      if (answer) {
        await vscode.commands.executeCommand('workbench.action.reloadWindow');
      }
    } catch (error) {
      this.output.appendLine(`Update failed: ${(error as Error).message}`);
      const answer = await vscode.window.showErrorMessage(`Could not update Spec2Test: ${(error as Error).message}`, 'Open release page');
      if (answer) {
        await vscode.env.openExternal(vscode.Uri.parse(release.pageUrl));
      }
    }
  }

  private async download(release: ReleaseInfo): Promise<string> {
    const response = await fetch(release.downloadUrl, { signal: AbortSignal.timeout(180_000) });
    if (!response.ok) {
      throw new Error(`the download answered ${response.status}`);
    }
    const data = new Uint8Array(await response.arrayBuffer());
    if (!matchesRelease(data, release)) {
      throw new Error('the downloaded file does not match the size or checksum GitHub reports');
    }
    const dir = this.context.globalStorageUri.fsPath;
    fs.mkdirSync(dir, { recursive: true });
    for (const old of fs.readdirSync(dir)) {
      if (old.endsWith('.vsix')) {
        fs.rmSync(path.join(dir, old), { force: true });
      }
    }
    const file = path.join(dir, release.assetName);
    fs.writeFileSync(file, data);
    return file;
  }
}
