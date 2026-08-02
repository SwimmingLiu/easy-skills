const FALLBACK_TOKENS = {
  'business-minimal': { background: '#F3F4EF', surface: '#FFFFFF', text: '#172019', muted: '#59645C', accent: '#146C5A', support: '#C58C2B', line: '#D3D9D1', radius: '6px', heading: "Inter, 'Noto Sans SC', system-ui, sans-serif", body: "Inter, 'Noto Sans SC', system-ui, sans-serif" },
  editorial: { background: '#F1EEE7', surface: '#FCF9F2', text: '#201C18', muted: '#70665C', accent: '#A23B2A', support: '#285C7A', line: '#D4CABC', radius: '0px', heading: "Georgia, 'Noto Serif SC', serif", body: "Georgia, 'Noto Serif SC', serif" },
  'swiss-grid': { background: '#F3F1E7', surface: '#FFFEF7', text: '#101010', muted: '#55554F', accent: '#E63B2E', support: '#1647A8', line: '#BEBDB5', radius: '0px', heading: "Arial, 'Noto Sans SC', sans-serif", body: "Arial, 'Noto Sans SC', sans-serif" },
  'launch-tech': { background: '#071719', surface: '#10282B', text: '#EAF8F7', muted: '#8AA7A8', accent: '#35D3D3', support: '#E8B44C', line: '#285054', radius: '2px', heading: "Inter, 'Noto Sans SC', sans-serif", body: "Inter, 'Noto Sans SC', sans-serif" },
  'data-consulting': { background: '#F5F7F8', surface: '#FFFFFF', text: '#17212B', muted: '#5E6974', accent: '#007A6E', support: '#D04A3A', line: '#D4DCE1', radius: '2px', heading: "Arial, 'Noto Sans SC', sans-serif", body: "Arial, 'Noto Sans SC', sans-serif" },
  academic: { background: '#FBFBF7', surface: '#FFFFFF', text: '#202421', muted: '#616963', accent: '#2F5D50', support: '#7A3E48', line: '#D4D9D3', radius: '0px', heading: "Georgia, 'Noto Serif SC', serif", body: "Arial, 'Noto Sans SC', sans-serif" },
  'brand-bold': { background: '#F7D94C', surface: '#FFF9E8', text: '#171717', muted: '#554B31', accent: '#EA4B35', support: '#067A83', line: '#171717', radius: '0px', heading: "Arial Black, Arial, 'Noto Sans SC', sans-serif", body: "Arial, 'Noto Sans SC', sans-serif" },
  'premium-dark': { background: '#11100F', surface: '#1D1B18', text: '#F4EFE3', muted: '#B5ADA0', accent: '#D6B25E', support: '#4EA7A0', line: '#454139', radius: '0px', heading: "Georgia, 'Noto Serif SC', serif", body: "Inter, 'Noto Sans SC', sans-serif" },
};

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function escapeJsonForScript(value) {
  return JSON.stringify(value).replaceAll('<', '\\u003c');
}

function themeTokens(theme = {}) {
  return theme.tokens ?? FALLBACK_TOKENS[theme.id ?? theme.family] ?? FALLBACK_TOKENS['business-minimal'];
}

function slideSource(deck, item, index) {
  return deck?.slides?.find((slide) => slide.id === item.id) ?? deck?.slides?.[index] ?? {};
}

function copyMarkup(source) {
  const lines = Array.isArray(source.exact_text) && source.exact_text.length ? source.exact_text : [source.claim ?? ''];
  const title = lines[0] ?? '';
  const rest = lines.slice(1);
  if (source.role === 'process' && rest.length) {
    return `<div class="copy"><h1>${escapeHtml(title)}</h1><ol class="steps">${rest.map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ol></div>`;
  }
  return `<div class="copy"><h1>${escapeHtml(title)}</h1>${rest.map((line) => `<p>${escapeHtml(line)}</p>`).join('')}</div>`;
}

function slideMarkup(source, visualSrc, index, total) {
  const role = source.role ?? 'statement';
  const fullBleed = ['cover', 'closing', 'image-hero'].includes(role);
  const visual = `<div class="visual-wrap"><img class="visual" src="${escapeHtml(visualSrc)}" alt="${escapeHtml(source.claim ?? source.id)}" data-asset-role="background-or-illustration" decoding="async"></div>`;
  return `<section class="slide mode-html-image-assisted role-${escapeHtml(role)}${fullBleed ? ' full-bleed' : ''}${index === 0 ? ' active' : ''}" data-slide="${index}" data-slide-id="${escapeHtml(source.id)}" data-mode="html-image-assisted">${visual}${copyMarkup(source)}<span class="counter">${index + 1} / ${total}</span></section>`;
}

