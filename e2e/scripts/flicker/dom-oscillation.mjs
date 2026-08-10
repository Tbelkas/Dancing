// Samples the DOM every animation frame while a page loads and while it is driven, then
// looks for *oscillation*: a marker or count that goes A -> B -> A. That is what "flicker"
// is in an SPA — an empty state that flashes before the data lands, a list that empties and
// refills, a skeleton that comes back after content was already on screen.
//
// Read-only: no favourites, no saves, no settings toggles. It only types, sorts, paginates,
// hovers and navigates — the authed pages here run against the production database, so this
// stays under the same rule as the suite.
//
// Writes a JSON blob of samples; read it with scripts/flicker/osc.py.
//
//   OUT_FILE=/tmp/dom.json node scripts/flicker/dom-oscillation.mjs
//   python scripts/flicker/osc.py /tmp/dom.json
import { chromium } from '@playwright/test';
// Side effect: populates process.env from e2e/.env before the constants below are read.
import { BASE_URL, API_URL, USERNAME, PASSWORD } from './env.mjs';
import fs from 'node:fs';
import path from 'node:path';

const BASE = BASE_URL, API = API_URL;
const USER = USERNAME, PASS = PASSWORD;
// Artifacts land under the gitignored test-results/ by default.
const OUT = process.env.OUT_FILE || 'test-results/flicker-dom.json';
const ONLY = process.env.ONLY ? process.env.ONLY.split(',') : null;

const PROBE = `
window.__samples = [];
window.__label = 'load';
(function () {
  const q = s => document.querySelectorAll(s).length;
  const main = () => document.querySelector('main') || document.body;
  function sample() {
    const m = main();
    window.__samples.push({
      t: Math.round(performance.now()),
      label: window.__label,
      url: location.pathname + location.search,
      danceCards: q('[data-testid=dance-card]'),
      roadmapCards: q('[data-testid=roadmap-card]'),
      steps: q('[data-testid=roadmap-step]'),
      treeNodes: q('[data-testid=tree-node]'),
      empty: q('[data-testid=empty-state]'),
      results: (document.querySelector('[data-testid=results-count]') || {}).textContent || '',
      skeletons: document.querySelectorAll('[class*=skeleton i],[class*=shimmer i]').length,
      spinners: document.querySelectorAll('[class*=spinner i],[class*=loading i]').length,
      textLen: (m.innerText || '').length,
      h: Math.round(document.documentElement.scrollHeight),
      y: Math.round(window.scrollY),
    });
    requestAnimationFrame(sample);
  }
  requestAnimationFrame(sample);
})();
`;

async function login() {
  const r = await fetch(`${API}/auth/login`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ username: USER, password: PASS }),
  });
  return r.json();
}

const label = (page, l) => page.evaluate(v => { window.__label = v; }, l);

