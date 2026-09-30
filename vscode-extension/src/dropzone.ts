import * as vscode from 'vscode';
import type { Controller } from './controller';

/**
 * The drop target. Webviews cannot receive drops from the VS Code Explorer (and never see
 * the path of files dropped from the OS), while tree views receive real URIs for both.
 * So this small native view is the one place to drop files; the React page only has a button.
 */
export class DropZone implements vscode.TreeDataProvider<string>, vscode.TreeDragAndDropController<string> {
  readonly dropMimeTypes = ['text/uri-list', 'files'];
  readonly dragMimeTypes: string[] = [];
  private readonly changed = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.changed.event;

  constructor(private readonly controller: Controller) {
    controller.onState(() => this.changed.fire());
  }

  getTreeItem(): vscode.TreeItem {
    const project = this.controller.selectedName;
    const item = new vscode.TreeItem(project ? 'Drop files here' : 'Create a project first');
    item.iconPath = new vscode.ThemeIcon(project ? 'cloud-upload' : 'info');
    item.description = project ? `→ ${project}  ·  PDF, MP4, MD, TXT` : undefined;
    item.tooltip = 'Drag files from your computer or from the VS Code Explorer onto this line. Click to choose files instead.';
    item.command = project ? { command: 'spec2test.addFiles', title: 'Add files' } : undefined;
    return item;
  }

  getChildren(element?: string): string[] {
    return element ? [] : ['drop'];
  }

  async handleDrop(_target: string | undefined, dataTransfer: vscode.DataTransfer): Promise<void> {
    const uris = new Map<string, vscode.Uri>();
    const add = (uri: vscode.Uri | undefined) => uri && uris.set(uri.toString(), uri);

    // The Explorer and most OS drops provide a list of URIs...
    const list = await dataTransfer.get('text/uri-list')?.asString();
    for (const line of (list ?? '').split(/\r?\n/)) {
      const text = line.trim();
      if (text && !text.startsWith('#')) {
        add(vscode.Uri.parse(text));
      }
    }
    // ...and some OS drops only provide file entries.
    dataTransfer.forEach((item) => add(item.asFile()?.uri));

    if (uris.size === 0) {
      void vscode.window.showWarningMessage('Nothing to add: the dropped items had no file path. Use “Add files…” instead.');
      return;
    }
    await this.controller.addUris([...uris.values()]);
  }
}
