// Scratch: eyeball the streak-at-risk banner at a few points on the clock.
// Needs `node e2e/scripts/serve-dist.mjs 4300` running against a fresh production build.
//   node e2e/scripts/shot-streak-warning.mjs
import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';

const BASE = 'http://localhost:4300';
const OUT = process.env.SHOT_DIR ?? 'shots';

// The route guard only checks that a token exists and hasn't expired (authGuard →
// AuthService.isAuthenticated), and every call this page makes is either stubbed below or
// allowed to fail, so a synthetic token is enough to render it. No credentials needed.
const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
const token = `${b64({ alg: 'none' })}.${b64({ exp: 4102444800 })}.sig`;
const [userId, username] = [1, 'screenshot'];

/** A day, YYYY-MM-DD, offset from a reference date. */
const day = (from, offset) => {
  const d = new Date(from + 'T12:00:00');
  d.setDate(d.getDate() + offset);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

/** A four-day run ending yesterday: a live streak with nothing logged today. */
const atRiskSessions = (today) =>
  [1, 2, 3, 4].map((back, i) => ({
    id: 900 + i,
    date: day(today, -back),
    startedAt: `${day(today, -back)}T18:00:00Z`,
    lastActivityAt: `${day(today, -back)}T18:30:00Z`,
    totalSeconds: 1800,
    durationMinutes: 30,
    items: [{
      danceId: 1, danceName: 'Salsa', danceSlug: 'salsa', danceStyleSlug: 'latin',
      danceStyleName: 'Latin', seconds: 1800, minutes: 30,
    }],
  }));

const cases = [
  ['1-plenty-of-day', '2026-08-11T21:00:00'],   // no countdown yet
  ['2-four-hours', '2026-08-12T00:05:00'],
  ['3-two-hours', '2026-08-12T02:10:00'],
  ['4-minutes', '2026-08-12T03:47:00'],
];

mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();

for (const [name, when] of cases) {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    timezoneId: 'Europe/Vilnius',
  });
  const page = await context.newPage();
  // Must land before the app bootstraps — AuthService reads localStorage in a field initializer.
  await page.addInitScript(([t, u]) => {
    localStorage.setItem('dp_token', t);
    localStorage.setItem('dp_user', u);
  }, [token, JSON.stringify({ userId, username })]);
  await page.clock.setFixedTime(new Date(when));

  // The practice day for `when`: before 4 AM it's still the previous calendar day.
  const shifted = new Date(new Date(when).getTime() - 4 * 3600000);
  const practiceDay = `${shifted.getFullYear()}-${String(shifted.getMonth() + 1).padStart(2, '0')}-${String(shifted.getDate()).padStart(2, '0')}`;

  // Catch-all first (later routes win): a real 401 from prod would trip the auth interceptor
  // and bounce this synthetic session straight to /login.
  await page.route('**/api/**', (route) => route.fulfill({ json: [] }));
  await page.route('**/api/practice', (route) =>
    route.fulfill({ json: atRiskSessions(practiceDay) }));

  await page.goto(`${BASE}/practice`);
  const banner = page.locator('.streak-risk');
  try {
    await banner.waitFor({ timeout: 15_000 });
  } catch (err) {
    await page.screenshot({ path: `${OUT}/${name}-FAILED.png`, fullPage: true });
    console.log(`${name}: no banner. url=${page.url()}`);
    console.log((await page.locator('body').innerText()).slice(0, 600));
    await context.close();
    continue;
  }
  await banner.screenshot({ path: `${OUT}/${name}.png` });
  console.log(`${name.padEnd(18)} ${when}  ->  ${JSON.stringify(await banner.innerText())}`);
  await context.close();
}

await browser.close();
