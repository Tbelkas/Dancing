import { test, expect, type Page } from '@playwright/test';
import { blockEmbeds } from '../fixtures/block-embeds.js';

/**
 * The "is the site up and not broken" pass. Every test here must pass against a healthy
 * production deploy at any time, signed out, with no test data assumptions.
 *
 * This file runs under both the `anon` (desktop) and `mobile` projects, so nothing here may
 * assume a viewport — see `revealNav` below.
 *
 * Tagged @smoke — `npm run test:smoke` runs just these for a fast post-deploy check.
 */

/**
 * Below 720px the primary nav collapses behind the hamburger, so its links are genuinely
 * hidden until it's opened. Open it when needed so the same test is meaningful on both
 * viewports instead of asserting desktop-only markup.
 */
async function revealNav(page: Page) {
  const browse = page.getByTestId('nav-browse');
  if (await browse.isVisible().catch(() => false)) return;
  const toggle = page.getByRole('button', { name: 'Toggle navigation menu' });
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
}

test.describe('shell + routing @smoke', () => {
  // None of these test an embed. Keeping third-party iframes out makes the run faster and
  // stops a slow YouTube from timing out an assertion about our own shell.
  test.beforeEach(async ({ page }) => {
    await blockEmbeds(page);
  });

  // A JS error on load means the SPA bundle is broken even if HTML renders.
  test('loads the browse page without console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
    page.on('pageerror', err => errors.push(err.message));

    await page.goto('/dances');
    await expect(page.getByTestId('results-count')).toBeVisible();

    // Ignore noise from third-party embeds (YouTube/TikTok iframes log freely) and from
    // blocked trackers; we only care about errors coming from our own bundle.
    const ours = errors.filter(e =>
      !/youtube|ytimg|tiktok|instagram|doubleclick|ERR_BLOCKED_BY_CLIENT/i.test(e));
    expect(ours, `console errors: ${ours.join(' | ')}`).toHaveLength(0);
  });

  test('landing page renders and links into the catalog', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Dance Platform/);
    await revealNav(page);
    await page.getByTestId('nav-browse').click();
    await expect(page).toHaveURL(/\/dances/);
  });

  test('the roadmaps destination is reachable from the nav', async ({ page }) => {
    await page.goto('/dances');
    await revealNav(page);
    await page.getByTestId('nav-roadmaps').click();
    await expect(page).toHaveURL(/\/roadmaps/);
    await expect(page.getByTestId('roadmap-card').first()).toBeVisible();
  });

  test('unknown route shows the 404 page, not a blank shell', async ({ page }) => {
    await page.goto('/this-route-does-not-exist');
    await expect(page).toHaveTitle(/Page not found/);
    // The shell must survive — a 404 that loses the header means SPA fallback is misconfigured.
    // The logo is in the header at every viewport, unlike the nav links.
    await expect(page.locator('.header__logo')).toBeVisible();
  });

  test('deep-linking straight to a dance page works (SPA fallback)', async ({ page }) => {
    // Reaching a dance URL directly (not via client-side routing) is what breaks when
    // Apache stops rewriting unknown paths to index.html.
    await page.goto('/dances');
    const first = page.getByTestId('dance-card-link').first();
    await expect(first).toBeVisible();
    const href = await first.getAttribute('href');
    expect(href).toBeTruthy();

    await page.goto(href!);
    await expect(page.getByTestId('dance-title')).toBeVisible();
  });

  test('signed-out visitors are redirected away from guarded routes @smoke', async ({ page }) => {
    for (const route of ['/my-dances', '/practice', '/library', '/choreos', '/profile']) {
      await page.goto(route);
      await expect(page, `${route} should not render signed out`).toHaveURL(/\/login/);
    }
  });

  test('admin-only route is not reachable signed out', async ({ page }) => {
    await page.goto('/admin/add-video');
    await expect(page).not.toHaveURL(/\/admin\/add-video/);
  });
});
