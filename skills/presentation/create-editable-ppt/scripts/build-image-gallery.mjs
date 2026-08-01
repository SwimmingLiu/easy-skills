#!/usr/bin/env node
import { access, readFile, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';

function flag(args, name, fallback) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

const root = resolve(flag(process.argv.slice(2), '--root', '.'));
const catalog = JSON.parse(await readFile(join(root, 'showcase.json'), 'utf8'));
const cards = [];
for (const theme of catalog.themes) {
  const project = join(root, theme.project);
  const deck = JSON.parse(await readFile(join(project, 'deck_spec.json'), 'utf8'));
  const manifest = JSON.parse(await readFile(join(project, 'generation_manifest.json'), 'utf8'));
  for (const [index, slide] of manifest.slides.entries()) {
    try { await access(join(project, slide.output_path)); } catch { throw new Error(`Missing generated slide image: ${theme.id}/${slide.id}`); }
    if (!['generated', 'pass'].includes(slide.status)) slide.status = 'generated';
    const source = deck.slides.find((item) => item.id === slide.id) ?? deck.slides[index] ?? {};
    const src = `${theme.project}/${slide.output_path}`.replaceAll('\\', '/');
    cards.push(`<article class="slide-card" data-theme="${escapeHtml(theme.id)}" data-role="${escapeHtml(slide.role)}"><img src="${escapeHtml(src)}" alt="${escapeHtml(source.claim ?? slide.id)}" loading="lazy"><div class="card-meta"><span>${String(index + 1).padStart(2, '0')} · ${escapeHtml(slide.role)}</span><strong>${escapeHtml(source.claim ?? slide.id)}</strong></div></article>`);
  }
}
const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(catalog.title)}</title><style>*{box-sizing:border-box}body{margin:0;background:#f3f4f0;color:#172019;font-family:Inter,"Noto Sans SC",system-ui,sans-serif;letter-spacing:0}.wrap{max-width:1500px;margin:0 auto;padding:48px 28px 80px}header{max-width:900px;margin-bottom:34px}h1{font-size:clamp(30px,4vw,58px);line-height:1.1;margin:0 0 14px;letter-spacing:0}.lead{font-size:20px;line-height:1.5;color:#4c5b50;margin:0}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px}.slide-card{margin:0;background:#fff;border:1px solid #d8ded6;box-shadow:0 10px 30px #20302012;overflow:hidden}.slide-card img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;background:#141817}.card-meta{padding:13px 16px 15px;display:grid;gap:7px}.card-meta span{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#647168}.card-meta strong{font-size:17px;line-height:1.35;font-weight:650}@media(max-width:760px){.wrap{padding:30px 16px 52px}.grid{grid-template-columns:1fr;gap:20px}.lead{font-size:17px}}@media print{.wrap{padding:12px}.grid{grid-template-columns:1fr 1fr;gap:10px}.slide-card{break-inside:avoid;box-shadow:none}.card-meta{padding:6px}.card-meta strong{font-size:10px}}</style></head><body><main class="wrap"><header><h1>${escapeHtml(catalog.title)}</h1><p class="lead">中心含义：${escapeHtml(catalog.central_message)} · ${catalog.themes.length} 个主题 · ${cards.length} 页</p></header><section class="grid">${cards.join('')}</section></main></body></html>`;
await writeFile(join(root, 'index.html'), html, 'utf8');
console.log(join(root, 'index.html'));
