// Two suspected wrong-page flashes:
//   1. signed-in user opening "/" — LandingComponent paints, then ngOnInit redirects
//   2. signed-out user opening an authed route — does the page paint before the guard fires?
import { chromium } from '@playwright/test';
import fs from 'node:fs';

const BASE = process.env.E2E_BASE_URL, API = process.env.E2E_API_URL;
const USER = process.env.E2E_USERNAME, PASS = process.env.E2E_PASSWORD;
const OUT = process.env.OUT_DIR;

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
  console.log('samples:', t.length, await page.evaluate(() => typeof window.__t));
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
