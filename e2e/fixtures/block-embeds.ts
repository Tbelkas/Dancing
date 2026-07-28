import type { Page } from '@playwright/test';

/**
 * Blocks third-party video embeds (YouTube / TikTok / Instagram) and their thumbnail CDNs.
 *
 * Use this in every spec that isn't specifically testing an embed. Those iframes pull in
 * megabytes of uncontrolled third-party JS and keep networking long after the assertion has
 * passed; with a single shared browser process that starves whichever test runs next, which
 * showed up as intermittent timeouts on the browse page rather than anywhere near the
 * embeds themselves.
 *
 * It also keeps the suite honest: a test that isn't about the embed shouldn't be able to
 * fail because YouTube was slow.
 *
 * `dance-detail.spec.ts`'s player test deliberately does NOT call this — verifying that a
 * real embed mounts is its entire point.
 */
const EMBED_HOSTS = [
  '**://*.youtube.com/**',
  '**://*.youtube-nocookie.com/**',
  '**://*.ytimg.com/**',
  '**://*.tiktok.com/**',
  '**://*.instagram.com/**',
  '**://*.cdninstagram.com/**',
];

export async function blockEmbeds(page: Page): Promise<void> {
  for (const pattern of EMBED_HOSTS) {
    await page.route(pattern, route => route.abort());
  }
}
