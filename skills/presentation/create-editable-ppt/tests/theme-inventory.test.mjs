import assert from 'node:assert/strict';
import test from 'node:test';

import {
  loadThemeCatalog,
  loadThemeInventory,
  resolveThemeRecipe,
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
    new Set(['frontend-slides', 'visual-explainer', 'open-codesign', 'html-ppt-skill', 'open-slide', 'dashi-ppt-skill', 'beautiful-html-templates', 'bento', 'baoyu-design']),
  );
});

test('every source repository is pinned to a full commit', async () => {
  for (const mode of ['ai-image', 'html']) {
    const inventory = await loadThemeInventory(mode);
    for (const repository of inventory.repositories) assert.match(repository.commit, /^[0-9a-f]{40}$/, `${repository.id} commit`);
  }
});

test('inventory counts prove complete extraction at each pinned source', async () => {
  const expected = {
    'ai-image': {
      'guizang-ppt-skill': 9,
      'codex-ppt-skill': 12,
      GordenSuperPPTSkills: 6,
      'gpt-image2-ppt-skills': 265,
      'wuming-cyan-circuit-launch-ppt': 1,
      'wuming-ai-ppt-cover': 2,
    },
    html: {
      'frontend-slides': 12,
      'visual-explainer': 4,
      'open-codesign': 35,
      'html-ppt-skill': 51,
      'open-slide': 5,
      'dashi-ppt-skill': 12,
      'beautiful-html-templates': 34,
      bento: 0,
      'baoyu-design': 0,
    },
  };
  for (const mode of ['ai-image', 'html']) {
    const inventory = await loadThemeInventory(mode);
    const repositories = new Map(inventory.repositories.map(repository => [repository.id, repository]));
    for (const [id, count] of Object.entries(expected[mode])) assert.equal(repositories.get(id).theme_count, count, `${mode}:${id}`);
    assert.equal(inventory.themes.filter(theme => theme.kind === 'theme').length, Object.values(expected[mode]).reduce((sum, count) => sum + count, 0));
  }
  const html = await loadThemeInventory('html');
  assert.equal(html.repositories.find(repository => repository.id === 'baoyu-design').methodology_count, 1);
});

test('HTML inventory points at the requested repositories and real named systems', async () => {
  const html = await loadThemeInventory('html');
  const repositories = new Map(html.repositories.map(item => [item.id, item]));
  assert.equal(repositories.get('visual-explainer').url, 'https://github.com/nicobailon/visual-explainer');
  assert.equal(repositories.get('open-codesign').url, 'https://github.com/OpenCoworkAI/open-codesign');
  assert.equal(repositories.get('open-slide').url, 'https://github.com/1weiho/open-slide');
  assert.equal(repositories.get('bento').role, 'output-editor');

  const keys = new Set(html.themes.map(theme => theme.key));
  for (const id of ['midnight-editorial', 'warm-signal', 'terminal-mono', 'swiss-clean']) assert.ok(keys.has(`visual-explainer:${id}`), id);
  for (const id of ['bright-sans', 'minecraft', 'aurora', 'replit', 'sticker-pop']) assert.ok(keys.has(`open-slide:${id}`), id);
  for (const id of ['vercel', 'linear', 'stripe', 'figma', 'notion', 'apple', 'airbnb', 'spotify', 'cursor', 'supabase', 'posthog', 'framer', 'runwayml', 'mistral', 'elevenlabs', 'coinbase', 'revolut', 'nike', 'ferrari', 'spacex', 'starbucks', 'shopify', 'ibm', 'raycast', 'cal-com']) assert.ok(keys.has(`open-codesign:brand/${id}`), id);
  const methodology = html.themes.find(theme => theme.key === 'baoyu-design:methodology/design-system-bound');
  assert.equal(methodology.kind, 'methodology');
  assert.equal(methodology.canonical_id, null);
  assert.ok(!keys.has('visual-explainer:editorial'));
  assert.ok(!keys.has('open-slide:default'));
});

test('every source theme maps exactly once to a canonical recipe in the same mode', async () => {
  const catalog = await loadThemeCatalog();
  for (const mode of ['ai-image', 'html']) {
    const inventory = await loadThemeInventory(mode);
    const aliases = catalog[mode].flatMap(theme => theme.aliases.map(alias => [alias, theme.id]));
    assert.equal(new Set(aliases.map(([alias]) => alias)).size, aliases.length, `${mode} aliases must be unique`);
    const sourceThemes = inventory.themes.filter(source => source.kind === 'theme');
    assert.equal(aliases.length, sourceThemes.length, `${mode} alias coverage`);
    const aliasMap = new Map(aliases);
    for (const source of sourceThemes) assert.ok(aliasMap.has(source.key), source.key);
  }
  assert.deepEqual(validateThemeCatalog(catalog), { valid: true, errors: [] });
});

test('distinct upstream HTML styles survive deduplication', async () => {
  const html = await loadThemeInventory('html');
  const mapped = new Map(html.themes.map(theme => [theme.key, theme.canonical_id]));
  assert.equal(mapped.get('open-slide:minecraft'), 'pixel-arcade');
  assert.equal(mapped.get('open-slide:sticker-pop'), 'playful-pastel');
  assert.equal(mapped.get('frontend-slides:creative-vibrant'), 'playful-pastel');
  assert.equal(mapped.get('frontend-slides:luxury-premium'), 'magazine-deep-blue');
  assert.equal(mapped.get('dashi-ppt-skill:theme03'), 'terminal-mono');
  assert.equal(mapped.get('dashi-ppt-skill:theme04'), 'glass-candy');
  assert.equal(mapped.get('dashi-ppt-skill:theme10'), 'finance-index');
  assert.equal(mapped.get('open-codesign:brand/spotify'), 'neon-entertainment');
  assert.equal(mapped.get('open-codesign:brand/starbucks'), 'organic-craft');
});

test('canonical recipes resolve from both canonical ids and source aliases', async () => {
  const catalog = await loadThemeCatalog();
  assert.equal(resolveThemeRecipe(catalog, 'html', 'pixel-arcade').id, 'pixel-arcade');
  assert.equal(resolveThemeRecipe(catalog, 'html', 'open-slide:minecraft').id, 'pixel-arcade');
  assert.equal(resolveThemeRecipe(catalog, 'ai-image', 'wuming-cyan-circuit-launch-ppt:cyan-circuit-launch').id, 'cyan-circuit');
  assert.equal(resolveThemeRecipe(catalog, 'html', 'missing-theme'), undefined);
});

test('retired canonical theme ids are absent', async () => {
  const catalog = await loadThemeCatalog();
  const ids = [...catalog['ai-image'], ...catalog.html].map(theme => theme.id);
  for (const retired of ['business-minimal', 'editorial', 'swiss-grid', 'launch-tech', 'data-consulting', 'academic', 'brand-bold', 'premium-dark']) {
    assert.ok(!ids.includes(retired), retired);
  }
});
