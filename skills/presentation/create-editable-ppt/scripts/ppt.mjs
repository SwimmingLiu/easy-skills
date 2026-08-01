#!/usr/bin/env node
import { createRequire } from 'node:module';
import { access, copyFile, mkdir, readFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import {
  approveOutlineDraft,
  compileDeckPrompts,
  createGenerationManifest,
  renderImageDeck,
  renderOutlinePreview,
  validateOutlineDraft,
} from './lib/image-first.mjs';
import { buildBundledImageDeck } from './lib/bundle.mjs';
import { writeJsonAtomic, writeTextAtomic } from './lib/storage.mjs';

const require = createRequire(import.meta.url);
const skillRoot = resolve(fileURLToPath(new URL('..', import.meta.url)));
const themesPath = join(skillRoot, 'assets', 'themes', 'image-themes.json');

const HELP = `create-image-ppt

Commands:
  draft <dir> [--title text]
  approve <dir> --theme theme-id
  prompts <dir> [--model name] [--size WxH] [--quality low|medium|high|auto]
  render <dir>
  qa <dir> [--json]
  bundle <dir> [--out file]
  export <dir> --format html|png|pdf|pptx
  doctor [--json]
`;

function flag(args, name, fallback = undefined) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
}

async function readJson(path) {
  return JSON.parse(await readFile(path, 'utf8'));
}

async function exists(path) {
  return access(path).then(() => true, () => false);
}

function defaultDraft(title) {
  return {
    schema_version: 1,
    status: 'draft',
    title,
    audience: '产品团队、知识工作者与组织管理者',
    purpose: '说明 AI 原生知识工作流的核心变化与行动路径',
    central_message: '让散落的信息和判断沿着工作流持续产生价值',
    narrative: {
      opening: '从信息越来越多、理解却更碎片化的日常感受切入',
      problem: '资料、判断与行动分散在不同工具和短期记忆中',
      insight: '真正需要保存的不是文件数量，而是可复用的上下文',
      method: '通过收集现场、建立关联、形成判断、推进行动形成闭环',
      action: '先选择一条高频流程，把上下文、判断和行动连起来',
    },
    slides: [
      { id: 's01', role: 'cover', content_kind: 'image', purpose: '建立主题和核心判断', claim: 'AI 原生知识工作流', exact_text: ['AI 原生知识工作流', '把散落信息变成持续可用的判断'], evidence: [], media_brief: '城市、网络与知识流动形成的克制视觉意象', transition: '从愿景进入现实中的信息碎片化问题' },
      { id: 's02', role: 'process', content_kind: 'flow', purpose: '解释形成持续价值的方法', claim: '四个动作，让信息持续产生价值', exact_text: ['四个动作，让信息持续产生价值', '收集现场', '建立关联', '形成判断', '推进行动'], evidence: [], media_brief: '四个连续动作形成清晰的单向流程，不使用数据图表', transition: '从方法转向一条可以立即开始的流程' },
      { id: 's03', role: 'closing', content_kind: 'image', purpose: '给出明确行动建议', claim: '先重做一条高频流程', exact_text: ['先重做一条高频流程', '把上下文、判断和行动连起来'], evidence: [], media_brief: '专注工作、开始行动和持续推进的真实场景', transition: '结束' },
    ],
  };
}

async function writePromptJobs(root, jobs) {
  const lines = jobs.map((job) => JSON.stringify({
    prompt: job.prompt,
    model: job.model,
    size: job.size,
    quality: job.quality,
    use_case: job.use_case,
    out: job.out,
  })).join('\n');
  await writeTextAtomic(join(root, 'imagegen-jobs.jsonl'), `${lines}\n`);
}

async function refreshManifestFromFiles(root, manifest) {
  for (const slide of manifest.slides) {
    if (await exists(join(root, slide.output_path))) {
      slide.status = slide.status === 'pass' ? 'pass' : 'generated';
      slide.attempts = Math.max(1, slide.attempts ?? 0);
      slide.error = null;
    }
  }
  return manifest;
}

async function optional(name) {
  try { return await import(name); } catch {
    try { return require(name); } catch { return null; }
  }
}

