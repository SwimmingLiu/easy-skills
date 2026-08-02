import { createBentoDocument } from './bento-document.mjs';

const palettes = {
  light: ['#F7F7F2','#121212','#1565C0','#DDE7F0'],
  dark: ['#0D1117','#F4F7FA','#55D6BE','#1B2635'],
  warm: ['#F4EFE6','#20211F','#D8503F','#E1D2BC'],
  vivid: ['#FFFDF7','#101010','#FF4D00','#FFD83D'],
};

function paletteFor(recipe) {
  if (/dark|terminal|neon|pixel/.test(recipe.id)) return palettes.dark;
  if (/editorial|organic|culture|riso/.test(recipe.id)) return palettes.warm;
  if (/brutal|playful|glass|growth/.test(recipe.id)) return palettes.vivid;
  return palettes.light;
}

const base = (id, type, x, y, w, h) => ({ id, type, x, y, w, h, rotation: 0, opacity: 1 });
const shape = (id, x, y, w, h, fill, radius = 0) => ({ ...base(id, 'shape', x, y, w, h), shape: 'rect', fill, stroke: fill, strokeWidth: 0, radius });
const text = (id, html, x, y, w, h, size, color, weight = 700, align = 'left', family = 'Arial, sans-serif') => ({ ...base(id, 'text', x, y, w, h), html, fontSize: size, fontFamily: family, fontWeight: weight, color, align, valign: 'top', lineHeight: 1.08 });

function familyFor(id) {
  if (/editorial|magazine|culture|organic/.test(id)) return 'editorial';
  if (/swiss|blueprint|research|data|finance|institutional/.test(id)) return 'grid';
  if (/terminal|code|pixel|retro/.test(id)) return 'terminal';
  if (/brutal|riso|growth/.test(id)) return 'poster';
  if (/glass|playful|neon|aurora/.test(id)) return 'chromatic';
  return 'professional';
}

