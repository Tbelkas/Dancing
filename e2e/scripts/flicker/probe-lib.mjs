// Shared rig for the DOM probes in this folder: login, a context with the token already in
// localStorage, and a per-frame DOM recorder that logs only the transitions.
import { chromium } from '@playwright/test';
import { BASE_URL, API_URL, USERNAME, PASSWORD } from './env.mjs';

export { chromium, BASE_URL, API_URL, USERNAME, PASSWORD };

export async function login() {
  const r = await fetch(`${API_URL}/auth/login`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ username: USERNAME, password: PASSWORD }),
  });
  if (!r.ok) throw new Error(`login failed: ${r.status}`);
  return r.json();
}

const RECORDER = (defs) => {
  window.__log = [];
  const read = (d) => {
    const els = document.querySelectorAll(d.sel);
    if (d.mode === 'count') return els.length;
    const el = els[0];
    if (d.mode === 'exists') return el ? 1 : 0;
    if (!el) return null;
    if (d.mode === 'height') return Math.round(el.getBoundingClientRect().height);
    if (d.mode === 'top') return Math.round(el.getBoundingClientRect().top + window.scrollY);
    if (d.mode === 'text') return (el.textContent || '').trim().slice(0, 60);
    return null;
  };
  let prev = null;
  (function tick() {
    // Runs from document-start, so everything here has to survive a page with no <body> yet;
    // an uncaught throw would kill the loop for good and the log would come back empty.
    try {
      const now = {};
      for (const d of defs) now[d.name] = read(d);
      if (!prev || defs.some(d => now[d.name] !== prev[d.name])) {
        window.__log.push({ t: Math.round(performance.now()), ...now, h: document.body ? document.body.scrollHeight : 0 });
        prev = now;
      }
    } catch (e) { /* keep sampling */ }
    requestAnimationFrame(tick);
  })();
};

/**
 * Opens `url` with the recorder installed.
 *  - YouTube/thumbnail traffic is aborted: irrelevant here, and it dominates the timeline.
 *  - POST /videos/:id/view is aborted so probing never writes to the prod DB.
 *  - `delays` throttles matching API calls, to force a skeleton a warm API would outrun.
 */
export async function record(browser, creds, { url, probes, settleMs = 4000, delays = [], viewport }) {
  const ctx = await browser.newContext({ viewport: viewport ?? { width: 1440, height: 900 } });
  await ctx.addInitScript(([t, u]) => {
    localStorage.setItem('dp_token', t);
    localStorage.setItem('dp_user', u);
  }, [creds.token, JSON.stringify({ userId: creds.userId, username: creds.username })]);

  const page = await ctx.newPage();
  await page.addInitScript(RECORDER, probes);
  for (const p of ['**://*.youtube.com/**', '**://*.ytimg.com/**', '**://*.ggpht.com/**']) {
    await page.route(p, r => r.abort());
  }
  await page.route('**/videos/*/view', r => r.abort());
  for (const { match, ms } of delays) {
    await page.route(match, async r => { await new Promise(x => setTimeout(x, ms)); await r.continue(); });
  }

  const api = [];
  const t0 = Date.now();
  page.on('response', r => {
    const u = r.url();
    if (u.includes('/api/')) api.push({ path: u.replace(/^.*\/api\//, ''), status: r.status(), t: Date.now() - t0 });
  });

  await page.goto(url, { waitUntil: 'commit', timeout: 45000 });
  await page.waitForTimeout(settleMs);
  const log = await page.evaluate(() => window.__log);
  await ctx.close();
  return { log, api };
}

/** [start, end, ms] windows where `name` was truthy. */
export function windows(log, name, truthy = v => v) {
  const out = [];
  let open = null;
  for (const row of log) {
    const on = truthy(row[name]);
    if (on && open === null) open = row.t;
    else if (!on && open !== null) { out.push([open, row.t, row.t - open]); open = null; }
  }
  if (open !== null && log.length) {
    const last = log[log.length - 1].t;
    out.push([open, last, last - open]);
  }
  return out;
}

export const pace = (ms = 2500) => new Promise(r => setTimeout(r, ms));
