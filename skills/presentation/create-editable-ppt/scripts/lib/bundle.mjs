import { readFile } from 'node:fs/promises';
import { extname, isAbsolute, join, relative, resolve } from 'node:path';

import { renderBundledPureHtmlDeck } from './pure-html.mjs';

const MIME_TYPES = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
};

function present(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

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

function assetMime(path) {
  return MIME_TYPES[extname(path).toLowerCase()] ?? 'application/octet-stream';
}

function safeAssetPath(root, outputPath) {
  if (!present(outputPath) || isAbsolute(outputPath)) throw new Error(`Invalid bundled asset path: ${outputPath ?? 'missing'}`);
  const rootPath = resolve(root);
  const candidate = resolve(root, outputPath);
  const relativePath = relative(rootPath, candidate);
  if (relativePath.startsWith('..') || isAbsolute(relativePath)) throw new Error(`Bundled asset escapes project root: ${outputPath}`);
  return candidate;
}

export async function buildBundledImageDeck(root, deck, manifest) {
  if (!deck || !Array.isArray(deck.slides)) throw new Error('Deck slides are required for bundling.');
  if (!manifest || !Array.isArray(manifest.slides)) throw new Error('Generation manifest slides are required for bundling.');
  const slides = [];
  const assets = {};
  for (const [index, item] of manifest.slides.entries()) {
    if (!['generated', 'pass'].includes(item.status)) throw new Error(`Slide ${item.id ?? index + 1} is not generated.`);
    const absolutePath = safeAssetPath(root, item.output_path);
    let bytes;
    try { bytes = await readFile(absolutePath); } catch { throw new Error(`Missing generated slide image: ${item.output_path}`); }
    const assetKey = item.output_path.replaceAll('\\', '/');
    assets[assetKey] = `data:${assetMime(assetKey)};base64,${bytes.toString('base64')}`;
    const source = deck.slides.find((slide) => slide.id === item.id) ?? deck.slides[index] ?? {};
    slides.push({
      id: item.id,
      role: item.role ?? source.role,
      image: `asset:${assetKey}`,
      claim: source.claim ?? item.role ?? item.id,
      exact_text: source.exact_text ?? [],
      speaker_notes: source.speaker_notes ?? source.claim ?? '',
      visual_anchor_id: source.visual_anchor_id ?? `${deck.theme?.family ?? 'default'}-anchor`,
      continuity_group: source.continuity_group ?? `${deck.theme?.family ?? 'default'}-deck`,
      transition: source.transition ?? 'fade',
    });
  }
  const document = {
    format: 'image-ppt',
    version: 1,
    mode: 'present',
    readonly: true,
    title: deck.title ?? 'Image presentation',
    purpose: deck.purpose ?? '',
    central_message: deck.central_message ?? '',
    theme: deck.theme ?? {},
    assets,
    slides,
    source: { deck_schema_version: deck.schema_version ?? null, manifest_schema_version: manifest.schema_version ?? null },
  };
  return renderBundledImageDeck(document);
}

export async function buildBundledPureHtmlDeck(root, deck, manifest) {
  if (!deck || !Array.isArray(deck.slides)) throw new Error('Deck slides are required for bundling.');
  if (!manifest || !Array.isArray(manifest.slides)) throw new Error('Generation manifest slides are required for bundling.');
  const slides = [];
  for (const [index, item] of manifest.slides.entries()) {
    if (!['generated', 'pass'].includes(item.status)) throw new Error(`Slide ${item.id ?? index + 1} is not generated.`);
    const source = deck.slides.find((slide) => slide.id === item.id) ?? deck.slides[index] ?? {};
    slides.push({
      id: item.id,
      role: item.role ?? source.role,
      claim: source.claim ?? item.role ?? item.id,
      exact_text: source.exact_text ?? [],
      speaker_notes: source.speaker_notes ?? source.claim ?? '',
      visual_anchor_id: source.visual_anchor_id ?? `${deck.theme?.family ?? 'default'}-anchor`,
      continuity_group: source.continuity_group ?? `${deck.theme?.family ?? 'default'}-deck`,
      transition: source.transition ?? 'fade',
    });
  }
  const document = {
    format: 'image-ppt',
    version: 1,
    mode: 'pure-html',
    readonly: true,
    title: deck.title ?? 'Pure HTML presentation',
    purpose: deck.purpose ?? '',
    central_message: deck.central_message ?? '',
    theme: deck.theme ?? {},
    assets: {},
    slides,
    source: { deck_schema_version: deck.schema_version ?? null, manifest_schema_version: manifest.schema_version ?? null },
  };
  return renderBundledPureHtmlDeck(document);
}

export function renderBundledImageDeck(document) {
  const serialized = escapeJsonForScript(document);
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(document.title)}</title><style>*{box-sizing:border-box}html,body{margin:0;background:#101311;color:#fff;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}.deck{height:100vh;display:grid;place-items:center}.slide{display:none;position:relative;width:min(100vw,177.78vh);aspect-ratio:16/9}.slide.active{display:block}.slide img{display:block;width:100%;height:100%;object-fit:contain}.counter{position:absolute;right:16px;bottom:12px;padding:5px 8px;border-radius:3px;background:#000a;color:#fff;font-size:12px}.nav{position:fixed;top:50%;width:42px;height:42px;transform:translateY(-50%);border:0;background:#000a;color:#fff;font-size:24px;cursor:pointer}.nav:focus-visible{outline:2px solid #fff;outline-offset:3px}#prev{left:8px}#next{right:8px}@media print{body{background:#fff}.deck{height:auto;display:block}.slide{display:block;width:100vw;height:56.25vw;page-break-after:always}.nav,.counter{display:none}}</style></head><body><script type="application/image-ppt+json" id="image-ppt-doc">${serialized}</script><main class="deck" id="app"></main><button class="nav" id="prev" type="button" aria-label="上一页">‹</button><button class="nav" id="next" type="button" aria-label="下一页">›</button><script>(()=>{const source=document.getElementById('image-ppt-doc');const app=document.getElementById('app');const doc=JSON.parse(source.textContent);let current=0;function assetUrl(ref){return ref.startsWith('asset:')?doc.assets[ref.slice(6)]:ref}function render(){app.innerHTML='';for(const [index,slide] of doc.slides.entries()){const section=document.createElement('section');section.className='slide'+(index===current?' active':'');section.dataset.slide=String(index);section.dataset.slideId=slide.id;const image=document.createElement('img');image.src=assetUrl(slide.image);image.alt=slide.claim||slide.id;image.decoding='async';const counter=document.createElement('span');counter.className='counter';counter.textContent=(index+1)+' / '+doc.slides.length;section.append(image,counter);app.append(section)}}function show(next){current=(next+doc.slides.length)%doc.slides.length;render()}document.getElementById('prev').onclick=()=>show(current-1);document.getElementById('next').onclick=()=>show(current+1);addEventListener('keydown',event=>{if(['ArrowRight','PageDown',' '].includes(event.key))show(current+1);if(['ArrowLeft','PageUp'].includes(event.key))show(current-1)});window.imagePpt={loadDoc(next){if(!next||!Array.isArray(next.slides))throw new Error('Invalid image-ppt document');Object.assign(doc,next);current=0;render()},getDoc(){return structuredClone(doc)}};render()})()</script></body></html>`;
}
