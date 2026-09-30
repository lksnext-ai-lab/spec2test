import type { ToHost } from '../src/shared/messages';

interface VsCodeApi {
  postMessage(message: ToHost): void;
  getState<T>(): T | undefined;
  setState<T>(state: T): void;
}

declare function acquireVsCodeApi(): VsCodeApi;

export const vscode = acquireVsCodeApi();
export const send = (message: ToHost): void => vscode.postMessage(message);
