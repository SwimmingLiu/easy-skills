import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { defaultEditorState } from '../scripts/lib/model.mjs';
import { createProjectHandler } from '../scripts/lib/server.mjs';

const deck = {
  schema_version: 1,
  revision: 1,
  title: 'Local editor',
  audience: 'Team',
  purpose: 'Decision',
  language: 'en',
  canvas: '16:9',
  density: 'speaker-led',
  theme: { family: 'business-minimal', variant: 'ink' },
  slides: [{ id: 's1', role: 'cover', claim: 'One claim', layout: 'center', props: {}, evidence: [], media: [], speaker_notes: '' }],
};

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), 'ppt-server-'));
  await mkdir(join(root, 'media'));
  await writeFile(join(root, 'deck_spec.json'), JSON.stringify(deck));
  await writeFile(join(root, 'editor_state.json'), JSON.stringify(defaultEditorState(deck)));
  await writeFile(join(root, 'asset_manifest.json'), JSON.stringify({ schema_version: 1, assets: [] }));
  return { root, handle: createProjectHandler(root) };
}

function request(method, path, body, remoteAddress = '127.0.0.1') {
  return { method, path, body, remoteAddress };
}

test('GET project returns the current source, state, and assets', async () => {
  const { handle } = await fixture();
  const response = await handle(request('GET', '/api/project'));
  assert.equal(response.status, 200);
  assert.equal(response.json.deck.title, 'Local editor');
  assert.equal(response.json.state.revision, 0);
  assert.deepEqual(response.json.assets.assets, []);
});

test('optimistic save increments revision and rejects stale clients', async () => {
  const { handle } = await fixture();
  const first = await handle(request('POST', '/api/save', { expected_revision: 0, patch: { text_overrides: { s1: { claim: 'Edited' } } } }));
  assert.equal(first.status, 200);
  assert.equal(first.json.state.revision, 1);

  const stale = await handle(request('POST', '/api/save', { expected_revision: 0, patch: { skipped_slides: ['s1'] } }));
  assert.equal(stale.status, 409);
  assert.equal(stale.json.error, 'project.revision.conflict');
});

test('media upload is content-addressed and updates the manifest atomically', async () => {
  const { root, handle } = await fixture();
  const uploaded = await handle(request('POST', '/api/media', {
    filename: 'diagram.png',
    content_base64: Buffer.from('fake-png').toString('base64'),
    purpose: 'Hero diagram',
  }));
  assert.equal(uploaded.status, 201);
  assert.match(uploaded.json.asset.path, /^media\/[a-f0-9]{64}\.png$/);
  const manifest = JSON.parse(await readFile(join(root, 'asset_manifest.json'), 'utf8'));
  assert.equal(manifest.assets.length, 1);
});

test('rejects path traversal and write attempts from non-local clients', async () => {
  const { handle } = await fixture();
  const traversal = await handle(request('POST', '/api/media', { filename: '../secret.png', content_base64: 'eA==' }));
  assert.equal(traversal.status, 400);

  const remote = await handle(request('POST', '/api/save', { expected_revision: 0, patch: {} }, '10.0.0.20'));
  assert.equal(remote.status, 403);
});

test('render refresh writes the self-contained HTML page', async () => {
  const { root, handle } = await fixture();
  const response = await handle(request('POST', '/api/render', {}));
  assert.equal(response.status, 200);
  const html = await readFile(join(root, 'index.html'), 'utf8');
  assert.match(html, /<!doctype html>/);
  assert.match(html, /Local editor/);
});

test('QA endpoint persists a report and export endpoint routes the selected format', async () => {
  const { root } = await fixture();
  const formats = [];
  const handle = createProjectHandler(root, {
    exportProject: async (_root, _project, format) => { formats.push(format); return { format, files: [] }; },
  });
  const qa = await handle(request('POST', '/api/qa', {}));
  assert.equal(qa.status, 200);
  await readFile(join(root, 'qa_report.json'), 'utf8');
  const blocked = await handle(request('POST', '/api/export', { format: 'pptx' }));
  assert.equal(blocked.status, 422);
  const exported = await handle(request('POST', '/api/export', { format: 'pptx', force: true }));
  assert.equal(exported.status, 200);
  assert.deepEqual(formats, ['pptx']);
});

test('project status endpoint enforces the configured Gate sequence', async () => {
  const { handle } = await fixture();
  const invalid = await handle(request('POST', '/api/status', { expected_revision: 0, status: 'generating' }));
  assert.equal(invalid.status, 400);
  const valid = await handle(request('POST', '/api/status', { expected_revision: 0, status: 'outline-review' }));
  assert.equal(valid.status, 200);
  assert.equal(valid.json.state.project_status, 'outline-review');
  assert.equal(valid.json.state.revision, 1);
});
