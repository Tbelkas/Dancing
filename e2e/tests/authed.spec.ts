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

  /**
   * Fullscreen moves the detail panel from under the tree to beside it. The panel is projected
   * into the tree component precisely so it ends up inside the fullscreen element — left as a
   * page sibling it would still exist, still pass a visibility check, and be invisible behind
   * the fullscreened tree. So this asserts containment as well as position.
   *
   * Read-only: it picks a node and toggles fullscreen, and touches no status chip.
   */
  test('fullscreen moves the detail panel beside the tree', async ({ authedPage: page }) => {
    await blockEmbeds(page);
    await page.goto('/roadmaps/house');
    await expect(page.getByTestId('roadmap-tree')).toBeVisible();

    await page.getByTestId('tree-node').nth(3).click();
    const panel = page.getByTestId('roadmap-detail-panel');
    await expect(panel).toBeVisible();

    // Stacked to begin with — the panel starts below the tree.
    const svgBefore = (await page.locator('.tree__svg').boundingBox())!;
    const panelBefore = (await panel.boundingBox())!;
    expect(panelBefore.y).toBeGreaterThan(svgBefore.y + svgBefore.height - 1);

    const button = page.getByTestId('tree-fullscreen');
    await button.click();
    await expect(button).toHaveAttribute('aria-pressed', 'true');

    expect(
      await page.evaluate(() => document.fullscreenElement!.contains(
        document.querySelector('[data-testid="roadmap-detail-panel"]'))),
      'the panel must be inside the fullscreen element or it is not on screen at all'
    ).toBe(true);

    const svgAfter = (await page.locator('.tree__svg').boundingBox())!;
    const panelAfter = (await panel.boundingBox())!;
    expect(panelAfter.x, 'the panel should sit to the right of the tree')
      .toBeGreaterThan(svgAfter.x + svgAfter.width - 1);
    expect(panelAfter.y, 'and level with the tree, not below it')
      .toBeLessThan(svgAfter.y + svgAfter.height);

    // Selecting another node has to keep updating the panel in its new home.
    await page.getByTestId('tree-node').nth(5).click();
    await expect(panel.locator('.detail__title')).not.toBeEmpty();

    await button.click();
    await expect(button).toHaveAttribute('aria-pressed', 'false');
  });

  /**
   * A panel taller than the screen used to stop dead at the bottom edge, which reads as the end
   * of the text rather than the end of the box — you'd assume you'd seen everything. The fade is
   * driven by a measured class, so this asserts the measurement: present when there is more,
   * gone at the bottom. A fade that never cleared would be just as misleading.
   *
   * The window is deliberately short so any step's panel overflows; asserting on a particular
   * move's content would tie the test to authored curriculum that gets re-cut.
   */
  test('a detail panel taller than the screen shows there is more below', async ({ authedPage: page }) => {
    await blockEmbeds(page);
    await page.setViewportSize({ width: 1100, height: 400 });
    await page.goto('/roadmaps/house');
    await expect(page.getByTestId('roadmap-tree')).toBeVisible();

    await page.getByTestId('tree-fullscreen').click();
    await expect(page.getByTestId('tree-fullscreen')).toHaveAttribute('aria-pressed', 'true');
    await page.getByTestId('tree-node').first().click();

    const aside = page.locator('.tree__aside');
    await expect(aside, 'a panel that overflows must advertise it').toHaveClass(/has-more/);

    await aside.evaluate(el => { el.scrollTop = el.scrollHeight; });
    await expect(aside, 'and stop advertising it once you reach the end').not.toHaveClass(/has-more/);
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
 * Personal skill trees — the one part of roadmaps that writes.
 *
 * ⚠️ These create rows in the real database, so every one deletes what it made, in a `finally`
 * that runs even when an assertion fails. The cleanup goes over the API rather than through the
 * UI: a test that only tidies up when the UI still works would leave a tree behind on exactly
 * the run that found a bug.
 */
test.describe('personal skill trees', () => {
  /** The bearer token the app is holding, so cleanup can call the API as the same user. */
  async function tokenOf(page: import('@playwright/test').Page): Promise<string> {
    const token = await page.evaluate(() => localStorage.getItem('dp_token'));
    expect(token, 'the auth fixture should have planted a token').toBeTruthy();
    return token!;
  }

  /** Deletes a tree by slug if it still exists. Safe to call twice. */
  async function destroy(page: import('@playwright/test').Page, slug: string): Promise<void> {
    const token = await tokenOf(page);
    const headers = { Authorization: `Bearer ${token}` };
    const found = await page.request.get(`${API_URL}/roadmaps/${slug}`, { headers });
    if (!found.ok()) return;
    await page.request.delete(`${API_URL}/roadmaps/${(await found.json()).id}`, { headers });
  }

  test('a tree can be built through the form, opened, and deleted again', async ({ authedPage: page }) => {
    await blockEmbeds(page);
    // Unique per run: two runs overlapping would otherwise fight over one slug, and the
    // second would silently be handed "…-2".
    const name = `E2E tree ${Date.now()}`;
    let slug = '';

    try {
      // In through the index, so the entry point is covered too.
      await page.goto('/roadmaps');
      await page.getByTestId('roadmap-new').click();
      await expect(page).toHaveURL(/\/roadmaps\/new$/);
      await expect(page.getByTestId('builder-title')).toBeVisible();

      // Validation happens before anything is sent, so a nameless tree never reaches the API.
      await page.getByTestId('builder-save').click();
      await expect(page.getByTestId('builder-error')).toBeVisible();

      await page.getByTestId('builder-name').fill(name);
      // House, because the move picker below is scoped to the tree's style and this one is
      // known to have a catalog behind it. No test here names a specific move — the paths are
      // authored content that can be re-cut.
      await page.getByTestId('builder-style').selectOption({ label: 'House' });

      // The blank form opens with one branch holding one move.
      const steps = page.getByTestId('builder-step');
      await expect(steps).toHaveCount(1);
      await steps.nth(0).getByRole('textbox', { name: 'Move name' }).fill('First move');

      // A second branch, so the saved tree exercises the branch grouping rather than being one
      // flat run of moves. It arrives with a blank move of its own.
      await page.getByTestId('builder-add-branch').click();
      await expect(steps).toHaveCount(2);
      await steps.nth(1).getByRole('textbox', { name: 'Move name' }).fill('Second move');

      // A third, deleted again: removing a move must take its row with it, not blank it.
      await page.getByTestId('builder-add-step').last().click();
      await expect(steps).toHaveCount(3);
      await steps.nth(2).getByTestId('builder-step-delete').click();
      await expect(steps).toHaveCount(2);

      // Wiring the second behind the first is what makes this a tree rather than a list.
      // By index, not label: index 0 is the placeholder and index 1 is the only legal option
      // (a move can't come after itself), so this asserts the filtering as well as the wiring.
      const comesAfter = steps.nth(1).getByTestId('builder-requires-add');
      await expect(comesAfter.locator('option')).toHaveCount(2);
      await comesAfter.selectOption({ index: 1 });
      await expect(steps.nth(1).locator('.req-chip')).toContainText('First move');

      // Link the first move to something in the catalog. Whatever comes back first — the
      // assertion is that the picker resolves to *a* move, not to a named one.
      await steps.nth(0).getByTestId('builder-step-link').click();
      await steps.nth(0).getByRole('textbox', { name: 'Search moves' }).fill('a');
      await steps.nth(0).locator('.picker__result').first().click();
      await expect(steps.nth(0).getByTestId('builder-step-move')).toBeVisible();

      // The preview renders from the draft, before anything is saved.
      await expect(page.getByTestId('roadmap-tree')).toBeVisible();
      await expect(page.getByTestId('tree-node')).toHaveCount(2);

      await page.getByTestId('builder-save').click();

      // A save lands on the tree itself, not back on the form. The `(?!new$)` matters: without
      // it the pattern matches the builder's own /roadmaps/new, so the assertion passes before
      // the save has navigated anywhere and `slug` below comes out as "new".
      await expect(page).toHaveURL(/\/roadmaps\/(?!new$)[a-z0-9-]+$/, { timeout: 15_000 });
      slug = page.url().split('/').pop()!;

      await expect(page.getByTestId('roadmap-title')).toHaveText(name);
      await expect(page.getByTestId('roadmap-owned-badge')).toBeVisible();
      await expect(page.getByTestId('tree-node')).toHaveCount(2);
      // Editing is the owner's, and only the owner's.
      await expect(page.getByTestId('roadmap-edit')).toBeVisible();
      await expect(page.getByTestId('roadmap-copy')).toHaveCount(0);

      // It shows up on the index under the user's own section.
      await page.goto('/roadmaps');
      await expect(page.getByTestId('my-roadmaps')).toContainText(name);

      // Delete through the UI, which is the only place a user can do it. The confirm step
      // exists so a stray click can't cost a tree — assert it's actually there.
      await page.goto(`/roadmaps/${slug}`);
      // The owner controls only render once the roadmap has loaded and come back as theirs;
      // clicking straight after the navigation races that fetch.
      await expect(page.getByTestId('roadmap-owned-badge')).toBeVisible();
      await page.getByTestId('roadmap-delete').click();
      await page.getByTestId('roadmap-delete-confirm').click();

      await expect(page).toHaveURL(/\/roadmaps$/, { timeout: 15_000 });
      await expect(page.getByTestId('roadmap-card').first()).toBeVisible();
      await expect(page.locator('body')).not.toContainText(name);
    } finally {
      if (slug) await destroy(page, slug);
    }
  });

  test('a curated path can be forked into an editable copy', async ({ authedPage: page }) => {
    await blockEmbeds(page);
    let slug = '';

    try {
      await page.goto('/roadmaps/house');
      await expect(page.getByTestId('roadmap-title')).toBeVisible();
      // A curated path is never editable in place, however you are signed in.
      await expect(page.getByTestId('roadmap-edit')).toHaveCount(0);

      await page.getByTestId('roadmap-copy').click();

      // The fork opens in the builder, ready to cut about.
      await expect(page).toHaveURL(/\/roadmaps\/[a-z0-9-]+\/edit$/, { timeout: 15_000 });
      slug = page.url().split('/').slice(-2)[0];
      expect(slug, 'the copy must get its own slug, not the curated one').not.toBe('house');

      await expect(page.getByTestId('builder-name')).toHaveValue(/House/);
      // The structure comes with it — a fork that arrived empty would be a blank page with
      // extra steps.
      expect(await page.getByTestId('builder-step').count()).toBeGreaterThan(1);
    } finally {
      if (slug) await destroy(page, slug);
    }
  });

  test('the builder refuses a path the user does not own', async ({ authedPage: page }) => {
    // Read-only: nothing is created, so there is nothing to clean up.
    await page.goto('/roadmaps/house/edit');
    await expect(page.getByRole('heading', { name: /not yours to edit/i })).toBeVisible();
    await expect(page.getByTestId('builder-name')).toHaveCount(0);
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
