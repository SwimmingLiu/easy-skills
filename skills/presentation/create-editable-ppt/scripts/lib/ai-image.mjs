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

function jpegSize(buffer) {
  if (buffer.length < 4 || buffer[0] !== 0xff || buffer[1] !== 0xd8) return null;
  let offset = 2;
  while (offset + 8 < buffer.length) {
    while (buffer[offset] === 0xff) offset += 1;
    const marker = buffer[offset];
    offset += 1;
    if (marker === 0xd9 || marker === 0xda) break;
    if (offset + 2 > buffer.length) break;
    const length = buffer.readUInt16BE(offset);
    if (length < 2 || offset + length > buffer.length) break;
    if ([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf].includes(marker)) {
      return { width: buffer.readUInt16BE(offset + 5), height: buffer.readUInt16BE(offset + 3) };
    }
    offset += length;
  }
  return null;
}

export function inspectRaster(buffer, path = 'image') {
  const extension = extname(path).toLowerCase();
  let type;
  let size;
  if (extension === '.png' && buffer.length >= 24 && buffer.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) {
    type = 'image/png';
    size = { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
  } else if (['.jpg', '.jpeg'].includes(extension)) {
    type = 'image/jpeg';
    size = jpegSize(buffer);
  }
  if (!type || !size || !size.width || !size.height) throw new Error(`${path} 不是可识别的 PNG 或 JPEG 图片`);
  const ratio = size.width / size.height;
  if (Math.abs(ratio - 16 / 9) > 0.01) throw new Error(`${path} 必须是 16:9，实际为 ${size.width}x${size.height}`);
  return { type, ...size };
}

export async function composeAiImageDeck(outline, recipe, assets) {
  if (outline.mode && outline.mode !== 'ai-image') throw new Error('ai-image mode required');
  if (assets.length !== outline.slides.length) throw new Error('每一页都必须有一张完整页面图片');
  const embedded = {};
  const slides = [];
  for (const [index, source] of outline.slides.entries()) {
    const path = assets[index];
    const key = `slide-${source.id}`;
    const buffer = await readFile(path);
    const raster = inspectRaster(buffer, path);
    embedded[key] = `data:${raster.type};base64,${buffer.toString('base64')}`;
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
