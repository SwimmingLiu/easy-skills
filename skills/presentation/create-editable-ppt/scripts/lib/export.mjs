import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

import { writeJsonAtomic } from './storage.mjs';

const require = createRequire(import.meta.url);

async function optional(name) {
  try {
    return await import(name);
  } catch {
    try {
      return require(name);
    } catch {
      return null;
    }
  }
}

function activeSlides(project) {
  return project.deck.slides.filter((slide) => !slide.skipped);
}

async function defaultBrowserAdapter(root, loadPlaywright = () => optional('playwright')) {
  const playwright = await loadPlaywright();
  if (!playwright) throw new Error('Playwright optional dependency is required for PDF and PNG export. Run npm install in scripts/.');
  const chromium = playwright.chromium ?? playwright.default?.chromium;
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(join(root, 'index.html')).href, { waitUntil: 'load' });
  return {
    pdf: async (path) => {
      await page.emulateMedia({ media: 'print' });
      await page.evaluate(() => document.body.classList.add('print-all'));
      await page.pdf({ path, width: '1600px', height: '900px', printBackground: true, preferCSSPageSize: true });
    },
    png: async (path, slide) => {
      await page.evaluate(() => {
        document.body.classList.add('presentation');
        window.dispatchEvent(new Event('resize'));
      });
      await page.evaluate((slideId) => {
        for (const node of document.querySelectorAll('.slide')) node.classList.toggle('is-active', node.dataset.slideId === slideId);
      }, slide.id);
      await page.locator(`.slide[data-slide-id="${slide.id}"]`).screenshot({ path });
    },
    close: () => browser.close(),
  };
}

function addText(slide, text, options) {
  if (text) slide.addText(Array.isArray(text) ? text : String(text), { margin: 0, breakLine: false, ...options });
}

async function captureFallbackSlides(root, slides) {
  const unsupported = slides.filter((slide) => slide.effects?.length);
  if (!unsupported.length) return new Map();
  const loaded = await optional('playwright');
  if (!loaded) throw new Error('Playwright optional dependency is required to rasterize unsupported PPTX effects.');
  const chromium = loaded.chromium ?? loaded.default?.chromium;
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  const paths = new Map();
  try {
    await page.goto(pathToFileURL(join(root, 'index.html')).href, { waitUntil: 'load' });
    await page.evaluate(() => { document.body.classList.add('presentation'); window.dispatchEvent(new Event('resize')); });
    for (const slide of unsupported) {
      await page.evaluate((id) => { for (const node of document.querySelectorAll('.slide')) node.classList.toggle('is-active', node.dataset.slideId === id); }, slide.id);
      const path = join(root, 'dist', `fallback-${slide.id}.png`);
      await page.locator(`.slide[data-slide-id="${slide.id}"]`).screenshot({ path });
      paths.set(slide.id, path);
    }
  } finally {
    await browser.close();
  }
  return paths;
}