function baseStyles(tokens) {
  return `*{box-sizing:border-box}html,body{margin:0;background:${tokens.background};color:${tokens.text};font-family:${tokens.body};letter-spacing:0}body{min-height:100vh}.deck{height:100vh;display:grid;place-items:center;padding:24px}.slide{display:none;position:relative;overflow:hidden;width:min(calc(100vw - 48px),calc(177.78vh - 48px));aspect-ratio:16/9;background:${tokens.surface};border:1px solid ${tokens.line};border-radius:${tokens.radius};box-shadow:0 18px 50px #0002}.slide.active{display:grid}.visual-wrap{position:absolute;inset:0 0 0 52%;overflow:hidden;background:${tokens.background}}.visual{display:block;width:100%;height:100%;object-fit:cover}.visual-wrap:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,${tokens.surface} 0%,${tokens.surface}00 46%)}.copy{position:relative;z-index:1;align-self:center;width:56%;padding:7%;max-width:760px}.copy h1{margin:0 0 24px;font-family:${tokens.heading};font-size:clamp(28px,4.2vw,72px);line-height:1.08;letter-spacing:0}.copy p{margin:12px 0;color:${tokens.muted};font-size:clamp(16px,1.5vw,28px);line-height:1.45}.steps{display:grid;gap:12px;list-style:none;padding:0;margin:26px 0 0;counter-reset:step}.steps li{counter-increment:step;display:flex;align-items:center;gap:12px;color:${tokens.text};font-size:clamp(16px,1.45vw,25px);line-height:1.2}.steps li:before{content:counter(step,decimal-leading-zero);display:grid;place-items:center;flex:none;width:42px;height:32px;border:1px solid ${tokens.accent};border-radius:${tokens.radius};color:${tokens.accent};font-size:12px}.full-bleed{display:block;background:${tokens.text}}.full-bleed .visual-wrap{inset:0}.full-bleed .visual-wrap:after{background:linear-gradient(90deg,${tokens.text}cc 0%,${tokens.text}55 48%,${tokens.text}00 78%)}.full-bleed .copy{position:absolute;left:0;top:0;height:100%;display:flex;justify-content:center;flex-direction:column;color:${tokens.surface};width:63%}.full-bleed .copy p{color:${tokens.surface}cc}.role-process .visual-wrap,.role-comparison .visual-wrap,.role-data .visual-wrap,.role-two-column .visual-wrap{inset:10% 6% 10% 57%;border-radius:${tokens.radius};border:1px solid ${tokens.line}}.role-process .visual-wrap:after,.role-comparison .visual-wrap:after,.role-data .visual-wrap:after,.role-two-column .visual-wrap:after{background:${tokens.text}18}.counter{position:absolute;z-index:2;right:18px;bottom:14px;padding:5px 8px;background:${tokens.text}aa;color:${tokens.surface};font:12px system-ui,sans-serif}.nav{position:fixed;top:50%;width:42px;height:42px;transform:translateY(-50%);border:0;border-radius:50%;background:${tokens.text}dd;color:${tokens.surface};font-size:24px;cursor:pointer}.nav:focus-visible{outline:2px solid ${tokens.accent};outline-offset:3px}#prev{left:10px}#next{right:10px}@media(max-width:760px){.deck{padding:0}.slide{width:100vw;border:0;border-radius:0}.visual-wrap{inset:45% 0 0}.copy{width:100%;padding:8%;align-self:start}.copy h1{font-size:clamp(28px,8vw,48px)}.full-bleed .copy{width:92%;padding:8%}.role-process .visual-wrap,.role-comparison .visual-wrap,.role-data .visual-wrap,.role-two-column .visual-wrap{inset:52% 6% 8%}.role-process .copy,.role-comparison .copy,.role-data .copy,.role-two-column .copy{padding-top:8%}}@media print{body{background:${tokens.surface}}.deck{height:auto;display:block;padding:0}.slide{display:block;width:100vw;height:56.25vw;border:0;border-radius:0;box-shadow:none;page-break-after:always}.nav,.counter{display:none}}`;
}

function styles(tokens) {
  return `${baseStyles(tokens)}@media screen{.slide.full-bleed{display:none}.slide.active.full-bleed{display:block}}.full-bleed .copy h1{font-size:clamp(26px,3.8vw,64px);white-space:nowrap}`;
}

