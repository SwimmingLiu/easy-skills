import assert from 'node:assert/strict';
import test from 'node:test';

import {
  loadThemeCatalog,
  loadThemeInventory,
  validateThemeCatalog,
} from '../scripts/lib/theme-catalog.mjs';

test('every requested source repository is represented in its mode inventory', async () => {
  const image = await loadThemeInventory('ai-image');
  const html = await loadThemeInventory('html');
  assert.deepEqual(
    new Set(image.repositories.map(item => item.id)),
    new Set(['guizang-ppt-skill', 'codex-ppt-skill', 'GordenSuperPPTSkills', 'gpt-image2-ppt-skills', 'wuming-cyan-circuit-launch-ppt', 'wuming-ai-ppt-cover']),
  );
  assert.deepEqual(
    new Set(html.repositories.map(item => item.id)),
    new Set(['frontend-slides', 'visual-explainer', 'open-codesign', 'html-ppt-skill', 'open-slide', 'dashi-ppt-skill', 'beautiful-html-templates', 'baoyu-design']),
  );
});

test('every source theme maps exactly once to a canonical recipe in the same mode', async () => {
  const catalog = await loadThemeCatalog();
  for (const mode of ['ai-image', 'html']) {
    const inventory = await loadThemeInventory(mode);
    const aliases = catalog[mode].flatMap(theme => theme.aliases.map(alias => [alias, theme.id]));
    assert.equal(new Set(aliases.map(([alias]) => alias)).size, aliases.length, `${mode} aliases must be unique`);
    assert.equal(aliases.length, inventory.themes.length, `${mode} alias coverage`);
    const aliasMap = new Map(aliases);
    for (const source of inventory.themes) assert.ok(aliasMap.has(source.key), source.key);
  }
  assert.deepEqual(validateThemeCatalog(catalog), { valid: true, errors: [] });
});

test('retired canonical theme ids are absent', async () => {
  const catalog = await loadThemeCatalog();
  const ids = [...catalog['ai-image'], ...catalog.html].map(theme => theme.id);
  for (const retired of ['business-minimal', 'editorial', 'swiss-grid', 'launch-tech', 'data-consulting', 'academic', 'brand-bold', 'premium-dark']) {
    assert.ok(!ids.includes(retired), retired);
  }
});
