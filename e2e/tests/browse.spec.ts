import { test, expect, type Page } from '@playwright/test';

/**
 * Browse page: search, filters, sort, pagination, URL sync.
 *
 * These assert *behaviour*, never specific dance names — the catalog is curated and
 * reseeded, so "Bachata is on page 1" would be a test that rots on its own.
 */

/**
 * Waits for the grid to hold real cards. `results-count` becoming visible is not enough:
 * it renders as a skeleton during the first load, so counting cards at that moment
 * reliably returns 0.
 */
async function waitForCards(page: Page) {
  await expect(page.getByTestId('dance-card').first()).toBeVisible();
}

/**
 * The filter panel is collapsed behind a "Filters" toggle only at <=720px; on desktop the
 * toggle is display:none and the panel is always open. Click it only when it's really there.
 */
async function openFilters(page: Page) {
  const toggle = page.getByRole('button', { name: 'Filters' });
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
}

test.describe('browse', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dances');
    await expect(page.getByTestId('results-count')).toBeVisible();
  });

  test('renders a grid of dances @smoke', async ({ page }) => {
    const cards = page.getByTestId('dance-card');
    await expect(cards.first()).toBeVisible();
    expect(await cards.count()).toBeGreaterThan(0);

    // The count text should report a real number, not the "0 dances" empty state.
    await expect(page.getByTestId('results-count')).toContainText(/\d/);
    await expect(page.getByTestId('results-count')).not.toContainText(/^0 dances$/);
  });

  test('search narrows the result set and survives a reload', async ({ page }) => {
    await waitForCards(page);
    const before = await page.getByTestId('dance-card').count();
    expect(before).toBeGreaterThan(0);

    await page.getByTestId('search-input').fill('salsa');
    // Search is debounced and writes through to the query string.
    await expect(page).toHaveURL(/[?&]q=salsa/, { timeout: 10_000 });

    const cards = page.getByTestId('dance-card');
    await expect(cards.first()).toBeVisible();
    expect(await cards.count()).toBeLessThanOrEqual(before);

    // URL is the source of truth: a reload must restore the same search.
    await page.reload();
    await expect(page.getByTestId('search-input')).toHaveValue('salsa');
  });

  test('a search with no matches shows the empty state, not a broken grid', async ({ page }) => {
    await page.getByTestId('search-input').fill('zzzznotarealdancezzzz');
    await expect(page.getByTestId('empty-state')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId('dance-card')).toHaveCount(0);
  });

  test('style filter applies and is clearable', async ({ page }) => {
    await openFilters(page);

    // Skip "All" (index 0) — pick the first real style pill.
    const stylePill = page.locator('.style-filters .filter-pill').nth(1);
    await expect(stylePill).toBeVisible();
    const styleName = (await stylePill.textContent())?.trim() ?? '';
    await stylePill.click();

    await expect(page).toHaveURL(/[?&]style=\d+/);
    await expect(page.getByTestId('dance-card').first()).toBeVisible();

    // The active-filter chip is the user's escape hatch; it must reflect the choice.
    const chip = page.locator('.active-chip', { hasText: styleName });
    await expect(chip).toBeVisible();
    await page.getByRole('button', { name: 'Clear all' }).click();
    await expect(page).not.toHaveURL(/[?&]style=\d/);
  });

  test('sort order is applied and reflected in the URL', async ({ page }) => {
    await waitForCards(page);
    const firstBefore = await page.getByTestId('dance-card-link').first().textContent();

    await page.getByTestId('sort-select').selectOption('name');
    await expect(page).toHaveURL(/[?&]sort=name/);

    // Compare only initial letters, stripped of accents and punctuation. A full ordering
    // check would be asserting Postgres's collation, which legitimately disagrees with JS
    // localeCompare on spaces and diacritics ("Airfreeze" vs "Air Walk" vs "À la seconde") —
    // that's a collation difference, not a bug, and would make this test permanently red.
    const initial = (name: string) =>
      name.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]/gi, '').toLowerCase().charAt(0);

    // The URL updates immediately but the re-query is still in flight — poll rather than
    // asserting once against the stale grid.
    await expect.poll(async () => {
      const names = await page.getByTestId('dance-card-link').allTextContents();
      const letters = names.map(n => initial(n.trim())).filter(Boolean);
      if (letters.length < 2) return false;
      return letters.every((letter, i) => i === 0 || letters[i - 1] <= letter);
    }, { message: 'dance names should render in alphabetical order' }).toBe(true);

    // ...and the order actually changed from the default "recommended" ranking.
    expect(await page.getByTestId('dance-card-link').first().textContent()).not.toBe(firstBefore);
  });

  test('pagination moves to page 2 and keeps the page in the URL', async ({ page }) => {
    // Wait for the grid first — the pager renders alongside the cards, so checking for it
    // before they load would skip this test on every run instead of running it.
    await waitForCards(page);

    const pager = page.locator('.pagination');
    // Nothing to assert on a single-page catalog; don't fake a failure.
    test.skip(await pager.count() === 0, 'catalog fits on one page');

    const firstBefore = await page.getByTestId('dance-card-link').first().textContent();
    await page.getByRole('button', { name: 'Next page' }).click();

    await expect(page).toHaveURL(/[?&]page=2/);
    // The grid keeps the previous page's cards in place (dimmed) while the next page loads,
    // so poll for the turnover rather than reading straight after the URL changes.
    await expect
      .poll(() => page.getByTestId('dance-card-link').first().textContent(),
            { message: 'page 2 should render different dances than page 1' })
      .not.toBe(firstBefore);
  });

  test('clicking a dance card opens its detail page', async ({ page }) => {
    const link = page.getByTestId('dance-card-link').first();
    const name = (await link.textContent())?.trim();
    await link.click();

    await expect(page).toHaveURL(/\/dances\/.+/);
    await expect(page.getByTestId('dance-title')).toHaveText(name!);
  });
});
