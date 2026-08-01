import assert from 'node:assert/strict';
import test from 'node:test';

import { runQa } from '../scripts/lib/qa.mjs';

function project(overrides = {}) {
  const slides = overrides.slides ?? [
    { id: 's1', role: 'cover', claim: 'A clear opening', layout: 'center', props: {}, evidence: [], media: [], speaker_notes: '', review_status: 'pass' },
    { id: 's2', role: 'data', claim: 'Activation improved', layout: 'metrics', props: { metrics: [{ value: '24%', label: 'Activation' }] }, evidence: [{ source: 'analytics', locator: 'Q2 report' }], media: [], speaker_notes: '', review_status: 'pass' },
    { id: 's3', role: 'closing', claim: 'Approve the pilot', layout: 'center', props: { action: 'Decide today' }, evidence: [], media: [], speaker_notes: '', review_status: 'pass' },
  ];
  return {
    deck: { schema_version: 1, revision: 1, title: 'QA deck', audience: 'Board', purpose: 'Decision', language: 'en', canvas: '16:9', density: 'speaker-led', theme: { family: 'business-minimal', variant: 'ink' }, slides },
    state: null,
    assets: { schema_version: 1, assets: [] },
    ...overrides,
  };
}

test('a reviewed, evidence-backed title chain is export-ready', async () => {
  const report = await runQa(project());
  assert.equal(report.export_ready, true);
  assert.equal(report.summary.blocking, 0);
});

test('finds title-chain gaps, unsupported data claims, and missing assets per slide', async () => {
  const slides = project().deck.slides;
  slides[1] = { ...slides[1], claim: '', evidence: [], media: ['missing'] };
  const report = await runQa(project({ slides }));
  assert.ok(report.findings.some((item) => item.code === 'slide.claim.required' && item.slide_id === 's2'));
  assert.ok(report.findings.some((item) => item.code === 'claim.evidence.missing' && item.slide_id === 's2'));
  assert.ok(report.findings.some((item) => item.code === 'slide.media.missing' && item.slide_id === 's2'));
  assert.equal(report.export_ready, false);
});

test('applies role-specific and review gate checks', async () => {
  const slides = project().deck.slides;
  slides[0] = { ...slides[0], review_status: 'pending' };
  slides[2] = { ...slides[2], props: {} };
  const report = await runQa(project({ slides }));
  assert.ok(report.findings.some((item) => item.code === 'review.unresolved'));
  assert.ok(report.findings.some((item) => item.code === 'closing.action.required'));
});

test('integrates browser geometry findings with blocking, degraded, and warning severity', async () => {
  const browserCheck = async () => ({
    mode: 'browser',
    findings: [
      { code: 'layout.overflow', severity: 'blocking', slide_id: 's2', message: 'Content exceeds slide bounds.' },
      { code: 'layout.collision', severity: 'warning', slide_id: 's1', message: 'Two labels touch.' },
    ],
  });
  const report = await runQa(project(), { browserCheck });
  assert.equal(report.mode, 'browser');
  assert.equal(report.summary.blocking, 1);
  assert.equal(report.summary.warning, 1);
});

test('allows an explicitly approved image placeholder but reports it', async () => {
  const slides = project().deck.slides;
  slides.splice(1, 0, { id: 'image', role: 'image-hero', claim: 'Concept before screenshot', layout: 'split', props: { image: 'product-shot', image_status: 'missing-approved' }, evidence: [], media: [], speaker_notes: '', review_status: 'pass' });
  const report = await runQa(project({ slides }));
  assert.equal(report.export_ready, true);
  assert.ok(report.findings.some((item) => item.code === 'image.placeholder.approved' && item.slide_id === 'image'));
});
