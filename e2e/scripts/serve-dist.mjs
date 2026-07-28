#!/usr/bin/env node
/**
 * Serves the Angular production build so the e2e suite can run against a freshly built UI
 * without deploying to the Pi first. This is what CI uses, and what you want locally when
 * validating UI changes before `deploy-dance.bat`.
 *
 * Two things it does beyond static file serving, both necessary:
 *
 * 1. SPA fallback — an unknown path renders index.html, mirroring the Apache rewrite in
 *    production. Without it the deep-link tests would fail for reasons unrelated to the app.
 *
 * 2. Same-origin API — it proxies `/api/*` to the real API, and rewrites the hardcoded
 *    absolute API URL inside the served JS bundles to the relative `/api`. The production
 *    bundle points at https://dance-api.takelord.com/api, whose CORS policy allows only
 *    https://dance.takelord.com — so a localhost-served bundle would get every response
 *    blocked by the browser. That is correct API behaviour, not something to loosen in
 *    production config; making the test origin same-origin is the right fix.
 *
 * Usage: node scripts/serve-dist.mjs [port]
 *        E2E_API_URL=http://localhost:5000/api node scripts/serve-dist.mjs 4300
 */
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, join, extname, normalize } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..', '..', 'dance-platform-ui', 'dist', 'dance-platform-ui', 'browser');
const port = Number(process.argv[2] ?? 4200);
const apiTarget = (process.env.E2E_API_URL ?? 'https://dance-api.takelord.com/api').replace(/\/$/, '');

// Every absolute API base the built bundle might carry, mapped to the same-origin path.
const ABSOLUTE_API_URLS = [
  'https://dance-api.takelord.com/api',
  'http://localhost:5000/api',
];

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
};

async function readIfFile(path) {
  try {
    if (!(await stat(path)).isFile()) return null;
    return await readFile(path);
  } catch {
    return null;
  }
}

async function proxyToApi(req, res) {
  const target = apiTarget + req.url.slice('/api'.length);

  const headers = { ...req.headers };
  // Host must match the upstream, and hop-by-hop headers must not be forwarded.
  delete headers.host;
  delete headers.connection;
  delete headers['accept-encoding'];

  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const body = chunks.length > 0 ? Buffer.concat(chunks) : undefined;

  try {
    const upstream = await fetch(target, { method: req.method, headers, body });
    const payload = Buffer.from(await upstream.arrayBuffer());
    res.writeHead(upstream.status, {
      'Content-Type': upstream.headers.get('content-type') ?? 'application/json',
    });
    res.end(payload);
  } catch (err) {
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: `proxy to ${target} failed: ${err.message}` }));
  }
}

createServer(async (req, res) => {
  const urlPath = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);

  if (urlPath === '/api' || urlPath.startsWith('/api/')) {
    await proxyToApi(req, res);
    return;
  }

  // Contain path traversal: resolve, then require the result to stay under root.
  const candidate = resolve(join(root, normalize(urlPath)));
  const safe = candidate.startsWith(root) ? candidate : root;

  let body = await readIfFile(safe);
  let ext = extname(safe);

  if (!body) {
    body = await readIfFile(join(root, 'index.html'));
    ext = '.html';
    if (!body) {
      res.writeHead(500).end(`No build found at ${root}. Run: npm run build -- --configuration production`);
      return;
    }
  }

  // Point the bundle's API calls back at this origin so nothing is cross-origin.
  if (ext === '.js' || ext === '.mjs') {
    let text = body.toString('utf8');
    for (const absolute of ABSOLUTE_API_URLS) text = text.split(absolute).join('/api');
    body = Buffer.from(text, 'utf8');
  }

  res.writeHead(200, { 'Content-Type': MIME[ext] ?? 'application/octet-stream' }).end(body);
}).listen(port, () => {
  console.log(`serving ${root}`);
  console.log(`  on   http://localhost:${port}`);
  console.log(`  /api -> ${apiTarget}`);
});
