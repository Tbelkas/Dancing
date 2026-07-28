import { test as base, expect, type Page } from '@playwright/test';
import { API_URL, USERNAME, PASSWORD } from './env.js';

/**
 * Signs in over the API and plants the result in localStorage under the same keys
 * AuthService reads (`dp_token` / `dp_user`, see core/services/auth.service.ts).
 *
 * The UI login form is covered by its own test in authed.spec.ts — driving the form for
 * every authed test would just add a slow, flaky prologue to each one.
 */
export async function signIn(page: Page): Promise<{ userId: number; username: string }> {
  const response = await page.request.post(`${API_URL}/auth/login`, {
    data: { username: USERNAME, password: PASSWORD },
  });

  if (!response.ok()) {
    throw new Error(
      `E2E login failed (${response.status()}). Check E2E_USERNAME / E2E_PASSWORD against ${API_URL}.`
    );
  }

  const { token, userId, username } = await response.json();

  // Must land before the app bootstraps: AuthService reads localStorage in a field
  // initializer, so a token written after navigation wouldn't be picked up.
  await page.addInitScript(
    ([t, u]) => {
      localStorage.setItem('dp_token', t as string);
      localStorage.setItem('dp_user', u as string);
    },
    [token, JSON.stringify({ userId, username })] as const
  );

  return { userId, username };
}

/** `test` with an already-signed-in page. */
export const test = base.extend<{ authedPage: Page }>({
  authedPage: async ({ page }, use) => {
    await signIn(page);
    await use(page);
  },
});

export { expect };
