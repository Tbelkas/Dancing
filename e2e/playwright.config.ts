import { defineConfig, devices } from '@playwright/test';
// Importing this for its side effect too: it populates process.env from e2e/.env before
// the values below are read.
import { BASE_URL, API_URL, USERNAME, PASSWORD } from './fixtures/env.js';

/**
 * Targets a *deployed* environment, not a build output — these are smoke tests you run
 * after `deploy-dance.bat` to confirm the Pi is actually serving a working app, so they
 * talk to real HTTP rather than a dev server this config started.
 *
 * Override for a local pair (`ng serve` + `dotnet run`):
 *   E2E_BASE_URL=http://localhost:4200 E2E_API_URL=http://localhost:5000/api npm test
 */

// Credentials are never committed — see e2e/.env.example. The authed project is skipped
// entirely when they're absent, so an unconfigured checkout still runs the anon + api suites.
const HAS_CREDS = Boolean(USERNAME && PASSWORD);

export default defineConfig({
  testDir: './tests',
  outputDir: './test-results',
  // The Pi is a single small box: parallel workers hammering it produce timeouts that look
  // like product bugs. Serial keeps failures meaningful.
  workers: 1,
  fullyParallel: false,
  // Never let a stray .only silently shrink a scheduled run to one test.
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 1,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI
    ? [['list'], ['html', { open: 'never' }], ['github']]
    : [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: BASE_URL,
    // Traces/screenshots only on the retry — a green scheduled run leaves no artifacts behind.
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',
    actionTimeout: 10_000,
    navigationTimeout: 20_000,
    extraHTTPHeaders: { 'X-E2E-Run': '1' },
  },

  projects: [
    {
      name: 'api',
      testMatch: /api\.spec\.ts/,
      // Trailing slash matters: Playwright resolves paths with `new URL(path, baseURL)`, so
      // baseURL ".../api" + "styles" would resolve to ".../styles" and 404. With ".../api/"
      // and slash-less relative paths in the spec, it lands where you expect.
      use: { baseURL: API_URL.endsWith('/') ? API_URL : `${API_URL}/` },
    },
    {
      name: 'anon',
      testMatch: /(smoke|browse|dance-detail)\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'authed',
      testMatch: /authed\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
      // Skip rather than fail: a missing credential is a config gap, not a product regression.
      grep: HAS_CREDS ? /.*/ : /$^/,
    },
    {
      name: 'mobile',
      testMatch: /smoke\.spec\.ts/,
      use: { ...devices['Pixel 7'] },
    },
  ],
});
