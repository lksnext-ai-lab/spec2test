import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  // React components are rendered to a string in tests, with the automatic JSX runtime of the webview build.
  oxc: { jsx: { runtime: 'automatic' } },
  resolve: {
    // The Controller imports 'vscode', which only exists inside the editor.
    alias: { vscode: fileURLToPath(new URL('./test/support/vscode.ts', import.meta.url)) },
  },
  test: {
    include: ['test/**/*.test.ts', 'webview-ui/test/**/*.test.tsx'],
    coverage: { provider: 'v8', include: ['src/core/**', 'src/mcp.ts', 'src/repo.ts', 'src/docker.ts'], reporter: ['text', 'lcov'] },
  },
});
