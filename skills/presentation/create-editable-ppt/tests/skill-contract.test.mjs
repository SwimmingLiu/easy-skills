import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const skillUrl = new URL('../SKILL.md', import.meta.url);
const metadataUrl = new URL('../agents/openai.yaml', import.meta.url);

test('skill exposes only Bento-native ai-image and html modes', async () => {
  const skill = await readFile(skillUrl, 'utf8');
  assert.match(skill, /name:\s*storyweave/);
  assert.match(skill, /# Storyweave/);
  assert.match(skill, /ai-image/);
  assert.match(skill, /`html`/);
  assert.match(skill, /#bento-doc/);
  assert.match(skill, /bento\/slides/);
  assert.doesNotMatch(skill, /image-first|pure-html|image-ppt-doc|business-minimal|premium-dark/);
});

test('agent metadata routes presentation requests to the Bento master workflow', async () => {
  const metadata = await readFile(metadataUrl, 'utf8');
  assert.match(metadata, /Storyweave/);
  assert.match(metadata, /\$storyweave/);
  assert.match(metadata, /Bento/);
  assert.match(metadata, /ai-image/);
  assert.match(metadata, /html/);
  assert.doesNotMatch(metadata, /image-first|pure-html|HTML-assisted/);
});
