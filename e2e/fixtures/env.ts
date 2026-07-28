import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

/**
 * Minimal .env loader so the suite has no runtime dependency beyond Playwright.
 * Real shell env always wins over the file — CI sets secrets that way.
 */
const here = dirname(fileURLToPath(import.meta.url));
const envPath = resolve(here, '..', '.env');

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
