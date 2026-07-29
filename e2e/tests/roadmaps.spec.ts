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
 * re-cut. It asserts the *shape*: the tree has nodes and connectors, branches have headings,
 * linked steps offer videos, and a step's link lands on that move's dance page.
 *
 * The tree is the default view; tests that need every step's videos on screen at once switch
 * to the list first rather than clicking around the fan.
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

  test('a path opens as a skill tree @smoke', async ({ page }) => {
    await page.goto('/roadmaps');
    await expect(page.getByTestId('roadmap-card').first()).toBeVisible();
    await page.getByTestId('roadmap-card-link').first().click();

    await expect(page).toHaveURL(/\/roadmaps\/[a-z0-9-]+$/);
    await expect(page.getByTestId('roadmap-title')).toBeVisible();

    // Tree is the default view.
    await expect(page.getByTestId('roadmap-tree')).toBeVisible();
    const nodes = page.getByTestId('tree-node');
    expect(await nodes.count()).toBeGreaterThan(1);

    // Connectors are what make it a tree rather than a scatter of circles. Cross-links are
    // hidden until focused, so this counts the structural ones only.
    expect(await page.locator('.tree__edge').count()).toBeGreaterThan(1);

    // Clicking a node fills the detail panel with that move.
    await nodes.nth(1).click();
    await expect(page.getByTestId('roadmap-detail-panel')).toBeVisible();
    await expect(page.getByTestId('roadmap-detail-panel').locator('.detail__title')).not.toBeEmpty();
  });

  test('the list view is reachable and shows the same steps as branches', async ({ page }) => {
    await page.goto('/roadmaps/house');
    await expect(page.getByTestId('roadmap-title')).toBeVisible();

    await page.getByTestId('roadmap-view-list').click();
    const steps = page.getByTestId('roadmap-step');
    await expect(steps.first()).toBeVisible();
    expect(await steps.count()).toBeGreaterThan(1);
    // A path with no branch headings is a flat list, not a roadmap.
    expect(await page.locator('.stage__title').count()).toBeGreaterThan(0);

    // The choice sticks — it's a strong preference either way.
    await page.reload();
    await expect(page.getByTestId('roadmap-step').first()).toBeVisible();
    await expect(page.getByTestId('roadmap-tree')).toHaveCount(0);

    // Put it back so a later test (and the next scheduled run) starts on the tree.
    await page.getByTestId('roadmap-view-tree').click();
    await expect(page.getByTestId('roadmap-tree')).toBeVisible();
  });

  test('steps backed by a move show their videos and link to the move', async ({ page }) => {
    await page.goto('/roadmaps');
    await expect(page.getByTestId('roadmap-card').first()).toBeVisible();
    await page.getByTestId('roadmap-card-link').first().click();
    await expect(page.getByTestId('roadmap-title')).toBeVisible();
    // The list view is where every step's videos are on screen at once.
    await page.getByTestId('roadmap-view-list').click();

    // Videos are expanded by default, so the first linked step should already show some.
    const videoLists = page.getByTestId('roadmap-step-videos');
    await expect(videoLists.first()).toBeVisible();

    const firstVideo = videoLists.first().locator('a.video__link').first();
    await expect(firstVideo).toHaveAttribute('href', /\/dances\/[a-z0-9-]+\/[a-z0-9-]+\?v=\d+/);

    await firstVideo.click();
    await expect(page.getByTestId('dance-title')).toBeVisible();
  });

  /**
   * Steps can be pinned to one section of a longer tutorial (`segmentLabel` in the authored
   * JSON). Those must deep-link with a `t=` offset, or the user lands at 0:00 of a 12-minute
   * video and has to hunt for the part the step is about.
   */
  test('a step pinned to a video section deep-links to that timestamp', async ({ page }) => {
    await page.goto('/roadmaps/waacking');
    await expect(page.getByTestId('roadmap-title')).toBeVisible();
    await page.getByTestId('roadmap-view-list').click();

    const clipLink = page.locator('a.video__link[href*="t="]').first();
    await expect(clipLink).toBeVisible();
    await expect(clipLink).toHaveAttribute('href', /\/dances\/[a-z0-9-]+\/[a-z0-9-]+\?v=\d+&t=\d+/);

    await clipLink.click();
    await expect(page.getByTestId('dance-title')).toBeVisible();
    await expect(page).toHaveURL(/[?&]t=\d+/);
  });

  test('an unknown slug shows the not-found state, not a redirect', async ({ page }) => {
    await page.goto('/roadmaps/definitely-not-a-real-path');

    await expect(page.getByRole('heading', { name: /roadmap not found/i })).toBeVisible();
    // Staying put matters: a silent bounce to the index hides broken links.
    await expect(page).toHaveURL(/\/roadmaps\/definitely-not-a-real-path$/);
  });
});
