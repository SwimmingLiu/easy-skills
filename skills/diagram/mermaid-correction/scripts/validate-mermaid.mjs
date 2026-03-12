import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { spawn } from 'node:child_process';

function printUsage() {
  console.error('Usage: node validate-mermaid.mjs [--file <path>]');
}

function getMmdcPath() {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  return path.resolve(scriptDir, 'node_modules', '.bin', process.platform === 'win32' ? 'mmdc.cmd' : 'mmdc');
}

function detectDiagramType(code) {
  const lines = code.split(/\r?\n/);
  let index = 0;

  if (lines[0]?.trim() === '---') {
    index = 1;
    while (index < lines.length && lines[index].trim() !== '---') {
      index += 1;
    }
    index += 1;
  }

  for (; index < lines.length; index += 1) {
    const line = lines[index].trim();
    if (!line || line.startsWith('%%')) {
      continue;
    }

    return line.split(/\s+/)[0] ?? null;
  }

  return null;
}

function stripFence(input) {
  const trimmed = input.trim();

  if (!trimmed.startsWith('```')) {
    return input;
  }

  const lines = trimmed.split(/\r?\n/);
  const firstLine = lines[0].trim().toLowerCase();
  const lastLine = lines.at(-1)?.trim();

  if ((firstLine === '```mermaid' || firstLine === '```') && lastLine === '```') {
    return lines.slice(1, -1).join('\n');
  }

  return input;
}

function extractExpecting(message) {
  const match = message.match(/Expecting\s+(.+?),\s+got\s+'([^']+)'/s);
  if (!match) {
    return { expecting: null, got: null };
  }

  return {
    expecting: match[1].trim(),
    got: match[2].trim(),
  };
}

function extractLine(message) {
  const lineMatch = message.match(/Parse error on line\s+(\d+):/i);
  return lineMatch ? Number(lineMatch[1]) : null;
}

function extractExcerpt(message) {
  const lines = message.split(/\r?\n/);
  const parseIndex = lines.findIndex((line) => /^Parse error on line\s+\d+:/i.test(line));

  if (parseIndex === -1) {
    return { excerpt: null, column: null };
  }

  const excerptLine = lines[parseIndex + 1] ?? null;
  const pointerLine = lines[parseIndex + 2] ?? null;
  const caretIndex = pointerLine ? pointerLine.indexOf('^') : -1;

  return {
    excerpt: excerptLine,
    column: caretIndex >= 0 ? caretIndex + 1 : null,
  };
}

function normalizeCliError(stderr) {
  const trimmed = stderr.trim();
  if (!trimmed) {
    return 'Mermaid CLI reported a validation failure without stderr output.';
  }

  const parseIndex = trimmed.indexOf('Parse error on line');
  if (parseIndex >= 0) {
    const parseBlock = trimmed.slice(parseIndex);
    const stackIndex = parseBlock.indexOf('\nParser');
    return stackIndex >= 0 ? parseBlock.slice(0, stackIndex) : parseBlock;
  }

  return trimmed;
}

async function runMmdc(inputFile, outputFile) {
  const mmdcPath = getMmdcPath();

  return new Promise((resolve, reject) => {
    const child = spawn(mmdcPath, ['-i', inputFile, '-o', outputFile], {
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    const timeout = setTimeout(() => {
      child.kill();
    }, 30000);

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString('utf8');
    });

    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString('utf8');
    });

    child.on('error', reject);
    child.on('close', (code) => {
      clearTimeout(timeout);
      resolve({ code: code ?? 1, stdout, stderr });
    });
  });
}

async function readInput(argv) {
  if (argv.length === 0) {
    if (process.stdin.isTTY) {
      printUsage();
      process.exit(1);
    }

    const chunks = [];
    for await (const chunk of process.stdin) {
      chunks.push(chunk);
    }
    return Buffer.concat(chunks).toString('utf8');
  }

  if (argv.length === 2 && argv[0] === '--file') {
    return fs.readFile(argv[1], 'utf8');
  }

  printUsage();
  process.exit(1);
}

async function main() {
  const rawInput = await readInput(process.argv.slice(2));
  const code = stripFence(rawInput).trim();

  if (!code) {
    console.log(JSON.stringify({
      valid: false,
      error: {
        message: 'Mermaid input is empty.',
        line: null,
        column: null,
        excerpt: null,
        expecting: null,
        got: null,
      },
    }, null, 2));
    process.exit(1);
  }

  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'mermaid-validate-'));
  const inputPath = path.join(tempDir, 'diagram.mmd');
  const outputPath = path.join(tempDir, 'diagram.svg');
  const diagramType = detectDiagramType(code);

  try {
    await fs.writeFile(inputPath, code, 'utf8');
    const result = await runMmdc(inputPath, outputPath);

    if (result.code === 0) {
      console.log(JSON.stringify({
        valid: true,
        diagramType,
        normalizedCode: code,
      }, null, 2));
      process.exit(0);
    }

    const message = normalizeCliError(result.stderr);
    const { excerpt, column } = extractExcerpt(message);
    const { expecting, got } = extractExpecting(message);

    console.log(JSON.stringify({
      valid: false,
      diagramType,
      normalizedCode: code,
      error: {
        message,
        line: extractLine(message),
        column,
        excerpt,
        expecting,
        got,
      },
    }, null, 2));
    process.exit(1);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const { excerpt, column } = extractExcerpt(message);
    const { expecting, got } = extractExpecting(message);

    console.log(JSON.stringify({
      valid: false,
      diagramType,
      normalizedCode: code,
      error: {
        message,
        line: extractLine(message),
        column,
        excerpt,
        expecting,
        got,
      },
    }, null, 2));
    process.exit(1);
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true });
  }
}

main();
