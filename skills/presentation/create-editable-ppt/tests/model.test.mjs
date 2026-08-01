import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ProjectConflictError,
  defaultEditorState,
  mergeDeckState,
  transitionProjectState,
  validateDeck,
} from '../scripts/lib/model.mjs';

function validDeck(overrides = {}) {
  return {
    schema_version: 1,
    revision: 1,
    title: 'Nimbus 投资人介绍',
    audience: 'investors',
    purpose: 'fundraising',
    language: 'zh-CN',
    canvas: '16:9',
    density: 'speaker-led',
    theme: { family: 'business-minimal', variant: 'ink' },
    slides: [
      {
        id: 's01',
        role: 'cover',
        claim: 'Nimbus 让会议结论直接进入执行',
        layout: 'cover-centered',
        props: { subtitle: 'AI 会议助手' },
        evidence: [],
        media: [],
        speaker_notes: '',
      },
      {
        id: 's02',
        role: 'statement',
        claim: '跨语言讨论不再丢失行动项',
        layout: 'statement-focus',
        props: { points: ['自动转录', '中英文总结'] },
        evidence: [{ type: 'product-capability', ref: 'source-01' }],
        media: [],
        speaker_notes: '只陈述已有能力，不补造数据。',
      },
    ],
    ...overrides,
  };
}

test('accepts a concise deck with supported roles', () => {
  const result = validateDeck(validDeck(), { assets: { assets: [] } });
  assert.equal(result.valid, true);
  assert.deepEqual(result.findings, []);
});

test('rejects a deck without a title', () => {
  const result = validateDeck(validDeck({ title: '' }), { assets: { assets: [] } });
  assert.equal(result.valid, false);
  assert.ok(result.findings.some((item) => item.code === 'deck.title.required'));
});

test('rejects duplicate slide ids', () => {
  const deck = validDeck();
  deck.slides[1].id = 's01';
  const result = validateDeck(deck, { assets: { assets: [] } });
  assert.ok(result.findings.some((item) => item.code === 'slide.id.duplicate'));
});

test('rejects unsupported slide roles', () => {
  const deck = validDeck();
  deck.slides[1].role = 'freeform-canvas';
  const result = validateDeck(deck, { assets: { assets: [] } });
  assert.ok(result.findings.some((item) => item.code === 'slide.role.unsupported'));
});

test('flags speaker-led slides with more than 60 visible Chinese characters', () => {
  const deck = validDeck();
  deck.slides[1].claim = '这是一段故意写得很长的页面标题，用来验证现场演讲页面不会因为自动生成而塞入过多文字。';
  deck.slides[1].props.points = [
    '第一条说明也故意保持很长，因为标题和正文合计应该触发简洁度检查。',
    '第二条继续增加可见文字，验证规则不会只检查标题。',
  ];
  const result = validateDeck(deck, { assets: { assets: [] } });
  assert.ok(result.findings.some((item) => item.code === 'slide.copy.too_long'));
});

test('does not count media ids, footers, or production metadata as audience copy', () => {
  const deck = validDeck();
  deck.slides[0].props = { subtitle: '一句简短说明', image: 'an-extremely-long-internal-media-identifier-that-is-not-visible-copy', footer: 'INTERNAL SECTION MARK', meta: '2026.07' };
  const result = validateDeck(deck, { assets: { assets: [] } });
  assert.ok(!result.findings.some((item) => item.code === 'slide.copy.too_long' && item.slide_id === deck.slides[0].id));
});

test('rejects media references missing from the asset manifest', () => {
  const deck = validDeck();
  deck.slides[1].media = ['product-shot'];
  const result = validateDeck(deck, { assets: { assets: [] } });
  assert.ok(result.findings.some((item) => item.code === 'slide.media.missing'));
});

test('merges text, props, ordering, deletion, and skip state', () => {
  const deck = validDeck();
  const merged = mergeDeckState(deck, {
    schema_version: 1,
    base_revision: 1,
    revision: 3,
    slide_order: ['s02', 's01'],
    deleted_slides: ['s01'],
    skipped_slides: ['s02'],
    duplicated_slides: [],
    text_overrides: { s02: { claim: '修改后的主张' } },
    prop_overrides: { s02: { points: ['修改后的内容'] } },
    review_status: { s02: 'revise' },
  });

  assert.equal(merged.slides.length, 1);
  assert.equal(merged.slides[0].id, 's02');
  assert.equal(merged.slides[0].claim, '修改后的主张');
  assert.deepEqual(merged.slides[0].props.points, ['修改后的内容']);
  assert.equal(merged.slides[0].skipped, true);
  assert.equal(merged.slides[0].review_status, 'revise');
});

test('rejects editor state based on a stale deck revision', () => {
  assert.throws(
    () => mergeDeckState(validDeck({ revision: 2 }), {
      schema_version: 1,
      base_revision: 1,
      revision: 1,
      slide_order: [],
      deleted_slides: [],
      skipped_slides: [],
      duplicated_slides: [],
      text_overrides: {},
      prop_overrides: {},
      review_status: {},
    }),
    ProjectConflictError,
  );
});

test('enforces adjacent project Gate transitions while allowing review rollback', () => {
  const state = defaultEditorState(validDeck());
  assert.equal(state.project_status, 'drafting');
  assert.equal(transitionProjectState(state, 'outline-review').project_status, 'outline-review');
  assert.throws(() => transitionProjectState(state, 'generating'), /Invalid project status transition/);
  const review = { ...state, project_status: 'review' };
  assert.equal(transitionProjectState(review, 'editing').project_status, 'editing');
  assert.equal(transitionProjectState(review, 'exported').project_status, 'exported');
});