async function defaultPptxAdapter({ path, slides, project, root }) {
  const loaded = await optional('pptxgenjs');
  if (!loaded) throw new Error('PptxGenJS optional dependency is required for editable PPTX export. Run npm install in scripts/.');
  const PptxGenJS = loaded.default ?? loaded;
  const pptx = new PptxGenJS();
  pptx.layout = project.deck.canvas === '4:3' ? 'LAYOUT_4X3' : 'LAYOUT_WIDE';
  pptx.author = 'create-editable-ppt';
  pptx.subject = project.deck.purpose;
  pptx.title = project.deck.title;
  let editable = 0;
  const fallback = [];
  const assetsById = new Map((project.assets?.assets ?? []).map((asset) => [asset.id, asset]));
  const fallbackImages = await captureFallbackSlides(root, slides);
  for (const source of slides) {
    const page = pptx.addSlide();
    page.background = { color: 'F7F6F2' };
    if (fallbackImages.has(source.id)) {
      page.addImage({ path: fallbackImages.get(source.id), x: 0, y: 0, w: 13.333, h: 7.5 });
      fallback.push(source.id);
      if (source.speaker_notes) page.addNotes?.(source.speaker_notes);
      continue;
    }
    addText(page, source.claim, { x: 0.65, y: 0.6, w: 11.9, h: 1.0, fontFace: 'Arial', fontSize: source.role === 'cover' ? 30 : 24, bold: true, color: '171917', fit: 'shrink' });
    editable += 1;
    const props = source.props ?? {};
    const supporting = props.subtitle ?? props.summary ?? props.caption ?? props.quote ?? props.action;
    if (supporting) {
      addText(page, supporting, { x: 0.8, y: 1.65, w: 6.0, h: 1.0, fontSize: 17, color: '606B76', fit: 'shrink' });
      editable += 1;
    }
    const lines = props.points ?? props.steps?.map((item) => item.title ?? item) ?? [];
    if (lines.length) {
      addText(page, lines.map((line) => ({ text: typeof line === 'string' ? line : line.text ?? line.title ?? '', options: { bullet: { indent: 14 } } })), { x: 0.8, y: 2.0, w: 6.0, h: 3.6, fontSize: 18, color: '30352F', breakLine: true, valign: 'top', fit: 'shrink' });
      editable += lines.length;
    }
    if (props.left?.length || props.right?.length) {
      addText(page, props.left_title ?? 'Left', { x: 0.8, y: 2.0, w: 5.5, h: 0.45, fontSize: 18, bold: true, color: '146C5A' });
      addText(page, (props.left ?? []).map((line) => ({ text: String(line), options: { bullet: { indent: 14 }, breakLine: true } })), { x: 0.8, y: 2.55, w: 5.5, h: 3.2, fontSize: 16, fit: 'shrink' });
      addText(page, props.right_title ?? 'Right', { x: 6.95, y: 2.0, w: 5.5, h: 0.45, fontSize: 18, bold: true, color: '205493' });
      addText(page, (props.right ?? []).map((line) => ({ text: String(line), options: { bullet: { indent: 14 }, breakLine: true } })), { x: 6.95, y: 2.55, w: 5.5, h: 3.2, fontSize: 16, fit: 'shrink' });
      editable += 2 + (props.left?.length ?? 0) + (props.right?.length ?? 0);
    }
    for (const metric of props.metrics ?? []) {
      addText(page, `${metric.value}\n${metric.label}`, { x: 0.9 + editable % 3 * 3.6, y: 2.3, w: 3.0, h: 1.5, fontSize: 20, bold: true, color: '146C5A', align: 'center', fit: 'shrink' });
      editable += 2;
    }
    const mediaId = props.image ?? source.media?.[0];
    const asset = assetsById.get(mediaId);
    if (asset?.path) {
      page.addImage({ path: join(root, asset.path), x: 7.0, y: 1.7, w: 5.5, h: 4.7 });
      editable += 1;
    }
    if (source.speaker_notes) page.addNotes?.(source.speaker_notes);
  }
  await pptx.writeFile({ fileName: path });
  return { editable_object_count: editable, fallback_slides: fallback };
}

export async function exportProject(root, project, format, options = {}) {
  const dist = join(root, 'dist');
  await mkdir(dist, { recursive: true });
  const slides = activeSlides(project);
  const report = {
    schema_version: 1,
    format,
    generated_at: new Date().toISOString(),
    active_slide_count: slides.length,
    files: [],
    editable_object_count: 0,
    fallback_slides: [],
  };

  if (format === 'pdf' || format === 'png') {
    const adapter = options.browserAdapter ?? await defaultBrowserAdapter(root, options.loadPlaywright);
    try {
      if (format === 'pdf') {
        const path = join(dist, 'presentation.pdf');
        await adapter.pdf(path);
        report.files.push(path);
      } else {
        for (const [index, slide] of slides.entries()) {
          const path = join(dist, `${String(index + 1).padStart(2, '0')}-${slide.id}.png`);
          await adapter.png(path, slide);
          report.files.push(path);
        }
      }
    } finally {
      await adapter.close?.();
    }
  } else if (format === 'pptx') {
    const path = join(dist, 'presentation.pptx');
    const result = await (options.pptxAdapter ?? defaultPptxAdapter)({ path, slides, project, root });
    report.files.push(path);
    report.editable_object_count = result.editable_object_count ?? 0;
    report.fallback_slides = result.fallback_slides ?? [];
  } else if (format === 'html') {
    const path = join(dist, 'presentation.html');
    await writeFile(path, await (await import('node:fs/promises')).readFile(join(root, 'index.html')));
    report.files.push(path);
  } else {
    throw new Error(`Unsupported export format: ${format}`);
  }
  await writeJsonAtomic(join(dist, 'export-report.json'), report);
  return report;
}
