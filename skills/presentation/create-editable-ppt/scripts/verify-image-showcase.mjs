#!/usr/bin/env node
import { mkdir, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { chromium } from 'playwright';

function flag(args, name, fallback) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
}

const root = resolve(flag(process.argv.slice(2), '--root', '.'));
const baseUrl = flag(process.argv.slice(2), '--url', 'http://127.0.0.1:4190');
const catalog = JSON.parse(await (await import('node:fs/promises')).readFile(join(root, 'showcase.json'), 'utf8'));
const qaDir = join(root, 'qa');
await mkdir(join(qaDir, 'screenshots'), { recursive: true });
const browser = await chromium.launch({ headless: true });
const findings = [];
try {
  const gallery = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 });
  await gallery.goto(`${baseUrl}/index.html`, { waitUntil: 'networkidle' });
  await gallery.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await gallery.waitForTimeout(300);
  await gallery.evaluate(() => window.scrollTo(0, 0));
  await gallery.screenshot({ path: join(root, 'gallery-desktop.png'), fullPage: true });
  const desktop = await gallery.evaluate(() => ({
    cards: document.querySelectorAll('.slide-card').length,
    images: [...document.images].map((image) => ({ complete: image.complete, width: image.naturalWidth })),
    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  }));
  findings.push({ surface: 'gallery-desktop', ...desktop });
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  await mobile.goto(`${baseUrl}/index.html`, { waitUntil: 'networkidle' });
  await mobile.screenshot({ path: join(root, 'gallery-mobile.png'), fullPage: true });
  findings.push({ surface: 'gallery-mobile', ...(await mobile.evaluate(() => ({ overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth, cards: document.querySelectorAll('.slide-card').length }))) });
  await mobile.close();
  for (const theme of catalog.themes) {
    const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
    await page.goto(`${baseUrl}/${theme.project}/index.html`, { waitUntil: 'networkidle' });
    const pageCheck = await page.evaluate(() => ({
      slides: document.querySelectorAll('.slide').length,
      active: document.querySelectorAll('.slide.active').length,
      imageWidth: document.querySelector('.slide.active img')?.naturalWidth ?? 0,
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    }));
    for (let index = 0; index < 3; index += 1) {
      if (index > 0) await page.locator('#next').click();
      const current = await page.locator('.slide.active').getAttribute('data-slide');
      if (current !== String(index)) throw new Error(`${theme.id} did not advance to slide ${index}`);
    }
    findings.push({ surface: `deck-${theme.id}`, ...pageCheck, navigation: 'pass' });
    await page.close();
    const bundle = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
    await bundle.goto(`${baseUrl}/${theme.project}/dist/presentation.image-ppt.html`, { waitUntil: 'networkidle' });
    const bundleCheck = await bundle.evaluate(() => ({
      slides: document.querySelectorAll('.slide').length,
      imageWidth: document.querySelector('.slide.active img')?.naturalWidth ?? 0,
      embedded: document.querySelector('#image-ppt-doc')?.textContent.includes('data:image/png;base64,') ?? false,
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    }));
    for (let index = 0; index < 3; index += 1) {
      if (index > 0) await bundle.locator('#next').click();
      const current = await bundle.locator('.slide.active').getAttribute('data-slide');
      if (current !== String(index)) throw new Error(`bundle ${theme.id} did not advance to slide ${index}`);
    }
    findings.push({ surface: `bundle-${theme.id}`, ...bundleCheck, navigation: 'pass' });
    await bundle.close();
  }
} finally {
  await browser.close();
}
const blocking = findings.filter((item) => {
  if (item.overflow) return true;
  if (item.surface.startsWith('gallery')) return item.cards === 0 || item.images?.some((image) => !image.complete || image.width === 0);
  return item.slides !== 3 || item.imageWidth === 0 || (item.surface.startsWith('bundle-') && !item.embedded);
});
const report = { schema_version: 1, viewport: { desktop: [1600, 1000], mobile: [390, 844] }, findings, blocking };
await writeFile(join(root, 'gallery-qa.json'), `${JSON.stringify(report, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(report, null, 2));
if (blocking.length) process.exitCode = 2;
