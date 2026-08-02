import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { compileImageJobs } from '../scripts/lib/ai-image.mjs';
import { parseBentoDocument, spliceBentoDocument } from '../scripts/lib/bento-document.mjs';
import { composeHtmlDeck } from '../scripts/lib/html-composer.mjs';
import { approveOutline, createOutline } from '../scripts/lib/outline.mjs';
import { loadThemeCatalog } from '../scripts/lib/theme-catalog.mjs';

test('html mode creates only native Bento elements and zero image jobs', async () => {
  const catalog = await loadThemeCatalog();
  const deck = approveOutline(createOutline(), { mode: 'html', theme: catalog.html[0].id });
  const doc = composeHtmlDeck(deck, catalog.html[0]);
  assert.deepEqual(compileImageJobs(deck, catalog['ai-image'][0]), []);
  assert.ok(doc.slides.every(slide => slide.elements.every(element => element.type !== 'image')));
});

test('ai-image mode creates one exact-text job per page', async () => {
  const catalog = await loadThemeCatalog();
  const deck = approveOutline(createOutline(), { mode: 'ai-image', theme: catalog['ai-image'][0].id });
  const jobs = compileImageJobs(deck, catalog['ai-image'][0]);
  assert.equal(jobs.length, deck.page_count);
  for (const [index, job] of jobs.entries()) for (const exact of deck.slides[index].exact_text) assert.match(job.prompt, new RegExp(exact));
});

test('HTML showcase is a real 22-page Bento deck', async () => {
  const path = new URL('../assets/examples/bento-theme-showcase/html/theme-showcase.bento.html', import.meta.url);
  const doc = parseBentoDocument(await readFile(path, 'utf8'));
  assert.equal(doc.slides.length, 22);
  assert.ok(doc.slides.every(slide => slide.elements.some(element => element.type === 'text')));
  assert.ok(doc.slides.every(slide => slide.elements.every(element => element.type !== 'image')));
});
