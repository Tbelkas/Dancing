import { test, expect } from '@playwright/test';
import { blockEmbeds } from '../fixtures/block-embeds.js';

/**
 * Roadmaps: the index and one path end to end, signed out.
 *
 * Read-only by design. The status chips on a step write to the production database
 * (they set the same learned/in-progress flags as the dance page), so they are only
 * rendered for a signed-in user and this suite never touches them.
 *
 * Nothing here asserts a specific move name — the paths are authored content that can be
 * re-cut. It asserts the *shape*: stages contain numbered steps, linked steps offer videos,
 * and a step's link lands on that move's dance page.
 */

test.describe('roadmaps', () => {
  test.beforeEach(async ({ page }) => {
    // No test here plays an embed; keep YouTube out so a slow third party can't
    // time out an assertion about the path.
    await blockEmbeds(page);
  });

  test('the index lists paths and each links to its own page @smoke', async ({ page }) => {
    await page.goto('/roadmaps');

    const cards = page.getByTestId('roadmap-card');
    await expect(cards.first()).toBeVisible();
    expect(await cards.count()).toBeGreaterThan(0);

    // Every card must name a real path and route to it — a card with no href is the
    // failure mode when the summary DTO loses its slug.
    const first = cards.first().getByTestId('roadmap-card-link');
    await expect(first).toHaveAttribute('href', /\/roadmaps\/[a-z0-9-]+$/);
  });

  test('a path renders stages of numbered steps @smoke', async ({ page }) => {
    await page.goto('/roadmaps');
    await expect(page.getByTestId('roadmap-card').first()).toBeVisible();
    await page.getByTestId('roadmap-card-link').first().click();

    await expect(page).toHaveURL(/\/roadmaps\/[a-z0-9-]+$/);
    await expect(page.getByTestId('roadmap-title')).toBeVisible();

    const steps = page.getByTestId('roadmap-step');
    await expect(steps.first()).toBeVisible();
    expect(await steps.count()).toBeGreaterThan(1);

    // A path with no stage headings is a flat list, not a roadmap.
    expect(await page.locator('.stage__title').count()).toBeGreaterThan(0);
  });

  test('steps backed by a move show their videos and link to the move', async ({ page }) => {
    await page.goto('/roadmaps');
    await expect(page.getByTestId('roadmap-card').first()).toBeVisible();
    await page.getByTestId('roadmap-card-link').first().click();
    await expect(page.getByTestId('roadmap-title')).toBeVisible();

    // Videos are expanded by default, so the first linked step should already show some.
    const videoLists = page.getByTestId('roadmap-step-videos');
    await expect(videoLists.first()).toBeVisible();

    const firstVideo = videoLists.first().locator('a.video__link').first();
    await expect(firstVideo).toHaveAttribute('href', /\/dances\/[a-z0-9-]+\/[a-z0-9-]+\?v=\d+/);

    await firstVideo.click();
    await expect(page.getByTestId('dance-title')).toBeVisible();
  });

  test('an unknown slug shows the not-found state, not a redirect', async ({ page }) => {
    await page.goto('/roadmaps/definitely-not-a-real-path');

    await expect(page.getByRole('heading', { name: /roadmap not found/i })).toBeVisible();
    // Staying put matters: a silent bounce to the index hides broken links.
    await expect(page).toHaveURL(/\/roadmaps\/definitely-not-a-real-path$/);
  });
});
