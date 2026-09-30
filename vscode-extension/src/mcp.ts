import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { LoggingMessageNotificationSchema } from '@modelcontextprotocol/sdk/types.js';
import type { RunHooks } from './core/jobqueue';

export const PROJECT_HEADER = 'X-Spec2Test-Project';
const HOUR = 60 * 60 * 1000;

export interface ProcessResult {
  status: string;
  error?: string;
}

/** Text of the first text block of a tool result. */
export function toolText(result: unknown): string {
  const content = (result as { content?: { type: string; text?: string }[] }).content ?? [];
  return content.find((block) => block.type === 'text')?.text ?? '';
}

export function parseProcessResult(text: string): ProcessResult {
  try {
    const payload = JSON.parse(text) as { status?: string; error?: string };
    if (payload.error) {
      return { status: 'error', error: payload.error };
    }
    return { status: payload.status ?? 'error', error: payload.status ? undefined : 'Unexpected answer from the server.' };
  } catch {
    return { status: 'error', error: text || 'Empty answer from the server.' };
  }
}

export class McpService {
  constructor(
    private readonly port: () => number,
    private readonly onLog: (line: string) => void,
  ) {}

  /** Process one file, streaming the server's progress to `hooks`. Aborting closes the request, which cancels the work. */
  async processFile(project: string, file: string, force: boolean, hooks: RunHooks): Promise<ProcessResult> {
    const transport = new StreamableHTTPClientTransport(new URL(`http://127.0.0.1:${this.port()}/mcp`), {
      requestInit: { headers: { [PROJECT_HEADER]: project } },
    });
    const client = new Client({ name: 'spec2test-vscode', version: '0.1.0' });
    let lastLog = '';
    client.setNotificationHandler(LoggingMessageNotificationSchema, (notification) => {
      const line = String(notification.params.data);
      if (line !== lastLog) {
        lastLog = line;
        this.onLog(line);
        hooks.onStage(line);
      }
    });
    await client.connect(transport);
    try {
      const result = await client.callTool({ name: 'process_file', arguments: { file_name: file, force } }, undefined, {
        signal: hooks.signal,
        timeout: HOUR,
        resetTimeoutOnProgress: true,
        maxTotalTimeout: 6 * HOUR,
        onprogress: (progress) => {
          if (progress.message) {
            hooks.onStage(progress.message);
          }
        },
      });
      return parseProcessResult(toolText(result));
    } finally {
      await client.close().catch(() => undefined);
    }
  }
}
