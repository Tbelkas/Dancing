import { test, expect } from '@playwright/test';

/**
 * Glossaries signed out: the index, a style's glossary, and the learned toggle as a sign-in wall.
 *
 * Read-only. Marking a move learned is covered in authed.spec.ts, which restores what it changes.
 * Nothing asserts a specific term's wording — the glossary is authored content that gets
 * reworded. It asserts the shape, plus one slug ("jack") that is load-bearing on purpose: slugs
 * are the key learned marks hang off, so renaming it would silently wipe users' progress.
 */

test.describe('glossary', () => {
  test('the index lists House and links to it @smoke', async ({ page }) => {
    await page.goto('/glossary');
    const cards = page.getByTestId('glossary-card');
    await expect(cards.first()).toBeVisible();
    await expect(page.locator('[data-testid="glossary-card"][href="/glossary/house"]')).toBeVisible();
  });

  test('a glossary lists terms that expand into their detail', async ({ page }) => {
    await page.goto('/glossary/house');
    const terms = page.getByTestId('glossary-term');
    await expect(terms.first()).toBeVisible();
    expect(await terms.count()).toBeGreaterThan(20);

    const jack = page.locator('[data-testid="glossary-term"][data-slug="jack"]');
    await jack.locator('.term__head').click();
    await expect(jack.locator('.term__steps li').first()).toBeVisible();
  });

  test('search narrows the list', async ({ page }) => {
    await page.goto('/glossary/house');
    const terms = page.getByTestId('glossary-term');
    await expect(terms.first()).toBeVisible();
    const before = await terms.count();

    await page.getByTestId('glossary-search').fill('twist');
    await expect.poll(() => terms.count()).toBeLessThan(before);
    await expect(page.locator('[data-testid="glossary-term"][data-slug="toe-twist"]')).toBeVisible();
  });

  test('marking a move learned asks a signed-out visitor to sign in', async ({ page }) => {
    await page.goto('/glossary/house');
    await page.getByTestId('glossary-learned-toggle').first().click();
    await expect(page.getByTestId('signin-dialog')).toBeVisible();
    await expect(page.getByTestId('glossary-progress')).toHaveCount(0);
  });

  test('a #fragment link opens that term', async ({ page }) => {
    await page.goto('/glossary/house#skate');
    const skate = page.locator('[data-testid="glossary-term"][data-slug="skate"]');
    await expect(skate).toHaveClass(/is-open/);
  });
});
