import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

/**
 * Same minimal .env load as fixtures/env.ts, in plain JS.
 *
 * The duplication is deliberate: these probes run under bare `node`, not Playwright's test
 * runner, so they cannot import the TypeScript one. Shell env still wins over the file.
 */
const here = dirname(fileURLToPath(import.meta.url));
const envPath = resolve(here, '..', '..', '.env');

if (existsSync(envPath)) {
  for (const line of readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const match = /^\s*([A-Z0-9_]+)\s*=\s*(.*)$/.exec(line);
    if (!match) continue;
    const [, key, rawValue] = match;
    if (process.env[key]) continue;
    process.env[key] = rawValue.trim().replace(/^["']|["']$/g, '');
  }
}

export const BASE_URL = process.env.E2E_BASE_URL ?? 'https://dance.takelord.com';
export const API_URL = process.env.E2E_API_URL ?? 'https://dance-api.takelord.com/api';
export const USERNAME = process.env.E2E_USERNAME ?? '';
export const PASSWORD = process.env.E2E_PASSWORD ?? '';
