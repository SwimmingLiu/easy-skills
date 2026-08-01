import assert from 'node:assert/strict';
import { mkdtemp, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { buildThemeShowcase } from '../scripts/build-theme-showcase.mjs';
import { THEMES } from '../scripts/lib/themes.mjs';

test('builds all eight themes from one shared content model', async () => {
  const root = await mkdtemp(join(tmpdir(), 'theme-showcase-'));
  const result = await buildThemeShowcase(root);
  assert.equal(result.themes.length, 8);
  const claims = [];
  for (const id of Object.keys(THEMES)) {
    const deck = JSON.parse(await readFile(join(root, 'decks', id, 'deck_spec.json'), 'utf8'));
    assert.equal(deck.theme.family, id);
    assert.ok(deck.slides.some((slide) => slide.media.length > 0));
    claims.push(deck.slides.map((slide) => slide.claim));
  }
  for (const claimSet of claims.slice(1)) assert.deepEqual(claimSet, claims[0]);
});

test('gallery links every theme and previews its rendered cover', async () => {
  const root = await mkdtemp(join(tmpdir(), 'theme-showcase-'));
  await buildThemeShowcase(root);
  const html = await readFile(join(root, 'index.html'), 'utf8');
  for (const id of Object.keys(THEMES)) {
    assert.match(html, new RegExp(`decks/${id}/index.html`));
    assert.match(html, new RegExp(`decks/${id}/qa/screenshots/01-s01.png`));
  }
});
