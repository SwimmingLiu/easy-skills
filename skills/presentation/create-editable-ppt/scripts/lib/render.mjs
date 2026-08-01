import { readFileSync } from 'node:fs';

import { mergeDeckState } from './model.mjs';
import { resolveTheme, themeCss, THEMES } from './themes.mjs';

const baseCss = readFileSync(new URL('../../assets/runtime/base.css', import.meta.url), 'utf8');
const editorJs = readFileSync(new URL('../../assets/runtime/editor.js', import.meta.url), 'utf8');
const themeRecipesCss = readFileSync(new URL('../../assets/runtime/themes.css', import.meta.url), 'utf8');

const LAYOUTS_BY_ROLE = Object.freeze({
  cover: ['center', 'left'], section: ['index', 'statement'], statement: ['focus', 'points'],
  'image-hero': ['split', 'full-bleed'], 'two-column': ['balanced', 'emphasis-left', 'emphasis-right'],
  comparison: ['split', 'before-after'], process: ['steps', 'timeline'], data: ['metrics', 'chart-led'],
  quote: ['center', 'editorial'], closing: ['center', 'action-led'],
});

export function escapeHtml(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function safeJson(value) {
  return JSON.stringify(value).replaceAll('<', '\\u003c').replaceAll('>', '\\u003e').replaceAll('&', '\\u0026');
}

function editable(tag, text, slideId, field, className = '') {
  return `<${tag} class="editable ${className}" contenteditable="true" spellcheck="false" data-slide-id="${escapeHtml(slideId)}" data-field="${escapeHtml(field)}">${escapeHtml(text)}</${tag}>`;
}

function list(items, slideId, field, className = 'points') {
  const rows = (items ?? []).map((item, index) => `<li class="editable" contenteditable="true" spellcheck="false" data-slide-id="${escapeHtml(slideId)}" data-field="${escapeHtml(field)}.${index}">${escapeHtml(typeof item === 'string' ? item : item?.text ?? item?.title ?? '')}</li>`).join('');
  return `<ul class="${className}">${rows}</ul>`;
}

function mediaFrame(mediaId, assetsById) {
  const asset = assetsById.get(mediaId);
  if (!asset?.path) {
    return `<div class="media-frame"><div class="media-gap" data-missing-media="${escapeHtml(mediaId)}">缺少图片 · ${escapeHtml(mediaId)}</div></div>`;
  }
  return `<div class="media-frame" data-media-slot="hero"><img src="${escapeHtml(asset.path)}" alt="${escapeHtml(asset.alt ?? asset.purpose ?? '')}" data-asset-id="${escapeHtml(mediaId)}"></div>`;
}

function renderRole(slide, assetsById) {
  const p = slide.props ?? {};
  const claim = editable('h1', slide.claim, slide.id, 'claim');
  switch (slide.role) {
    case 'cover': {
      const mediaId = p.image ?? slide.media?.[0];
      return `<div class="cover-shell ${mediaId ? 'has-media' : 'no-media'}"><div class="cover-copy"><div class="eyebrow">${escapeHtml(p.eyebrow ?? 'Presentation')}</div>${claim}${editable('p', p.subtitle ?? '', slide.id, 'props.subtitle', 'lead')}${p.meta ? editable('p', p.meta, slide.id, 'props.meta', 'cover-meta') : ''}</div>${mediaId ? mediaFrame(mediaId, assetsById) : ''}</div>`;
    }
    case 'section':
      return `<div class="content"><div class="section-number">${escapeHtml(p.index ?? '')}</div>${claim}${editable('p', p.summary ?? '', slide.id, 'props.summary', 'lead')}</div>`;
    case 'statement':
      return `<div class="content statement-focus">${claim}${list(p.points, slide.id, 'props.points')}</div>`;
    case 'image-hero': {
      const mediaId = p.image ?? slide.media?.[0] ?? 'image';
      return `<div class="media-layout"><div>${claim}${editable('p', p.caption ?? '', slide.id, 'props.caption', 'lead')}</div>${mediaFrame(mediaId, assetsById)}</div>`;
    }
    case 'two-column':
    case 'comparison':
      return `<div class="content">${claim}<div class="columns"><div class="panel"><h3>${escapeHtml(p.left_title ?? '左侧')}</h3>${list(p.left, slide.id, 'props.left')}</div><div class="panel support"><h3>${escapeHtml(p.right_title ?? '右侧')}</h3>${list(p.right, slide.id, 'props.right')}</div></div></div>`;
    case 'process': {
      const steps = (p.steps ?? []).map((step, index) => `<div class="step"><div class="step-index">${String(index + 1).padStart(2, '0')}</div><div class="editable step-title" contenteditable="true" spellcheck="false" data-slide-id="${escapeHtml(slide.id)}" data-field="props.steps.${index}.title">${escapeHtml(step.title ?? step)}</div></div>`).join('');
      return `<div class="content">${claim}<div class="steps" style="--step-count:${Math.max(1, p.steps?.length ?? 1)}">${steps}</div></div>`;
    }
    case 'data': {
      const metrics = (p.metrics ?? []).map((metric, index) => `<div class="metric"><div class="editable metric-value" contenteditable="true" spellcheck="false" data-slide-id="${escapeHtml(slide.id)}" data-field="props.metrics.${index}.value">${escapeHtml(metric.value ?? '')}</div><div class="editable metric-label" contenteditable="true" spellcheck="false" data-slide-id="${escapeHtml(slide.id)}" data-field="props.metrics.${index}.label">${escapeHtml(metric.label ?? '')}</div></div>`).join('');
      return `<div class="content">${claim}<div class="metrics">${metrics}</div>${list(p.points, slide.id, 'props.points')}</div>`;
    }
    case 'quote':
      return `<div class="content"><div class="quote-mark">“</div>${editable('p', p.quote ?? slide.claim, slide.id, 'props.quote', 'quote-text')}${editable('p', p.attribution ?? '', slide.id, 'props.attribution', 'quote-attribution')}</div>`;
    case 'closing': {
      const mediaId = p.image ?? slide.media?.[0];
      if (mediaId) return `<div class="closing-shell"><div class="closing-copy">${claim}${editable('p', p.action ?? '', slide.id, 'props.action', 'closing-action')}${editable('p', p.contact ?? '', slide.id, 'props.contact', 'lead')}</div>${mediaFrame(mediaId, assetsById)}</div>`;
      return `<div class="content hero-center">${claim}${editable('p', p.action ?? '', slide.id, 'props.action', 'closing-action')}${editable('p', p.contact ?? '', slide.id, 'props.contact', 'lead')}</div>`;
    }
    default:
      return `<div class="content">${claim}</div>`;
  }
}

function slideMarkup(slide, index, total, assetsById) {
  const classes = ['slide', `role-${slide.role}`, slide.skipped ? 'is-skipped' : '', index === 0 ? 'is-active' : ''].filter(Boolean).join(' ');
  return `<section class="${classes}" data-slide-id="${escapeHtml(slide.id)}" data-role="${escapeHtml(slide.role)}" data-layout="${escapeHtml(slide.layout)}" data-review-status="${escapeHtml(slide.review_status ?? 'pending')}">${renderRole(slide, assetsById)}<footer class="footer"><span>${escapeHtml(slide.props?.footer ?? '')}</span><span>${index + 1} / ${total}</span></footer></section>`;
}

export function renderDeck({ deck, state, assets = { schema_version: 1, assets: [] } }) {
  const merged = state ? mergeDeckState(deck, state) : structuredClone(deck);
  const theme = resolveTheme(merged.theme?.family);
  const assetsById = new Map((assets.assets ?? []).map((asset) => [asset.id, asset]));
  const slides = merged.slides.map((slide, index) => slideMarkup(slide, index, merged.slides.length, assetsById)).join('\n');
  const viewModel = { deck: merged, state, assets, themes: Object.keys(THEMES), layouts: LAYOUTS_BY_ROLE };
  const themeOptions = Object.values(THEMES).map((item) => `<option value="${escapeHtml(item.id)}"${item.id === theme.id ? ' selected' : ''}>${escapeHtml(item.label)}</option>`).join('');
  const thumbnails = merged.slides.map((slide, index) => `<button type="button" class="thumbnail${index === 0 ? ' is-active' : ''}" data-thumbnail="${escapeHtml(slide.id)}" draggable="true"><span>${index + 1}</span><strong>${escapeHtml(slide.claim)}</strong><small>${escapeHtml(slide.role)}</small></button>`).join('');

  return `<!doctype html>
<html lang="${escapeHtml(merged.language ?? 'en')}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>${escapeHtml(merged.title)}</title>
<style>${baseCss}\n${themeCss()}\n${themeRecipesCss}</style>
</head>
<body>
<div class="app">
  <header class="toolbar" aria-label="Presentation controls">
    <strong class="toolbar-title">${escapeHtml(merged.title)}</strong>
    <button type="button" data-action="previous" title="Previous slide" aria-label="Previous slide">←</button>
    <span class="page-counter" data-page-counter>1 / ${merged.slides.length}</span>
    <button type="button" data-action="next" title="Next slide" aria-label="Next slide">→</button>
    <button type="button" data-action="present" title="Presentation mode" aria-label="Presentation mode">⛶</button>
    <button type="button" data-action="save" title="Save changes" aria-label="Save changes">✓</button>
    <button type="button" data-action="export" title="Export" aria-label="Export">⇩</button>
    <span class="save-status" data-save-status>已保存</span>
  </header>
  <div class="workspace">
    <aside class="slide-list" data-slide-list aria-label="Slides">${thumbnails}</aside>
    <main class="viewport">
      <div class="deck" data-theme="${escapeHtml(theme.id)}" data-variant="${escapeHtml(merged.theme?.variant ?? theme.variants[0])}">${slides}</div>
    </main>
    <aside class="inspector" aria-label="Slide inspector">
      <label>主题<select data-theme-select>${themeOptions}</select></label>
      <label>布局<select data-layout-select></select></label>
      <div class="inspector-actions">
        <button type="button" data-action="duplicate" title="Duplicate slide">⧉</button>
        <button type="button" data-action="delete" title="Delete slide">⌫</button>
        <button type="button" data-action="skip" title="Skip slide">⊘</button>
      </div>
      <div class="review-actions" aria-label="Review status">
        <button type="button" data-action="review-pass">通过</button>
        <button type="button" data-action="review-revise">待修改</button>
      </div>
      <label class="image-control">替换插图<input type="file" accept="image/*" data-image-input></label>
      <div class="export-menu" data-export-menu hidden>
        <button type="button" data-export-format="html">HTML</button><button type="button" data-export-format="pdf">PDF</button><button type="button" data-export-format="png">PNG</button><button type="button" data-export-format="pptx">PPTX</button>
      </div>
    </aside>
  </div>
</div>
<script id="deck-view-model" type="application/json">${safeJson(viewModel)}</script>
<script>${editorJs.replaceAll('</script', '<\\/script')}</script>
</body>
</html>`;
}
