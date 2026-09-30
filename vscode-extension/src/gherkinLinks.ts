import * as vscode from 'vscode';
import type { Controller } from './controller';
import { parseFeature, type SourceRef } from './core/gherkin';

const SELECTOR: vscode.DocumentSelector = { pattern: '**/*.feature' };
export const REVEAL_COMMAND = 'spec2test.revealInput';

const rangeOf = (ref: SourceRef): vscode.Range => new vscode.Range(ref.line - 1, ref.start, ref.line - 1, ref.end);

/**
 * Makes the input names written in `# Inputs:` / `# Source:` comments useful inside the editor:
 * a link that selects the input's card in the sidebar, a hover with its status, and a warning
 * when the name is not an input file of the project. Only `.feature` files that sit inside a
 * project's features folder are touched.
 */
export class GherkinEditor implements vscode.DocumentLinkProvider, vscode.HoverProvider, vscode.Disposable {
  private readonly diagnostics = vscode.languages.createDiagnosticCollection('spec2test');
  private readonly disposables: vscode.Disposable[] = [];
  private timer?: NodeJS.Timeout;

  constructor(private readonly controller: Controller) {
    this.disposables.push(
      this.diagnostics,
      vscode.languages.registerDocumentLinkProvider(SELECTOR, this),
      vscode.languages.registerHoverProvider(SELECTOR, this),
      vscode.workspace.onDidOpenTextDocument((document) => this.check(document)),
      vscode.workspace.onDidChangeTextDocument((event) => this.later(event.document)),
      vscode.workspace.onDidCloseTextDocument((document) => this.diagnostics.delete(document.uri)),
      // Inputs are added, renamed and processed while feature files stay open.
      controller.onState(() => this.checkAll()),
    );
    this.checkAll();
  }

  provideDocumentLinks(document: vscode.TextDocument): vscode.DocumentLink[] {
    const context = this.controller.projectForFeature(document.uri.fsPath);
    if (!context) {
      return [];
    }
    return parseFeature(document.getText()).refs.map((ref) => {
      const link = new vscode.DocumentLink(rangeOf(ref), vscode.Uri.parse(`command:${REVEAL_COMMAND}?${encodeURIComponent(JSON.stringify([context.project, ref.name]))}`));
      link.tooltip = context.inputs.has(ref.name) ? `Show ${ref.name} in Spec2Test` : `${ref.name} is not an input of '${context.project}'`;
      return link;
    });
  }

  provideHover(document: vscode.TextDocument, position: vscode.Position): vscode.Hover | undefined {
    const context = this.controller.projectForFeature(document.uri.fsPath);
    if (!context) {
      return undefined;
    }
    const ref = parseFeature(document.getText()).refs.find((item) => rangeOf(item).contains(position));
    if (!ref) {
      return undefined;
    }
    const input = context.inputs.get(ref.name);
    const text = new vscode.MarkdownString(undefined, true);
    if (!input) {
      text.appendMarkdown(`**${ref.name}**\n\n$(warning) Not an input file of project \`${context.project}\`.`);
    } else {
      const cited = context.cited.get(ref.name);
      text.appendMarkdown(`**${ref.name}** · input of \`${context.project}\`\n\n`);
      text.appendMarkdown(input.processed ? '$(check) Processed' : '$(circle-slash) Not processed yet');
      if (cited !== undefined) {
        text.appendMarkdown(` · cited by ${cited} scenario${cited === 1 ? '' : 's'}`);
      }
      text.appendMarkdown('\n\nClick the name to show its card in Spec2Test.');
    }
    return new vscode.Hover(text, rangeOf(ref));
  }

  private later(document: vscode.TextDocument): void {
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.check(document), 300);
  }

  private checkAll(): void {
    vscode.workspace.textDocuments.forEach((document) => this.check(document));
  }

  private check(document: vscode.TextDocument): void {
    if (!document.uri.fsPath.endsWith('.feature')) {
      return;
    }
    const context = this.controller.projectForFeature(document.uri.fsPath);
    if (!context) {
      this.diagnostics.delete(document.uri);
      return;
    }
    const known = [...context.inputs.keys()];
    const found = parseFeature(document.getText()).refs.filter((ref) => !context.inputs.has(ref.name));
    this.diagnostics.set(
      document.uri,
      found.map((ref) => {
        const guess = known.find((name) => name.toLowerCase() === ref.name.toLowerCase());
        const message = guess ? `Unknown input '${ref.name}' in project '${context.project}'. Did you mean '${guess}'?` : `Unknown input '${ref.name}' in project '${context.project}'.`;
        const diagnostic = new vscode.Diagnostic(rangeOf(ref), message, vscode.DiagnosticSeverity.Warning);
        diagnostic.source = 'Spec2Test';
        return diagnostic;
      }),
    );
  }

  dispose(): void {
    clearTimeout(this.timer);
    this.disposables.forEach((item) => item.dispose());
  }
}