const SCENARIOS = [
  { name: 'landing', url: '/', auth: false, async run(page) {
      await page.hover('[data-testid=nav-browse]').catch(() => {});
      await page.waitForTimeout(600);
    } },
  { name: 'dances', url: '/dances', auth: false, async run(page) {
      await label(page, 'type-search');
      await page.fill('[data-testid=search-input]', 'step');
      await page.waitForTimeout(2500);
      await label(page, 'clear-search');
      await page.fill('[data-testid=search-input]', '');
      await page.waitForTimeout(2500);
      await label(page, 'sort');
      await page.selectOption('[data-testid=sort-select]', 'name').catch(() => {});
      await page.waitForTimeout(2500);
      await label(page, 'style-pill');
      const pill = page.locator('[data-testid=style-filter-pills] button, [data-testid=style-filter-pills] a').nth(2);
      await pill.click({ timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(2500);
      await label(page, 'no-results');
      await page.fill('[data-testid=search-input]', 'zzzznotathing');
      await page.waitForTimeout(2500);
      await label(page, 'back-to-results');
      await page.fill('[data-testid=search-input]', 'a');
      await page.waitForTimeout(2500);
      await label(page, 'hover-card');
      await page.locator('[data-testid=dance-card]').first().hover().catch(() => {});
      await page.waitForTimeout(800);
    } },
  { name: 'dances-paging', url: '/dances', auth: false, async run(page) {
      await label(page, 'scroll-bottom');
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(1500);
      await label(page, 'next-page');
      const next = page.getByRole('button', { name: /next|→/i }).first();
      await next.click({ timeout: 4000 }).catch(() => {});
      await page.waitForTimeout(3000);
      await label(page, 'prev-page');
      await page.getByRole('button', { name: /prev|←/i }).first().click({ timeout: 4000 }).catch(() => {});
      await page.waitForTimeout(3000);
    } },
  { name: 'roadmaps', url: '/roadmaps', auth: true, async run(page) {
      await label(page, 'hover-cards');
      const cards = page.locator('[data-testid=roadmap-card]');
      const n = Math.min(await cards.count(), 4);
      for (let i = 0; i < n; i++) { await cards.nth(i).hover().catch(() => {}); await page.waitForTimeout(500); }
    } },
  { name: 'roadmap-detail', url: '/roadmaps/house', auth: true, async run(page) {
      await label(page, 'view-list');
      await page.click('[data-testid=roadmap-view-list]', { timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(2000);
      await label(page, 'expand-step');
      await page.locator('[data-testid=roadmap-step]').first().click({ timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(2000);
      await label(page, 'view-tree');
      await page.click('[data-testid=roadmap-view-tree]', { timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(2000);
      await label(page, 'click-node');
      await page.locator('[data-testid=tree-node]').nth(1).click({ timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(2000);
    } },
  { name: 'dance-detail', url: '/dances/hip-hop/6-step', auth: true, async run(page) {
      await label(page, 'scroll');
      await page.evaluate(() => window.scrollTo(0, 800));
      await page.waitForTimeout(1500);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(1500);
    } },
  { name: 'my-dances', url: '/my-dances', auth: true, async run(page) {
      await label(page, 'tabs');
      const tabs = page.locator('button[role=tab], .tab, [class*=tab-]');
      const n = Math.min(await tabs.count(), 4);
      for (let i = 0; i < n; i++) { await tabs.nth(i).click({ timeout: 3000 }).catch(() => {}); await page.waitForTimeout(1800); }
    } },
  { name: 'practice', url: '/practice', auth: true, async run(page) {
      await page.waitForTimeout(2000);
    } },
  { name: 'nav-spa', url: '/', auth: true, async run(page) {
      for (const [l, sel] of [['to-browse', '[data-testid=nav-browse]'],
                              ['to-roadmaps', '[data-testid=nav-roadmaps]'],
                              ['to-my-dances', '[data-testid=nav-my-dances]']]) {
        await label(page, l);
        await page.click(sel, { timeout: 5000 }).catch(() => {});
        await page.waitForTimeout(2500);
      }
      await label(page, 'back');
      await page.goBack(); await page.waitForTimeout(2500);
      await label(page, 'back2');
      await page.goBack(); await page.waitForTimeout(2500);
      await label(page, 'forward');
      await page.goForward(); await page.waitForTimeout(2500);
    } },
];

const creds = await login();
const browser = await chromium.launch();
const out = [];

for (const s of SCENARIOS) {
  if (ONLY && !ONLY.includes(s.name)) continue;
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  if (s.auth) await ctx.addInitScript(([t, u]) => {
    localStorage.setItem('dp_token', t); localStorage.setItem('dp_user', u);
  }, [creds.token, JSON.stringify({ userId: creds.userId, username: creds.username })]);
  const page = await ctx.newPage();
  await page.addInitScript(PROBE);
  for (const p of ['**://*.youtube.com/**', '**://*.youtube-nocookie.com/**', '**://*.ytimg.com/**'])
    await page.route(p, r => r.abort());

  await page.goto(BASE + s.url, { waitUntil: 'commit', timeout: 45000 });
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2000);
  await label(page, 'idle');
  await page.waitForTimeout(1500);
  try { await s.run(page); } catch (e) { console.log(s.name, 'run error', String(e).slice(0, 120)); }
  const samples = await page.evaluate(() => window.__samples);
  out.push({ scenario: s.name, url: s.url, samples });
  console.log(`${s.name.padEnd(16)} samples=${samples.length}`);
  await ctx.close();
}
await browser.close();
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out));
console.log('wrote ' + OUT);
