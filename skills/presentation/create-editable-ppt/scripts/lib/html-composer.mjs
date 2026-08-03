import { createBentoDocument } from './bento-document.mjs';

const specs = {
  'clean-professional': ['#F7F8FA', '#101828', '#1967D2', '#E7EDF7', 'Arial, sans-serif'],
  'strict-swiss-html': ['#FFFFFF', '#0B0B0B', '#F04438', '#E9E9E5', 'Arial, sans-serif'],
  'editorial-paper': ['#F4EFE6', '#1E1A17', '#C84B31', '#E4D6C6', 'Georgia, serif'],
  'institutional-signal': ['#F7F8FA', '#092A4A', '#D6262E', '#DDE8F1', 'Arial Narrow, Arial, sans-serif'],
  'neo-brutalist-grid': ['#FFF7E8', '#111111', '#FF3D00', '#FFD83D', 'Arial, sans-serif'],
  'terminal-mono': ['#0B0F0D', '#D7FFE6', '#5CFF8A', '#17211C', 'Menlo, Consolas, monospace'],
  'blueprint-engineering': ['#0B3A68', '#F5FBFF', '#57D5FF', '#174F82', 'Menlo, Consolas, monospace'],
  'dark-aurora-html': ['#090B18', '#F5F4FF', '#8C6CFF', '#171A33', 'Arial, sans-serif'],
  'glass-candy': ['#F5F2FF', '#182033', '#7B61FF', '#E5DDFC', 'Arial, sans-serif'],
  'data-spectrum': ['#F6F8FA', '#111827', '#2563EB', '#DDE7F2', 'Arial, sans-serif'],
  'research-white': ['#FCFCFA', '#1F2937', '#174EA6', '#E9EDF3', 'Georgia, serif'],
  'magazine-deep-blue': ['#082A44', '#F7F0DE', '#42B883', '#123B57', 'Georgia, serif'],
  'finance-index': ['#071C33', '#F7F5E8', '#D6A84B', '#13304B', 'Arial, sans-serif'],
  'growth-ember': ['#FFF8F3', '#18120F', '#FF5A36', '#FFE0D2', 'Arial, sans-serif'],
  'retro-interface': ['#D8D8D0', '#111111', '#008C8C', '#B8B8B0', 'Arial, sans-serif'],
  'pixel-arcade': ['#08112B', '#F5F7FF', '#00E5FF', '#18234A', 'Menlo, Consolas, monospace'],
  'riso-zine-html': ['#F6E8CF', '#16120F', '#EA3D2F', '#2D60D4', 'Arial Narrow, Arial, sans-serif'],
  'organic-craft': ['#F2EFE3', '#173B2C', '#6C8E56', '#D9D3B9', 'Georgia, serif'],
  'playful-pastel': ['#FFF7FB', '#29223D', '#FF5A8F', '#FFE06D', 'Arial, sans-serif'],
  'culture-poster': ['#F2E6C9', '#10264B', '#E3B400', '#D85D46', 'Georgia, serif'],
  'code-editorial': ['#F7F2E8', '#1D252C', '#E0523E', '#DCE4E8', 'Menlo, Consolas, monospace'],
  'neon-entertainment': ['#08080E', '#FFFFFF', '#00F5D4', '#1A1229', 'Arial, sans-serif'],
};

const escapeHtml = value => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#39;');

const base = (id, type, x, y, w, h, extra = {}) => ({ id, type, x, y, w, h, rotation: 0, opacity: 1, ...extra });
const shape = (id, x, y, w, h, fill, radius = 0, extra = {}) => ({
  ...base(id, 'shape', x, y, w, h, extra), shape: 'rect', fill, stroke: extra.stroke ?? fill, strokeWidth: extra.strokeWidth ?? 0, radius,
});
const text = (id, value, x, y, w, h, size, color, weight = 700, align = 'left', family = 'Arial, sans-serif', extra = {}) => ({
  ...base(id, 'text', x, y, w, h, extra), html: escapeHtml(value), fontSize: size, fontFamily: family, fontWeight: weight, color, align, valign: 'top', lineHeight: extra.lineHeight ?? 1.08,
});

function contentItems(source) {
  return source.exact_text.filter(item => item !== source.claim).slice(0, 4);
}

