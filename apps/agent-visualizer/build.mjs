import { build } from 'esbuild';
import { mkdir, copyFile } from 'node:fs/promises';

await mkdir(new URL('./dist/', import.meta.url), { recursive: true });
await build({ entryPoints: ['src/app.mjs'], bundle: true, outfile: 'dist/app.js', format: 'esm',
  platform: 'browser', target: ['chrome120', 'safari17'], minify: true, sourcemap: false, legalComments: 'eof' });
await copyFile('index.html', 'dist/index.html');
await copyFile('src/app.css', 'dist/app.css');
console.log('Built agent-visualizer 0.1.0');
