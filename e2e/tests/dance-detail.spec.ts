import { test, expect, type Page } from '@playwright/test';
import { API_URL } from '../fixtures/env.js';

/**
 * Dance detail page, signed out. The most valuable assertion here is that a dance with
 * videos actually mounts a player — a broken embed is invisible to the API tests and is
 * the whole point of the product.
 */

/** Opens the first dance in the catalog and returns its name. */
async function openFirstDance(page: Page): Promise<string> {
  await page.goto('/dances');
  const link = page.getByTestId('dance-card-link').first();
  await expect(link).toBeVisible();
  const name = (await link.textContent())?.trim() ?? '';
  await link.click();
  await expect(page.getByTestId('dance-title')).toBeVisible();
  return name;
}

test.describe('dance detail', () => {
  test('shows title, metadata and a videos section @smoke', async ({ page }) => {
    const name = await openFirstDance(page);

    await expect(page.getByTestId('dance-title')).toHaveText(name);
    // exact: the videos section is headed "Videos", and a dance holding more than one also
    // carries an "All N videos" sub-heading over the list under the player. A substring match
    // hits both and fails strict mode, on whichever dance the browse rotation happens to lead
    // with that day.
    await expect(page.getByRole('heading', { name: 'Videos', exact: true })).toBeVisible();
    // Page title should follow the dance, not stay on the browse title.
    await expect(page).toHaveTitle(new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'));
  });

  test('a dance with videos mounts a player embed', async ({ page }) => {
    // Ask the API for a dance that definitely has videos rather than hoping the first card
    // of some sort order does. Relying on ordering made this test skip itself instead of run.
    const res = await page.request.get(`${API_URL}/search/dances?sort=tutorials&pageSize=20`);
    expect(res.ok()).toBe(true);
    const withVideo = (await res.json()).items.find((d: { videoCount: number }) => d.videoCount > 0);
    expect(withVideo, 'catalog should contain at least one dance with a video').toBeTruthy();

    await page.goto(`/dances/${withVideo.styleSlug}/${withVideo.slug}`);
    await expect(page.getByTestId('dance-title')).toBeVisible();

    // Either a third-party embed or the app's own player surface.
    const embed = page.locator(
      'iframe[src*="youtube"], iframe[src*="tiktok"], iframe[src*="instagram"], app-video-player, app-local-video-player'
    );
    await expect(embed.first()).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('.empty', { hasText: 'No videos available' })).toHaveCount(0);
  });

  test('a signed-out visitor can open the report form on the playing video', async ({ page }) => {
    // Deliberately stops at "open, then cancel". Sending would write a real VideoFlag row to
    // the production database, and a scheduled run repeats forever -- the suite's rule is that
    // an authed or write-capable test restores whatever it changed, and the cheapest way to
    // obey it here is not to write at all. What matters is that the control reaches an
    // anonymous viewer, which is the whole reason it isn't behind a sign-in.
    const res = await page.request.get(`${API_URL}/search/dances?sort=tutorials&pageSize=20`);
    expect(res.ok()).toBe(true);
    const withVideo = (await res.json()).items.find((d: { videoCount: number }) => d.videoCount > 0);
    expect(withVideo, 'catalog should contain at least one dance with a video').toBeTruthy();

    await page.goto(`/dances/${withVideo.styleSlug}/${withVideo.slug}`);
    await expect(page.getByTestId('dance-title')).toBeVisible();

    const trigger = page.getByTestId('report-video-open');
    await expect(trigger).toBeVisible({ timeout: 15_000 });
    await trigger.click();

    await expect(page.getByTestId('report-video-detail')).toBeVisible();
    // Nothing picked yet, so there is nothing to send.
    await expect(page.getByTestId('report-video-send')).toBeDisabled();

    await page.getByRole('radio', { name: "It won't play" }).check();
    await expect(page.getByTestId('report-video-send')).toBeEnabled();

    await page.getByRole('button', { name: 'Cancel' }).click();
    await expect(page.getByTestId('report-video-detail')).toHaveCount(0);
  });

  test('favorite and progress controls are hidden when signed out', async ({ page }) => {
    await openFirstDance(page);
    await expect(page.getByTestId('favorite-button')).toHaveCount(0);
    await expect(page.getByTestId('progress-learned')).toHaveCount(0);
  });

  test('prev/next pager navigates within the style', async ({ page }) => {
    const name = await openFirstDance(page);

    // Neighbours arrive in their own request; give them a bounded chance to render before
    // concluding this dance genuinely has none, or the test would always skip.
    await page.locator('.dance-pager').waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {});

    const next = page.locator('.dance-pager__link--next');
    test.skip(await next.count() === 0, 'dance is at the end of its style');

    await next.click();
    await expect(page.getByTestId('dance-title')).toBeVisible();
    await expect(page.getByTestId('dance-title')).not.toHaveText(name);
  });

  test('a nonexistent dance slug shows the not-found panel, not a crash', async ({ page }) => {
    await page.goto('/dances/definitely-not-a-real-dance-slug-xyz');
    await expect(page.locator('.dance-missing__msg')).toBeVisible();
  });
});
