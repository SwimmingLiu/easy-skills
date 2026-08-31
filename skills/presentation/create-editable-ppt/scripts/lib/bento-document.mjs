const BLOCK = /(<script\b(?=[^>]*\btype=["']application\/bento\+json["'])(?=[^>]*\bid=["']bento-doc["'])[^>]*>)([\s\S]*?)(<\/script>)/gi;

function matchBlock(html) {
  const matches = [...html.matchAll(BLOCK)];
  if (matches.length !== 1) throw new Error(`Expected one #bento-doc block, found ${matches.length}`);
  return matches[0];
}

export function extractBentoBlock(html) {
  return matchBlock(html)[2];
}

export function parseBentoDocument(html) {
  const doc = JSON.parse(extractBentoBlock(html));
  validateBentoDocument(doc);
  return doc;
}

export function createBentoDocument({ title = 'Untitled presentation', slides = [], theme = {}, size = {} } = {}) {
  return {
    format: 'bento/slides',
    version: 1,
    title,
    size: { width: 1280, height: 720, ...size },
    theme: { background: '#ffffff', color: '#111111', accent: '#2563eb', fontFamily: 'Arial, sans-serif', ...theme },
    slides: slides.map((slide, index) => ({
      id: slide.id || `slide-${String(index + 1).padStart(2, '0')}`,
      background: slide.background || { color: theme.background || '#ffffff' },
      transition: slide.transition || 'none',
      notes: slide.notes || '',
      elements: slide.elements || [],
      ...slide,
    })),
  };
}

export function validateBentoDocument(doc) {
  if (!doc || doc.format !== 'bento/slides') throw new Error('Expected format bento/slides');
  if (doc.version !== 1) throw new Error('Expected Bento document version 1');
  if (!doc.size || !Number.isFinite(doc.size.width) || !Number.isFinite(doc.size.height)) throw new Error('Bento document requires numeric size');
  if (!doc.theme || typeof doc.theme !== 'object') throw new Error('Bento document requires theme');
  if (!Array.isArray(doc.slides)) throw new Error('Bento document requires slides');
  const ids = doc.slides.map(slide => slide.id);
  if (ids.some(id => typeof id !== 'string' || !id)) throw new Error('Every slide requires a stable id');
  if (new Set(ids).size !== ids.length) throw new Error('Slide ids must be unique');
  return doc;
}

export function spliceBentoDocument(shell, doc, { previous } = {}) {
  validateBentoDocument(doc);
  if (previous?.docId && doc.docId !== previous.docId) throw new Error('Existing docId must be preserved');
  const match = matchBlock(shell);
  const body = JSON.stringify(doc).replaceAll('<', '\\u003c');
  const start = match.index;
  return shell.slice(0, start) + match[1] + body + match[3] + shell.slice(start + match[0].length);
}
