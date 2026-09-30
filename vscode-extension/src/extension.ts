import * as vscode from 'vscode';
import { Controller } from './controller';
import { DropZone } from './dropzone';
import { GherkinEditor, REVEAL_COMMAND } from './gherkinLinks';
import { SidebarProvider } from './sidebar';

export function activate(context: vscode.ExtensionContext): void {
  const controller = new Controller(context);
  const sidebar = new SidebarProvider(context.extensionUri, controller);
  const dropZone = new DropZone(controller);
  const gherkin = new GherkinEditor(controller);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(SidebarProvider.viewType, sidebar, {
      webviewOptions: { retainContextWhenHidden: true },
    }),
    vscode.window.createTreeView('spec2test.dropZone', {
      treeDataProvider: dropZone,
      dragAndDropController: dropZone,
    }),
    gherkin,
    vscode.commands.registerCommand(REVEAL_COMMAND, (project: string, name: string) => controller.revealInput(project, name)),
    vscode.commands.registerCommand('spec2test.focus', () => vscode.commands.executeCommand('spec2test.main.focus')),
    vscode.commands.registerCommand('spec2test.startService', () => controller.startService()),
    vscode.commands.registerCommand('spec2test.stopService', () => controller.dockerAction('stop')),
    vscode.commands.registerCommand('spec2test.showLogs', () => controller.dockerAction('logs')),
    vscode.commands.registerCommand('spec2test.addFiles', () => controller.addFilesDialog()),
    vscode.commands.registerCommand('spec2test.chooseRepo', () => controller.chooseRepo()),
    vscode.commands.registerCommand('spec2test.openWalkthrough', () =>
      vscode.commands.executeCommand('workbench.action.openWalkthrough', 'lksnext-ai-lab.spec2test#spec2test.gettingStarted'),
    ),
  );

  void controller.init();
}

export function deactivate(): void {}
