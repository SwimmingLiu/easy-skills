#!/usr/bin/env node
import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';

import { composeAiImageDeck, compileImageJobs } from './lib/ai-image.mjs';
import { parseBentoDocument, spliceBentoDocument } from './lib/bento-document.mjs';
import { composeHtmlDeck } from './lib/html-composer.mjs';
import { approveOutline, createOutline, validateOutline } from './lib/outline.mjs';
import { loadThemeCatalog, resolveThemeRecipe } from './lib/theme-catalog.mjs';

const skillRoot = resolve(new URL('..', import.meta.url).pathname);
const shellPath = join(skillRoot, 'assets', 'bento', 'Bento_Slides.bento.html');
const HELP = `storyweave

Commands:
  draft <dir> [--title text]
  themes --mode ai-image|html [--json]
  approve <dir> --mode ai-image|html --theme id
  prompts <dir>
  build <dir> [--out file]
  qa <dir> [--json]
  doctor [--json]
`;

const flag = (args, name, fallback) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
};
const readJson = async path => JSON.parse(await readFile(path, 'utf8'));
const writeJson = async (path, value) => writeFile(path, `${JSON.stringify(value, null, 2)}\n`);
const exists = path => access(path).then(() => true, () => false);

async function recipeFor(mode, id) {
  const catalog = await loadThemeCatalog();
  const recipe = resolveThemeRecipe(catalog, mode, id);
  if (!recipe) throw new Error(`未知 ${mode} 主题：${id || '未提供'}`);
  return recipe;
}

async function main(args) {
  const command = args[0];
  if (!command || ['help','-h','--help'].includes(command)) { console.log(HELP); return; }
  if (command === 'themes') {
    const mode = flag(args, '--mode');
    const catalog = await loadThemeCatalog();
    if (!catalog[mode]) throw new Error('themes 需要 --mode ai-image|html');
    const rows = catalog[mode].map(({ id, name, composition, density, provenance }) => ({ id, name, composition, density, provenance }));
    console.log(args.includes('--json') ? JSON.stringify(rows) : rows.map(row => `${row.id}\t${row.name}\t${row.composition}`).join('\n'));
    return;
  }
  if (command === 'doctor') {
    const shell = await readFile(shellPath, 'utf8');
    const blocks = (shell.match(/id="bento-doc"/g) || []).length;
    const report = { node: process.versions.node, supported: Number(process.versions.node.split('.')[0]) >= 20, bento_shell: blocks === 1, imagegen_cli_key_configured: Boolean(process.env.OPENAI_API_KEY) };
    console.log(JSON.stringify(report, null, args.includes('--json') ? 0 : 2));
    if (!report.supported || !report.bento_shell) process.exitCode = 1;
    return;
  }
  const root = resolve(args[1] || '.');
  if (command === 'draft') {
    await mkdir(root, { recursive: true });
    const outline = createOutline(flag(args, '--title', 'AI 原生知识工作流'));
    await writeJson(join(root, 'outline_draft.json'), outline);
    console.log(join(root, 'outline_draft.json'));
    return;
  }
  if (command === 'approve') {
    const outline = await readJson(join(root, 'outline_draft.json'));
    const mode = flag(args, '--mode');
    const theme = flag(args, '--theme');
    const recipe = await recipeFor(mode, theme);
    const approved = {
      ...approveOutline(outline, { mode, theme: recipe.id }),
      ...(theme !== recipe.id ? { theme_alias: theme } : {}),
    };
    await writeJson(join(root, 'deck_spec.json'), approved);
    console.log(join(root, 'deck_spec.json'));
    return;
  }
  if (command === 'prompts') {
    const deck = await readJson(join(root, 'deck_spec.json'));
    if (deck.mode !== 'ai-image') throw new Error('prompts 只用于 ai-image 模式');
    const jobs = compileImageJobs(deck, await recipeFor(deck.mode, deck.theme));
    await writeFile(join(root, 'imagegen-jobs.jsonl'), `${jobs.map(job => JSON.stringify(job)).join('\n')}\n`);
    console.log(join(root, 'imagegen-jobs.jsonl'));
    return;
  }
  if (command === 'build') {
    const deck = await readJson(join(root, 'deck_spec.json'));
    const recipe = await recipeFor(deck.mode, deck.theme);
    let doc;
    if (deck.mode === 'html') {
      doc = composeHtmlDeck(deck, recipe);
    } else {
      const jobsPath = join(root, 'imagegen-jobs.jsonl');
      if (!await exists(jobsPath)) throw new Error('缺少 imagegen-jobs.jsonl，请先运行 prompts');
      const jobs = (await readFile(jobsPath, 'utf8')).trim().split('\n').filter(Boolean).map(JSON.parse);
      const assets = jobs.map(job => join(root, job.out));
      const missing = [];
      for (const path of assets) if (!await exists(path)) missing.push(path);
      if (missing.length) throw new Error(`缺少完整页面图片：${missing.join(', ')}`);
      doc = await composeAiImageDeck(deck, recipe, assets);
    }
    const shell = await readFile(shellPath, 'utf8');
    const out = resolve(flag(args, '--out', join(root, `${deck.title}.bento.html`)));
    await writeFile(out, spliceBentoDocument(shell, doc));
    console.log(out);
    return;
  }
  if (command === 'qa') {
    const deck = await readJson(join(root, 'deck_spec.json'));
    const outlineCheck = validateOutline(deck);
    const target = flag(args, '--file', join(root, `${deck.title}.bento.html`));
    const findings = [...outlineCheck.errors];
    let doc;
    if (!await exists(target)) findings.push('缺少 .bento.html 主文件');
    else {
      doc = parseBentoDocument(await readFile(target, 'utf8'));
      if (doc.slides.length !== deck.page_count) findings.push('Bento 页数与草稿不一致');
      for (const [index, slide] of doc.slides.entries()) {
        if (!slide.notes) findings.push(`第 ${index + 1} 页缺少备注`);
        if (deck.mode === 'ai-image' && (slide.elements.length !== 1 || slide.elements[0].type !== 'image')) findings.push(`第 ${index + 1} 页不是单一完整图片`);
        if (deck.mode === 'html' && slide.elements.some(el => el.type === 'image' && el.x === 0 && el.y === 0 && el.w >= 1280 && el.h >= 720)) findings.push(`第 ${index + 1} 页含整页栅格图片`);
      }
    }
    const report = { valid: findings.length === 0, mode: deck.mode, theme: deck.theme, page_count: doc?.slides.length || 0, findings };
    await writeJson(join(root, 'qa_report.json'), report);
    console.log(args.includes('--json') ? JSON.stringify(report) : report.valid ? 'PASS' : findings.join('\n'));
    if (!report.valid) process.exitCode = 1;
    return;
  }
  throw new Error(`未知命令：${command}`);
}

main(process.argv.slice(2)).catch(error => { console.error(error.message); process.exitCode = 1; });
