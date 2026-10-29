import { build, context } from 'esbuild';
import { cpSync, mkdirSync, readdirSync, copyFileSync } from 'node:fs';

// The provider catalog is shared with the container image: one source of truth, copied at build time.
mkdirSync('dist/providers', { recursive: true });
for (const file of ['native.json', 'catalog.json']) {
  cpSync(`../input-processor/src/providers/${file}`, `dist/providers/${file}`);
}

// The agent files and the skill package the "Add the Gherkin-Generator" command installs.
mkdirSync('dist/agents', { recursive: true });
for (const name of readdirSync('../.github/agents')) {
  if (name.toLowerCase().endsWith('.agent.md')) {
    // Lower-cased: the repository tracks these names with capitals, but the agents are called gherkin-generator and web-crawler.
    copyFileSync(`../.github/agents/${name}`, `dist/agents/${name.toLowerCase()}`);
  }
}
copyFileSync('../gherkin-generator.skill', 'dist/agents/gherkin-generator.skill');

const watch = process.argv.includes('--watch');

const host = {
  entryPoints: ['src/extension.ts'],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  target: 'node20',
  outfile: 'dist/extension.js',
  external: ['vscode'],
  sourcemap: true,
};

const webview = {
  entryPoints: ['webview-ui/main.tsx'],
  bundle: true,
  platform: 'browser',
  format: 'iife',
  target: 'es2022',
  outfile: 'dist/webview.js',
  sourcemap: true,
  jsx: 'automatic',
  define: { 'process.env.NODE_ENV': '"production"' },
  loader: { '.css': 'css' },
};

if (watch) {
  for (const options of [host, webview]) {
    (await context(options)).watch();
  }
} else {
  await Promise.all([build(host), build(webview)]);
}
