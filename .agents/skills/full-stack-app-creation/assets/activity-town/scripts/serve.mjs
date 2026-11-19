import { createReadStream } from 'node:fs';
import { realpath, stat } from 'node:fs/promises';
import { createServer } from 'node:http';
import { extname, isAbsolute, relative, resolve } from 'node:path';
import { pipeline } from 'node:stream/promises';
import { fileURLToPath } from 'node:url';
import { createActivityHandler, isLoopbackHost } from './activity.mjs';

const bindAddress = '127.0.0.1';
const port = Number(process.env.PORT ?? 4173);
const dist = await realpath(fileURLToPath(new URL('../dist/', import.meta.url))).catch(() => null);
if (!dist) {
  console.error('Build Activity Town with npm run build before starting the production server.');
  process.exit(1);
}
if (!Number.isInteger(port) || port < 0 || port > 65535) {
  console.error('PORT must be a valid TCP port.');
  process.exit(1);
}

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.glb': 'model/gltf-binary',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
};
const serveActivity = createActivityHandler();
const basicHeaders = {
  'Content-Security-Policy': "default-src 'self'; img-src 'self' data:; base-uri 'none'; object-src 'none'; frame-ancestors 'none'",
  'Cross-Origin-Resource-Policy': 'same-origin',
  'X-Content-Type-Options': 'nosniff',
};

function isInsideDist(path) {
  const entry = relative(dist, path);
  return !isAbsolute(entry) && entry.split(/[\\/]/)[0] !== '..';
}

async function serveStatic(request, response) {
  if (!['GET', 'HEAD'].includes(request.method)) {
    response.writeHead(405, { ...basicHeaders, Allow: 'GET, HEAD' }).end();
    return;
  }
  let path;
  try {
    const { pathname } = new URL(request.url, 'http://localhost');
    path = decodeURIComponent(pathname);
  } catch {
    response.writeHead(400, basicHeaders).end();
    return;
  }
  const requested = resolve(dist, path === '/' ? 'index.html' : `.${path}`);
  const file = isInsideDist(requested) ? await realpath(requested).catch(() => null) : null;
  const details = file && isInsideDist(file) ? await stat(file).catch(() => null) : null;
  if (!details?.isFile()) {
    response.writeHead(404, basicHeaders).end();
    return;
  }
  response.writeHead(200, {
    ...basicHeaders,
    'Cache-Control': 'no-cache',
    'Content-Length': details.size,
    'Content-Type': contentTypes[extname(file)] ?? 'application/octet-stream',
  });
  if (request.method === 'HEAD') {
    response.end();
    return;
  }
  await pipeline(createReadStream(file), response).catch(() => {});
}

const server = createServer((request, response) => {
  if (!isLoopbackHost(request.headers.host)) {
    response.writeHead(403, basicHeaders).end();
    return;
  }
  serveActivity(request, response, () => serveStatic(request, response)).catch(() => {
    if (!response.headersSent) response.writeHead(500, basicHeaders);
    response.end();
  });
});
server.on('error', (error) => {
  console.error(`Could not start Activity Town (${error.code ?? 'server error'}).`);
  process.exitCode = 1;
});
server.listen(port, bindAddress, () => {
  console.log(`Activity Town is available at http://${bindAddress}:${server.address().port}`);
});