async function exportImageDeck(root, format) {
  const deck = await readJson(join(root, 'deck_spec.json'));
  const manifest = await refreshManifestFromFiles(root, await readJson(join(root, 'generation_manifest.json')));
  const missing = manifest.slides.filter((slide) => !['generated', 'pass'].includes(slide.status));
  if (missing.length) throw new Error(`Missing generated slide images: ${missing.map((slide) => slide.id).join(', ')}`);
  const dist = join(root, 'dist');
  await mkdir(dist, { recursive: true });
  if (format === 'html') {
    await copyFile(join(root, 'index.html'), join(dist, 'presentation.html'));
    return [join(dist, 'presentation.html')];
  }
  if (format === 'png') {
    const files = [];
    for (const [index, slide] of manifest.slides.entries()) {
      const target = join(dist, `${String(index + 1).padStart(2, '0')}-${slide.id}.png`);
      await copyFile(join(root, slide.output_path), target);
      files.push(target);
    }
    return files;
  }
  if (format === 'pptx') {
    const loaded = await optional('pptxgenjs');
    if (!loaded) throw new Error('PptxGenJS is required for image-only PPTX export. Run npm install in scripts/.');
    const PptxGenJS = loaded.default ?? loaded;
    const pptx = new PptxGenJS();
    pptx.layout = 'LAYOUT_WIDE';
    pptx.author = 'create-image-ppt';
    pptx.title = deck.title;
    pptx.subject = deck.purpose;
    for (const slide of manifest.slides) {
      const page = pptx.addSlide();
      page.addImage({ path: join(root, slide.output_path), x: 0, y: 0, w: 13.333, h: 7.5 });
      const source = deck.slides.find((item) => item.id === slide.id);
      if (source) page.addNotes?.(`${source.claim}\n${source.exact_text.join('\n')}`);
    }
    const target = join(dist, 'presentation.pptx');
    await pptx.writeFile({ fileName: target });
    return [target];
  }
  if (format === 'pdf') {
    const loaded = await optional('playwright');
    if (!loaded) throw new Error('Playwright is required for PDF export. Run npm install in scripts/.');
    const chromium = loaded.chromium ?? loaded.default?.chromium;
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
    try {
      await page.goto(pathToFileURL(join(root, 'index.html')).href, { waitUntil: 'load' });
      await page.addStyleTag({ content: '.slide{display:block!important;page-break-after:always;width:1600px!important;height:900px!important}.deck{display:block!important;height:auto!important}button,.slide span{display:none!important}' });
      const target = join(dist, 'presentation.pdf');
      await page.pdf({ path: target, width: '1600px', height: '900px', printBackground: true });
      return [target];
    } finally {
      await browser.close();
    }
  }
  throw new Error(`Unsupported export format: ${format}`);
}

