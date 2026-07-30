import { test, expect } from '@playwright/test';
import { blockEmbeds } from '../fixtures/block-embeds.js';

/**
 * Roadmaps signed out: the index, and a path as the teaser it is.
 *
 * A signed-out visitor gets the tree and nothing else — no view toggle, no branch blurbs, no
 * detail panel — and touching any node opens the sign-in dialog. So everything that reads the
 * *contents* of a path (the list view, a step's videos, the segment deep-links) now lives in
 * `authed.spec.ts`; this file guards the wall itself.
 *
 * Read-only by design, and it never submits the dialog — the sign-in flow through a form is
 * covered once, in authed.spec.ts.
 *
 * Nothing here asserts a specific move name — the paths are authored content that can be re-cut.
 * It asserts the *shape*: the tree has nodes and connectors, and clicking one asks for an account.
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

  test('a path opens as a skill tree and nothing else @smoke', async ({ page }) => {
    await page.goto('/roadmaps');
    await expect(page.getByTestId('roadmap-card').first()).toBeVisible();
    await page.getByTestId('roadmap-card-link').first().click();

    await expect(page).toHaveURL(/\/roadmaps\/[a-z0-9-]+$/);
    await expect(page.getByTestId('roadmap-title')).toBeVisible();

    await expect(page.getByTestId('roadmap-tree')).toBeVisible();
    const nodes = page.getByTestId('tree-node');
    expect(await nodes.count()).toBeGreaterThan(1);

    // Connectors are what make it a tree rather than a scatter of circles. Cross-links are
    // hidden until focused, so this counts the structural ones only.
    expect(await page.locator('.tree__edge').count()).toBeGreaterThan(1);

    // The rest of the page is signed-in only. If any of these come back, the path is
    // readable without an account again and the wall below is decorative.
    await expect(page.getByTestId('roadmap-view-list')).toHaveCount(0);
    await expect(page.getByTestId('roadmap-view-tree')).toHaveCount(0);
    await expect(page.getByTestId('roadmap-detail-panel')).toHaveCount(0);
    await expect(page.getByTestId('roadmap-step')).toHaveCount(0);
    await expect(page.getByTestId('roadmap-tree-hint')).toBeVisible();
  });

  test('clicking a move asks a signed-out visitor to sign in', async ({ page }) => {
    await page.goto('/roadmaps/house');
    await expect(page.getByTestId('roadmap-title')).toBeVisible();

    const dialog = page.getByTestId('signin-dialog');
    await expect(dialog).toHaveCount(0);

    await page.getByTestId('tree-node').nth(1).click();

    // The form itself, not a bounce to /login — the visitor keeps the path they were reading.
    await expect(dialog).toBeVisible();
    await expect(page.getByTestId('signin-username')).toBeVisible();
    await expect(page.getByTestId('signin-password')).toBeVisible();
    await expect(page).toHaveURL(/\/roadmaps\/house$/);

    // Escape closes it and leaves the tree standing, rather than trapping them behind it.
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(page.getByTestId('roadmap-tree')).toBeVisible();
  });

  test('the header sign-in prompt opens the same dialog', async ({ page }) => {
    await page.goto('/roadmaps/house');
    await expect(page.getByTestId('roadmap-title')).toBeVisible();

    await page.locator('.roadmap-signin .link').click();
    await expect(page.getByTestId('signin-dialog')).toBeVisible();

    // Register is reachable in place too — most people hitting this wall have no account yet.
    await page.getByTestId('signin-dialog').getByRole('button', { name: 'Create account' }).click();
    await expect(page.getByTestId('signin-submit')).toHaveText(/create account/i);
  });

  /**
   * Validation only — deliberately no credentials, so this never posts to the auth endpoint on
   * a scheduled run. Wrong-password handling is covered once, on the /login form.
   */
  test('the dialog validates before it posts anything', async ({ page }) => {
    await page.goto('/roadmaps/house');
    await page.getByTestId('tree-node').nth(1).click();
    await expect(page.getByTestId('signin-dialog')).toBeVisible();

    await page.getByTestId('signin-submit').click();
    await expect(page.getByTestId('signin-error')).toBeVisible();
    // Still on the path, still signed out.
    await expect(page.getByTestId('nav-sign-in')).toBeVisible();
  });

  test('an unknown slug shows the not-found state, not a redirect', async ({ page }) => {
    await page.goto('/roadmaps/definitely-not-a-real-path');

    await expect(page.getByRole('heading', { name: /roadmap not found/i })).toBeVisible();
    // Staying put matters: a silent bounce to the index hides broken links.
    await expect(page).toHaveURL(/\/roadmaps\/definitely-not-a-real-path$/);
  });
});
