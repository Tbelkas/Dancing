import { test, expect } from '../fixtures/auth.js';
import { USERNAME, PASSWORD, API_URL } from '../fixtures/env.js';
import { test as base, expect as baseExpect } from '@playwright/test';
import { blockEmbeds } from '../fixtures/block-embeds.js';

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

  /**
   * The undo toast, exercised on the one deletion that touches nothing but localStorage.
   * The other undoable deletes (video, choreo, practice session, note) share the same
   * ToastService machinery but would write to the production database, so this stands in
   * for all of them — see the file header.
   *
   * The card is seeded rather than earned by browsing: "Recently viewed" is built from
   * a local trail, so a synthetic entry gives the test a card that is guaranteed present
   * and belongs to no real dance.
   */
  test('dismissing a Recently viewed card offers an undo that puts it back', async ({ authedPage: page }) => {
    const probe = {
      id: 999_001,
      name: 'E2E Undo Probe',
      slug: 'e2e-undo-probe',
      styleSlug: 'hip-hop',
      styleName: 'Hip-hop',
      viewedAt: Date.now(),
      learned: false,
    };
    await page.addInitScript(entry => {
      localStorage.setItem('dp_recent_dances', JSON.stringify([entry]));
    }, probe);

    await page.goto('/my-dances');
    const card = page.locator('.continue-card', { hasText: probe.name });
    await expect(card).toBeVisible();

    await page.getByLabel(`Remove ${probe.name} from Recently viewed`).click();
    await expect(card, 'the card should go straight away, before any undo window closes').toHaveCount(0);

    const undo = page.getByTestId('toast-undo');
    await expect(undo).toBeVisible();
    await undo.click();

    await expect(card, 'undo should restore the dismissed card').toBeVisible();
    await expect(undo, 'the toast should close once undo is taken').toHaveCount(0);
  });

  test('a dismissal left alone sticks once the undo window closes', async ({ authedPage: page }) => {
    const probe = {
      id: 999_002,
      name: 'E2E Expiry Probe',
      slug: 'e2e-expiry-probe',
      styleSlug: 'hip-hop',
      viewedAt: Date.now(),
      learned: false,
    };
    await page.addInitScript(entry => {
      localStorage.setItem('dp_recent_dances', JSON.stringify([entry]));
    }, probe);

    await page.goto('/my-dances');
    await page.getByLabel(`Remove ${probe.name} from Recently viewed`).click();

    // Toast self-closes after its window; the removal must survive it.
    await expect(page.getByTestId('toast-undo')).toHaveCount(0, { timeout: 15_000 });
    await expect(page.locator('.continue-card', { hasText: probe.name })).toHaveCount(0);
    expect(await page.evaluate(() => localStorage.getItem('dp_recent_dances'))).not.toContain(probe.name);
  });

  /**
   * "By style" regroups the same local trail — nothing server-side — so a pair of synthetic
   * entries in two styles is enough to prove the grouping and that the choice is remembered.
   */
  test('Recently viewed can be regrouped by style, and remembers the choice', async ({ authedPage: page }) => {
    const probes = [
      { id: 999_003, name: 'E2E Group Probe House', slug: 'e2e-group-house', styleSlug: 'house', styleName: 'House', viewedAt: Date.now(), learned: false },
      { id: 999_004, name: 'E2E Group Probe Hip-hop', slug: 'e2e-group-hiphop', styleSlug: 'hip-hop', styleName: 'Hip-hop', viewedAt: Date.now() - 1000, learned: false },
    ];
    await page.addInitScript(entries => {
      localStorage.setItem('dp_recent_dances', JSON.stringify(entries));
      // This runs on the reload too, so only force the starting state once — otherwise it
      // would undo the very toggle the reload is meant to prove was remembered.
      if (!sessionStorage.getItem('e2e_grouping_seeded')) {
        sessionStorage.setItem('e2e_grouping_seeded', '1');
        localStorage.removeItem('dp_continue_grouped');
      }
    }, probes);

    await page.goto('/my-dances');
    const toggle = page.getByRole('button', { name: 'By style' });
    await expect(toggle).toHaveAttribute('aria-pressed', 'false');
    await expect(page.locator('.continue-group')).toHaveCount(0);

    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-pressed', 'true');

    // One group per style, most recently viewed first, each holding its own card.
    const groups = page.locator('.continue-group');
    await expect(groups).toHaveCount(2);
    await expect(groups.first().locator('.continue-group__name')).toHaveText('House');
    await expect(groups.first().locator('.continue-card')).toHaveText(/E2E Group Probe House/);
    await expect(groups.nth(1).locator('.continue-group__name')).toHaveText('Hip-hop');

    // The grouping survives a reload — it is stored, not just component state.
    await page.reload();
    await expect(page.locator('.continue-group')).toHaveCount(2);
    await expect(page.getByRole('button', { name: 'By style' })).toHaveAttribute('aria-pressed', 'true');
  });

  /**
   * Read-only on purpose. The "Learned" chip writes the same production status a real user
   * sets, so this asserts the signed-in affordances exist and never clicks them — the toggle
   * itself is already covered on the dance detail page, where it can be restored cleanly.
   */
  test('a path shows progress and per-step status chips when signed in', async ({ authedPage: page }) => {
    await page.goto('/roadmaps');
    await page.getByTestId('roadmap-card-link').first().click();
    await expect(page.getByTestId('roadmap-title')).toBeVisible();

    await expect(page.getByTestId('roadmap-progress')).toBeVisible();
    await expect(page.getByTestId('roadmap-progress')).toContainText(/\d+ of \d+ learned/);

    // Every step backed by a catalog move offers the status chips; unlinked steps do not.
    const learnedChips = page.getByTestId('roadmap-step-learned');
    await expect(learnedChips.first()).toBeVisible();
    expect(await learnedChips.count()).toBeGreaterThan(0);
  });

  /**
   * The contents of a path — the view toggle, the branch headings, every step's videos — are
   * signed-in only; a signed-out visitor gets the bare tree (see roadmaps.spec.ts). The three
   * tests below therefore live here rather than in the anon suite. All read-only: they click
   * through the path but never touch a status chip.
   */
  test('a path detail panel fills in when a move is picked off the tree', async ({ authedPage: page }) => {
    await blockEmbeds(page);
    await page.goto('/roadmaps/house');
    await expect(page.getByTestId('roadmap-title')).toBeVisible();
    await expect(page.getByTestId('roadmap-tree')).toBeVisible();

    await page.getByTestId('tree-node').nth(1).click();
    await expect(page.getByTestId('roadmap-detail-panel')).toBeVisible();
    await expect(page.getByTestId('roadmap-detail-panel').locator('.detail__title')).not.toBeEmpty();
  });

  test('the list view is reachable and shows the same steps as branches', async ({ authedPage: page }) => {
    await blockEmbeds(page);
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

  test('steps backed by a move show their videos and link to the move', async ({ authedPage: page }) => {
    await blockEmbeds(page);
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
  test('a step pinned to a video section deep-links to that timestamp', async ({ authedPage: page }) => {
    await blockEmbeds(page);
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
