import assert from 'node:assert/strict';
import test from 'node:test';

import { SLIDE_ROLES, defaultEditorState } from '../scripts/lib/model.mjs';
import { renderDeck } from '../scripts/lib/render.mjs';
import { THEMES } from '../scripts/lib/themes.mjs';
import { readFileSync } from 'node:fs';

function slideFor(role, index) {
  const propsByRole = {
    cover: { subtitle: '副标题', meta: '2026.07' },
    section: { index: '01', summary: '章节说明' },
    statement: { points: ['要点一', '要点二'] },
    'image-hero': { caption: '产品界面', image: 'hero' },
    'two-column': { left_title: '现状', left: ['问题'], right_title: '方案', right: ['处理'] },
    comparison: { left_title: '之前', left: ['手动'], right_title: '之后', right: ['自动'] },
    process: { steps: [{ title: '输入' }, { title: '生成' }, { title: '检查' }] },
    data: { metrics: [{ value: '42%', label: '转化率' }], points: ['数据有来源'] },
    quote: { quote: '会议结束时，行动已经开始。', attribution: '用户访谈' },
    closing: { action: '确认下一步', contact: 'team@example.com' },
  };
  return {
    id: `s${String(index + 1).padStart(2, '0')}`,
    role,
    claim: `${role} 页面主张`,
    layout: `${role}-default`,
    props: propsByRole[role],
    evidence: [],
    media: role === 'image-hero' ? ['hero'] : [],
    speaker_notes: '',
  };
}

function deck() {
  return {
    schema_version: 1,
    revision: 1,
    title: '完整角色测试',
    audience: 'team',
    purpose: 'demo',
    language: 'zh-CN',
    canvas: '16:9',
    density: 'speaker-led',
    theme: { family: 'business-minimal', variant: 'ink' },
    slides: SLIDE_ROLES.map(slideFor),
  };
}

test('every required role renders as a stable slide', () => {
  const spec = deck();
  const html = renderDeck({
    deck: spec,
    state: defaultEditorState(spec),
    assets: { schema_version: 1, assets: [{ id: 'hero', path: 'assets/hero.png', source: 'user', purpose: 'hero', fact_bearing: false }] },
  });
  for (const role of SLIDE_ROLES) {
    assert.match(html, new RegExp(`data-role="${role}"`));
  }
  assert.equal((html.match(/class="slide /g) ?? []).length, SLIDE_ROLES.length);
});

test('all eight theme families cover every required role', () => {
  assert.equal(Object.keys(THEMES).length, 8);
  for (const theme of Object.values(THEMES)) {
    assert.deepEqual([...theme.roles].sort(), [...SLIDE_ROLES].sort(), theme.id);
  }
});

test('escapes user-authored HTML in text and attributes', () => {
  const spec = deck();
  spec.slides[0].claim = '<img src=x onerror=alert(1)>';
  spec.slides[0].props.subtitle = '" onclick="alert(2)';
  const html = renderDeck({ deck: spec, state: defaultEditorState(spec), assets: { schema_version: 1, assets: [] } });
  assert.doesNotMatch(html, /<img src=x/);
  assert.doesNotMatch(html, /onclick="alert/);
  assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt;/);
});

test('embeds a safe project snapshot and offline presentation controls', () => {
  const spec = deck();
  spec.title = '</script><script>alert(1)</script>';
  const html = renderDeck({ deck: spec, state: defaultEditorState(spec), assets: { schema_version: 1, assets: [] } });
  assert.match(html, /id="deck-view-model" type="application\/json"/);
  assert.doesNotMatch(html, /<script>alert\(1\)<\/script>/);
  assert.match(html, /data-action="previous"/);
  assert.match(html, /data-action="next"/);
  assert.match(html, /data-action="present"/);
});

test('renders missing media as an explicit gap without a broken src', () => {
  const spec = deck();
  const html = renderDeck({ deck: spec, state: defaultEditorState(spec), assets: { schema_version: 1, assets: [] } });
  assert.match(html, /data-missing-media="hero"/);
  assert.doesNotMatch(html, /src="undefined"|src=""/);
});

test('includes the complete browser editing surface', () => {
  const spec = deck();
  const html = renderDeck({ deck: spec, state: defaultEditorState(spec), assets: { schema_version: 1, assets: [] } });
  for (const action of ['save', 'duplicate', 'delete', 'skip', 'review-pass', 'review-revise', 'export']) {
    assert.match(html, new RegExp(`data-action="${action}"`));
  }
  assert.match(html, /data-slide-list/);
  assert.match(html, /data-layout-select/);
  assert.match(html, /data-theme-select/);
  assert.match(html, /data-image-input/);
});

test('every theme has a dedicated visual recipe instead of token-only recoloring', () => {
  const css = readFileSync(new URL('../assets/runtime/themes.css', import.meta.url), 'utf8');
  for (const id of Object.keys(THEMES)) {
    assert.match(css, new RegExp(`data-theme="${id}"[^}]*\\] \\.role-cover|data-theme="${id}"\\] \\.role-cover`), id);
    assert.match(css, new RegExp(`data-theme="${id}"[^}]*\\] \\.media-frame|data-theme="${id}"\\] \\.media-frame`), id);
  }
});

test('cover slides can combine editable copy with a real image and omit debug role labels', () => {
  const spec = deck();
  spec.slides = [slideFor('cover', 0)];
  spec.slides[0].media = ['cover-photo'];
  const html = renderDeck({ deck: spec, state: defaultEditorState(spec), assets: { schema_version: 1, assets: [{ id: 'cover-photo', path: 'media/cover.jpg', source: 'user', purpose: 'cover', fact_bearing: false }] } });
  assert.match(html, /class="cover-shell has-media"/);
  assert.match(html, /src="media\/cover.jpg"/);
  assert.doesNotMatch(html, /<footer[^>]*>\s*<span>cover<\/span>/);
});
