import { readFile } from 'node:fs/promises';
import { extname } from 'node:path';
import { createBentoDocument } from './bento-document.mjs';

export function compileImageJobs(outline, recipe, outputDir = 'slides') {
  if (outline.mode && outline.mode !== 'ai-image') return [];
  return outline.slides.map((slide, index) => ({
    id: slide.id,
    out: `${outputDir}/${String(index + 1).padStart(2, '0')}-${slide.id}.png`,
    use_case: 'productivity-visual',
    prompt: [
      'Create one complete 16:9 presentation slide as a single raster image.',
      `Theme: ${recipe.name}. Palette: ${recipe.palette}. Composition: ${recipe.composition}. Typography: ${recipe.typography}.`,
      `Page role: ${slide.role}. Claim: ${slide.claim}. Visual brief: ${slide.visual_brief}.`,
      `Text (verbatim, no other visible text): ${slide.exact_text.map(item => `"${item}"`).join('; ')}`,
      `Constraints: ${recipe.image_prompt_recipe.require.join('; ')}. Avoid: ${recipe.image_prompt_recipe.forbid.join('; ')}; tiny text; UI chrome; watermark.`,
    ].join('\n'),
  }));
}

const mime = path => extname(path).toLowerCase() === '.jpg' || extname(path).toLowerCase() === '.jpeg' ? 'image/jpeg' : 'image/png';

export async function composeAiImageDeck(outline, recipe, assets) {
  if (outline.mode && outline.mode !== 'ai-image') throw new Error('ai-image mode required');
  if (assets.length !== outline.slides.length) throw new Error('每一页都必须有一张完整页面图片');
  const embedded = {};
  const slides = [];
  for (const [index, source] of outline.slides.entries()) {
    const path = assets[index];
    const key = `slide-${source.id}`;
    embedded[key] = `data:${mime(path)};base64,${(await readFile(path)).toString('base64')}`;
    slides.push({
      id: source.id,
      background: '#000000',
      transition: index ? 'fade' : 'none',
      notes: `${source.purpose}\n${source.claim}\n主题：${recipe.name}`,
      elements: [{ id: `page-${source.id}`, type: 'image', x: 0, y: 0, w: 1280, h: 720, rotation: 0, opacity: 1, src: `asset:${key}`, fit: 'fill', radius: 0 }],
    });
  }
  return { ...createBentoDocument({ title: outline.title, theme: { background: '#000000', color: '#ffffff', accent: '#ffffff', fontFamily: 'Arial, sans-serif' }, slides }), assets: embedded };
}
