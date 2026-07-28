import { test, expect, type Page } from '@playwright/test';
import { API_URL } from '../fixtures/env.js';

/**
 * The camera pane: your own webcam beside (or over) the practice video.
 *
 * Chromium's fake capture device stands in for real hardware, so these run headless on
 * CI and on a machine with no webcam — and nobody is ever asked to click "Allow".
 * Everything here is read-only: the camera is a browser-local feature that touches no
 * API and no database.
 */
test.use({
  permissions: ['camera'],
  // The default headless shell has no media stack at all — getUserMedia there rejects
  // with NotSupportedError no matter what you grant it. `channel: 'chromium'` runs the
  // full browser in new headless mode, which does capture. `npx playwright install
  // chromium` already fetches it, so CI needs no extra step.
  channel: 'chromium',
  launchOptions: { args: ['--use-fake-device-for-media-stream'] },
});

/** Opens a dance whose first video is a YouTube embed — the player that carries the tools. */
async function openDanceWithYouTubeVideo(page: Page): Promise<void> {
  const res = await page.request.get(`${API_URL}/search/dances?sort=tutorials&pageSize=20`);
  expect(res.ok()).toBe(true);
  const candidates = (await res.json()).items.filter((d: { videoCount: number }) => d.videoCount > 0);
  expect(candidates.length, 'catalog should contain dances with videos').toBeGreaterThan(0);

  for (const dance of candidates.slice(0, 8)) {
    const videos = await page.request.get(`${API_URL}/videos/dance/${dance.id}`);
    if (!videos.ok()) continue;
    if (!(await videos.json()).some((v: { platform: string }) => v.platform === 'youtube')) continue;
    await page.goto(`/dances/${dance.styleSlug}/${dance.slug}`);
    await expect(page.getByTestId('dance-title')).toBeVisible();
    return;
  }
  // Not a skip: a catalog with no YouTube video is a content problem worth failing on,
  // and a skip here would quietly go green forever.
  throw new Error('no dance with a YouTube video found in the first 8 candidates');
}

/** The pane's live <video>, once it's actually carrying frames. */
async function expectFeedIsLive(page: Page) {
  const feed = page.getByTestId('camera-pane').locator('video').first();
  await expect.poll(
    () => feed.evaluate((el: HTMLVideoElement) => el.videoWidth),
    { message: 'camera feed should report a picture size', timeout: 15_000 }
  ).toBeGreaterThan(0);
}

test.describe('camera denied', () => {
  // No camera permission: getUserMedia rejects, the way it does for a user who clicked
  // "Block". The pane must stay mounted and say so — a pane that silently vanished
  // would read as a broken button.
  test.use({ permissions: [] });

  test('a blocked camera explains itself instead of disappearing', async ({ page }) => {
    await openDanceWithYouTubeVideo(page);
    await page.getByTestId('camera-toggle').first().click();

    const error = page.getByTestId('camera-error');
    await expect(error).toBeVisible({ timeout: 15_000 });
    await expect(error.getByRole('button', { name: 'Try again' })).toBeVisible();

    await error.getByRole('button', { name: 'Close' }).click();
    await expect(page.getByTestId('camera-pane')).toHaveCount(0);
  });
});