function blocks(elements, items, { x = 72, y = 458, w = 1136, h = 132, gap = 14, fill, firstFill, ink, firstInk, family, radius = 0, rotate = false } = {}) {
  const width = (w - gap * Math.max(0, items.length - 1)) / Math.max(1, items.length);
  items.forEach((item, index) => {
    const left = x + index * (width + gap);
    elements.push(shape(`block-${index}`, left, y, width, h, index === 0 ? firstFill : fill, radius, rotate ? { rotation: index % 2 ? 1.2 : -1.2 } : {}));
    elements.push(text(`item-${index}`, item, left + 16, y + 24, width - 32, h - 36, items.length > 3 ? 20 : 23, index === 0 ? firstInk : ink, 700, 'left', family));
  });
}

function composeSlide(source, recipe, label, title) {
  const [bg, ink, accent, soft, family] = specs[recipe.id] || specs['clean-professional'];
  const items = contentItems(source);
  const elements = [];
  const claimSize = source.role === 'cover' || source.role === 'closing' ? 72 : 56;

  if (recipe.id === 'clean-professional') {
    elements.push(shape('rail', 72, 72, 7, 576, accent));
    elements.push(text('deck-label', title.toUpperCase(), 104, 76, 720, 28, 15, accent));
    elements.push(text('page-number', label, 1020, 76, 180, 28, 15, ink, 500, 'right'));
    elements.push(text(`claim-${source.id}`, source.claim, 104, 152, 1020, 190, claimSize, ink, 800));
    blocks(elements, items, { x: 104, y: 438, w: 1010, fill: soft, firstFill: accent, ink, firstInk: bg, family, radius: 4 });
  } else if (recipe.id === 'strict-swiss-html') {
    elements.push(shape('top-rule', 60, 58, 1160, 4, ink));
    elements.push(text('deck-label', recipe.name.toUpperCase(), 60, 76, 560, 30, 15, ink));
    elements.push(shape('index-box', 1090, 76, 130, 44, accent));
    elements.push(text('page-number', label, 1100, 87, 110, 24, 14, bg, 800, 'center'));
    elements.push(text(`claim-${source.id}`, source.claim, 60, 158, 1120, 190, claimSize + 4, ink, 800));
    blocks(elements, items, { x: 60, y: 444, w: 1160, fill: soft, firstFill: ink, ink, firstInk: bg, family });
  } else if (recipe.id === 'editorial-paper') {
    elements.push(shape('top-rule', 72, 66, 1136, 2, accent));
    elements.push(text('deck-label', recipe.name.toUpperCase(), 72, 82, 540, 28, 15, accent, 700, 'left', 'Arial, sans-serif'));
    elements.push(text('page-number', label, 1020, 82, 188, 28, 15, ink, 500, 'right', 'Arial, sans-serif'));
    elements.push(text(`claim-${source.id}`, source.claim, 72, 150, 820, 230, claimSize, ink, 700, 'left', family));
    elements.push(shape('editorial-mark', 980, 156, 150, 150, accent, 75));
    blocks(elements, items, { x: 72, y: 466, w: 1136, fill: 'transparent', firstFill: accent, ink, firstInk: bg, family });
  } else if (recipe.id === 'institutional-signal') {
    elements.push(shape('masthead', 0, 0, 1280, 318, ink));
    elements.push(shape('signal', 68, 64, 230, 36, accent));
    elements.push(text('deck-label', 'BRIEFING / SIGNAL', 80, 72, 210, 24, 14, bg, 800));
    elements.push(text('page-number', label, 1030, 68, 180, 30, 15, bg, 600, 'right'));
    elements.push(text(`claim-${source.id}`, source.claim, 68, 142, 1100, 142, claimSize - 4, bg, 800));
    blocks(elements, items, { x: 68, y: 402, w: 1144, fill: soft, firstFill: accent, ink, firstInk: bg, family, radius: 2 });
  } else if (recipe.id === 'neo-brutalist-grid') {
    elements.push(shape('frame', 38, 38, 1204, 644, bg, 0, { stroke: ink, strokeWidth: 6 }));
    elements.push(shape('tag', 68, 68, 258, 48, accent));
    elements.push(text('deck-label', recipe.name.toUpperCase(), 82, 79, 230, 28, 15, bg, 900));
    elements.push(text('page-number', label, 1020, 68, 170, 34, 17, ink, 900, 'right'));
    elements.push(text(`claim-${source.id}`, source.claim, 68, 146, 1120, 206, claimSize + 6, ink, 900));
    elements.push(shape('offset-square', 1010, 250, 126, 126, soft, 0, { rotation: 8, stroke: ink, strokeWidth: 4 }));
    blocks(elements, items, { x: 68, y: 444, w: 1144, fill: soft, firstFill: accent, ink, firstInk: bg, family, rotate: true });
  } else if (recipe.id === 'terminal-mono') {
    elements.push(shape('window', 54, 48, 1172, 624, soft, 8, { stroke: accent, strokeWidth: 1 }));
    elements.push(shape('bar', 54, 48, 1172, 34, accent, 8));
    for (let i = 0; i < 3; i += 1) elements.push(shape(`dot-${i}`, 74 + i * 24, 58, 12, 12, i === 0 ? '#FF5F57' : i === 1 ? '#FEBC2E' : '#28C840', 6));
    elements.push(text('deck-label', `> ${recipe.id}`, 78, 104, 600, 28, 16, accent, 700, 'left', family));
    elements.push(text('page-number', label, 1012, 104, 170, 28, 16, ink, 500, 'right', family));
    elements.push(text(`claim-${source.id}`, source.claim, 78, 176, 1080, 190, claimSize - 10, ink, 700, 'left', family));
    blocks(elements, items, { x: 78, y: 438, w: 1080, fill: bg, firstFill: accent, ink, firstInk: bg, family, radius: 4 });
  } else if (recipe.id === 'blueprint-engineering') {
    for (let x = 70; x <= 1210; x += 95) elements.push(shape(`grid-v-${x}`, x, 44, 1, 632, soft));
    for (let y = 58; y <= 660; y += 86) elements.push(shape(`grid-h-${y}`, 52, y, 1176, 1, soft));
    elements.push(shape('measure', 72, 76, 310, 3, accent));
    elements.push(text('deck-label', 'SYSTEM / BLUEPRINT', 72, 92, 500, 26, 14, accent, 700, 'left', family));
    elements.push(text('page-number', label, 1020, 92, 188, 26, 14, ink, 500, 'right', family));
    elements.push(text(`claim-${source.id}`, source.claim, 72, 170, 920, 180, claimSize - 4, ink, 700, 'left', family));
    elements.push(shape('node', 1038, 164, 122, 122, 'transparent', 61, { stroke: accent, strokeWidth: 3 }));
    blocks(elements, items, { x: 72, y: 454, w: 1136, fill: soft, firstFill: accent, ink, firstInk: bg, family, radius: 2 });
  } else if (recipe.id === 'dark-aurora-html') {
    elements.push(shape('halo-a', 880, 36, 310, 310, '#5639C8', 155, { opacity: 0.7 }));
    elements.push(shape('halo-b', 990, 190, 176, 176, '#27C2D1', 88, { opacity: 0.7 }));
    elements.push(shape('panel', 52, 52, 1176, 616, soft, 18, { opacity: 0.88, stroke: '#32385C', strokeWidth: 1 }));
    elements.push(text('deck-label', recipe.name, 84, 82, 620, 30, 16, accent));
    elements.push(text('page-number', label, 1010, 82, 170, 28, 15, ink, 600, 'right'));
    elements.push(text(`claim-${source.id}`, source.claim, 84, 168, 850, 200, claimSize - 2, ink, 800));
    blocks(elements, items, { x: 84, y: 458, w: 1096, fill: '#101426', firstFill: accent, ink, firstInk: bg, family, radius: 14 });
  } else if (recipe.id === 'glass-candy') {
    elements.push(shape('candy-a', 930, 50, 210, 210, '#FF7EB6', 105, { opacity: 0.72 }));
    elements.push(shape('candy-b', 1020, 210, 126, 126, '#54D7D0', 63, { opacity: 0.72 }));
    elements.push(shape('glass', 50, 50, 1180, 620, '#FFFFFF', 24, { opacity: 0.76, stroke: '#FFFFFF', strokeWidth: 2 }));
    elements.push(shape('pill', 82, 82, 268, 42, soft, 21));
    elements.push(text('deck-label', recipe.name, 100, 92, 230, 24, 15, accent));
    elements.push(text('page-number', label, 1010, 86, 170, 28, 15, ink, 600, 'right'));
    elements.push(text(`claim-${source.id}`, source.claim, 82, 174, 840, 190, claimSize, ink, 800));
    blocks(elements, items, { x: 82, y: 454, w: 1100, fill: soft, firstFill: accent, ink, firstInk: bg, family, radius: 22, rotate: true });
  } else if (recipe.id === 'data-spectrum') {
    elements.push(text('deck-label', 'DATA / SPECTRUM', 68, 66, 520, 28, 15, accent));
    elements.push(text('page-number', label, 1020, 66, 190, 28, 15, ink, 600, 'right'));
    elements.push(text(`claim-${source.id}`, source.claim, 68, 124, 810, 190, claimSize - 4, ink, 800));
    const barColors = ['#2563EB', '#19A974', '#F59E0B', '#E54B4B'];
    [190, 250, 150, 300].forEach((width, index) => elements.push(shape(`bar-${index}`, 900, 156 + index * 42, width, 22, barColors[index], 3)));
    blocks(elements, items, { x: 68, y: 442, w: 1144, fill: soft, firstFill: ink, ink, firstInk: bg, family, radius: 4 });
  } else if (recipe.id === 'research-white') {
    elements.push(shape('citation-rule', 70, 62, 1140, 2, accent));
    elements.push(text('deck-label', 'RESEARCH NOTE / 2026', 70, 78, 560, 26, 14, accent, 700, 'left', 'Arial, sans-serif'));
    elements.push(text('page-number', label, 1020, 78, 190, 26, 14, ink, 500, 'right', 'Arial, sans-serif'));
    elements.push(text(`claim-${source.id}`, source.claim, 70, 156, 1040, 178, claimSize - 2, ink, 700, 'left', family));
    elements.push(text('evidence-label', 'EVIDENCE / CLAIM', 70, 390, 260, 26, 13, accent, 700, 'left', 'Arial, sans-serif'));
    blocks(elements, items, { x: 70, y: 430, w: 1140, fill: soft, firstFill: accent, ink, firstInk: bg, family: 'Arial, sans-serif', radius: 2 });
  } else if (recipe.id === 'magazine-deep-blue') {
    elements.push(shape('emerald-chip', 1032, 64, 140, 140, accent));
    elements.push(text('deck-label', 'FIELD NOTES / VOL. 01', 68, 70, 620, 28, 14, accent, 700, 'left', 'Arial, sans-serif'));
    elements.push(text('page-number', label, 1010, 220, 160, 28, 14, ink, 500, 'right', 'Arial, sans-serif'));
    elements.push(text(`claim-${source.id}`, source.claim, 68, 152, 875, 240, claimSize + 2, ink, 700, 'left', family));
    blocks(elements, items, { x: 68, y: 468, w: 1104, fill: soft, firstFill: accent, ink, firstInk: bg, family, radius: 0 });
  } else if (recipe.id === 'finance-index') {
    elements.push(shape('gold-rule', 64, 64, 1152, 3, accent));
    elements.push(text('deck-label', 'MARKET / INDEX', 64, 82, 520, 28, 14, accent));
    elements.push(text('page-number', label, 1020, 82, 196, 28, 14, ink, 600, 'right'));
    elements.push(text(`claim-${source.id}`, source.claim, 64, 160, 1030, 190, claimSize - 2, ink, 800));
    elements.push(shape('index-rail', 64, 384, 1152, 2, soft));
    blocks(elements, items, { x: 64, y: 430, w: 1152, fill: soft, firstFill: accent, ink, firstInk: bg, family, radius: 2 });
  } else if (recipe.id === 'growth-ember') {
    elements.push(shape('status', 70, 66, 210, 40, ink, 20));
    elements.push(text('deck-label', 'GROWTH / ACTIVE', 88, 76, 180, 22, 13, bg, 800));
    elements.push(text('page-number', label, 1020, 72, 190, 28, 15, ink, 700, 'right'));
    elements.push(text(`claim-${source.id}`, source.claim, 70, 152, 1040, 190, claimSize + 4, ink, 900));
    elements.push(shape('sweep', 70, 356, 1040, 20, accent, 10, { rotation: -2 }));
    blocks(elements, items, { x: 70, y: 446, w: 1140, fill: soft, firstFill: accent, ink, firstInk: bg, family, radius: 8 });
  } else if (recipe.id === 'retro-interface') {
    elements.push(shape('desktop', 46, 42, 1188, 636, bg, 4, { stroke: ink, strokeWidth: 3 }));
    elements.push(shape('titlebar', 46, 42, 1188, 38, accent, 4));
    elements.push(text('deck-label', `${recipe.name}.deck`, 64, 51, 520, 23, 14, bg, 700));
    elements.push(text('page-number', label, 1020, 51, 190, 23, 14, bg, 700, 'right'));
    elements.push(shape('window-a', 70, 112, 790, 270, '#ECECE5', 0, { stroke: ink, strokeWidth: 2 }));
    elements.push(text(`claim-${source.id}`, source.claim, 94, 146, 730, 190, claimSize - 8, ink, 800));
    elements.push(shape('window-b', 884, 112, 306, 270, soft, 0, { stroke: ink, strokeWidth: 2 }));
    elements.push(text('window-meta', 'READY\nOPEN\nSAVE', 910, 148, 250, 150, 18, ink, 700, 'left', 'Menlo, monospace'));
    blocks(elements, items, { x: 70, y: 426, w: 1120, fill: '#ECECE5', firstFill: accent, ink, firstInk: bg, family, radius: 0 });
  } else if (recipe.id === 'pixel-arcade') {
    for (let x = 56; x < 1224; x += 32) elements.push(shape(`pixel-top-${x}`, x, 46, 16, 16, x % 64 ? accent : '#FF4FD8'));
    elements.push(text('deck-label', 'PLAYER 01 / KNOWLEDGE RUN', 62, 84, 700, 28, 15, accent, 700, 'left', family));
    elements.push(text('page-number', label, 1018, 84, 190, 28, 15, ink, 700, 'right', family));
    elements.push(text(`claim-${source.id}`, source.claim, 62, 170, 1050, 190, claimSize - 8, ink, 800, 'left', family));
    elements.push(shape('cursor', 1090, 196, 58, 58, '#FF4FD8'));
    blocks(elements, items, { x: 62, y: 446, w: 1146, fill: soft, firstFill: accent, ink, firstInk: bg, family, radius: 0 });
  } else if (recipe.id === 'riso-zine-html') {
    elements.push(shape('spot-blue', 886, 68, 242, 242, soft, 121, { opacity: 0.9 }));
    elements.push(shape('spot-red', 1016, 184, 148, 148, accent, 74, { opacity: 0.85 }));
    elements.push(text('deck-label', 'RISO / FIELD EDITION', 68, 72, 560, 26, 15, ink, 800));
    elements.push(text('page-number', label, 1010, 72, 180, 26, 15, ink, 700, 'right'));
    elements.push(text(`claim-${source.id}`, source.claim, 68, 158, 840, 210, claimSize, ink, 900));
    blocks(elements, items, { x: 68, y: 450, w: 1124, fill: soft, firstFill: accent, ink, firstInk: bg, family, rotate: true });
  } else if (recipe.id === 'organic-craft') {
    elements.push(shape('leaf-a', 964, 70, 180, 250, accent, 90, { rotation: 26, opacity: 0.8 }));
    elements.push(shape('leaf-b', 1044, 184, 100, 180, soft, 50, { rotation: -24 }));
    elements.push(text('deck-label', 'FIELD / PRACTICE', 72, 76, 520, 26, 14, accent, 700, 'left', 'Arial, sans-serif'));
    elements.push(text('page-number', label, 1018, 76, 180, 26, 14, ink, 500, 'right', 'Arial, sans-serif'));
    elements.push(text(`claim-${source.id}`, source.claim, 72, 164, 840, 200, claimSize, ink, 700, 'left', family));
    blocks(elements, items, { x: 72, y: 454, w: 1126, fill: soft, firstFill: accent, ink, firstInk: bg, family, radius: 26 });
  } else if (recipe.id === 'playful-pastel') {
    elements.push(shape('sun', 1000, 66, 146, 146, soft, 73, { rotation: 8 }));
    elements.push(shape('spark', 1110, 190, 68, 68, accent, 18, { rotation: 18 }));
    elements.push(shape('label-pill', 72, 72, 248, 44, '#B7E4FF', 22));
    elements.push(text('deck-label', recipe.name, 92, 83, 210, 24, 15, ink));
    elements.push(text('page-number', label, 1010, 82, 170, 26, 15, ink, 700, 'right'));
    elements.push(text(`claim-${source.id}`, source.claim, 72, 166, 860, 200, claimSize, ink, 800));
    blocks(elements, items, { x: 72, y: 446, w: 1126, fill: soft, firstFill: accent, ink, firstInk: bg, family, radius: 24, rotate: true });
  } else if (recipe.id === 'culture-poster') {
    elements.push(shape('poster-band', 0, 0, 1280, 86, accent));
    elements.push(text('deck-label', 'PUBLIC PROGRAM / 01', 64, 28, 650, 28, 16, bg, 800));
    elements.push(text('page-number', label, 1030, 28, 180, 28, 16, bg, 800, 'right'));
    elements.push(text(`claim-${source.id}`, source.claim, 64, 144, 880, 230, claimSize + 4, ink, 700));
    elements.push(shape('civic-disc', 1014, 138, 154, 154, soft, 77));
    blocks(elements, items, { x: 64, y: 450, w: 1146, fill: 'transparent', firstFill: ink, ink, firstInk: bg, family, radius: 0 });
  } else if (recipe.id === 'code-editorial') {
    elements.push(shape('code-rail', 54, 48, 420, 624, ink));
    elements.push(text('deck-label', '01 / CONTEXT.ts', 82, 78, 340, 26, 14, accent, 700, 'left', family));
    elements.push(text('code-lines', 'const context = collect();\nconst links = connect(context);\nexport default decide(links);', 82, 140, 340, 190, 17, bg, 500, 'left', family, { lineHeight: 1.5 }));
    elements.push(text('page-number', label, 1010, 72, 180, 28, 14, ink, 600, 'right', family));
    elements.push(text(`claim-${source.id}`, source.claim, 530, 154, 650, 210, claimSize - 6, ink, 800, 'left', 'Arial, sans-serif'));
    blocks(elements, items, { x: 530, y: 446, w: 650, fill: soft, firstFill: accent, ink, firstInk: bg, family, radius: 2 });
  } else {
    elements.push(shape('stage', 52, 52, 1176, 616, soft, 14));
    elements.push(shape('light-a', 908, 60, 230, 230, accent, 115, { opacity: 0.78 }));
    elements.push(shape('light-b', 1022, 218, 126, 126, '#FF3CAC', 63, { opacity: 0.82 }));
    elements.push(text('deck-label', 'LIVE / SIGNAL', 82, 82, 520, 28, 15, accent, 800));
    elements.push(text('page-number', label, 1010, 82, 170, 28, 15, ink, 700, 'right'));
    elements.push(text(`claim-${source.id}`, source.claim, 82, 170, 820, 198, claimSize, ink, 900));
    blocks(elements, items, { x: 82, y: 454, w: 1096, fill: bg, firstFill: accent, ink, firstInk: bg, family, radius: 10 });
  }

  elements.push(text(`theme-${source.id}`, recipe.name, 72, 632, 540, 22, 13, accent, 600, 'left', family));
  return { id: source.id, background: bg, transition: 'none', notes: `${source.purpose}\n${source.claim}`, elements };
}

export function composeHtmlDeck(outline, recipe, { title = outline.title } = {}) {
  if (outline.mode && outline.mode !== 'html') throw new Error('html mode required');
  const spec = specs[recipe.id] || specs['clean-professional'];
  const slides = outline.slides.map((source, index) => composeSlide(source, recipe, `${String(index + 1).padStart(2, '0')} / ${outline.slides.length}`, title));
  return createBentoDocument({ title, theme: { background: spec[0], color: spec[1], accent: spec[2], fontFamily: spec[4] }, slides });
}

export function composeHtmlThemeShowcase(outline, recipes) {
  const slides = recipes.map((recipe, index) => {
    const source = outline.slides[index % outline.slides.length];
    const slide = composeSlide({ ...source, id: `html-${recipe.id}` }, recipe, `${String(index + 1).padStart(2, '0')} / ${recipes.length}`, outline.title);
    slide.notes = `主题：${recipe.name}\n来源：${recipe.provenance.join(', ')}\n${source.claim}`;
    return slide;
  });
  return createBentoDocument({ title: `${outline.title} · HTML 主题样例`, slides });
}
