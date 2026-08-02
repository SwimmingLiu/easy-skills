import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createBentoDocument,
  extractBentoBlock,
  parseBentoDocument,
  spliceBentoDocument,
} from '../scripts/lib/bento-document.mjs';

const shell = '<!doctype html><html><body><script type="application/bento+json" id="bento-doc">{"format":"bento/slides","version":1,"size":{"width":1280,"height":720},"theme":{"background":"#fff","color":"#111","accent":"#f00","fontFamily":"sans-serif"},"slides":[]}</script><main>shell</main></body></html>';

test('Bento block escaping prevents literal script termination', () => {
  const doc = createBentoDocument({ title: '</script><p>bad</p>', slides: [] });
  const html = spliceBentoDocument(shell, doc);
  assert.doesNotMatch(extractBentoBlock(html), /<\/script>/i);
  assert.equal(parseBentoDocument(html).title, '</script><p>bad</p>');
});

test('splicing changes only the Bento block and preserves an existing docId', () => {
  const existing = { ...parseBentoDocument(shell), docId: 'stable-doc-id', unknown: { keep: true } };
  const withExisting = spliceBentoDocument(shell, existing);
  const updated = { ...existing, title: 'Updated' };
  const output = spliceBentoDocument(withExisting, updated, { previous: existing });
  assert.equal(parseBentoDocument(output).docId, 'stable-doc-id');
  assert.deepEqual(parseBentoDocument(output).unknown, { keep: true });
  assert.equal(output.replace(extractBentoBlock(output), ''), withExisting.replace(extractBentoBlock(withExisting), ''));
});

test('invalid shells and changed document identity are rejected', () => {
  const doc = createBentoDocument({ title: 'Deck', slides: [] });
  assert.throws(() => spliceBentoDocument('<html></html>', doc), /one #bento-doc block/);
  assert.throws(() => spliceBentoDocument(shell + shell, doc), /one #bento-doc block/);
  assert.throws(() => spliceBentoDocument(shell, { ...doc, format: 'image-ppt' }), /bento\/slides/);
  assert.throws(() => spliceBentoDocument(shell, { ...doc, docId: 'new' }, { previous: { ...doc, docId: 'old' } }), /docId/);
});
