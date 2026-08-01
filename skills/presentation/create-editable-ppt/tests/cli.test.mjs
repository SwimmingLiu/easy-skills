import assert from 'node:assert/strict';
import { access, mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const cli = join(here, '..', 'scripts', 'ppt.mjs');

function run(args, cwd, env = {}) {
  return spawnSync(process.execPath, [cli, ...args], { cwd, encoding: 'utf8', env: { ...process.env, ...env } });
}

test('help documents only the image-first command path', () => {
  const result = run(['--help'], here);
  assert.equal(result.status, 0);
  for (const command of ['draft', 'approve', 'prompts', 'render', 'qa', 'bundle', 'export', 'doctor']) assert.match(result.stdout, new RegExp(command));
  assert.doesNotMatch(result.stdout, /asset add|status <dir>|browser editable/i);
});

test('draft creates a reviewable central message, narrative, and page plan', async () => {
  const parent = await mkdtemp(join(tmpdir(), 'image-ppt-cli-'));
  const root = join(parent, 'deck');
  const result = run(['draft', root, '--title', 'CLI deck'], parent);
  assert.equal(result.status, 0, result.stderr);
  for (const name of ['outline_draft.json', 'outline_preview.html']) await access(join(root, name));
  const draft = JSON.parse(await readFile(join(root, 'outline_draft.json'), 'utf8'));
  assert.equal(draft.title, 'CLI deck');
  assert.ok(draft.central_message);
  assert.ok(draft.narrative.action);
  assert.equal(draft.slides.length, 3);
  assert.doesNotMatch(await readFile(join(root, 'outline_preview.html'), 'utf8'), /contenteditable/i);
});

test('approval and prompt compilation enforce the content gate', async () => {
  const parent = await mkdtemp(join(tmpdir(), 'image-ppt-cli-'));
  const root = join(parent, 'deck');
  assert.notEqual(run(['approve', root, '--theme', 'launch-tech'], parent).status, 0);
  assert.equal(run(['draft', root], parent).status, 0);
  assert.equal(run(['approve', root, '--theme', 'launch-tech'], parent).status, 0);
  const deck = JSON.parse(await readFile(join(root, 'deck_spec.json'), 'utf8'));
  assert.equal(deck.status, 'approved');
  assert.equal(deck.theme.family, 'launch-tech');
  assert.equal(run(['prompts', root], parent).status, 0);
  const manifest = JSON.parse(await readFile(join(root, 'generation_manifest.json'), 'utf8'));
  assert.equal(manifest.slides.length, 3);
  assert.ok(manifest.slides.every((slide) => slide.status === 'prepared'));
  const jsonl = await readFile(join(root, 'imagegen-jobs.jsonl'), 'utf8');
  assert.equal(jsonl.trim().split('\n').length, 3);
});

test('render refuses to create an audience deck while generated slides are missing', async () => {
  const parent = await mkdtemp(join(tmpdir(), 'image-ppt-cli-'));
  const root = join(parent, 'deck');
  run(['draft', root], parent);
  run(['approve', root, '--theme', 'premium-dark'], parent);
  run(['prompts', root], parent);
  const result = run(['render', root], parent);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /missing generated slide images/i);
});

test('bundle creates a self-contained offline image document after generation', async () => {
  const parent = await mkdtemp(join(tmpdir(), 'image-ppt-cli-'));
  const root = join(parent, 'deck');
  assert.equal(run(['draft', root], parent).status, 0);
  assert.equal(run(['approve', root, '--theme', 'launch-tech'], parent).status, 0);
  assert.equal(run(['prompts', root], parent).status, 0);
  const manifest = JSON.parse(await readFile(join(root, 'generation_manifest.json'), 'utf8'));
  const pixels = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  for (const slide of manifest.slides) await writeFile(join(root, slide.output_path), pixels);
  const result = run(['bundle', root], parent);
  assert.equal(result.status, 0, result.stderr);
  const html = await readFile(join(root, 'dist', 'presentation.image-ppt.html'), 'utf8');
  assert.match(html, /application\/image-ppt\+json/);
  assert.match(html, /data:image\/png;base64/);
  assert.doesNotMatch(html, /src="slides\//);
});

test('doctor reports imagegen configuration without exposing values', () => {
  const result = run(['doctor', '--json'], here, {
    OPENAI_API_KEY: '',
    OPENAI_SUB_BASE_URL: 'hidden',
    OPENAI_SUB_KEY: 'hidden',
    OPENAI_SUB_IMAGE_MODEL: 'hidden',
  });
  assert.equal(result.status, 0);
  const report = JSON.parse(result.stdout);
  assert.equal(report.node.supported, true);
  assert.equal(report.imagegen.cli_key_configured, true);
  assert.equal(report.imagegen.configuration.primary_sub, true);
  assert.doesNotMatch(result.stdout, /hidden/);
});
