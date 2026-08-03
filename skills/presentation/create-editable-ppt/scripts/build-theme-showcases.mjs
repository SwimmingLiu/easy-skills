#!/usr/bin/env node
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';

import { compileImageJobs, composeAiImageDeck } from './lib/ai-image.mjs';
import { spliceBentoDocument } from './lib/bento-document.mjs';
import { composeHtmlThemeShowcase } from './lib/html-composer.mjs';
import { createOutline } from './lib/outline.mjs';
import { loadThemeCatalog } from './lib/theme-catalog.mjs';

const skillRoot = resolve(new URL('..', import.meta.url).pathname);
const sampleRoot = join(skillRoot, 'assets', 'examples', 'bento-theme-showcase');
const shell = await readFile(join(skillRoot, 'assets', 'bento', 'Bento_Slides.bento.html'), 'utf8');
const catalog = await loadThemeCatalog();
const outline = createOutline('AI 原生知识工作流');
await mkdir(join(sampleRoot, 'ai-image', 'slides'), { recursive: true });
await mkdir(join(sampleRoot, 'html'), { recursive: true });

const htmlDoc = composeHtmlThemeShowcase({ ...outline, mode: 'html' }, catalog.html);
await writeFile(join(sampleRoot, 'html', 'theme-showcase.bento.html'), spliceBentoDocument(shell, htmlDoc));

const imageSlides = catalog['ai-image'].map((recipe, index) => {
  const source = outline.slides[index % outline.slides.length];
  return { ...source, id: `image-${recipe.id}`, theme_id: recipe.id, visual_brief: `${source.visual_brief}；完整适配 ${recipe.name}，保持同一“AI 原生知识工作流”内容主题。` };
});
const imageOutline = { ...outline, mode: 'ai-image', page_count: imageSlides.length, slides: imageSlides };
const jobs = imageSlides.map((slide, index) => {
  const recipe = catalog['ai-image'][index];
  return compileImageJobs({ ...imageOutline, slides: [slide] }, recipe, 'slides')[0];
}).map((job, index) => ({ ...job, out: `${String(index + 1).padStart(2, '0')}-${catalog['ai-image'][index].id}.png`, size: '2048x1152', quality: 'low' }));
await writeFile(join(sampleRoot, 'ai-image', 'imagegen-jobs.jsonl'), `${jobs.map(job => JSON.stringify(job)).join('\n')}\n`);
await writeFile(join(sampleRoot, 'ai-image', 'outline.json'), `${JSON.stringify(imageOutline, null, 2)}\n`);

if (process.argv.includes('--assemble-ai')) {
  const assets = jobs.map(job => join(sampleRoot, 'ai-image', 'slides', job.out));
  const slides = [];
  const embedded = {};
  for (const [index, recipe] of catalog['ai-image'].entries()) {
    const oneOutline = { ...imageOutline, title: `${outline.title} · AI 图片主题样例`, slides: [imageSlides[index]] };
    const one = await composeAiImageDeck(oneOutline, recipe, [assets[index]]);
    slides.push(one.slides[0]);
    Object.assign(embedded, one.assets);
  }
  const doc = { ...htmlDoc, title: `${outline.title} · AI 图片主题样例`, theme: { background: '#000000', color: '#ffffff', accent: '#ffffff', fontFamily: 'Arial, sans-serif' }, slides, assets: embedded };
  await writeFile(join(sampleRoot, 'ai-image', 'theme-showcase.bento.html'), spliceBentoDocument(shell, doc));
}

console.log(sampleRoot);
