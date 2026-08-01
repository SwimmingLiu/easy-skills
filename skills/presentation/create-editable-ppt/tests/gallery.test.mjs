import assert from 'node:assert/strict';
import { access, mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const scripts = fileURLToPath(new URL('../scripts/', import.meta.url));

test('showcase gallery contains one image card for every theme and page', async () => {
  const root = await mkdtemp(join(tmpdir(), 'image-ppt-gallery-'));
  const prepare = spawnSync(process.execPath, [join(scripts, 'build-image-showcase.mjs'), '--prepare', '--root', root], { encoding: 'utf8' });
  assert.equal(prepare.status, 0, prepare.stderr);
  const catalog = JSON.parse(await readFile(join(root, 'showcase.json'), 'utf8'));
  const pixels = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  for (const theme of catalog.themes) {
    const project = join(root, theme.project);
    const manifest = JSON.parse(await readFile(join(project, 'generation_manifest.json'), 'utf8'));
    for (const slide of manifest.slides) await writeFile(join(project, slide.output_path), pixels);
  }
  const result = spawnSync(process.execPath, [join(scripts, 'build-image-gallery.mjs'), '--root', root], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  await access(join(root, 'index.html'));
  const html = await readFile(join(root, 'index.html'), 'utf8');
  assert.equal((html.match(/class="slide-card"/g) ?? []).length, 24);
  assert.equal((html.match(/data-theme=/g) ?? []).length, 24);
  assert.doesNotMatch(html, /https?:\/\//i);
});