export function composeHtmlDeck(outline, recipe, { title = outline.title } = {}) {
  if (outline.mode && outline.mode !== 'html') throw new Error('html mode required');
  const [bg, ink, accent, soft] = paletteFor(recipe);
  const family = familyFor(recipe.id);
  const slides = outline.slides.map((source, index) => {
    const label = `${String(index + 1).padStart(2, '0')} / ${outline.slides.length}`;
    const elements = [];
    let itemY = 430;
    let itemStart = 104;
    let itemArea = 980;
    let itemRadius = 0;
    let itemFill = soft;
    let familyFont = 'Arial, sans-serif';
    if (family === 'editorial') {
      familyFont = 'Georgia, serif';
      elements.push(shape('top-rule', 72, 66, 1136, 2, accent));
      elements.push(text('deck-label', recipe.name.toUpperCase(), 72, 82, 540, 28, 15, accent, 700, 'left', 'Arial, sans-serif'));
      elements.push(text('page-number', label, 1020, 82, 188, 28, 15, ink, 500, 'right', 'Arial, sans-serif'));
      elements.push(text(`claim-${source.id}`, source.claim, 72, 150, 820, 230, source.role === 'cover' ? 78 : 60, ink, 700, 'left', familyFont));
      elements.push(shape('editorial-mark', 980, 156, 150, 150, accent, 75));
      itemStart = 72; itemArea = 1136; itemY = 466; itemFill = 'transparent';
    } else if (family === 'terminal') {
      familyFont = 'Menlo, Consolas, monospace';
      elements.push(shape('terminal-window', 54, 48, 1172, 624, soft, 8));
      elements.push(shape('terminal-bar', 54, 48, 1172, 34, accent, 8));
      elements.push(text('deck-label', `> ${recipe.id}`, 78, 104, 600, 28, 16, accent, 700, 'left', familyFont));
      elements.push(text('page-number', label, 1012, 104, 170, 28, 16, ink, 500, 'right', familyFont));
      elements.push(text(`claim-${source.id}`, source.claim, 78, 176, 1080, 190, 54, ink, 700, 'left', familyFont));
      itemStart = 78; itemArea = 1080; itemY = 438; itemRadius = 4; itemFill = bg;
    } else if (family === 'poster') {
      elements.push(shape('poster-frame', 42, 42, 1196, 636, bg));
      elements.push({ ...base('poster-border', 'shape', 42, 42, 1196, 636), shape: 'rect', fill: 'transparent', stroke: ink, strokeWidth: 5, radius: 0 });
      elements.push(shape('poster-tag', 72, 72, 230, 44, accent));
      elements.push(text('deck-label', recipe.name.toUpperCase(), 84, 82, 210, 26, 15, bg, 800));
      elements.push(text('page-number', label, 1010, 72, 190, 36, 18, ink, 800, 'right'));
      elements.push(text(`claim-${source.id}`, source.claim, 72, 152, 1110, 210, source.role === 'cover' ? 82 : 64, ink, 900));
      itemStart = 72; itemArea = 1110; itemY = 444; itemFill = accent;
    } else if (family === 'chromatic') {
      elements.push(shape('ambient-panel', 52, 52, 1176, 616, soft, 22));
      elements.push(shape('accent-orbit', 938, 92, 212, 212, accent, 106));
      elements.push(text('deck-label', recipe.name, 86, 82, 620, 32, 17, accent, 700));
      elements.push(text('page-number', label, 1010, 82, 170, 28, 16, ink, 600, 'right'));
      elements.push(text(`claim-${source.id}`, source.claim, 86, 168, 850, 205, source.role === 'cover' ? 76 : 58, ink, 800));
      itemStart = 86; itemArea = 1094; itemY = 454; itemRadius = 16; itemFill = bg;
    } else {
      elements.push(shape('anchor-rule', 72, 72, family === 'grid' ? 1136 : 8, family === 'grid' ? 3 : 576, accent));
      elements.push(text('deck-label', title.toUpperCase(), 104, 76, 760, 30, 16, accent, 700));
      elements.push(text('page-number', label, 1030, 76, 170, 30, 16, ink, 500, 'right'));
      elements.push(text(`claim-${source.id}`, source.claim, 104, 154, 1030, 180, source.role === 'cover' || source.role === 'closing' ? 74 : 56, ink, 800));
    }
    const items = source.exact_text.filter(item => item !== source.claim).slice(0, 4);
    const itemWidth = Math.floor(itemArea / Math.max(1, items.length));
    items.forEach((item, itemIndex) => {
      const x = itemStart + itemIndex * itemWidth;
      const fill = itemIndex === 0 ? accent : itemFill;
      elements.push(shape(`block-${itemIndex}`, x, itemY, itemWidth - 16, 142, fill, itemRadius));
      elements.push(text(`item-${itemIndex}`, item, x + 16, itemY + 28, itemWidth - 48, 92, family === 'terminal' ? 20 : 23, itemIndex === 0 ? bg : ink, 700, 'left', familyFont));
    });
    elements.push(text(`theme-${source.id}`, recipe.name, family === 'terminal' ? 78 : 104, 624, 500, 24, 14, accent, 600, 'left', familyFont));
    return { id: source.id, background: bg, transition: index ? 'morph' : 'none', notes: `${source.purpose}\n${source.claim}`, elements };
  });
  return createBentoDocument({ title, theme: { background: bg, color: ink, accent, fontFamily: 'Arial, sans-serif' }, slides });
}

export function composeHtmlThemeShowcase(outline, recipes) {
  const slides = recipes.map((recipe, index) => {
    const source = outline.slides[index % outline.slides.length];
    const one = composeHtmlDeck({ ...outline, slides: [{ ...source, id: `html-${recipe.id}` }] }, recipe, { title: outline.title });
    const counter = one.slides[0].elements.find(element => element.id === 'page-number');
    if (counter) counter.html = `${String(index + 1).padStart(2, '0')} / ${recipes.length}`;
    one.slides[0].notes = `主题：${recipe.name}\n来源：${recipe.provenance.join(', ')}\n${source.claim}`;
    return one.slides[0];
  });
  return createBentoDocument({ title: `${outline.title} · HTML 主题样例`, slides });
}
