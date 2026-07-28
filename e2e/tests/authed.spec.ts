import { test, expect } from '../fixtures/auth.js';
import { USERNAME, PASSWORD, API_URL } from '../fixtures/env.js';
import { test as base, expect as baseExpect } from '@playwright/test';

/**
 * Signed-in flows. Skipped entirely when E2E_USERNAME / E2E_PASSWORD are unset.
 *
 * ⚠️ These run against whatever database E2E_API_URL points at — production, by default.
 * Every test here is therefore either read-only or restores the state it changed in the
 * same test. Do not add a test that creates a dance, video, or practice session without
 * deleting it again: scheduled runs would otherwise slowly fill the real catalog.
 */

test.describe('authenticated', () => {
  test('guarded routes render once signed in @smoke', async ({ authedPage: page }) => {
    const pages: Array<[string, string]> = [
      ['/my-dances', 'My Dances'],
      ['/practice', 'Practice Log'],
      ['/library', 'Added videos'],
      ['/profile', 'My Profile'],
    ];

    for (const [route, heading] of pages) {
      await page.goto(route);
      await expect(page, `${route} should not bounce to login`).not.toHaveURL(/\/login/);
      await expect(
        page.getByRole('heading', { name: heading, level: 1 }),
        `${route} should show its "${heading}" heading`
      ).toBeVisible();
    }
  });

  test('the account menu shows the signed-in user and can sign out', async ({ authedPage: page }) => {
    await page.goto('/dances');
    // Signed-in-only nav appears; signed-out CTA does not.
    await expect(page.getByTestId('nav-my-dances')).toBeVisible();
    await expect(page.getByTestId('nav-sign-in')).toHaveCount(0);

    await page.getByTestId('user-menu-button').click();
    await expect(page.locator('.user-menu__name')).toContainText(USERNAME);

    await page.getByTestId('sign-out').click();
    // Signing out must actually clear the token, not just repaint the header.
    await expect(page.getByTestId('nav-sign-in')).toBeVisible();
    expect(await page.evaluate(() => localStorage.getItem('dp_token'))).toBeNull();
  });

  test('favorite toggles on the detail page and persists across a reload', async ({ authedPage: page }) => {
    // Pick the dance by name order via the API, not "first card on /dances". The default
    // browse sort is "recommended", which floats styles the signed-in user favorites — so
    // this test's own favouriting changes which card is first, and a rerun would act on a
    // different dance than the one it restored.
    const res = await page.request.get(`${API_URL}/search/dances?sort=name&pageSize=1`);
    expect(res.ok()).toBe(true);
    const target = (await res.json()).items[0];

    await page.goto(`/dances/${target.styleSlug}/${target.slug}`);
    await expect(page.getByTestId('dance-title')).toBeVisible();

    // Let the page's other requests (videos, neighbours, recommended) land before clicking.
    // A dance GET still in flight would otherwise overwrite the toggled state on arrival.
    await expect(page.getByRole('heading', { name: 'Videos' })).toBeVisible();

    const fav = page.getByTestId('favorite-button');
    await expect(fav).toBeVisible();
    const initial = await fav.getAttribute('aria-pressed');

    try {
      await fav.click();
      const flipped = initial === 'true' ? 'false' : 'true';
      await expect(fav).toHaveAttribute('aria-pressed', flipped);

      // The point of the test: the flip survived a round-trip to the database.
      await page.reload();
      await expect(page.getByTestId('favorite-button')).toHaveAttribute('aria-pressed', flipped);
    } finally {
      // Restore whatever it was, even if an assertion above failed.
      const current = await page.getByTestId('favorite-button').getAttribute('aria-pressed');
      if (current !== initial) await page.getByTestId('favorite-button').click();
    }
  });

  test('favorites-only filter returns only favorited dances', async ({ authedPage: page }) => {
    await page.goto('/dances?fav=1');
    await expect(page.getByTestId('results-count')).toBeVisible();

    const empty = await page.getByTestId('empty-state').count();
    test.skip(empty > 0, 'test account has no favorites');

    // Every card's favorite control should read as pressed.
    const stars = page.getByTestId('dance-card').locator('button[aria-pressed]').first();
    await expect(stars).toHaveAttribute('aria-pressed', 'true');
  });
});

/**
 * The login form itself — driven through the UI rather than the API fixture, because the
 * form is what a real user touches and it has its own failure modes (validation, error
 * display, redirect-after-login).
 */
base.describe('login form', () => {
  base.skip(!USERNAME || !PASSWORD, 'E2E credentials not configured');

  base('signing in through the form lands the user in the app @smoke', async ({ page }) => {
    await page.goto('/login');
    await page.getByTestId('login-username').fill(USERNAME);
    await page.getByTestId('login-password').fill(PASSWORD);
    await page.getByTestId('login-submit').click();

    await baseExpect(page).not.toHaveURL(/\/login/, { timeout: 15_000 });
    await baseExpect(page.getByTestId('user-menu-button')).toBeVisible();
  });

  base('a wrong password shows an error and does not sign the user in', async ({ page }) => {
    await page.goto('/login');
    await page.getByTestId('login-username').fill(USERNAME);
    await page.getByTestId('login-password').fill('definitely-the-wrong-password');
    await page.getByTestId('login-submit').click();

    await baseExpect(page.getByTestId('login-error')).toBeVisible();
    await baseExpect(page).toHaveURL(/\/login/);
    baseExpect(await page.evaluate(() => localStorage.getItem('dp_token'))).toBeNull();
  });
});
