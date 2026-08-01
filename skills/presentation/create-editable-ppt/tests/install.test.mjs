import assert from 'node:assert/strict';
import { access, mkdtemp, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const installer = join(here, '..', 'install.mjs');

function run(args) { return spawnSync(process.execPath, [installer, ...args], { encoding: 'utf8' }); }

test('dry-run reports destination without writing it', async () => {
  const target = await mkdtemp(join(tmpdir(), 'ppt-install-'));
  const result = run(['--dir', target, '--dry-run']);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /create-editable-ppt/);
  await assert.rejects(() => access(join(target, 'create-editable-ppt', 'SKILL.md')));
});

test('explicit directory installs, refuses overwrite, and supports force', async () => {
  const target = await mkdtemp(join(tmpdir(), 'ppt-install-'));
  assert.equal(run(['--dir', target]).status, 0);
  await access(join(target, 'create-editable-ppt', 'SKILL.md'));
  assert.notEqual(run(['--dir', target]).status, 0);
  await writeFile(join(target, 'create-editable-ppt', 'marker'), 'old');
  assert.equal(run(['--dir', target, '--force']).status, 0);
  await assert.rejects(() => access(join(target, 'create-editable-ppt', 'marker')));
});
