import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const testDir = await fs.mkdtemp(path.join(os.tmpdir(), 'mermaid-correction-'));
const scriptDir = path.resolve(path.dirname(fileURLToPath(new URL('../scripts/validate-mermaid.mjs', import.meta.url))));
const scriptPath = path.join(scriptDir, 'validate-mermaid.mjs');

async function writeFixture(name, content) {
  const filePath = path.join(testDir, name);
  await fs.writeFile(filePath, content, 'utf8');
  return filePath;
}

function runValidator(filePath) {
  return spawnSync('node', [scriptPath, '--file', filePath], {
    cwd: scriptDir,
    encoding: 'utf8',
  });
}

const validPath = await writeFixture('valid.mmd', 'flowchart TD\n    A[Start] --> B[End]\n');
const invalidPath = await writeFixture('invalid.mmd', 'flowchart TD\n    A - > B\n');

const validRun = runValidator(validPath);
assert.equal(validRun.status, 0, `Expected valid Mermaid to pass. stderr=${validRun.stderr}`);
const validJson = JSON.parse(validRun.stdout);
assert.equal(validJson.valid, true);
assert.equal(validJson.diagramType, 'flowchart');

const invalidRun = runValidator(invalidPath);
assert.equal(invalidRun.status, 1, `Expected invalid Mermaid to fail. stderr=${invalidRun.stderr}`);
const invalidJson = JSON.parse(invalidRun.stdout);
assert.equal(invalidJson.valid, false);
assert.equal(invalidJson.diagramType, 'flowchart');
assert.equal(invalidJson.error.line, 2);
assert.ok(invalidJson.error.message.includes('Parse error on line 2'));
assert.ok(!invalidJson.error.message.includes('Parser3.parseError'));
assert.ok(invalidJson.error.expecting);
assert.equal(typeof invalidJson.error.column, 'number');

await fs.rm(testDir, { recursive: true, force: true });

console.log('All mermaid-correction validator tests passed.');
