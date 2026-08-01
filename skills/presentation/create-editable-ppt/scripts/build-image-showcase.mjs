#!/usr/bin/env node
import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const skillRoot = resolve(scriptDir, '..');
const cli = join(scriptDir, 'ppt.mjs');
const themesPath = join(skillRoot, 'assets', 'themes', 'image-themes.json');

function flag(args, name, fallback) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
}

function runCli(args) {
  const result = spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr.trim() || result.stdout.trim() || `CLI failed: ${args.join(' ')}`);
}

const args = process.argv.slice(2);
if (!args.includes('--prepare')) {
  console.error('Usage: node scripts/build-image-showcase.mjs --prepare --root <dir>');
  process.exitCode = 1;
} else {
  const root = resolve(flag(args, '--root', join(skillRoot, 'assets', 'examples', 'image-theme-showcase')));
  await mkdir(root, { recursive: true });
  runCli(['draft', root, '--title', 'AI 原生知识工作流']);
  const draftPath = join(root, 'outline_draft.json');
  const previewPath = join(root, 'outline_preview.html');
  const themes = JSON.parse(await readFile(themesPath, 'utf8'));
  const catalog = {
    format: 'image-theme-showcase',
    version: 1,
    title: 'AI 原生知识工作流 · 八种主题对照',
    central_message: JSON.parse(await readFile(draftPath, 'utf8')).central_message,
    slides_per_theme: 3,
    themes: [],
  };
  for (const id of Object.keys(themes)) {
    const projectRelative = join('themes', id);
    const project = join(root, projectRelative);
    await mkdir(project, { recursive: true });
    await copyFile(draftPath, join(project, 'outline_draft.json'));
    await copyFile(previewPath, join(project, 'outline_preview.html'));
    runCli(['approve', project, '--theme', id]);
    runCli(['prompts', project, '--model', 'gpt-image-2', '--size', '2048x1152', '--quality', 'medium']);
    catalog.themes.push({ id, label: themes[id].label, project: projectRelative, slides: 3 });
  }
  await writeFile(join(root, 'showcase.json'), `${JSON.stringify(catalog, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(catalog, null, 2));
}
