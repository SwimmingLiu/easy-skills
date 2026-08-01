import assert from 'node:assert/strict';
import { access, mkdtemp, mkdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { exportProject } from '../scripts/lib/export.mjs';

async function fixture() {
  const root = await mkdtemp(join(tmpdir(), 'ppt-export-'));
  await mkdir(join(root, 'dist'));
  const deck = {
    schema_version: 1, revision: 1, title: 'Export', audience: 'Team', purpose: 'Share', language: 'en', canvas: '16:9', density: 'speaker-led', theme: { family: 'business-minimal', variant: 'ink' },
    slides: [
      { id: 's1', role: 'cover', claim: 'Editable title', layout: 'center', props: {}, evidence: [], media: [], speaker_notes: '', review_status: 'pass' },
      { id: 's2', role: 'statement', claim: 'Skipped', layout: 'focus', props: {}, evidence: [], media: [], speaker_notes: '', skipped: true, review_status: 'skip' },
      { id: 's3', role: 'closing', claim: 'Next', layout: 'center', props: { action: 'Decide' }, evidence: [], media: [], speaker_notes: '', review_status: 'pass' },
    ],
  };
  await writeFile(join(root, 'index.html'), '<html></html>');
  return { root, project: { deck, state: null, assets: { schema_version: 1, assets: [] } } };
}

test('reports an actionable missing optional dependency', async () => {
  const { root, project } = await fixture();
  await assert.rejects(
    () => exportProject(root, project, 'pdf', { loadPlaywright: async () => null }),
    /Playwright.*optional dependency/i,
  );
});

test('PDF and PNG adapters create expected paths for active slides only', async () => {
  const { root, project } = await fixture();
  const adapter = {
    pdf: async (path) => writeFile(path, '%PDF fake'),
    png: async (path, slide) => writeFile(path, slide.id),
  };
  const pdf = await exportProject(root, project, 'pdf', { browserAdapter: adapter });
  await access(pdf.files[0]);
  const png = await exportProject(root, project, 'png', { browserAdapter: adapter });
  assert.equal(png.files.length, 2);
  assert.ok(png.files.every((path) => !path.includes('s2')));
});

test('PPTX export reports editable objects and per-slide screenshot fallback', async () => {
  const { root, project } = await fixture();
  project.deck.slides[0].effects = ['unsupported-mask'];
  const pptxAdapter = async ({ path, slides }) => {
    await writeFile(path, 'pptx');
    return { editable_object_count: 3, fallback_slides: slides.filter((slide) => slide.effects).map((slide) => slide.id) };
  };
  const result = await exportProject(root, project, 'pptx', { pptxAdapter });
  assert.equal(result.editable_object_count, 3);
  assert.deepEqual(result.fallback_slides, ['s1']);
  assert.equal(result.active_slide_count, 2);
  await access(join(root, 'dist', 'export-report.json'));
});
