#!/usr/bin/env node
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { defaultEditorState } from './lib/model.mjs';
import { renderDeck } from './lib/render.mjs';
import { writeJsonAtomic, writeTextAtomic } from './lib/storage.mjs';
import { THEMES } from './lib/themes.mjs';

const THEME_NOTES = Object.freeze({
  'business-minimal': { name: '商务极简', use: '管理汇报 / 方案沟通', note: '克制留白、左侧结论线和稳健图片框。' },
  editorial: { name: '编辑叙事', use: '行业观点 / 品牌故事', note: '纸刊质感、衬线标题和非对称图文关系。' },
  'swiss-grid': { name: '瑞士网格', use: '设计发布 / 鲜明主张', note: '严格网格、信号色与高对比几何边界。' },
  'launch-tech': { name: '科技发布', use: '产品发布 / 技术演讲', note: '深色舞台、青色工程线和低饱和影像。' },
  'data-consulting': { name: '数据咨询', use: '战略分析 / 经营汇报', note: '结论优先、紧凑层级与清晰对比结构。' },
  academic: { name: '学术研究', use: '答辩 / 白皮书 / 研究', note: '证据感、克制图像和出版式层级。' },
  'brand-bold': { name: '高能品牌', use: '创意提案 / 增长 / 品牌', note: '高反差色块、粗标题与海报式构图。' },
  'premium-dark': { name: '高端暗色', use: 'Keynote / 高端发布', note: '深黑舞台、金色细节与沉浸式影像。' },
});

const SLIDES = Object.freeze([
  { id: 's01', role: 'cover', claim: 'AI 原生知识工作流', layout: 'left', props: { eyebrow: 'Knowledge Work / 2026', subtitle: '把散落信息变成持续可用的判断', meta: '产品与方法论分享', footer: 'KNOWLEDGE WORKFLOW', image: 'cover-city' }, evidence: [], media: ['cover-city'], speaker_notes: '建立主题：重点不是保存更多，而是让上下文持续可用。' },
  { id: 's02', role: 'statement', claim: '信息更多，理解却更碎片化', layout: 'points', props: { points: ['文件在不同工具间漂移', '结论和来源逐渐分离', '行动依赖短期记忆'], footer: 'WHY NOW' }, evidence: [], media: [], speaker_notes: '只陈述常见工作现象，不使用未经来源支持的量化数据。' },
  { id: 's03', role: 'image-hero', claim: '新的工作台，核心是保留上下文', layout: 'split', props: { caption: '任务、资料、判断和行动在同一条线上', image: 'workbench', footer: 'THE WORKSPACE' }, evidence: [], media: ['workbench'], speaker_notes: '图片为工作场景示意，不是产品截图。' },
  { id: 's04', role: 'process', claim: '四个动作，让信息持续产生价值', layout: 'steps', props: { steps: [{ title: '收集现场' }, { title: '建立关联' }, { title: '形成判断' }, { title: '推进行动' }], footer: 'THE FLOW' }, evidence: [], media: [], speaker_notes: '用动作而不是功能列表解释方法。' },
  { id: 's05', role: 'comparison', claim: '真正的变化，是让信息持续流动', layout: 'before-after', props: { left_title: '传统', left: ['资料分散', '反复补背景', '结果停在文档'], right_title: 'AI 原生', right: ['聚合上下文', '复用判断路径', '行动持续更新'], footer: 'THE SHIFT' }, evidence: [], media: [], speaker_notes: '表达工作方式差异，不虚构效果数据。' },
  { id: 's06', role: 'closing', claim: '先重做一条高频流程', layout: 'action-led', props: { action: '把上下文、判断和行动连起来', contact: 'knowledge-work.example', footer: 'NEXT STEP', image: 'focus' }, evidence: [], media: ['focus'], speaker_notes: '以具体行动结束，不使用通用致谢页。' },
]);

const ASSETS = Object.freeze({
  schema_version: 1,
  assets: [
    { id: 'cover-city', path: '../../media/city.jpg', source: 'search', purpose: '封面城市与网络尺度意象', fact_bearing: false, license: 'Unsplash License', source_url: 'https://unsplash.com/photos/-icmOdYWXuQ', author: 'Kevin Young', alt: '夕阳下的城市天际线' },
    { id: 'workbench', path: '../../media/workbench.jpg', source: 'search', purpose: '知识工作台场景', fact_bearing: false, license: 'Unsplash License', source_url: 'https://unsplash.com/photos/ICW6QYOcdlg', author: 'Galymzhan Abdugalimov', alt: '笔记本电脑与纸质笔记组成的工作台' },
    { id: 'focus', path: '../../media/focus.jpg', source: 'search', purpose: '专注行动场景', fact_bearing: false, license: 'Unsplash License', source_url: 'https://unsplash.com/photos/6PF6DaiWz48', author: 'Rayi Christian Wicaksono', alt: '黑白键盘、咖啡杯与手部细节' },
  ],
});

function deckFor(themeId) {
  const theme = THEMES[themeId];
  return {
    schema_version: 1,
    revision: 1,
    title: 'AI 原生知识工作流',
    audience: '产品团队、知识工作者与组织管理者',
    purpose: '解释 AI 原生知识工作流的核心变化与行动路径',
    language: 'zh-CN',
    canvas: '16:9',
    density: 'speaker-led',
    theme: { family: themeId, variant: theme.variants[0] },
    slides: structuredClone(SLIDES),
  };
}

function escapeHtml(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
}

