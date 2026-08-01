#!/usr/bin/env node
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { writeJsonAtomic } from './lib/storage.mjs';

const require = createRequire(import.meta.url);

async function playwrightModule() {
  try { return await import('playwright'); } catch {
    try { return require('playwright'); } catch { throw new Error('Playwright is required to verify the theme showcase.'); }
  }
}

async function snapshot(page) {
  return page.evaluate(() => ({
    cards: document.querySelectorAll('.theme-card').length,
    broken_images: [...document.images].filter((image) => !image.complete || image.naturalWidth === 0).map((image) => image.src),
    horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    empty_titles: [...document.querySelectorAll('.theme-card h2')].filter((node) => !node.textContent.trim()).length,
  }));
}

export async function verifyThemeShowcase(root) {
  const playwright = await playwrightModule();
  const chromium = playwright.chromium ?? playwright.default?.chromium;
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const report = { schema_version: 1, generated_at: new Date().toISOString(), desktop: null, mobile: null, valid: false };
  try {
    await page.goto(pathToFileURL(resolve(root, 'index.html')).href, { waitUntil: 'load' });
    await page.waitForFunction(() => [...document.images].every((image) => image.complete));
    report.desktop = await snapshot(page);
    await page.screenshot({ path: resolve(root, 'gallery-desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(60);
    report.mobile = await snapshot(page);
    await page.screenshot({ path: resolve(root, 'gallery-mobile.png'), fullPage: true });
    report.valid = [report.desktop, report.mobile].every((item) => item.cards === 8 && item.broken_images.length === 0 && !item.horizontal_overflow && item.empty_titles === 0);
    await writeJsonAtomic(resolve(root, 'gallery-qa.json'), report);
    if (!report.valid) throw new Error(`Theme gallery QA failed: ${JSON.stringify(report)}`);
    return report;
  } finally {
    await browser.close();
  }
}

const root = resolve(process.argv[2] ?? fileURLToPath(new URL('../assets/examples/theme-showcase', import.meta.url)));
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  console.log(JSON.stringify(await verifyThemeShowcase(root), null, 2));
}
