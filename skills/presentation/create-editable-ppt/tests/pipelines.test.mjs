import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { compileImageJobs, composeAiImageDeck, inspectRaster } from '../scripts/lib/ai-image.mjs';
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

test('ai-image mode embeds one validated 16:9 raster per Bento page', async () => {
  const catalog = await loadThemeCatalog();
  const outline = createOutline();
  outline.slides = outline.slides.slice(0, 1);
  outline.page_count = 1;
  const deck = approveOutline(outline, { mode: 'ai-image', theme: catalog['ai-image'][0].id });
  const root = await mkdtemp(join(tmpdir(), 'bento-image-'));
  const path = join(root, 'slide.png');
  const fixture = Buffer.alloc(32);
  Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]).copy(fixture);
  fixture.writeUInt32BE(16, 16);
  fixture.writeUInt32BE(9, 20);
  await writeFile(path, fixture);
  try {
    assert.deepEqual(inspectRaster(fixture, path), { type: 'image/png', width: 16, height: 9 });
    const jpeg = Buffer.from([0xff, 0xd8, 0xff, 0xc0, 0x00, 0x11, 0x08, 0x00, 0x09, 0x00, 0x10, 0x03, 0x01, 0x11, 0x00, 0x02, 0x11, 0x00, 0x03, 0x11, 0x00, 0xff, 0xd9]);
    assert.deepEqual(inspectRaster(jpeg, 'slide.jpg'), { type: 'image/jpeg', width: 16, height: 9 });
    const doc = await composeAiImageDeck(deck, catalog['ai-image'][0], [path]);
    assert.match(doc.assets['slide-s01'], /^data:image\/png;base64,/);
    assert.deepEqual(doc.slides[0].elements[0], {
      id: 'page-s01', type: 'image', x: 0, y: 0, w: 1280, h: 720, rotation: 0, opacity: 1, src: 'asset:slide-s01', fit: 'fill', radius: 0,
    });
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('ai-image mode rejects missing pages, invalid files and non-16:9 assets', async () => {
  const catalog = await loadThemeCatalog();
  const outline = createOutline();
  outline.slides = outline.slides.slice(0, 1);
  outline.page_count = 1;
  const deck = approveOutline(outline, { mode: 'ai-image', theme: catalog['ai-image'][0].id });
  await assert.rejects(composeAiImageDeck(deck, catalog['ai-image'][0], []), /每一页/);
  assert.throws(() => inspectRaster(Buffer.from('not an image'), 'bad.png'), /不是可识别/);
  const square = Buffer.alloc(32);
  Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]).copy(square);
  square.writeUInt32BE(10, 16);
  square.writeUInt32BE(10, 20);
  assert.throws(() => inspectRaster(square, 'square.png'), /必须是 16:9/);
});

test('HTML showcase is a real 22-page Bento deck', async () => {
  const path = new URL('../assets/examples/bento-theme-showcase/html/theme-showcase.bento.html', import.meta.url);
  const doc = parseBentoDocument(await readFile(path, 'utf8'));
  assert.equal(doc.slides.length, 22);
  assert.ok(doc.slides.every(slide => slide.elements.some(element => element.type === 'text')));
  assert.ok(doc.slides.every(slide => slide.elements.every(element => element.type !== 'image')));
  const signatures = doc.slides.map(slide => `${slide.background}:${slide.elements.map(element => element.id).sort().join(',')}`);
  assert.equal(new Set(signatures).size, doc.slides.length, 'each canonical HTML theme needs a distinct visual structure');
});

test('html composer escapes user-visible text before placing it in Bento', async () => {
  const catalog = await loadThemeCatalog();
  const outline = createOutline();
  outline.slides[0].claim = '<context> & evidence';
  outline.slides[0].exact_text = [outline.slides[0].claim, 'A > B'];
  const deck = approveOutline(outline, { mode: 'html', theme: catalog.html[0].id });
  const doc = composeHtmlDeck(deck, catalog.html[0]);
  const values = doc.slides[0].elements.filter(element => element.type === 'text').map(element => element.html);
  assert.ok(values.includes('&lt;context&gt; &amp; evidence'));
  assert.ok(values.includes('A &gt; B'));
});
