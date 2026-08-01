import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { basename, extname, join } from 'node:path';

import { renderDeck } from './render.mjs';
import { runQa } from './qa.mjs';
import { exportProject as exportProjectDefault } from './export.mjs';
import { transitionProjectState } from './model.mjs';
import { writeJsonAtomic, writeTextAtomic } from './storage.mjs';

const PROJECT_FILES = {
  deck: 'deck_spec.json',
  state: 'editor_state.json',
  assets: 'asset_manifest.json',
};

function response(status, json) {
  return { status, json };
}

function isLocal(address = '') {
  const normalized = address.replace(/^::ffff:/u, '');
  return normalized === '127.0.0.1' || normalized === '::1' || normalized === 'localhost';
}

async function readJson(root, file) {
  return JSON.parse(await readFile(join(root, file), 'utf8'));
}

async function readProject(root) {
  const [deck, state, assets] = await Promise.all([
    readJson(root, PROJECT_FILES.deck),
    readJson(root, PROJECT_FILES.state),
    readJson(root, PROJECT_FILES.assets),
  ]);
  return { deck, state, assets };
}

function mergeState(state, patch) {
  const merged = { ...state, ...patch };
  for (const field of ['text_overrides', 'prop_overrides', 'review_status']) {
    if (patch[field]) merged[field] = { ...state[field], ...patch[field] };
  }
  merged.revision = state.revision + 1;
  return merged;
}

function safeFilename(filename) {
  return typeof filename === 'string'
    && filename === basename(filename)
    && !filename.includes('..')
    && /^[A-Za-z0-9._ -]+$/u.test(filename);
}

async function saveMedia(root, body) {
  if (!safeFilename(body?.filename) || typeof body?.content_base64 !== 'string') {
    return response(400, { error: 'media.invalid' });
  }
  let bytes;
  try {
    bytes = Buffer.from(body.content_base64, 'base64');
  } catch {
    return response(400, { error: 'media.invalid_base64' });
  }
  if (bytes.length === 0 || bytes.length > 25 * 1024 * 1024) {
    return response(400, { error: 'media.size' });
  }
  const hash = createHash('sha256').update(bytes).digest('hex');
  const extension = extname(body.filename).toLowerCase().replace(/[^.a-z0-9]/gu, '') || '.bin';
  const relativePath = `media/${hash}${extension}`;
  await writeFile(join(root, relativePath), bytes, { flag: 'wx' }).catch((error) => {
    if (error.code !== 'EEXIST') throw error;
  });
  const manifest = await readJson(root, PROJECT_FILES.assets);
  let asset = manifest.assets.find((item) => item.sha256 === hash);
  if (!asset) {
    asset = {
      id: body.id || `asset-${hash.slice(0, 12)}`,
      path: relativePath,
      source: 'user',
      purpose: body.purpose || body.filename,
      fact_bearing: Boolean(body.fact_bearing),
      sha256: hash,
      original_name: body.filename,
      ...(body.license ? { license: body.license } : {}),
    };
    manifest.assets.push(asset);
    await writeJsonAtomic(join(root, PROJECT_FILES.assets), manifest);
  }
  return response(201, { asset });
}

export function createProjectHandler(root, options = {}) {
  return async function handle(request) {
    try {
      if (request.method === 'GET' && request.path === '/api/project') {
        return response(200, await readProject(root));
      }
      if (request.method !== 'GET' && !isLocal(request.remoteAddress)) {
        return response(403, { error: 'server.local_write_only' });
      }
      if (request.method === 'POST' && request.path === '/api/save') {
        const state = await readJson(root, PROJECT_FILES.state);
        if (request.body?.expected_revision !== state.revision) {
          return response(409, { error: 'project.revision.conflict', state });
        }
        const next = mergeState(state, request.body?.patch ?? {});
        await writeJsonAtomic(join(root, PROJECT_FILES.state), next);
        return response(200, { state: next });
      }
      if (request.method === 'POST' && request.path === '/api/status') {
        const state = await readJson(root, PROJECT_FILES.state);
        if (request.body?.expected_revision !== state.revision) return response(409, { error: 'project.revision.conflict', state });
        let next;
        try { next = transitionProjectState(state, request.body?.status); } catch (error) { return response(400, { error: 'project.status.invalid', message: error.message }); }
        next.revision = state.revision + 1;
        await writeJsonAtomic(join(root, PROJECT_FILES.state), next);
        return response(200, { state: next });
      }
      if (request.method === 'POST' && request.path === '/api/media') {
        return saveMedia(root, request.body);
      }
      if (request.method === 'POST' && request.path === '/api/render') {
        const project = await readProject(root);
        const html = renderDeck(project);
        await writeTextAtomic(join(root, 'index.html'), html);
        return response(200, { path: 'index.html' });
      }
      if (request.method === 'POST' && request.path === '/api/qa') {
        const project = await readProject(root);
        const report = await runQa(project, options.qaOptions);
        await writeJsonAtomic(join(root, 'qa_report.json'), report);
        return response(200, report);
      }
      if (request.method === 'POST' && request.path === '/api/export') {
        const project = await readProject(root);
        const report = await runQa(project, options.qaOptions);
        await writeJsonAtomic(join(root, 'qa_report.json'), report);
        const gateReady = ['review', 'exported'].includes(project.state.project_status);
        if ((!report.export_ready || !gateReady) && !request.body?.force) {
          return response(422, { error: 'export.qa_blocked', report });
        }
        const exporter = options.exportProject ?? exportProjectDefault;
        const exported = await exporter(root, project, request.body?.format ?? 'html', options.exportOptions);
        if (project.state.project_status === 'review') {
          const next = transitionProjectState(project.state, 'exported');
          next.revision = project.state.revision + 1;
          await writeJsonAtomic(join(root, PROJECT_FILES.state), next);
        }
        return response(200, exported);
      }
      return response(404, { error: 'route.not_found' });
    } catch (error) {
      return response(500, { error: 'server.internal', message: error.message });
    }
  };
}