function galleryHtml() {
  const cards = Object.values(THEMES).map((theme) => {
    const info = THEME_NOTES[theme.id];
    const swatches = [theme.tokens.background, theme.tokens.text, theme.tokens.accent, theme.tokens.support].map((color) => `<i style="background:${escapeHtml(color)}" title="${escapeHtml(color)}"></i>`).join('');
    return `<article class="theme-card"><a class="preview" href="decks/${theme.id}/index.html" target="_blank" aria-label="打开${escapeHtml(info.name)}完整演示"><img src="decks/${theme.id}/qa/screenshots/01-s01.png" alt="${escapeHtml(info.name)}封面预览"></a><div class="card-body"><div class="card-head"><div><small>${escapeHtml(theme.id)}</small><h2>${escapeHtml(info.name)}</h2></div><a class="open" href="decks/${theme.id}/index.html" target="_blank" title="打开完整演示" aria-label="打开完整演示">↗</a></div><p class="use">${escapeHtml(info.use)}</p><p>${escapeHtml(info.note)}</p><div class="swatches" aria-label="主题色板">${swatches}</div></div></article>`;
  }).join('');
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PPT 主题对照实验室</title><style>
  :root{color-scheme:light;font-family:Inter,'Noto Sans SC',system-ui,sans-serif;color:#181a18;background:#eceee9}*{box-sizing:border-box}body{margin:0;letter-spacing:0}header{background:#fff;border-bottom:1px solid #d6d9d2;padding:28px max(24px,calc((100vw - 1440px)/2)) 24px}header .top{display:flex;gap:24px;align-items:end;justify-content:space-between}h1{font-size:34px;line-height:1.1;margin:0}header p{margin:10px 0 0;color:#5d625c;font-size:15px;max-width:760px;line-height:1.6}.count{font:700 42px/1 Georgia,serif;color:#146c5a}.count span{display:block;font:12px/1.2 Inter,sans-serif;color:#686d67;margin-top:6px;text-align:right}main{max-width:1440px;margin:auto;padding:28px 24px 48px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.theme-card{background:#fff;border:1px solid #d3d7d0;border-radius:6px;overflow:hidden}.preview{display:block;aspect-ratio:16/9;background:#252623;overflow:hidden;border-bottom:1px solid #d3d7d0}.preview img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .18s ease}.preview:hover img{transform:scale(1.012)}.card-body{padding:18px 20px 20px}.card-head{display:flex;gap:16px;justify-content:space-between;align-items:start}.card-head small{display:block;color:#747a73;font-size:10px;text-transform:uppercase;margin-bottom:4px}.card-head h2{font-size:22px;margin:0}.open{display:grid;place-items:center;width:34px;height:34px;border:1px solid #cdd2ca;border-radius:4px;color:#1d241f;text-decoration:none;font-size:19px}.open:hover{background:#eff3ed}.use{font-weight:650;color:#294d3f;margin:14px 0 6px}.card-body p:not(.use){margin:0;color:#646a63;font-size:13px;line-height:1.55}.swatches{display:flex;gap:7px;margin-top:16px}.swatches i{display:block;width:24px;height:16px;border:1px solid rgba(0,0,0,.16)}footer{max-width:1440px;margin:auto;padding:0 24px 36px;color:#6c716b;font-size:12px;line-height:1.7}@media(max-width:800px){header .top{align-items:start}.count{font-size:32px}.grid{grid-template-columns:1fr}h1{font-size:28px}main{padding-inline:14px}.theme-card{border-radius:4px}}
  </style></head><body><header><div class="top"><div><h1>PPT 主题对照实验室</h1><p>同一套 6 页内容、同一组图片、八种视觉 recipe。点击任意封面进入可编辑的完整演示。</p></div><div class="count">08<span>THEME FAMILIES</span></div></div></header><main><div class="grid">${cards}</div></main><footer>示例内容借鉴产品发布、行业观点与方法论演讲的低密度叙事方式。图片来源：Kevin Young、Galymzhan Abdugalimov、Rayi Christian Wicaksono / Unsplash。</footer></body></html>`;
}

export async function buildThemeShowcase(root) {
  await mkdir(root, { recursive: true });
  const built = [];
  for (const themeId of Object.keys(THEMES)) {
    const deckRoot = resolve(root, 'decks', themeId);
    await mkdir(resolve(deckRoot, 'media'), { recursive: true });
    await mkdir(resolve(deckRoot, 'dist'), { recursive: true });
    const deck = deckFor(themeId);
    const state = defaultEditorState(deck);
    state.project_status = 'review';
    state.review_status = Object.fromEntries(deck.slides.map((slide) => [slide.id, 'pass']));
    await writeJsonAtomic(resolve(deckRoot, 'deck_spec.json'), deck);
    await writeJsonAtomic(resolve(deckRoot, 'editor_state.json'), state);
    await writeJsonAtomic(resolve(deckRoot, 'asset_manifest.json'), ASSETS);
    await writeTextAtomic(resolve(deckRoot, 'index.html'), renderDeck({ deck, state, assets: ASSETS }));
    built.push({ id: themeId, root: deckRoot });
  }
  await writeJsonAtomic(resolve(root, 'content.json'), { title: 'AI 原生知识工作流', slides: SLIDES, assets: ASSETS });
  await writeTextAtomic(resolve(root, 'index.html'), galleryHtml());
  return { root, themes: built };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  const root = resolve(process.argv[2] ?? new URL('../assets/examples/theme-showcase', import.meta.url).pathname);
  const result = await buildThemeShowcase(root);
  console.log(`${result.themes.length} themes built at ${root}`);
}
