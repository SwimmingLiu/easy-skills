const NARRATIVE_KEYS = ['opening', 'problem', 'insight', 'method', 'action'];
const SLIDE_ROLES = new Set(['cover', 'section', 'statement', 'image-hero', 'two-column', 'comparison', 'process', 'data', 'quote', 'closing']);
const CONTENT_KINDS = new Set(['claim', 'image', 'flow', 'comparison', 'table', 'chart']);
export const PRESENTATION_MODES = Object.freeze({
  IMAGE_FIRST: 'image-first',
  PURE_HTML: 'pure-html',
});

function normalizeMode(value) {
  if (value === PRESENTATION_MODES.IMAGE_FIRST || value === 'full-slide-image' || value == null) return PRESENTATION_MODES.IMAGE_FIRST;
  if (value === PRESENTATION_MODES.PURE_HTML) return PRESENTATION_MODES.PURE_HTML;
  throw new Error(`Unsupported presentation mode: ${value}`);
}

function present(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function inferContentKind(role) {
  if (role === 'process') return 'flow';
  if (role === 'comparison') return 'comparison';
  if (role === 'data') return 'chart';
  if (role === 'image-hero' || role === 'cover' || role === 'closing') return 'image';
  return 'claim';
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

export function validateOutlineDraft(draft) {
  const errors = [];
  const requireText = (path, value) => { if (!present(value)) errors.push({ path, message: 'required text is missing' }); };
  if (!draft || typeof draft !== 'object') return { valid: false, errors: [{ path: '$', message: 'draft must be an object' }] };
  requireText('title', draft.title);
  requireText('audience', draft.audience);
  requireText('purpose', draft.purpose);
  requireText('central_message', draft.central_message);
  for (const key of NARRATIVE_KEYS) requireText(`narrative.${key}`, draft.narrative?.[key]);
  if (!Array.isArray(draft.slides) || draft.slides.length === 0) {
    errors.push({ path: 'slides', message: 'at least one slide is required' });
  } else {
    const ids = new Set();
    draft.slides.forEach((slide, index) => {
      const prefix = `slides.${index}`;
      requireText(`${prefix}.id`, slide?.id);
      if (ids.has(slide?.id)) errors.push({ path: `${prefix}.id`, message: 'slide id must be unique' });
      ids.add(slide?.id);
      if (!SLIDE_ROLES.has(slide?.role)) errors.push({ path: `${prefix}.role`, message: 'unsupported slide role' });
      if (slide?.content_kind && !CONTENT_KINDS.has(slide.content_kind)) errors.push({ path: `${prefix}.content_kind`, message: 'unsupported content kind' });
      requireText(`${prefix}.purpose`, slide?.purpose);
      requireText(`${prefix}.claim`, slide?.claim);
      if (!Array.isArray(slide?.exact_text) || slide.exact_text.length === 0 || slide.exact_text.some((line) => !present(line))) {
        errors.push({ path: `${prefix}.exact_text`, message: 'at least one exact visible text line is required' });
      }
      requireText(`${prefix}.media_brief`, slide?.media_brief);
      requireText(`${prefix}.transition`, slide?.transition);
    });
  }
  return { valid: errors.length === 0, errors };
}

export function approveOutlineDraft(draft, themeId, options = {}) {
  const validation = validateOutlineDraft(draft);
  if (!validation.valid) throw new Error(`Outline draft is invalid: ${validation.errors.map((error) => error.path).join(', ')}`);
  if (!present(themeId)) throw new Error('A theme id is required to approve the outline.');
  const mode = normalizeMode(options.mode ?? options.output_mode);
  return {
    schema_version: 2,
    status: 'approved',
    title: draft.title,
    audience: draft.audience,
    purpose: draft.purpose,
    central_message: draft.central_message,
    narrative: structuredClone(draft.narrative),
    language: draft.language ?? 'zh-CN',
    canvas: '16:9',
    presentation_mode: mode,
    output_mode: mode === PRESENTATION_MODES.PURE_HTML ? PRESENTATION_MODES.PURE_HTML : 'full-slide-image',
    theme: { family: themeId },
    slides: structuredClone(draft.slides).map((slide) => ({
      ...slide,
      content_kind: slide.content_kind ?? inferContentKind(slide.role),
      visual_anchor_id: slide.visual_anchor_id ?? `${themeId}-anchor`,
      continuity_group: slide.continuity_group ?? `${themeId}-deck`,
      speaker_notes: slide.speaker_notes ?? slide.claim,
    })),
  };
}

function promptLines(label, values) {
  return `${label}:\n${values.map((value, index) => `${index + 1}. "${value}"`).join('\n')}`;
}

export function compileSlidePrompt(slide, theme, options = {}) {
  if (!theme) throw new Error('Theme recipe is required.');
  const model = options.model ?? 'gpt-image-2';
  const size = options.size ?? '2048x1152';
  const quality = options.quality ?? 'medium';
  const mode = normalizeMode(options.mode ?? options.output_mode);
  if (mode === PRESENTATION_MODES.PURE_HTML) throw new Error('Pure HTML mode does not use image-generation prompts.');
  const shared = [
    'Use case: productivity-visual',
    `Primary request: create one polished 16:9 visual for the slide role "${slide.role}".`,
    `Communication purpose: ${slide.purpose}`,
    `Single claim: ${slide.claim}`,
    `Audience: ${options.audience ?? 'professional Chinese-speaking audience'}`,
    `Art direction: ${theme.art_direction}`,
    `Composition/framing: ${theme.composition}`,
    `Color palette: ${theme.palette}`,
    `Imagery: ${theme.imagery}. Page-specific visual brief: ${slide.media_brief}`,
    `Material classification: ${slide.content_kind ?? inferContentKind(slide.role)}; use the matching visual representation and do not invent factual content.`,
    `Continuity anchor: ${slide.visual_anchor_id ?? `${theme.id}-anchor`}; continuity group: ${slide.continuity_group ?? `${theme.id}-deck`}.`,
    `Materials/textures: ${theme.materials}`,
    `Theme consistency anchors: ${theme.anchors.join('; ')}`,
  ];
  const out = `${theme.id}-${slide.id}-${slide.role}.png`;
  const prompt = [
    ...shared,
    'Asset type: complete rasterized presentation slide.',
    promptLines('Text (verbatim, 文字必须逐字准确、顺序一致、每条只出现一次)', slide.exact_text),
    'Constraints: render the complete slide as a single finished image; readable from a projector; strong hierarchy; generous whitespace; no editable UI; no watermark（无水印）; no logo.',
    `Avoid: ${[...theme.avoid, '不得添加任何其他文字', '乱码', '伪造数据', 'dense card grid', 'tiny labels'].join('; ')}.`,
  ].join('\n');
  return { id: slide.id, role: slide.role, theme: theme.id, content_kind: slide.content_kind ?? inferContentKind(slide.role), output_mode: PRESENTATION_MODES.IMAGE_FIRST, asset_role: 'complete-slide', text_policy: 'exact-text', out, model, size, quality, use_case: 'productivity-visual', prompt };
}

export function compileDeckPrompts(deck, themes, options = {}) {
  if (deck?.status !== 'approved') throw new Error('Content draft must be approved before prompt compilation.');
  const theme = themes?.[deck.theme?.family];
  if (!theme) throw new Error(`Unknown image theme: ${deck.theme?.family ?? 'missing'}`);
  const mode = normalizeMode(options.mode ?? deck.output_mode);
  if (mode === PRESENTATION_MODES.PURE_HTML) return [];
  return deck.slides.map((slide) => compileSlidePrompt(slide, theme, { ...options, mode, audience: deck.audience }));
}

export function createGenerationManifest(deck, jobs, options = {}) {
  const mode = normalizeMode(options.mode ?? deck.output_mode);
  if (mode === PRESENTATION_MODES.PURE_HTML) {
    return {
      schema_version: 1,
      title: deck.title,
      theme: deck.theme.family,
      provider: options.provider ?? 'html',
      output_mode: PRESENTATION_MODES.PURE_HTML,
      slides: deck.slides.map((source) => ({
        id: source.id,
        role: source.role,
        theme: deck.theme.family,
        prompt: 'HTML-only; no image generation',
        model: 'none',
        size: '16:9',
        quality: 'n/a',
        output_path: null,
        status: 'pass',
        attempts: 0,
        error: null,
        content_kind: source.content_kind ?? inferContentKind(source.role),
        output_mode: PRESENTATION_MODES.PURE_HTML,
        asset_role: 'html-only',
        text_policy: 'exact-text',
      })),
    };
  }
  const outputMode = 'full-slide-image';
  const outputDir = 'slides';
  return {
    schema_version: 1,
    title: deck.title,
    theme: deck.theme.family,
    provider: options.provider ?? 'imagegen',
    output_mode: outputMode,
    slides: jobs.map((job) => ({
      id: job.id,
      role: job.role,
      theme: job.theme,
      prompt: job.prompt,
      model: job.model,
      size: job.size,
      quality: job.quality,
      output_path: `${outputDir}/${job.out}`,
      status: 'prepared',
      attempts: 0,
      error: null,
      content_kind: job.content_kind ?? null,
      output_mode: job.output_mode ?? mode,
      asset_role: job.asset_role ?? 'complete-slide',
      text_policy: job.text_policy ?? 'exact-text',
    })),
  };
}

export function renderOutlinePreview(draft) {
  const narrative = NARRATIVE_KEYS.map((key) => `<li><strong>${escapeHtml(key)}</strong><span>${escapeHtml(draft.narrative?.[key])}</span></li>`).join('');
  const slides = (draft.slides ?? []).map((slide, index) => `<article><div class="number">第 ${index + 1} 页</div><div><small>${escapeHtml(slide.role)}</small><h2>${escapeHtml(slide.claim)}</h2><p>${escapeHtml(slide.purpose)}</p><ul>${slide.exact_text.map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul><p class="meta">素材：${escapeHtml(slide.media_brief)} · 衔接：${escapeHtml(slide.transition)}</p></div></article>`).join('');
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(draft.title)} 内容草稿</title><style>*{box-sizing:border-box}body{margin:0;background:#f2f3ef;color:#172019;font-family:Inter,'Noto Sans SC',system-ui,sans-serif;letter-spacing:0}header,main{max-width:1100px;margin:auto;padding:40px 28px}header{padding-bottom:20px}h1{font-size:42px;margin:0 0 14px}.lead{font-size:24px;line-height:1.5;border-left:5px solid #146c5a;padding-left:20px}.narrative{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;padding:0;list-style:none}.narrative li{background:#fff;border-top:3px solid #146c5a;padding:16px}.narrative strong,.narrative span{display:block}.narrative strong{text-transform:uppercase;font-size:11px;color:#647068;margin-bottom:8px}article{display:grid;grid-template-columns:110px 1fr;gap:24px;background:#fff;border:1px solid #d8ddd7;margin:14px 0;padding:24px}.number{font-weight:700;color:#146c5a}article h2{font-size:27px;margin:4px 0 8px}article p{line-height:1.6}.meta{color:#667068;font-size:13px}@media(max-width:760px){.narrative{grid-template-columns:1fr}article{grid-template-columns:1fr}h1{font-size:32px}}</style></head><body><header><h1>${escapeHtml(draft.title)} · 内容草稿</h1><p class="lead"><strong>中心含义：</strong>${escapeHtml(draft.central_message)}</p><h2>叙事逻辑</h2><ol class="narrative">${narrative}</ol></header><main>${slides}</main></body></html>`;
}

export function renderImageDeck(deck, manifest) {
  const slides = manifest.slides.map((slide, index) => `<section class="slide${index === 0 ? ' active' : ''}" data-slide="${index}"><img src="${escapeHtml(slide.output_path)}" alt="${escapeHtml(deck.slides[index]?.claim ?? slide.role)}"><span>${index + 1} / ${manifest.slides.length}</span></section>`).join('');
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(deck.title)}</title><style>*{box-sizing:border-box}body{margin:0;background:#111;color:#fff;font-family:system-ui,sans-serif;letter-spacing:0}.deck{height:100vh;display:grid;place-items:center}.slide{display:none;position:relative;width:min(100vw,177.78vh);aspect-ratio:16/9}.slide.active{display:block}.slide img{width:100%;height:100%;display:block;object-fit:contain}.slide span{position:absolute;right:16px;bottom:10px;background:#0009;padding:5px 8px;font-size:12px}button{position:fixed;top:50%;width:42px;height:42px;border:0;background:#000a;color:#fff;font-size:24px;cursor:pointer}#prev{left:8px}#next{right:8px}</style></head><body><main class="deck">${slides}</main><button id="prev" title="上一页" aria-label="上一页">‹</button><button id="next" title="下一页" aria-label="下一页">›</button><script>const slides=[...document.querySelectorAll('.slide')];let current=0;function show(next){slides[current].classList.remove('active');current=(next+slides.length)%slides.length;slides[current].classList.add('active')}document.querySelector('#prev').onclick=()=>show(current-1);document.querySelector('#next').onclick=()=>show(current+1);addEventListener('keydown',event=>{if(['ArrowRight','PageDown',' '].includes(event.key))show(current+1);if(['ArrowLeft','PageUp'].includes(event.key))show(current-1)});</script></body></html>`;
}
