import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');

test('skill contract exposes mutually exclusive image-first and pure HTML modes', async () => {
  const skill = await readFile(join(root, 'SKILL.md'), 'utf8');
  assert.match(skill, /name: create-image-ppt/);
  assert.match(skill, /description: Use when/);
  assert.match(skill, /REQUIRED SUB-SKILL.*imagegen/);
  assert.match(skill, /中心含义/);
  assert.match(skill, /叙事逻辑/);
  assert.match(skill, /outline_preview\.html/);
  assert.match(skill, /草稿未确认.*不得.*生图/s);
  assert.match(skill, /整页图片/);
  assert.match(skill, /image-first/);
  assert.match(skill, /pure-html/);
  assert.match(skill, /不调用 imagegen/);
  assert.match(skill, /纯 HTML/);
  assert.doesNotMatch(skill, /html-image-assisted/);
  assert.doesNotMatch(skill, /contenteditable|browser-editable|默认保留文字.*可编辑/s);
});

test('agent metadata routes requests to the image-first workflow', async () => {
  const metadata = await readFile(join(root, 'agents', 'openai.yaml'), 'utf8');
  assert.match(metadata, /Create Image PPT/);
  assert.match(metadata, /\$create-image-ppt/);
  assert.doesNotMatch(metadata, /editable|可编辑/i);
});
