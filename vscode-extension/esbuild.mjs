import { build, context } from 'esbuild';

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
