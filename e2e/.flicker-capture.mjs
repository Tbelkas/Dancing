// Records every page loading cold, then sitting idle, then being scrolled — and writes a
// phase timeline so the frames can be diffed per phase. Idle flicker (content changing
// while nothing is happening) is the signal we care most about.
import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const BASE = process.env.E2E_BASE_URL || 'https://dance.takelord.com';
const API = process.env.E2E_API_URL || 'https://dance-api.takelord.com/api';
const USER = process.env.E2E_USERNAME;
const PASS = process.env.E2E_PASSWORD;
const OUT = process.env.OUT_DIR;
const ONLY = process.env.ONLY ? process.env.ONLY.split(',') : null;

const TARGETS = [
  { name: 'landing', url: '/' },
  { name: 'login', url: '/login' },
  { name: 'register', url: '/register' },
  { name: 'dances', url: '/dances' },
  { name: 'dances-query', url: '/dances?q=step&sort=name&page=2' },
  { name: 'roadmaps', url: '/roadmaps' },
  { name: 'roadmap-detail-house', url: '/roadmaps/house' },
  { name: 'roadmap-detail-waacking', url: '/roadmaps/waacking' },
  { name: 'dance-detail', url: '/dances/hip-hop/6-step' },
  { name: 'user-profile', url: `/users/${USER}` },
  { name: 'not-found', url: '/definitely-not-a-page-xyz' },
  { name: 'profile', url: '/profile', auth: true },
  { name: 'my-dances', url: '/my-dances', auth: true },
  { name: 'library', url: '/library', auth: true },
  { name: 'choreos', url: '/choreos', auth: true },
  { name: 'practice', url: '/practice', auth: true },
  { name: 'roadmap-builder-new', url: '/roadmaps/new', auth: true },
  { name: 'admin-add-video', url: '/admin/add-video', auth: true },
];

const EMBED_HOSTS = [
  '**://*.youtube.com/**', '**://*.youtube-nocookie.com/**', '**://*.ytimg.com/**',
  '**://*.tiktok.com/**', '**://*.instagram.com/**', '**://*.cdninstagram.com/**',
];

const SHIFT_PROBE = `
window.__shifts = [];
new PerformanceObserver(list => {
  for (const e of list.getEntries()) {
    if (e.hadRecentInput) continue;
    window.__shifts.push({
      t: Math.round(e.startTime), value: +e.value.toFixed(4),
      sources: (e.sources || []).map(s => ({
        node: s.node ? (s.node.nodeName + (typeof s.node.className === 'string' && s.node.className ? '.' + s.node.className.trim().split(/\\s+/).slice(0,3).join('.') : '')) : '?',
        from: s.previousRect ? [Math.round(s.previousRect.y), Math.round(s.previousRect.height)] : null,
        to: s.currentRect ? [Math.round(s.currentRect.y), Math.round(s.currentRect.height)] : null,
      })),
    });
  }
}).observe({ type: 'layout-shift', buffered: true });
`;

async function login() {
  if (!USER || !PASS) return null;
  const res = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ username: USER, password: PASS }),
  });
  if (!res.ok) throw new Error(`login failed ${res.status}`);
  return res.json();
}

const results = [];
const browser = await chromium.launch();
const creds = await login();

for (const t of TARGETS) {
  if (ONLY && !ONLY.includes(t.name)) continue;
  const dir = path.join(OUT, t.name);
  fs.mkdirSync(dir, { recursive: true });
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir, size: { width: 1440, height: 900 } },
  });
  if (t.auth && creds) {
    await ctx.addInitScript(([tok, u]) => {
      localStorage.setItem('dp_token', tok);
      localStorage.setItem('dp_user', u);
    }, [creds.token, JSON.stringify({ userId: creds.userId, username: creds.username })]);
  }
  const page = await ctx.newPage();
  await page.addInitScript(SHIFT_PROBE);
  for (const p of EMBED_HOSTS) await page.route(p, r => r.abort());

  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 160)); });
  page.on('pageerror', e => errors.push('pageerror: ' + String(e).slice(0, 160)));

  const t0 = Date.now();
  const mark = () => Date.now() - t0;
  const phases = {};
  let shifts = [], finalUrl = '', settleMs = null;

  try {
    phases.navStart = mark();
    await page.goto(BASE + t.url, { waitUntil: 'commit', timeout: 40000 });
    // "Settled" = the app has painted real content and the network went quiet.
    try { await page.waitForLoadState('networkidle', { timeout: 25000 }); } catch { errors.push('no networkidle'); }
    settleMs = mark();
    phases.idleStart = mark();
    await page.waitForTimeout(4000);            // idle observation window
    phases.idleEnd = mark();

    // Scroll pass: down in steps, pause, back up. Catches reveal-on-scroll re-triggers,
    // sticky-header repaint, and lazy images popping in and out.
    phases.scrollStart = mark();
    const h = await page.evaluate(() => document.documentElement.scrollHeight);
    for (let y = 0; y < h; y += 600) {
      await page.evaluate(v => window.scrollTo({ top: v, behavior: 'instant' }), y);
      await page.waitForTimeout(350);
    }
    await page.waitForTimeout(600);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
    await page.waitForTimeout(1200);
    phases.scrollEnd = mark();

    shifts = await page.evaluate(() => window.__shifts || []);
    finalUrl = page.url();
  } catch (e) {
    errors.push('nav: ' + String(e).slice(0, 160));
  }
  const totalMs = mark();
  await ctx.close();

  const cls = shifts.reduce((a, s) => a + s.value, 0);
  results.push({ name: t.name, url: t.url, finalUrl, auth: !!t.auth, settleMs, totalMs,
                 phases, cls: +cls.toFixed(4), shifts, errors });
  console.log(`${t.name.padEnd(24)} settle=${String(settleMs).padStart(5)}ms CLS=${cls.toFixed(4)} shifts=${shifts.length} errs=${errors.length}`);
  await new Promise(r => setTimeout(r, 1500));   // let the Pi breathe between pages
}

await browser.close();
fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify(results, null, 2));
console.log('\nwrote ' + path.join(OUT, 'results.json'));
