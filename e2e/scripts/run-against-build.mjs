#!/usr/bin/env node
/**
 * Runs the whole suite against the local production build: starts serve-dist.mjs, waits for
 * it, runs Playwright pointed at it, then shuts the server down.
 *
 * This is the pre-deploy check — it exercises UI changes that aren't on the Pi yet, which
 * running against https://dance.takelord.com cannot do.
 *
 * Assumes the build exists:
 *   cd ../dance-platform-ui && npm run build -- --configuration production
 *
 * Any extra args are forwarded to Playwright, e.g. `npm run test:local -- --grep @smoke`.
 */
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.E2E_LOCAL_PORT ?? 4300);
const baseUrl = `http://localhost:${port}`;

const server = spawn(process.execPath, [resolve(here, 'serve-dist.mjs'), String(port)], {
  stdio: ['ignore', 'inherit', 'inherit'],
});

const shutdown = () => { if (!server.killed) server.kill(); };
process.on('exit', shutdown);
process.on('SIGINT', () => { shutdown(); process.exit(130); });

/** Polls until the server answers, so Playwright never starts against a dead port. */
async function waitForServer(timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(baseUrl, { signal: AbortSignal.timeout(2000) });
      if (res.ok) return true;
    } catch { /* not up yet */ }
    await new Promise(r => setTimeout(r, 300));
  }
  return false;
}

if (!(await waitForServer())) {
  console.error(`\n  Local server never came up on ${baseUrl}.`);
  console.error('  Did you build the UI?  cd ../dance-platform-ui && npm run build -- --configuration production\n');
  shutdown();
  process.exit(1);
}

const args = process.argv.slice(2);
// Spawn Playwright's CLI entry point with node directly rather than going through `npx`:
// Node on Windows refuses to spawn a .cmd shim without shell:true, and using a shell would
// drag quoting rules into the forwarded args.
const playwrightCli = resolve(here, '..', 'node_modules', '@playwright', 'test', 'cli.js');
const playwright = spawn(
  process.execPath,
  [playwrightCli, 'test', ...args],
  { stdio: 'inherit', env: { ...process.env, E2E_BASE_URL: baseUrl } }
);

playwright.on('exit', code => {
  shutdown();
  process.exit(code ?? 1);
});
