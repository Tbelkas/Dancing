import { test, expect } from '@playwright/test';
import { USERNAME, PASSWORD } from '../fixtures/env.js';

/**
 * API contract + health checks. Browserless, so they run in about a second and pinpoint
 * whether a UI failure is the API's fault or the SPA's.
 *
 * `baseURL` for this project is E2E_API_URL (see playwright.config.ts). Paths below are
 * written WITHOUT a leading slash on purpose — Playwright resolves them with
 * `new URL(path, baseURL)`, and a leading slash would discard the `/api` prefix.
 */

test.describe('api health @smoke', () => {
  test('dance search returns a well-formed page', async ({ request }) => {
    const res = await request.get('search/dances?page=1&pageSize=5');
    expect(res.status()).toBe(200);

    const body = await res.json();
    expect(Array.isArray(body.items)).toBe(true);
    expect(body.items.length).toBeGreaterThan(0);
    expect(body.items.length).toBeLessThanOrEqual(5);
    expect(body.total).toBeGreaterThan(0);
    expect(body.grandTotal).toBeGreaterThanOrEqual(body.total);
    expect(body.page).toBe(1);

    // Shape the UI depends on — a rename here silently blanks cards.
    const dance = body.items[0];
    for (const field of ['id', 'name', 'slug', 'styleSlug', 'difficulty', 'videoCount']) {
      expect(dance, `search item missing "${field}"`).toHaveProperty(field);
    }
  });

  test('styles and musical styles are populated', async ({ request }) => {
    for (const path of ['styles', 'musicalstyles']) {
      const res = await request.get(path);
      expect(res.status(), `${path} should be 200`).toBe(200);
      const body = await res.json();
      expect(Array.isArray(body), `${path} should return an array`).toBe(true);
      expect(body.length, `${path} should not be empty`).toBeGreaterThan(0);
    }
  });

  test('a dance is fetchable by slug and by id', async ({ request }) => {
    const list = await (await request.get('search/dances?page=1&pageSize=1')).json();
    const { id, slug, styleSlug } = list.items[0];

    const byId = await request.get(`dances/${id}`);
    expect(byId.status()).toBe(200);
    expect((await byId.json()).id).toBe(id);

    // The two-segment style route is what the UI links to.
    const bySlug = await request.get(`dances/${styleSlug}/${slug}`);
    expect(bySlug.status()).toBe(200);
    expect((await bySlug.json()).slug).toBe(slug);
  });

  test('neighbors and recommended return without error', async ({ request }) => {
    const list = await (await request.get('search/dances?page=1&pageSize=1')).json();
    const { id } = list.items[0];

    const neighbors = await request.get(`dances/${id}/neighbors`);
    expect(neighbors.status()).toBe(200);

    const recommended = await request.get(`dances/${id}/recommended`);
    expect(recommended.status()).toBe(200);
    expect(Array.isArray(await recommended.json())).toBe(true);
  });

  test('every sort option is accepted', async ({ request }) => {
    // These strings are the <option> values in the browse sort control; a server-side
    // rename would silently fall through to alphabetical instead of erroring.
    for (const sortBy of ['recommended', 'tutorials', 'name', 'rating', 'popular', 'newest']) {
      const res = await request.get(`search/dances?pageSize=3&sortBy=${sortBy}`);
      expect(res.status(), `sortBy=${sortBy}`).toBe(200);
      expect((await res.json()).items.length, `sortBy=${sortBy} returned nothing`).toBeGreaterThan(0);
    }
  });

  test('a search with LIKE wildcards is treated literally, not as a pattern', async ({ request }) => {
    // Guards the wildcard escaping in DanceService.BuildFilteredQuery.
    const res = await request.get('search/dances?q=%25');
    expect(res.status()).toBe(200);
    expect((await res.json()).total).toBe(0);
  });

  test('unknown dance returns 404, not 500', async ({ request }) => {
    const res = await request.get('dances/definitely-not-a-real-slug-xyz');
    expect(res.status()).toBe(404);
  });

  test('roadmaps expose the shape the path page renders', async ({ request }) => {
    const list = await request.get('roadmaps');
    expect(list.status()).toBe(200);
    const summaries = await list.json();
    expect(Array.isArray(summaries)).toBe(true);
    expect(summaries.length, 'no roadmaps seeded').toBeGreaterThan(0);

    for (const field of ['id', 'slug', 'title', 'styleName', 'styleSlug', 'stageCount', 'stepCount', 'moveCount', 'videoCount']) {
      expect(summaries[0], `roadmap summary missing "${field}"`).toHaveProperty(field);
    }

    const detail = await request.get(`roadmaps/${summaries[0].slug}`);
    expect(detail.status()).toBe(200);
    const roadmap = await detail.json();

    expect(Array.isArray(roadmap.stages)).toBe(true);
    expect(roadmap.stages.length).toBeGreaterThan(0);
    expect(roadmap.stages[0].steps.length).toBeGreaterThan(0);

    // A step's dance is optional (moves the catalog doesn't cover yet render unlinked), but
    // a path where nothing resolves has silently lost its links — that is the regression to catch.
    const steps = roadmap.stages.flatMap((s: { steps: unknown[] }) => s.steps);
    const linked = steps.filter((s: { dance?: unknown }) => s.dance);
    expect(linked.length, 'no step resolved to a catalog move').toBeGreaterThan(0);

    for (const field of ['id', 'name', 'slug', 'styleSlug', 'difficulty', 'videos']) {
      expect(linked[0].dance, `roadmap step dance missing "${field}"`).toHaveProperty(field);
    }
  });

  test('roadmap steps can pin to a video section', async ({ request }) => {
    // Waacking's tutorials are consolidated onto one dance with their sub-moves as segments,
    // so its path leans on segmentLabel. If resolution breaks, every step silently widens to
    // "watch the whole 12-minute video" — which still renders, hence the explicit check.
    const res = await request.get('roadmaps/waacking');
    expect(res.status()).toBe(200);
    const roadmap = await res.json();

    const steps = roadmap.stages.flatMap((s: { steps: unknown[] }) => s.steps);
    const pinned = steps.filter((s: { segment?: unknown }) => s.segment);
    expect(pinned.length, 'no step resolved to a video segment').toBeGreaterThan(0);

    const segment = pinned[0].segment;
    for (const field of ['id', 'label', 'startTime', 'videoId']) {
      expect(segment, `step segment missing "${field}"`).toHaveProperty(field);
    }
    // The segment must belong to a video the step actually offers, or the UI filters it away.
    const videoIds = pinned[0].dance.videos.map((v: { id: number }) => v.id);
    expect(videoIds).toContain(segment.videoId);
  });

  test('unknown roadmap returns 404, not 500', async ({ request }) => {
    const res = await request.get('roadmaps/definitely-not-a-real-path-xyz');
    expect(res.status()).toBe(404);
  });

  test('protected endpoints reject anonymous callers', async ({ request }) => {
    for (const path of ['profile', 'practice', 'practice/review', 'videos/mine', 'videos/global']) {
      const res = await request.get(path);
      expect([401, 403], `${path} should require auth (got ${res.status()})`).toContain(res.status());
    }
  });

  test('admin-only endpoints reject an ordinary signed-in user', async ({ request }) => {
    test.skip(!USERNAME || !PASSWORD, 'E2E credentials not configured');

    const login = await request.post('auth/login', {
      data: { username: USERNAME, password: PASSWORD },
    });
    expect(login.status()).toBe(200);
    const { token } = await login.json();
    const auth = { Authorization: `Bearer ${token}` };

    // Read-only admin endpoint: safe to call, and a leak here would expose the curated library.
    const global = await request.get('videos/global', { headers: auth });
    expect([401, 403], `videos/global returned ${global.status()}`).toContain(global.status());

    // Editing the catalog is admin-only. Deliberately targets an id that cannot exist, so
    // that a regression in authorization damages nothing on the way to failing this test.
    const edit = await request.put('dances/999999999', {
      headers: auth,
      data: { name: 'e2e-should-never-apply' },
    });
    expect([401, 403], `dances PUT returned ${edit.status()}`).toContain(edit.status());

    // Note: POST /dances is intentionally [Authorize], not [RequireAdmin] — a non-admin
    // needs to create a dance to hang a personal video on. It is therefore NOT tested here,
    // and must not be: a passing call would leave a real row in the production catalog that
    // only an admin can delete.
  });

  test('login rejects a bad password', async ({ request }) => {
    const res = await request.post('auth/login', {
      data: { username: 'definitely-not-a-user-xyz', password: 'nope' },
    });
    expect(res.status()).toBe(401);
  });
});
