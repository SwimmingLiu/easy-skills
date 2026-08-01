export const SLIDE_ROLES = Object.freeze([
  'cover',
  'section',
  'statement',
  'image-hero',
  'two-column',
  'comparison',
  'process',
  'data',
  'quote',
  'closing',
]);

export const PROJECT_STATUSES = Object.freeze(['drafting', 'outline-review', 'sample-review', 'generating', 'editing', 'review', 'exported']);

const STATUS_TRANSITIONS = Object.freeze({
  drafting: ['outline-review'],
  'outline-review': ['drafting', 'sample-review'],
  'sample-review': ['outline-review', 'generating'],
  generating: ['sample-review', 'editing'],
  editing: ['generating', 'review'],
  review: ['editing', 'exported'],
  exported: ['review'],
});

export class ProjectConflictError extends Error {
  constructor(message, details = {}) {
    super(message);
    this.name = 'ProjectConflictError';
    this.code = 'project.revision.conflict';
    this.details = details;
  }
}

function finding(code, message, options = {}) {
  return {
    code,
    message,
    severity: options.severity ?? 'blocking',
    ...(options.slide_id ? { slide_id: options.slide_id } : {}),
    ...(options.path ? { path: options.path } : {}),
  };
}

function collectVisibleText(value) {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(collectVisibleText).join('');
  if (value && typeof value === 'object') {
    return Object.values(value).map(collectVisibleText).join('');
  }
  return '';
}

function visibleLength(value) {
  return collectVisibleText(value).replace(/\s+/gu, '').length;
}

function visibleSlideCopy(slide) {
  const props = slide?.props ?? {};
  const roleCopy = {
    cover: [props.subtitle],
    section: [props.summary],
    statement: [props.points],
    'image-hero': [props.caption],
    'two-column': [props.left_title, props.left, props.right_title, props.right],
    comparison: [props.left_title, props.left, props.right_title, props.right],
    process: [props.steps],
    data: [props.metrics, props.points],
    quote: [props.quote, props.attribution],
    closing: [props.action],
  };
  return visibleLength([slide?.claim, roleCopy[slide?.role] ?? []]);
}

export function validateDeck(deck, { assets = { assets: [] } } = {}) {
  const findings = [];
  if (!deck || typeof deck !== 'object') {
    return { valid: false, findings: [finding('deck.required', 'Deck specification is required.')] };
  }
  if (typeof deck.title !== 'string' || deck.title.trim() === '') {
    findings.push(finding('deck.title.required', 'Deck title is required.', { path: 'title' }));
  }
  if (!Array.isArray(deck.slides) || deck.slides.length === 0) {
    findings.push(finding('deck.slides.required', 'At least one slide is required.', { path: 'slides' }));
  }

  const ids = new Set();
  const assetIds = new Set((assets?.assets ?? []).map((asset) => asset.id));
  for (const [index, slide] of (deck.slides ?? []).entries()) {
    const slideId = slide?.id || `slides[${index}]`;
    if (!slide?.id) {
      findings.push(finding('slide.id.required', 'Slide id is required.', { path: `slides[${index}].id` }));
    } else if (ids.has(slide.id)) {
      findings.push(finding('slide.id.duplicate', `Duplicate slide id: ${slide.id}`, { slide_id: slide.id }));
    } else {
      ids.add(slide.id);
    }

    if (!SLIDE_ROLES.includes(slide?.role)) {
      findings.push(finding('slide.role.unsupported', `Unsupported slide role: ${slide?.role ?? ''}`, { slide_id: slideId }));
    }
    if (typeof slide?.claim !== 'string' || slide.claim.trim() === '') {
      findings.push(finding('slide.claim.required', 'Every slide needs one claim.', { slide_id: slideId }));
    }
    if (deck.density === 'speaker-led') {
      const copyLength = visibleSlideCopy(slide);
      if (copyLength > 60) {
        findings.push(finding(
          'slide.copy.too_long',
          `Speaker-led slide has ${copyLength} visible characters; target is 60 or fewer.`,
          { severity: 'warning', slide_id: slideId },
        ));
      }
    }
    for (const mediaId of slide?.media ?? []) {
      if (!assetIds.has(mediaId)) {
        findings.push(finding('slide.media.missing', `Missing asset: ${mediaId}`, { slide_id: slideId }));
      }
    }
  }

  return {
    valid: findings.every((item) => item.severity !== 'blocking'),
    findings,
  };
}

