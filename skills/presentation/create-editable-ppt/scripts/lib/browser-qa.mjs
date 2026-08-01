import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

import { writeTextAtomic } from './storage.mjs';

const require = createRequire(import.meta.url);

async function loadPlaywright() {
  try { return await import('playwright'); } catch {
    try { return require('playwright'); } catch { return null; }
  }
}

function item(code, severity, slideId, message, details = {}) {
  return { code, severity, slide_id: slideId, message, ...details };
}

export function classifyGeometry(snapshot) {
  const findings = [];
  if (!snapshot.text.trim()) findings.push(item('layout.blank', 'blocking', snapshot.slide_id, 'Slide has no visible text.'));
  if (snapshot.scroll_width > snapshot.client_width || snapshot.scroll_height > snapshot.client_height) findings.push(item('layout.overflow', 'blocking', snapshot.slide_id, 'Slide content exceeds its fixed canvas.'));
  if (snapshot.off_canvas.length) findings.push(item('layout.off_canvas', 'blocking', snapshot.slide_id, 'Visible elements extend outside the slide canvas.', { elements: snapshot.off_canvas }));
  if (snapshot.broken_media.length) findings.push(item('media.broken', 'blocking', snapshot.slide_id, 'One or more images failed to load.', { assets: snapshot.broken_media }));
  if (snapshot.collisions.length) findings.push(item('layout.collision', 'warning', snapshot.slide_id, 'Editable text elements overlap.', { pairs: snapshot.collisions }));
  return findings;
}

export async function createBrowserCheck(root, options = {}) {
  return async function browserCheck(project) {
    const loaded = await (options.loadPlaywright ?? loadPlaywright)();
    if (!loaded) return { mode: 'degraded', findings: [{ code: 'browser.qa.unavailable', severity: 'degraded', message: 'Playwright is not installed; geometry QA was not run.' }] };
    const chromium = loaded.chromium ?? loaded.default?.chromium;
    const browser = await chromium.launch({ headless: true });
    const screenshotDir = join(root, 'qa', 'screenshots');
    await mkdir(screenshotDir, { recursive: true });
    const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
    const findings = [];
    const screenshots = [];
    try {
      await page.goto(pathToFileURL(join(root, 'index.html')).href, { waitUntil: 'load' });
      await page.evaluate(() => document.fonts?.ready);
      for (const [index, slide] of project.deck.slides.filter((item) => !item.skipped).entries()) {
        await page.evaluate((id) => {
          for (const node of document.querySelectorAll('.slide')) node.classList.toggle('is-active', node.dataset.slideId === id);
        }, slide.id);
        const snapshot = await page.locator(`.slide[data-slide-id="${slide.id}"]`).evaluate((node) => {
          const bounds = node.getBoundingClientRect();
          const candidates = [...node.querySelectorAll('.editable')].filter((item) => {
            const rect = item.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
          });
          const offCanvas = [...node.querySelectorAll('*')].filter((item) => {
            const style = getComputedStyle(item);
            if (style.display === 'none' || style.visibility === 'hidden') return false;
            const rect = item.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && (rect.left < bounds.left - 1 || rect.top < bounds.top - 1 || rect.right > bounds.right + 1 || rect.bottom > bounds.bottom + 1);
          }).slice(0, 12).map((item) => item.dataset.field || item.className || item.tagName);
          const collisions = [];
          for (let a = 0; a < candidates.length; a += 1) for (let b = a + 1; b < candidates.length; b += 1) {
            const one = candidates[a].getBoundingClientRect(); const two = candidates[b].getBoundingClientRect();
            const overlap = Math.max(0, Math.min(one.right, two.right) - Math.max(one.left, two.left)) * Math.max(0, Math.min(one.bottom, two.bottom) - Math.max(one.top, two.top));
            if (overlap > 80) collisions.push([candidates[a].dataset.field, candidates[b].dataset.field]);
          }
          return {
            slide_id: node.dataset.slideId, text: node.innerText, scroll_width: node.scrollWidth, scroll_height: node.scrollHeight,
            client_width: node.clientWidth, client_height: node.clientHeight, off_canvas: offCanvas,
            broken_media: [...node.querySelectorAll('img')].filter((image) => !image.complete || image.naturalWidth === 0).map((image) => image.dataset.assetId || image.src),
            collisions,
          };
        });
        findings.push(...classifyGeometry(snapshot));
        const filename = `${String(index + 1).padStart(2, '0')}-${slide.id}.png`;
        await page.locator(`.slide[data-slide-id="${slide.id}"]`).screenshot({ path: join(screenshotDir, filename) });
        screenshots.push(filename);
      }
      await page.setViewportSize({ width: 390, height: 844 });
      await page.evaluate(() => window.dispatchEvent(new Event('resize')));
      await page.waitForTimeout(50);
      const mobileVisible = await page.evaluate(() => {
        const slide = document.querySelector('.slide.is-active')?.getBoundingClientRect();
        const viewport = document.querySelector('.viewport')?.getBoundingClientRect();
        return Boolean(slide && viewport && slide.width > 20 && slide.height > 20 && slide.right > viewport.left && slide.left < viewport.right && slide.bottom > viewport.top && slide.top < viewport.bottom);
      });
      if (!mobileVisible) findings.push({ code: 'mobile.canvas.blank', severity: 'blocking', message: 'The active slide is not visible in the mobile editor viewport.' });
      await page.screenshot({ path: join(root, 'qa', 'mobile-editor.png'), fullPage: false });
      const contact = `<!doctype html><meta charset="utf-8"><title>QA contact sheet</title><style>body{font:14px system-ui;margin:24px;background:#eee}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:18px}figure{margin:0;background:white;padding:10px}img{width:100%;display:block}figcaption{padding-top:8px}</style><main>${screenshots.map((file) => `<figure><img src="screenshots/${file}" alt="${file}"><figcaption>${file}</figcaption></figure>`).join('')}</main>`;
      await writeTextAtomic(join(root, 'qa', 'contact-sheet.html'), contact);
      return { mode: 'browser', findings, artifacts: { screenshots: screenshotDir, contact_sheet: join(root, 'qa', 'contact-sheet.html'), mobile: join(root, 'qa', 'mobile-editor.png') } };
    } finally {
      await browser.close();
    }
  };
}
