import { test, expect } from '@playwright/test';
import { API_URL } from '../fixtures/env.js';

/**
 * Social sign-in, anonymous side only.
 *
 * Nothing here completes a real OAuth round-trip: that would need live Google credentials, a
 * scripted consent screen, and it would create a real account in the production database on
 * every scheduled run. What IS worth asserting is everything up to the redirect — that the
 * server advertises its providers honestly, that `/start` hands off to the right host with the
 * parameters that make the callback safe, and that the two new pages refuse to do anything
 * without a valid ticket.
 *
 * This file runs in the `anon` (browser) project, so `request` resolves against the UI base
 * URL — API calls below are built from API_URL explicitly rather than as relative paths.
 *
 * Every test asserts something in both directions: a provider that is configured gets its
 * hand-off checked, one that is not gets asserted *absent*. Nothing here skips, so the suite
 * can't go quietly green just because credentials aren't set (see README, "conventions").
 */

const PROVIDERS = ['google', 'facebook'] as const;
const api = (path: string) => `${API_URL.replace(/\/$/, '')}/${path}`;

const CONSENT_HOSTS: Record<string, string> = {
  google: 'accounts.google.com',
  facebook: 'www.facebook.com'
};

test.describe('social sign-in @smoke', () => {
  test('the provider list is well-formed', async ({ request }) => {
    const res = await request.get(api('auth/external/providers'));
    expect(res.status()).toBe(200);

    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);

    // Shape the login page depends on — a rename here silently drops every button.
    for (const provider of body) {
      expect(provider).toHaveProperty('name');
      expect(provider).toHaveProperty('displayName');
      expect(PROVIDERS).toContain(provider.name);
    }
  });

  test('each provider either hands off correctly or is absent entirely', async ({ request }) => {
    const configured = new Set<string>(
      (await (await request.get(api('auth/external/providers'))).json()).map((p: { name: string }) => p.name));

    for (const name of PROVIDERS) {
      const res = await request.get(api(`auth/external/${name}/start`), { maxRedirects: 0 });

      if (!configured.has(name)) {
        // An unconfigured provider must be indistinguishable from an unknown one — no half-built
        // redirect to a consent screen that would only fail with a bad client_id.
        expect(res.status(), `${name} is unconfigured, so /start should 404`).toBe(404);
        continue;
      }

      expect(res.status(), `${name}/start should redirect`).toBe(302);
      const location = new URL(res.headers()['location']);
      expect(location.host, `${name} should hand off to its own consent screen`)
        .toBe(CONSENT_HOSTS[name]);

      // The parameters that make the callback safe to accept. Losing either is a real
      // vulnerability that no amount of "it still logs me in" testing would catch.
      expect(location.searchParams.get('state'), `${name} must send state`).toBeTruthy();
      expect(location.searchParams.get('code_challenge'), `${name} must send a PKCE challenge`).toBeTruthy();
      expect(location.searchParams.get('code_challenge_method')).toBe('S256');
      expect(location.searchParams.get('redirect_uri')).toContain(`/auth/external/${name}/callback`);
    }
  });

  test('an unknown provider is a 404, not a redirect', async ({ request }) => {
    const res = await request.get(api('auth/external/nitter/start'), { maxRedirects: 0 });
    expect(res.status()).toBe(404);
  });

  test('a callback with forged state never issues a token', async ({ request }) => {
    const res = await request.get(
      api('auth/external/google/callback?code=fake&state=not-a-real-state'), { maxRedirects: 0 });

    // 404 when Google isn't configured; otherwise a bounce back to /login carrying the error.
    // What must never happen either way is a token coming back.
    if (res.status() === 404) return;
    expect(res.status()).toBe(302);
    const location = res.headers()['location'];
    expect(location).toContain('/login');
    expect(location).not.toContain('token=');
  });

  test('a forged ticket cannot create an account', async ({ request }) => {
    const res = await request.post(api('auth/external/complete'), {
      data: { ticket: 'clearly.not.valid', username: 'e2e-should-never-exist' }
    });
    expect(res.status()).toBe(401);
  });

  test('linked accounts require authentication', async ({ request }) => {
    const res = await request.get(api('auth/external/links'));
    expect(res.status()).toBe(401);
  });
});

test.describe('social sign-in pages', () => {
  test('the login page mirrors the configured providers', async ({ page, request }) => {
    const configured = new Set<string>(
      (await (await request.get(api('auth/external/providers'))).json()).map((p: { name: string }) => p.name));

    await page.goto('/login');
    // The password form is the baseline and must survive regardless.
    await expect(page.getByTestId('login-submit')).toBeVisible();

    // Literal ids, not `login-${name}` — verify:testids scans statically and a template
    // literal would read as an anchor the UI doesn't have.
    const buttons = {
      google: page.getByTestId('login-google'),
      facebook: page.getByTestId('login-facebook')
    };

    for (const name of PROVIDERS) {
      if (configured.has(name)) await expect(buttons[name]).toBeVisible();
      else await expect(buttons[name]).toHaveCount(0);
    }
  });

  test('finish-signup without a ticket sends you back to sign in', async ({ page }) => {
    await page.goto('/finish-signup');
    await expect(page).toHaveURL(/\/login/);
  });

  test('the callback page without a token sends you back to sign in', async ({ page }) => {
    await page.goto('/auth/callback');
    await expect(page).toHaveURL(/\/login/);
  });
});
