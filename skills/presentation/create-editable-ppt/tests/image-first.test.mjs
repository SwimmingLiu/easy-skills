import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import {
  approveOutlineDraft,
  compileDeckPrompts,
  createGenerationManifest,
  renderImageDeck,
  renderOutlinePreview,
  validateOutlineDraft,
} from '../scripts/lib/image-first.mjs';
import { renderHtmlImageDeck } from '../scripts/lib/html-assisted.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const themes = JSON.parse(await readFile(join(here, '..', 'assets', 'themes', 'image-themes.json'), 'utf8'));

function draft() {
  return {
    schema_version: 1,
    status: 'draft',
    title: 'AI 原生知识工作流',
    audience: '产品团队',
    purpose: '说明工作方式变化',
    central_message: '让上下文持续产生价值',
    narrative: {
      opening: '从信息碎片化切入',
      problem: '资料和判断彼此分离',
      insight: '工作流需要保留上下文',
      method: '收集、关联、判断、行动',
      action: '先重做一条高频流程',
    },
    slides: [
      {
        id: 's01',
        role: 'cover',
        purpose: '建立主题',
        claim: 'AI 原生知识工作流',
        exact_text: ['AI 原生知识工作流', '把散落信息变成持续可用的判断'],
        evidence: [],
        media_brief: '城市网络与知识流动的抽象意象',
        transition: '进入工作中的碎片化问题',
      },
      {
        id: 's02',
        role: 'process',
        purpose: '说明方法',
        claim: '四个动作，让信息持续产生价值',
        exact_text: ['四个动作，让信息持续产生价值', '收集现场', '建立关联', '形成判断', '推进行动'],
        evidence: [],
        media_brief: '四步连续流程',
        transition: '把方法落到一条具体流程',
      },
      {
        id: 's03',
        role: 'closing',
        purpose: '推动行动',
        claim: '先重做一条高频流程',
        exact_text: ['先重做一条高频流程', '把上下文、判断和行动连起来'],
        evidence: [],
        media_brief: '专注工作与开始行动的场景',
        transition: '结束',
      },
    ],
  };
}

test('content draft gate requires a central message, narrative, and complete slides', () => {
  const invalid = draft();
  delete invalid.central_message;
  invalid.narrative.action = '';
  invalid.slides[1].exact_text = [];
  const result = validateOutlineDraft(invalid);
  assert.equal(result.valid, false);
  assert.ok(result.errors.some((error) => error.path === 'central_message'));
  assert.ok(result.errors.some((error) => error.path === 'narrative.action'));
  assert.ok(result.errors.some((error) => error.path === 'slides.1.exact_text'));
});

test('approved drafts become the only image-first deck content source', () => {
  const deck = approveOutlineDraft(draft(), 'launch-tech');
  assert.equal(deck.status, 'approved');
  assert.equal(deck.central_message, '让上下文持续产生价值');
  assert.deepEqual(deck.narrative, draft().narrative);
  assert.equal(deck.theme.family, 'launch-tech');
  assert.deepEqual(deck.slides[0].exact_text, draft().slides[0].exact_text);
});

test('approval can select the HTML plus AI image mode without changing the content source', () => {
  const deck = approveOutlineDraft(draft(), 'editorial', { mode: 'html-image-assisted' });
  assert.equal(deck.output_mode, 'html-image-assisted');
  assert.equal(deck.presentation_mode, 'html-image-assisted');
  assert.deepEqual(deck.slides[1].exact_text, draft().slides[1].exact_text);
});

test('prompt compiler emits one deterministic full-slide image job per slide', () => {
  const deck = approveOutlineDraft(draft(), 'business-minimal');
  const jobs = compileDeckPrompts(deck, themes);
  assert.equal(jobs.length, 3);
  assert.deepEqual(jobs.map((job) => job.out), ['business-minimal-s01-cover.png', 'business-minimal-s02-process.png', 'business-minimal-s03-closing.png']);
  for (const job of jobs) {
    assert.equal(job.model, 'gpt-image-2');
    assert.equal(job.size, '2048x1152');
    assert.equal(job.quality, 'medium');
    assert.equal(job.use_case, 'productivity-visual');
    assert.match(job.prompt, /16:9/);
    assert.match(job.prompt, /文字必须逐字准确/);
    assert.match(job.prompt, /不得添加任何其他文字/);
    assert.match(job.prompt, /无水印/);
    assert.match(job.prompt, new RegExp(deck.slides.find((slide) => slide.role === job.role).exact_text[0]));
  }
});

