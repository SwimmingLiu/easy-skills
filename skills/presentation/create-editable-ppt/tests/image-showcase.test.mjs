import assert from 'node:assert/strict';
import { access, mkdtemp, readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const scripts = join(here, '..', 'scripts');

test('showcase preparation reuses one content narrative across all eight themes', async () => {
  const root = await mkdtemp(join(tmpdir(), 'image-ppt-showcase-'));
  const result = spawnSync(process.execPath, [join(scripts, 'build-image-showcase.mjs'), '--prepare', '--root', root], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  const catalog = JSON.parse(await readFile(join(root, 'showcase.json'), 'utf8'));
  assert.equal(catalog.themes.length, 8);
  assert.equal(catalog.themes.reduce((count, theme) => count + theme.slides, 0), 24);
  const central = JSON.parse(await readFile(join(root, 'outline_draft.json'), 'utf8')).central_message;
  for (const theme of catalog.themes) {
    const project = join(root, theme.project);
    await access(join(project, 'deck_spec.json'));
    const deck = JSON.parse(await readFile(join(project, 'deck_spec.json'), 'utf8'));
    assert.equal(deck.central_message, central);
    assert.equal(deck.theme.family, theme.id);
    const jobs = (await readFile(join(project, 'imagegen-jobs.jsonl'), 'utf8')).trim().split('\n').map((line) => JSON.parse(line));
    assert.equal(jobs.length, 3);
    assert.ok(jobs.every((job) => job.use_case === 'productivity-visual'));
  }
});
