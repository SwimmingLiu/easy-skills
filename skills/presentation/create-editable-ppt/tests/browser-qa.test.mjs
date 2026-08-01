import assert from 'node:assert/strict';
import test from 'node:test';

import { classifyGeometry } from '../scripts/lib/browser-qa.mjs';

test('classifies blank slides, overflow, off-canvas nodes, and broken media', () => {
  const findings = classifyGeometry({
    slide_id: 's2', text: '', scroll_width: 1601, scroll_height: 900, client_width: 1600, client_height: 900,
    off_canvas: ['title'], broken_media: ['hero'], collisions: [['a', 'b']],
  });
  assert.deepEqual(findings.map((item) => item.code).sort(), [
    'layout.blank', 'layout.collision', 'layout.off_canvas', 'layout.overflow', 'media.broken',
  ]);
  assert.ok(findings.every((item) => item.slide_id === 's2'));
});

test('returns no findings for a healthy slide snapshot', () => {
  assert.deepEqual(classifyGeometry({ slide_id: 's1', text: 'Visible', scroll_width: 1600, scroll_height: 900, client_width: 1600, client_height: 900, off_canvas: [], broken_media: [], collisions: [] }), []);
});
