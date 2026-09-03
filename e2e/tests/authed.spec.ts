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

  test('the account card shows the recovery address and offers a password change', async ({ authedPage: page }) => {
    await page.goto('/profile');
    const card = page.getByTestId('account-card');
    await expect(card).toBeVisible();

    // This account has an address, so the "cannot be recovered" warning must NOT be here —
    // its presence would mean the profile is reading the field wrong.
    await expect(page.getByTestId('account-no-email')).toHaveCount(0);
    await expect(card).toContainText('@');

    await page.getByTestId('account-password-edit').click();
    await expect(page.getByTestId('account-new-password')).toBeVisible();
    // Deliberately never submitted: this runs against the production account the whole suite
    // signs in with.
  });

  test('deleting the account asks for the password first', async ({ authedPage: page }) => {
    await page.goto('/profile');
    await page.getByTestId('delete-account-start').click();

    // Stops here, permanently. Clicking through would delete the account every test run —
    // the confirmation step existing is the whole assertion.
    await expect(page.getByTestId('delete-account-password')).toBeVisible();
    await expect(page.getByTestId('delete-account-confirm')).toBeVisible();
  });

  test('the admin-mode switch is not offered to an ordinary account', async ({ authedPage: page }) => {
    // This suite signs in as a non-admin, which is exactly the case worth pinning: the
    // switch that hides the admin UI must not appear for someone who has no admin UI to
    // hide. If the @if guarding it is ever loosened to "signed in", this fails.
    await page.goto('/profile');
    await expect(page.getByRole('heading', { name: 'My Profile', level: 1 })).toBeVisible();
    await expect(page.getByTestId('setting-admin-mode')).toHaveCount(0);
  });

  test('a dance added by a non-admin stays out of the public catalogue', async ({ authedPage: page, request }) => {
    const login = await request.post(`${API_URL}/auth/login`, {
      data: { username: USERNAME, password: PASSWORD },
    });
    const { token } = await login.json();
    const auth = { Authorization: `Bearer ${token}` };
    const name = `e2e-pending-${Date.now()}`;

    const created = await request.post(`${API_URL}/dances`, { headers: auth, data: { name, styleIds: [] } });
    expect(created.status()).toBe(201);
    const dance = await created.json();

    try {
      // The point of the whole review gate: it exists, and nobody else can find it.
      expect(dance.reviewState).toBe('pending');

      const search = await request.get(`${API_URL}/search/dances?q=${encodeURIComponent(name)}`);
      const anonymous = (await search.json()).items as Array<{ id: number }>;
      expect(anonymous.some(d => d.id === dance.id), 'a pending dance must not be searchable').toBe(false);

      const direct = await request.get(`${API_URL}/dances/${dance.id}`);
      expect(direct.status(), 'a pending dance must 404 for a signed-out visitor').toBe(404);

      // Its author, on the other hand, sees it and is told why nobody else does.
      await page.goto(`/dances/${dance.slug}`);
      await expect(page.getByTestId('dance-pending')).toBeVisible();
    } finally {
      // Self-cleaning: a contributor may withdraw their own dance while it is still pending,
      // which is exactly the state this test leaves it in.
      const removed = await request.delete(`${API_URL}/dances/${dance.id}`, { headers: auth });
      expect(removed.status(), 'the test dance must not survive the run').toBe(204);
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
   * Style narrows the same local trail — nothing server-side — so a pair of synthetic entries
   * in two styles is enough to prove the filter, that the rail stays one rail, and that the
   * choice is remembered. The probes are dated into two different age bands so the run also
   * covers the markers that carry the rail's structure.
   */
  test('Recently viewed can be filtered by style, and remembers the choice', async ({ authedPage: page }) => {
    const midnight = new Date();
    midnight.setHours(0, 0, 0, 0);
    const probes = [
      { id: 999_003, name: 'E2E Filter Probe House', slug: 'e2e-filter-house', styleSlug: 'house', styleName: 'House', viewedAt: Date.now(), learned: false },
      // Yesterday afternoon: a different age band, so a second marker has to appear.
      { id: 999_004, name: 'E2E Filter Probe Hip-hop', slug: 'e2e-filter-hiphop', styleSlug: 'hip-hop', styleName: 'Hip-hop', viewedAt: midnight.getTime() - 6 * 3600_000, learned: false },
    ];
    await page.addInitScript(entries => {
      localStorage.setItem('dp_recent_dances', JSON.stringify(entries));
      // This runs on the reload too, so only force the starting state once — otherwise it
      // would undo the very choice the reload is meant to prove was remembered.
      if (!sessionStorage.getItem('e2e_trail_seeded')) {
        sessionStorage.setItem('e2e_trail_seeded', '1');
        localStorage.removeItem('dp_continue_style');
      }
    }, probes);

    await page.goto('/my-dances');
    const all = page.getByRole('button', { name: 'All styles' });
    const house = page.getByRole('button', { name: /^House/ });
    await expect(all).toHaveAttribute('aria-pressed', 'true');

    // Unfiltered: both cards on one rail, newest first. A marker is a boundary, so only the
    // crossing into the older band gets one - the newest band has nothing before it.
    const cards = page.locator('.continue-card');
    await expect(cards).toHaveCount(2);
    await expect(cards.first()).toHaveText(/E2E Filter Probe House/);
    await expect(page.locator('.trail-marker')).toHaveText(['Yesterday']);

    await house.click();
    await expect(house).toHaveAttribute('aria-pressed', 'true');
    await expect(all).toHaveAttribute('aria-pressed', 'false');

    // Filtering narrows the rail rather than regrouping it — still one track, fewer cards.
    await expect(cards).toHaveCount(1);
    await expect(cards.first()).toHaveText(/E2E Filter Probe House/);
    await expect(page.locator('.continue-track')).toHaveCount(1);
    // One band left, so no boundary and no marker.
    await expect(page.locator('.trail-marker')).toHaveCount(0);

    // The choice survives a reload — it is stored, not just component state.
    await page.reload();
    await expect(page.locator('.continue-card')).toHaveCount(1);
    await expect(page.getByRole('button', { name: /^House/ })).toHaveAttribute('aria-pressed', 'true');
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
   * A move opened from a path is still on the path. Two things have to hold on the move page,
   * and both are easy to lose because the URL is a plain `/dances/...` one: the right rail must
   * offer the rest of the tree instead of "More like this", and the header must not relabel the
   * visit as browsing. The `?roadmap=` param is what carries that, so it's asserted first —
   * without it the other two can only fail.
   */
  test('a move opened from a path shows what comes next, and the nav stays on Roadmaps', async ({ authedPage: page }) => {
    await blockEmbeds(page);
    await page.goto('/roadmaps/house');
    await expect(page.getByTestId('roadmap-title')).toBeVisible();
    await page.getByTestId('roadmap-view-list').click();

    const videoLists = page.getByTestId('roadmap-step-videos');
    await expect(videoLists.first()).toBeVisible();
    await videoLists.first().locator('a.video__link').first().click();

    await expect(page.getByTestId('dance-title')).toBeVisible();
    await expect(page).toHaveURL(/[?&]roadmap=house/);

    // "Next in roadmap" here; a module path would say "Next in module".
    await expect(page.getByTestId('roadmap-rail')).toBeVisible();
    await expect(page.getByTestId('roadmap-rail-title')).toHaveText('Next in roadmap');
    await expect(page.getByRole('heading', { name: 'More like this' })).toHaveCount(0);

    await expect(page.getByTestId('nav-roadmaps')).toHaveClass(/is-active/);
    await expect(page.getByTestId('nav-browse')).not.toHaveClass(/is-active/);
  });

  /**
   * Steps can be pinned to one section of a longer tutorial (`segmentLabel` in the authored
   * JSON). Those must deep-link with a `t=` offset, or the user lands at 0:00 of a 12-minute
   * video and has to hunt for the part the step is about.
   */
  test('a step pinned to a video section deep-links to that timestamp', async ({ authedPage: page }) => {
    await blockEmbeds(page);
    // The pinned step lives in the arms module, not the top-level Waacking path.
    await page.goto('/roadmaps/waacking-arms');
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