test('HTML plus AI image mode emits visual-only jobs with deliberate negative space', () => {
  const deck = approveOutlineDraft(draft(), 'editorial', { mode: 'html-image-assisted' });
  const jobs = compileDeckPrompts(deck, themes);
  assert.equal(jobs.length, 3);
  assert.ok(jobs.every((job) => job.output_mode === 'html-image-assisted'));
  assert.ok(jobs.every((job) => job.asset_role === 'background-or-illustration'));
  assert.ok(jobs.every((job) => job.out.startsWith('editorial-') && job.out.endsWith('-visual.png')));
  assert.ok(jobs.every((job) => /Text:\s*none/i.test(job.prompt)));
  assert.ok(jobs.every((job) => /no letters|不得添加任何文字|do not render any text/i.test(job.prompt)));
  assert.doesNotMatch(jobs[0].prompt, /文字必须逐字准确/);
});

test('generation manifest is reproducible and never stores secret configuration', () => {
  const deck = approveOutlineDraft(draft(), 'academic');
  const jobs = compileDeckPrompts(deck, themes);
  const manifest = createGenerationManifest(deck, jobs, { provider: 'imagegen-cli' });
  const serialized = JSON.stringify(manifest);
  assert.equal(manifest.slides.length, 3);
  assert.doesNotMatch(serialized, /api[_-]?key|bearer|base_url|signed_url/i);
  assert.ok(manifest.slides.every((slide) => slide.status === 'prepared'));
});

test('HTML plus AI image manifests place generated visuals under assets', () => {
  const deck = approveOutlineDraft(draft(), 'business-minimal', { mode: 'html-image-assisted' });
  const manifest = createGenerationManifest(deck, compileDeckPrompts(deck, themes));
  assert.equal(manifest.output_mode, 'html-image-assisted');
  assert.ok(manifest.slides.every((slide) => slide.output_path.startsWith('assets/')));
  assert.ok(manifest.slides.every((slide) => slide.asset_role === 'background-or-illustration'));
});

test('outline preview shows narrative before page-level content', () => {
  const html = renderOutlinePreview(draft());
  assert.ok(html.indexOf('中心含义') < html.indexOf('第 1 页'));
  assert.ok(html.indexOf('叙事逻辑') < html.indexOf('第 1 页'));
  assert.doesNotMatch(html, /contenteditable/i);
});

test('image deck renderer uses only full-slide images for audience-facing pages', () => {
  const deck = approveOutlineDraft(draft(), 'premium-dark');
  const manifest = createGenerationManifest(deck, compileDeckPrompts(deck, themes));
  for (const slide of manifest.slides) slide.status = 'generated';
  const html = renderImageDeck(deck, manifest);
  assert.equal((html.match(/<img /g) ?? []).length, 3);
  assert.doesNotMatch(html, /contenteditable/i);
  assert.doesNotMatch(html, /data-field=/i);
  assert.match(html, /premium-dark-s01-cover\.png/);
});

test('HTML plus AI image renderer keeps exact copy in HTML and visual assets separate', () => {
  const deck = approveOutlineDraft(draft(), 'business-minimal', { mode: 'html-image-assisted' });
  const manifest = createGenerationManifest(deck, compileDeckPrompts(deck, themes));
  for (const slide of manifest.slides) slide.status = 'generated';
  const html = renderHtmlImageDeck(deck, manifest, themes['business-minimal']);
  assert.equal((html.match(/class="slide/g) ?? []).length, 3);
  assert.equal((html.match(/class="slide[^"]* active/g) ?? []).length, 1);
  assert.match(html, /\.slide\.full-bleed\{display:none/);
  assert.match(html, /\.slide\.active\.full-bleed\{display:block/);
  assert.match(html, /AI 原生知识工作流/);
  assert.match(html, /background-or-illustration/);
  assert.match(html, /business-minimal-s01-cover-visual\.png/);
  assert.doesNotMatch(html, /contenteditable|data-field=/i);
});