function clone(value) {
  return structuredClone(value);
}

function makeDuplicate(source, duplicate) {
  return {
    ...clone(source),
    id: duplicate.id,
    duplicated_from: source.id,
  };
}

export function mergeDeckState(deck, state) {
  if (!state) return clone(deck);
  if (state.base_revision !== deck.revision) {
    throw new ProjectConflictError(
      `Editor state targets deck revision ${state.base_revision}; current revision is ${deck.revision}.`,
      { expected: deck.revision, actual: state.base_revision },
    );
  }

  const slides = new Map((deck.slides ?? []).map((slide) => [slide.id, clone(slide)]));
  for (const duplicate of state.duplicated_slides ?? []) {
    const source = slides.get(duplicate.source_id);
    if (source && duplicate.id && !slides.has(duplicate.id)) {
      slides.set(duplicate.id, makeDuplicate(source, duplicate));
    }
  }

  const deleted = new Set(state.deleted_slides ?? []);
  const skipped = new Set(state.skipped_slides ?? []);
  const order = [
    ...(state.slide_order ?? []),
    ...slides.keys(),
  ].filter((id, index, all) => all.indexOf(id) === index);

  const mergedSlides = [];
  for (const id of order) {
    if (deleted.has(id) || !slides.has(id)) continue;
    const slide = slides.get(id);
    const text = state.text_overrides?.[id] ?? {};
    const props = state.prop_overrides?.[id] ?? {};
    mergedSlides.push({
      ...slide,
      ...text,
      props: { ...(slide.props ?? {}), ...props },
      skipped: skipped.has(id),
      review_status: state.review_status?.[id] ?? 'pending',
    });
  }

  return {
    ...clone(deck),
    theme: state.theme_override ?? clone(deck.theme),
    editor_revision: state.revision,
    slides: mergedSlides,
  };
}

export function defaultEditorState(deck) {
  return {
    schema_version: 1,
    base_revision: deck.revision,
    revision: 0,
    slide_order: deck.slides.map((slide) => slide.id),
    deleted_slides: [],
    skipped_slides: [],
    duplicated_slides: [],
    text_overrides: {},
    prop_overrides: {},
    review_status: Object.fromEntries(deck.slides.map((slide) => [slide.id, 'pending'])),
    theme_override: null,
    project_status: 'drafting',
  };
}

export function transitionProjectState(state, nextStatus) {
  const current = state.project_status ?? 'drafting';
  if (!PROJECT_STATUSES.includes(nextStatus) || !STATUS_TRANSITIONS[current]?.includes(nextStatus)) {
    throw new Error(`Invalid project status transition: ${current} -> ${nextStatus}`);
  }
  return { ...structuredClone(state), project_status: nextStatus };
}

export function createProjectSpec({ title = 'Untitled presentation', pages = 6, language = 'zh-CN' } = {}) {
  const count = Math.max(3, Math.min(60, Number(pages) || 6));
  const slides = Array.from({ length: count }, (_, index) => {
    const first = index === 0;
    const last = index === count - 1;
    return {
      id: `s${String(index + 1).padStart(2, '0')}`,
      role: first ? 'cover' : last ? 'closing' : 'statement',
      claim: first ? title : last ? '明确下一步' : `待确认：第 ${index + 1} 页核心主张`,
      layout: first || last ? 'center' : 'focus',
      props: first ? { subtitle: '待确认：一句话说明价值' } : last ? { action: '待确认：希望听众采取的行动' } : { points: [] },
      evidence: [], media: [], speaker_notes: '',
    };
  });
  return {
    schema_version: 1, revision: 1, title,
    audience: '待确认', purpose: '待确认', language, canvas: '16:9', density: 'speaker-led',
    theme: { family: 'business-minimal', variant: 'ink' }, slides,
  };
}