test.describe('camera pane', () => {
  test('the Camera tool shows a live feed and closes again @smoke', async ({ page }) => {
    await openDanceWithYouTubeVideo(page);

    const toggle = page.getByTestId('camera-toggle').first();
    await expect(toggle).toBeVisible();
    await expect(page.getByTestId('camera-pane')).toHaveCount(0);

    await toggle.click();
    await expect(page.getByTestId('camera-pane')).toBeVisible();
    await expectFeedIsLive(page);

    await page.getByTestId('camera-close').first().click();
    await expect(page.getByTestId('camera-pane')).toHaveCount(0);
  });

  test('side layout puts the camera beside the video, overlay puts it on top', async ({ page }) => {
    await openDanceWithYouTubeVideo(page);
    await page.getByTestId('camera-toggle').first().click();
    await expectFeedIsLive(page);

    const pane = page.getByTestId('camera-pane');
    const embed = page.locator('iframe[src*="youtube"]').first();

    // Geometry rather than class names: the assertion survives a restyle, and it's the
    // thing that actually matters — do the two pictures sit next to each other?
    const sideBySide = async () => {
      const [paneBox, embedBox] = [await pane.boundingBox(), await embed.boundingBox()];
      expect(paneBox && embedBox).toBeTruthy();
      return paneBox!.x >= embedBox!.x + embedBox!.width - 4;
    };
    expect(await sideBySide(), 'camera should start beside the video').toBe(true);

    await page.getByRole('button', { name: 'Overlay on the video' }).click();
    await expect.poll(async () => await sideBySide(), { message: 'overlay should stop being beside' })
      .toBe(false);

    const [paneBox, embedBox] = [await pane.boundingBox(), await embed.boundingBox()];
    expect(Math.abs(paneBox!.x - embedBox!.x), 'overlay should sit on the video').toBeLessThan(8);

    // Put it back so a rerun in the same profile starts from the documented default.
    await page.getByRole('button', { name: 'Show side by side' }).click();
    await page.getByTestId('camera-close').first().click();
  });

  test('fullscreen takes the camera with it on a default player', async ({ page }) => {
    // The default player uses YouTube's own controls, whose fullscreen button fullscreens
    // the iframe — the pane lives outside it and simply disappears. So the tool row grows
    // its own fullscreen control once the camera is on. This is the common case: the beta
    // viewer (covered below) is opt-in.
    await openDanceWithYouTubeVideo(page);
    await expect(page.getByTestId('stage-fullscreen')).toHaveCount(0);

    await page.getByTestId('camera-toggle').first().click();
    await expectFeedIsLive(page);

    const stageFullscreen = page.getByTestId('stage-fullscreen').first();
    await expect(stageFullscreen, 'the control appears with the camera').toBeVisible();
    await stageFullscreen.click();
    await expect.poll(() => page.evaluate(() => !!document.fullscreenElement)).toBe(true);

    const geometry = await page.evaluate(() => {
      const pane = document.querySelector('[data-testid="camera-pane"]')!.getBoundingClientRect();
      const video = document.querySelector('iframe.yt-player')!.getBoundingClientRect();
      return { paneWidth: pane.width, videoWidth: video.width, paneHeight: pane.height, viewport: window.innerHeight };
    });
    expect(geometry.paneWidth, 'the camera must still be on screen').toBeGreaterThan(0);
    expect(Math.abs(geometry.paneWidth - geometry.videoWidth), 'fullscreen should split evenly').toBeLessThan(4);
    expect(geometry.paneHeight).toBeGreaterThan(geometry.viewport * 0.9);

    // In fullscreen the tool row is off screen and the default player's other controls are
    // inside the iframe, so the camera bar carries the way back out.
    await page.getByTestId('camera-exit-fullscreen').click();
    await expect.poll(() => page.evaluate(() => !!document.fullscreenElement)).toBe(false);
    await page.getByTestId('camera-close').first().click();
  });

  test("the player's own controls stay clear of the pane, in and out of fullscreen", async ({ page }) => {
    // The beta viewer replaces YouTube's controls with ours, which is the only case where
    // the player draws a control bar across the media frame — and the frame is what the
    // camera splits. Both halves of this test are regressions:
    //   1. the bar spanned the whole frame, putting its fullscreen button underneath the
    //      pane's close button, where it could not be clicked at all;
    //   2. the pane carried an aspect-ratio that beat the grid's stretch once fullscreen
    //      made the row height explicit — 1280px of pane inside a 639px column.
    await page.addInitScript(() => localStorage.setItem('dp_beta_viewer', '1'));
    await openDanceWithYouTubeVideo(page);
    await page.getByTestId('camera-toggle').first().click();
    await expectFeedIsLive(page);

    const fullscreenButton = page.getByRole('button', { name: 'Fullscreen' });
    const paneBox = (await page.getByTestId('camera-pane').boundingBox())!;
    const buttonBox = (await fullscreenButton.boundingBox())!;
    expect(
      buttonBox.x + buttonBox.width,
      "the player's controls must not run under the camera pane"
    ).toBeLessThanOrEqual(paneBox.x + 1);

    await fullscreenButton.click();
    await expect.poll(() => page.evaluate(() => !!document.fullscreenElement)).toBe(true);

    const geometry = await page.evaluate(() => {
      const pane = document.querySelector('[data-testid="camera-pane"]')!.getBoundingClientRect();
      const video = document.querySelector('iframe.yt-player')!.getBoundingClientRect();
      return { paneWidth: pane.width, videoWidth: video.width, paneHeight: pane.height, viewport: window.innerHeight };
    });
    expect(Math.abs(geometry.paneWidth - geometry.videoWidth), 'fullscreen should split evenly').toBeLessThan(4);
    expect(geometry.paneHeight, 'the pane should fill the height').toBeGreaterThan(geometry.viewport * 0.9);

    await page.keyboard.press('Escape');
    await page.getByTestId('camera-close').first().click();
  });

  test('the delay records and plays back what you just did', async ({ page }) => {
    await openDanceWithYouTubeVideo(page);
    await page.getByTestId('camera-toggle').first().click();
    await expectFeedIsLive(page);

    const threeSeconds = page.getByRole('button', { name: 'Replay the last 3 seconds' });
    await threeSeconds.click();
    await expect(threeSeconds).toHaveAttribute('aria-pressed', 'true');

    // Wait for the recorder to actually finish a clip and start playing it back — this
    // is the whole feature, not just the button state.
    const replay = page.getByTestId('camera-replay');
    await expect.poll(
      () => replay.evaluate((el: HTMLVideoElement) => !el.paused && el.currentTime > 0),
      { message: 'a recorded clip should be playing back', timeout: 20_000 }
    ).toBe(true);

    // …and the label has to agree with the picture. Asserted on a short timeout on
    // purpose: MediaRecorder's on* properties aren't zone-patched, and assigning them
    // (rather than addEventListener) left the pane playing the replay while still
    // announcing itself as live.
    await expect(page.getByTestId('camera-pane').getByText('−3s')).toBeVisible({ timeout: 2_000 });

    await threeSeconds.click();
    await expect(page.getByTestId('camera-pane').getByText('You')).toBeVisible();
    await page.getByTestId('camera-close').first().click();
  });

  test('a camera that will not open falls back instead of sticking', async ({ page }) => {
    // Advertise a second camera that doesn't exist, so selecting it fails the way a busy
    // or unplugged one does. Found on real hardware: the failed choice was stored, so
    // every later start — including the auto-restore on the next page — retried the dead
    // camera and left the feature broken with no way back except the picker.
    await page.addInitScript(() => {
      const real = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
      navigator.mediaDevices.enumerateDevices = async () => {
        const found = await real();
        return [...found, {
          kind: 'videoinput', deviceId: 'does-not-exist', label: 'Ghost cam', groupId: 'g2',
          toJSON() { return this; },
        } as MediaDeviceInfo];
      };
    });
    await openDanceWithYouTubeVideo(page);
    await page.getByTestId('camera-toggle').first().click();
    await expectFeedIsLive(page);

    await page.getByRole('button', { name: 'Camera settings' }).click();
    await page.getByRole('combobox', { name: 'Which camera to use' }).selectOption('does-not-exist');

    // It falls back to the camera that was working, says why, and doesn't keep the choice.
    await expect(page.getByTestId('camera-notice')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId('camera-error')).toHaveCount(0);
    await expectFeedIsLive(page);
    expect(await page.evaluate(() => localStorage.getItem('dp_camera_device'))).not.toBe('does-not-exist');

    await page.getByTestId('camera-close').first().click();
  });

  test('the camera comes back on the next page it was left on', async ({ page }) => {
    await openDanceWithYouTubeVideo(page);
    await page.getByTestId('camera-toggle').first().click();
    await expectFeedIsLive(page);

    // Navigate away with it on, then into another dance: permission is already granted,
    // so the pane should return without another click.
    await page.goto('/dances');
    await openDanceWithYouTubeVideo(page);
    await expect(page.getByTestId('camera-pane')).toBeVisible({ timeout: 15_000 });

    await page.getByTestId('camera-close').first().click();
    await expect(page.getByTestId('camera-pane')).toHaveCount(0);
    // And an explicit close must not come back on the next page.
    await openDanceWithYouTubeVideo(page);
    await expect(page.getByTestId('camera-pane')).toHaveCount(0);
  });
});