function runtimeScript() {
  return `(()=>{const slides=[...document.querySelectorAll('.slide')];let current=0;function show(next){if(!slides.length)return;slides[current]?.classList.remove('active');current=(next+slides.length)%slides.length;slides[current]?.classList.add('active')}document.getElementById('prev').onclick=()=>show(current-1);document.getElementById('next').onclick=()=>show(current+1);addEventListener('keydown',event=>{if(['ArrowRight','PageDown',' '].includes(event.key))show(current+1);if(['ArrowLeft','PageUp'].includes(event.key))show(current-1)})})();`;
}

export function renderHtmlImageDeck(deck, manifest, theme = {}) {
  const tokenSet = themeTokens((theme && (theme.id || theme.family)) ? theme : { family: deck.theme?.family });
  const slides = manifest.slides.map((item, index) => slideMarkup(slideSource(deck, item, index), item.output_path, index, manifest.slides.length)).join('');
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="presentation-mode" content="html-image-assisted"><title>${escapeHtml(deck.title)}</title><style>${styles(tokenSet)}</style></head><body data-mode="html-image-assisted"><main class="deck">${slides}</main><button class="nav" id="prev" type="button" title="上一页" aria-label="上一页">‹</button><button class="nav" id="next" type="button" title="下一页" aria-label="下一页">›</button><script>${runtimeScript()}</script></body></html>`;
}

export function renderBundledHtmlImageDeck(document) {
  const tokenSet = themeTokens({ family: document.theme?.family });
  const serialized = escapeJsonForScript(document);
  const runtime = `(()=>{const source=document.getElementById('image-ppt-doc');const app=document.getElementById('app');const doc=JSON.parse(source.textContent);let current=0;function assetUrl(ref){return ref?.startsWith('asset:')?doc.assets[ref.slice(6)]:ref}function addText(parent,tag,text){const node=document.createElement(tag);node.textContent=text;parent.append(node);return node}function render(){app.innerHTML='';for(const [index,slide] of doc.slides.entries()){const section=document.createElement('section');section.className='slide mode-html-image-assisted role-'+(slide.role||'statement')+(index===current?' active':'')+(['cover','closing','image-hero'].includes(slide.role)?' full-bleed':'');section.dataset.slide=String(index);section.dataset.slideId=slide.id;section.dataset.mode='html-image-assisted';const visualWrap=document.createElement('div');visualWrap.className='visual-wrap';const image=document.createElement('img');image.className='visual';image.src=assetUrl(slide.visual);image.alt=slide.claim||slide.id;image.dataset.assetRole='background-or-illustration';image.decoding='async';visualWrap.append(image);section.append(visualWrap);const copy=document.createElement('div');copy.className='copy';const lines=Array.isArray(slide.exact_text)&&slide.exact_text.length?slide.exact_text:[slide.claim||''];addText(copy,'h1',lines[0]);if(slide.role==='process'&&lines.length>1){const list=document.createElement('ol');list.className='steps';for(const line of lines.slice(1))addText(list,'li',line);copy.append(list)}else for(const line of lines.slice(1))addText(copy,'p',line);section.append(copy);const counter=document.createElement('span');counter.className='counter';counter.textContent=(index+1)+' / '+doc.slides.length;section.append(counter);app.append(section)}}function show(next){current=(next+doc.slides.length)%doc.slides.length;render()}document.getElementById('prev').onclick=()=>show(current-1);document.getElementById('next').onclick=()=>show(current+1);addEventListener('keydown',event=>{if(['ArrowRight','PageDown',' '].includes(event.key))show(current+1);if(['ArrowLeft','PageUp'].includes(event.key))show(current-1)});window.imagePpt={loadDoc(next){if(!next||!Array.isArray(next.slides))throw new Error('Invalid image-ppt document');Object.assign(doc,next);current=0;render()},getDoc(){return structuredClone(doc)}};render()})();`;
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="presentation-mode" content="html-image-assisted"><title>${escapeHtml(document.title)}</title><style>${styles(tokenSet)}</style></head><body data-mode="html-image-assisted"><script type="application/image-ppt+json" id="image-ppt-doc">${serialized}</script><main class="deck" id="app"></main><button class="nav" id="prev" type="button" title="上一页" aria-label="上一页">‹</button><button class="nav" id="next" type="button" title="下一页" aria-label="下一页">›</button><script>${runtime}</script></body></html>`;
}
