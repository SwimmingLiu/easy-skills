#!/usr/bin/env node
import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

function flag(args, name, fallback) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
}

const skillRoot = fileURLToPath(new URL('..', import.meta.url));
const root = resolve(flag(process.argv.slice(2), '--root', join(skillRoot, 'assets', 'examples', 'image-theme-showcase')));
const catalog = JSON.parse(await readFile(join(root, 'showcase.json'), 'utf8'));
const roleSource = { cover: '01-s01.png', process: '04-s04.png', closing: '06-s06.png' };
const sourceRoot = join(skillRoot, 'assets', 'examples', 'theme-showcase', 'decks');

for (const theme of catalog.themes) {
  const project = join(root, theme.project);
  const manifestPath = join(project, 'generation_manifest.json');
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  await mkdir(join(project, 'slides'), { recursive: true });
  for (const slide of manifest.slides) {
    const source = join(sourceRoot, theme.id, 'qa', 'screenshots', roleSource[slide.role] ?? '01-s01.png');
    const target = join(project, slide.output_path);
    await copyFile(source, target);
    slide.status = 'generated';
    slide.attempts = 0;
    slide.error = null;
    slide.source_kind = 'existing-theme-showcase-fallback';
    slide.source_path = `assets/examples/theme-showcase/decks/${theme.id}/qa/screenshots/${roleSource[slide.role] ?? '01-s01.png'}`;
  }
  manifest.provider = 'existing-theme-showcase-fallback';
  manifest.fallback = true;
  manifest.fallback_reason = 'imagegen CLI returned no active plan and the fallback channel was blocked; replace these images by rerunning the same jobs with configured imagegen.';
  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
}

const notice = `# Imagegen fallback notice

The 24 requested imagegen jobs were prepared but could not run in the current environment: the primary channel returned \`403 no active plan\`, and the fallback channel was blocked. This showcase therefore uses existing, local theme-showcase screenshots as a temporary visual fallback.

These PNGs are marked \`existing-theme-showcase-fallback\` in each \`generation_manifest.json\`. They are complete slide images and preserve the shared three-page narrative, but they are not claimed as fresh imagegen output. Configure an active imagegen plan, then rerun the \`imagegen-jobs.jsonl\` files into each theme's \`slides/\` directory and run \`node scripts/ppt.mjs render <project>\` plus \`node scripts/build-image-gallery.mjs --root <showcase>\`.
`;
await writeFile(join(root, 'imagegen-fallback-notice.md'), notice, 'utf8');
console.log(join(root, 'imagegen-fallback-notice.md'));
