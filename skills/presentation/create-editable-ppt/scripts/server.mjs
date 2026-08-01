#!/usr/bin/env node
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, normalize, resolve } from 'node:path';

import { createProjectHandler } from './lib/server.mjs';

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml' };

export async function startProjectServer(root, { host = '127.0.0.1', port = 4173 } = {}) {
  if (!['127.0.0.1', 'localhost', '::1'].includes(host)) throw new Error('Editor server must bind to localhost.');
  const projectRoot = resolve(root);
  const handle = createProjectHandler(projectRoot);
  const server = createServer(async (request, response) => {
    try {
      const url = new URL(request.url, `http://${host}:${port}`);
      if (url.pathname.startsWith('/api/')) {
        const chunks = [];
        let size = 0;
        for await (const chunk of request) {
          size += chunk.length;
          if (size > 30 * 1024 * 1024) throw new Error('Request body too large.');
          chunks.push(chunk);
        }
        const body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {};
        const result = await handle({ method: request.method, path: url.pathname, body, remoteAddress: request.socket.remoteAddress });
        response.writeHead(result.status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' });
        response.end(JSON.stringify(result.json));
        return;
      }
      const requested = url.pathname === '/' ? 'index.html' : normalize(decodeURIComponent(url.pathname)).replace(/^[/\\]+/u, '');
      const path = resolve(join(projectRoot, requested));
      if (!path.startsWith(`${projectRoot}/`) && path !== projectRoot) { response.writeHead(403); response.end('Forbidden'); return; }
      const info = await stat(path);
      if (!info.isFile()) throw new Error('Not a file.');
      response.writeHead(200, { 'content-type': MIME[extname(path).toLowerCase()] ?? 'application/octet-stream', 'cache-control': 'no-store' });
      response.end(await readFile(path));
    } catch (error) {
      response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
      response.end(error.message);
    }
  });
  await new Promise((resolveListen, reject) => { server.once('error', reject); server.listen(port, host, resolveListen); });
  return server;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const root = process.argv[2] ?? process.cwd();
  const portIndex = process.argv.indexOf('--port');
  const port = portIndex >= 0 ? Number(process.argv[portIndex + 1]) : 4173;
  const server = await startProjectServer(root, { port });
  const address = server.address();
  console.log(`Editable PPT: http://127.0.0.1:${address.port}`);
}
