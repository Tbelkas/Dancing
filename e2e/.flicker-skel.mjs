// How long is each page's loading skeleton actually on screen? Anything under ~150ms is a
// flash rather than a loading state. Measures both a cold page load and an in-app (SPA)
// navigation, three runs each.
import { chromium } from '@playwright/test';

const BASE = process.env.E2E_BASE_URL, API = process.env.E2E_API_URL;
const USER = process.env.E2E_USERNAME, PASS = process.env.E2E_PASSWORD;
const RUNS = Number(process.env.RUNS || 3);

const PROBE = `
window.__sk = [];
(function s(){
  try {
    var n = document.querySelectorAll('[class*=skeleton i],[class*=shimmer i]').length;
    var last = window.__sk[window.__sk.length - 1];
    if (!last || last.n !== n) window.__sk.push({ t: Math.round(performance.now()), n: n, url: location.pathname + location.search });
  } catch (e) {}
  requestAnimationFrame(s);
})();
`;

const PAGES = (process.env.PAGES ? JSON.parse(process.env.PAGES) : [
  ['/', 'landing'], ['/dances', 'browse'], ['/roadmaps', 'roadmaps'],
  ['/roadmaps/house', 'roadmap detail'], ['/dances/hip-hop/6-step', 'dance detail'],
  ['/profile', 'profile'], ['/my-dances', 'my dances'], ['/library', 'library'],
  ['/choreos', 'choreos'], ['/practice', 'practice'], ['/users/' + USER, 'public profile'],
]);

const r = await fetch(`${API}/auth/login`, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ username: USER, password: PASS }),
});
const creds = await r.json();
const browser = await chromium.launch();

function windows(sk) {
  // [start, end] pairs where the skeleton count was > 0
  const out = [];
  let open = null;
  for (const s of sk) {
    if (s.n > 0 && open === null) open = s.t;
    else if (s.n === 0 && open !== null) { out.push([open, s.t]); open = null; }
  }
  return out;
}

console.log('page                 cold-load skeleton visible (ms)      spa-nav skeleton visible (ms)');
for (const [url, name] of PAGES) {
  const cold = [], spa = [];
  for (let i = 0; i < RUNS; i++) {
   try {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    await ctx.addInitScript(([t, u]) => {
      localStorage.setItem('dp_token', t); localStorage.setItem('dp_user', u);
    }, [creds.token, JSON.stringify({ userId: creds.userId, username: creds.username })]);
    const page = await ctx.newPage();
    await page.addInitScript(PROBE);
    for (const p of ['**://*.youtube.com/**', '**://*.ytimg.com/**']) await page.route(p, x => x.abort());

    await page.goto(BASE + url, { waitUntil: 'commit', timeout: 45000 });
    await page.waitForTimeout(4000);
    cold.push(...windows(await page.evaluate(() => window.__sk)).map(([a, b]) => b - a));

    // now an in-app navigation to the same page, from /dances (or /roadmaps if that's us)
    const hop = url.startsWith('/dances') ? '/roadmaps' : '/dances';
    await page.evaluate(() => { window.__sk = []; });
    await page.goto(BASE + hop, { waitUntil: 'commit' });
    await page.waitForTimeout(2500);
    await page.evaluate(() => { window.__sk = []; });
    // Click a real in-app link so the router handles it (a synthetic <a> would reload).
    const link = page.locator(`a[href="${url}"], a[href="${url}/"]`).first();
    if (await link.count()) {
      await link.click({ timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(3000);
      spa.push(...windows(await page.evaluate(() => window.__sk).catch(() => [])).map(([a, b]) => b - a));
    }
    await ctx.close();
   } catch (e) { console.log(`  (${name} run ${i + 1} aborted: ${String(e).slice(0, 60)})`); }
   await new Promise(r => setTimeout(r, 2500));   // the Pi wedges if you hammer it
  }
  const fmt = a => a.length ? a.join(', ') : 'none';
  console.log(`${name.padEnd(20)} ${fmt(cold).padEnd(35)} ${fmt(spa)}`);
}
await browser.close();
