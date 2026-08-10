import { DestroyRef, Signal, computed, effect, inject, signal, untracked } from '@angular/core';

/** Wait this long before admitting we're loading at all. */
const DEFAULT_DELAY_MS = 220;
/** Once a skeleton is up, leave it up at least this long. */
const DEFAULT_MIN_VISIBLE_MS = 320;

/**
 * Turns a raw `loading` signal into one that drives a skeleton without flashing it.
 *
 * The API answers in 30–80ms, so binding a skeleton straight to `loading` put it on screen
 * for two or three frames — long enough to see a grey block and a half-finished shimmer
 * sweep, too short to read as "loading". Every page in the app did this.
 *
 * So: stay quiet for `delayMs`. If the data arrives inside that window the skeleton never
 * renders and the user sees content appear directly. If it doesn't, show the skeleton and
 * hold it for `minVisibleMs` so it can't blink out the instant the response lands.
 *
 * Call it from an injection context (a field initializer is one) — it registers an effect
 * and cleans its timers up on destroy.
 *
 *   loading = signal(true);
 *   showSkeleton = delayedLoading(this.loading);
 *
 * Templates need three states, not two, because there is now a gap where we are loading but
 * showing nothing:
 *
 *   @if (showSkeleton()) { <skeleton/> } @else if (!loading()) { <content/> }
 */
export function delayedLoading(
  source: Signal<boolean>,
  delayMs = DEFAULT_DELAY_MS,
  minVisibleMs = DEFAULT_MIN_VISIBLE_MS
): Signal<boolean> {
  const visible = signal(false);
  let showTimer: ReturnType<typeof setTimeout> | null = null;
  let hideTimer: ReturnType<typeof setTimeout> | null = null;
  let shownAt = 0;

  const clearShow = () => { if (showTimer) { clearTimeout(showTimer); showTimer = null; } };
  const clearHide = () => { if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; } };

  effect(() => {
    const loading = source();
    untracked(() => {
      if (loading) {
        clearHide();
        if (visible() || showTimer) return;
        showTimer = setTimeout(() => {
          showTimer = null;
          shownAt = Date.now();
          visible.set(true);
        }, delayMs);
        return;
      }

      clearShow();
      if (!visible()) return;
      const held = Date.now() - shownAt;
      if (held >= minVisibleMs) { visible.set(false); return; }
      if (!hideTimer) {
        hideTimer = setTimeout(() => {
          hideTimer = null;
          visible.set(false);
        }, minVisibleMs - held);
      }
    });
  }, { allowSignalWrites: true });

  inject(DestroyRef).onDestroy(() => { clearShow(); clearHide(); });

  return computed(() => visible());
}
