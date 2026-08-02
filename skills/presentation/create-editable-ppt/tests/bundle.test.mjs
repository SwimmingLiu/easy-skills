import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { buildBundledHtmlImageDeck, buildBundledImageDeck } from '../scripts/lib/bundle.mjs';

test('Bento-inspired bundle embeds the JSON document and every slide image offline', async () => {
  const root = await mkdtemp(join(tmpdir(), 'image-ppt-bundle-'));
  await mkdir(join(root, 'slides'));
  const pixels = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  await writeFile(join(root, 'slides', 's01.png'), pixels);
  const deck = {
    schema_version: 2,
    status: 'approved',
    title: 'Bundle test <safe>',
    purpose: 'verify offline document',
    central_message: 'One source of truth',
    theme: { family: 'business-minimal' },
    slides: [{ id: 's01', role: 'cover', claim: 'A claim <safe>', exact_text: ['A claim <safe>'], speaker_notes: 'note' }],
  };
  const manifest = {
    schema_version: 1,
    title: deck.title,
    theme: deck.theme.family,
    output_mode: 'full-slide-image',
    slides: [{ id: 's01', role: 'cover', output_path: 'slides/s01.png', status: 'generated', prompt: 'safe prompt' }],
  };
  const html = await buildBundledImageDeck(root, deck, manifest);
  assert.match(html, /type="application\/image-ppt\+json"/);
  assert.match(html, /id="image-ppt-doc"/);
  assert.match(html, /data:image\/png;base64,/);
  assert.doesNotMatch(html, /src="slides\//);
  const jsonBlock = html.match(/<script type="application\/image-ppt\+json" id="image-ppt-doc">([\s\S]*?)<\/script>/)?.[1] ?? '';
  assert.doesNotMatch(jsonBlock, /</);
  assert.match(html, /\\u003c/);
  assert.match(html, /readonly/);
  assert.match(html, /"mode":"present"/);
});

test('bundle rejects a prepared or missing slide', async () => {
  const root = await mkdtemp(join(tmpdir(), 'image-ppt-bundle-'));
  const deck = { title: 'Deck', slides: [{ id: 's01', role: 'cover', claim: 'Claim' }] };
  const manifest = { slides: [{ id: 's01', output_path: 'slides/missing.png', status: 'prepared' }] };
  await assert.rejects(buildBundledImageDeck(root, deck, manifest), /generated|missing/i);
});

test('HTML plus AI image bundle separates visual asset references from exact copy', async () => {
  const root = await mkdtemp(join(tmpdir(), 'html-image-ppt-bundle-'));
  await mkdir(join(root, 'assets'));
  const pixels = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  await writeFile(join(root, 'assets', 's01-visual.png'), pixels);
  const deck = {
    schema_version: 2,
    status: 'approved',
    title: 'HTML visual test',
    purpose: 'verify HTML copy',
    central_message: 'Copy remains structured',
    theme: { family: 'editorial' },
    output_mode: 'html-image-assisted',
    slides: [{ id: 's01', role: 'cover', claim: 'A claim', exact_text: ['A claim', 'A support line'], speaker_notes: 'note' }],
  };
  const manifest = {
    schema_version: 1,
    title: deck.title,
    theme: deck.theme.family,
    output_mode: 'html-image-assisted',
    slides: [{ id: 's01', role: 'cover', output_path: 'assets/s01-visual.png', status: 'generated', prompt: 'visual only', asset_role: 'background-or-illustration' }],
  };
  const html = await buildBundledHtmlImageDeck(root, deck, manifest);
  assert.match(html, /"mode":"html-image-assisted"/);
  assert.match(html, /data:image\/png;base64,/);
  assert.match(html, /A claim/);
  assert.match(html, /visual/);
  assert.doesNotMatch(html, /src="assets\//);
});
