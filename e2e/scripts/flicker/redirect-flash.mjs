// Does a redirect show the wrong page on the way past?
//
// Samples the URL and the visible copy every animation frame, then prints one line per
// distinct state. A redirect done right produces two states (blank, then the destination).
// A third state naming the *source* page means it painted before the redirect fired — that
// is the bug landingGuard was written for.
//
// Cases: a signed-in visitor opening "/", and a signed-out one opening a guarded route.
//
//   OUT_DIR=/tmp/flicker node scripts/flicker/redirect-flash.mjs
import { chromium } from '@playwright/test';
// Side effect: populates process.env from e2e/.env before the constants below are read.
import { BASE_URL, API_URL, USERNAME, PASSWORD } from './env.mjs';

const BASE = BASE_URL, API = API_URL;
const USER = USERNAME, PASS = PASSWORD;
// Videos land under test-results/ by default so a bare run doesn't scatter files.
const OUT = process.env.OUT_DIR || 'test-results/flicker-redirect';

const PROBE = `
window.__t = [];
(function s(){
  try {
    var m = document.querySelector('main') || document.body;
    window.__t.push({ t: Math.round(performance.now()), url: location.pathname,
                      head: ((m && m.innerText) || '').replace(/\s+/g,' ').slice(0, 90) });
  } catch (e) {}
  requestAnimationFrame(s);
})();
`;

const r = await fetch(`${API}/auth/login`, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ username: USER, password: PASS }),
});
const creds = await r.json();

const browser = await chromium.launch();
const cases = [
  { name: 'authed-root', url: '/', auth: true },
  { name: 'anon-profile', url: '/profile', auth: false },
  { name: 'anon-practice', url: '/practice', auth: false },
];

for (const c of cases) {
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: `${OUT}/${c.name}`, size: { width: 1440, height: 900 } },
  });
  if (c.auth) await ctx.addInitScript(([t, u]) => {
    localStorage.setItem('dp_token', t); localStorage.setItem('dp_user', u);
  }, [creds.token, JSON.stringify({ userId: creds.userId, username: creds.username })]);
  const page = await ctx.newPage();
  await page.addInitScript(PROBE);
  await page.goto(BASE + c.url, { waitUntil: 'commit', timeout: 45000 });
  await page.waitForTimeout(5000);
  const t = await page.evaluate(() => window.__t || []);
  // collapse to state changes
  const states = [];
  let prev = null;
  for (const s of t) {
    const sig = s.url + '|' + s.head;
    if (sig !== prev) { states.push(s); prev = sig; }
  }
  console.log(`\n== ${c.name} (${c.url}) -> ${page.url().replace(BASE, '')}`);
  for (const s of states) console.log(`   ${String(s.t).padStart(5)}ms ${s.url.padEnd(12)} ${s.head}`);
  await ctx.close();
}
await browser.close();