async function main(args) {
  const command = args[0];
  if (!command || ['--help', '-h', 'help'].includes(command)) { console.log(HELP); return 0; }
  if (command === 'doctor') {
    const major = Number(process.versions.node.split('.')[0]);
    const standard = Boolean(process.env.OPENAI_API_KEY);
    const primary = ['OPENAI_SUB_BASE_URL', 'OPENAI_SUB_KEY', 'OPENAI_SUB_IMAGE_MODEL'].every((name) => Boolean(process.env[name]));
    const fallback = ['OPENAI_SUB_FALLBAK_BASE_URL', 'OPENAI_SUB_FALLBAK_KEY', 'OPENAI_SUB_FALLBAK_IMAGE_MODEL'].every((name) => Boolean(process.env[name]));
    const report = {
      node: { version: process.versions.node, supported: major >= 20 },
      imagegen: {
        built_in: 'host-dependent',
        cli_key_configured: standard || primary || fallback,
        configuration: { standard_openai: standard, primary_sub: primary, fallback_sub: fallback },
        setup: 'Configure image-generation keys locally. Never paste or persist key values in chat, prompts, logs, or project files.',
      },
    };
    console.log(JSON.stringify(report, null, args.includes('--json') ? 0 : 2));
    return report.node.supported ? 0 : 1;
  }
  const root = resolve(args[1] ?? '.');
  if (command === 'draft') {
    await mkdir(root, { recursive: true });
    const draft = defaultDraft(flag(args, '--title', 'AI 原生知识工作流'));
    await writeJsonAtomic(join(root, 'outline_draft.json'), draft);
    await writeTextAtomic(join(root, 'outline_preview.html'), renderOutlinePreview(draft));
    console.log(join(root, 'outline_preview.html'));
    return 0;
  }
  if (command === 'approve') {
    const draft = await readJson(join(root, 'outline_draft.json'));
    const themeId = flag(args, '--theme');
    const themes = await readJson(themesPath);
    if (!themes[themeId]) throw new Error(`Unknown image theme: ${themeId ?? 'missing'}`);
    const deck = approveOutlineDraft(draft, themeId);
    await writeJsonAtomic(join(root, 'deck_spec.json'), deck);
    console.log(join(root, 'deck_spec.json'));
    return 0;
  }
  if (command === 'prompts') {
    const deck = await readJson(join(root, 'deck_spec.json'));
    const themes = await readJson(themesPath);
    const jobs = compileDeckPrompts(deck, themes, {
      model: flag(args, '--model', 'gpt-image-2'),
      size: flag(args, '--size', '2048x1152'),
      quality: flag(args, '--quality', 'medium'),
    });
    const manifest = createGenerationManifest(deck, jobs, { provider: 'imagegen-cli' });
    await mkdir(join(root, 'slides'), { recursive: true });
    await writeJsonAtomic(join(root, 'generation_manifest.json'), manifest);
    await writePromptJobs(root, jobs);
    console.log(`${jobs.length} image jobs prepared`);
    return 0;
  }
  if (command === 'render') {
    const deck = await readJson(join(root, 'deck_spec.json'));
    const manifest = await refreshManifestFromFiles(root, await readJson(join(root, 'generation_manifest.json')));
    const missing = manifest.slides.filter((slide) => !['generated', 'pass'].includes(slide.status));
    if (missing.length) throw new Error(`Missing generated slide images: ${missing.map((slide) => slide.id).join(', ')}`);
    await writeJsonAtomic(join(root, 'generation_manifest.json'), manifest);
    await writeTextAtomic(join(root, 'index.html'), renderImageDeck(deck, manifest));
    console.log(join(root, 'index.html'));
    return 0;
  }
  if (command === 'qa') {
    const draft = await readJson(join(root, 'outline_draft.json'));
    const manifest = await refreshManifestFromFiles(root, await readJson(join(root, 'generation_manifest.json')));
    const outline = validateOutlineDraft(draft);
    const missing = manifest.slides.filter((slide) => !['generated', 'pass'].includes(slide.status));
    const report = {
      schema_version: 1,
      export_ready: outline.valid && missing.length === 0,
      summary: { blocking: outline.errors.length + missing.length, warning: 0 },
      findings: [...outline.errors, ...missing.map((slide) => ({ path: `slides.${slide.id}`, message: 'generated image is missing' }))],
    };
    await writeJsonAtomic(join(root, 'qa_report.json'), report);
    console.log(JSON.stringify(report, null, args.includes('--json') ? 0 : 2));
    return report.export_ready ? 0 : 2;
  }
  if (command === 'bundle') {
    const deck = await readJson(join(root, 'deck_spec.json'));
    const manifest = await refreshManifestFromFiles(root, await readJson(join(root, 'generation_manifest.json')));
    const missing = manifest.slides.filter((slide) => !['generated', 'pass'].includes(slide.status));
    if (missing.length) throw new Error(`Missing generated slide images: ${missing.map((slide) => slide.id).join(', ')}`);
    const dist = join(root, 'dist');
    await mkdir(dist, { recursive: true });
    const target = resolve(flag(args, '--out', join(dist, 'presentation.image-ppt.html')));
    await mkdir(join(target, '..'), { recursive: true });
    await writeTextAtomic(target, await buildBundledImageDeck(root, deck, manifest));
    console.log(target);
    return 0;
  }
  if (command === 'export') {
    const format = flag(args, '--format', 'html');
    if (!['html', 'png', 'pdf', 'pptx'].includes(format)) throw new Error(`Unsupported export format: ${format}`);
    if (!(await exists(join(root, 'index.html')))) throw new Error('Render the image deck before export.');
    const files = await exportImageDeck(root, format);
    const report = { schema_version: 1, format, output_mode: 'full-slide-image', editable_object_count: 0, files };
    await writeJsonAtomic(join(root, 'dist', 'export-report.json'), report);
    console.log(JSON.stringify(report, null, 2));
    return 0;
  }
  throw new Error(`Unknown command: ${command}`);
}

try {
  const code = await main(process.argv.slice(2));
  if (typeof code === 'number') process.exitCode = code;
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
