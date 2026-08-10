import { Signal, computed, signal } from '@angular/core';

const KEY_PREFIX = 'dp_skel_';

/**
 * How many placeholders a loading list should draw.
 *
 * A hardcoded count is right exactly once — the first visit. After that we already know how
 * long the list actually was, and painting three grey rows in front of twelve real ones just
 * moves the jump to the moment the data lands, which is the thing the skeleton existed to
 * prevent. So each list remembers its last real length in localStorage and reserves that many
 * slots next time.
 *
 * `fallback` is what a first-time visitor gets — keep it at whatever the hardcoded count was.
 * `max` caps the reservation: a 200-video library must not paint 200 rows, one screenful is
 * all anyone reads before the data arrives. Lists that page (browse) pass their existing count
 * as the max, so remembering can only ever *shrink* the placeholder to match a small result
 * set, never grow it past the fold.
 *
 * At least one slot always renders — a remembered zero would leave the `aria-busy` container
 * empty, which reads as "nothing is happening" rather than "loading".
 *
 *   private readonly skeleton = new SkeletonCount('choreos', 3, { max: 10 });
 *   // template:  @for (i of skeleton.slots(); track i) { … }
 *   // on load:   this.skeleton.remember(list.length);
 */
export class SkeletonCount {
  private readonly key: string;
  private readonly max: number;
  private readonly count = signal(1);

  /** An array of that length, for `@for` to iterate. */
  readonly slots: Signal<number[]> = computed(() =>
    Array.from({ length: this.count() }, (_, i) => i)
  );

  constructor(key: string, fallback: number, opts: { max?: number } = {}) {
    this.key = KEY_PREFIX + key;
    this.max = opts.max ?? fallback;
    this.count.set(this.clamp(this.read() ?? fallback));
  }

  /** Record how many items the list ended up with, so the next load reserves that much. */
  remember(count: number): void {
    if (!Number.isFinite(count) || count < 0) return;
    this.count.set(this.clamp(count));
    // Store the raw count, not the clamped one, so raising `max` later takes effect.
    try {
      localStorage.setItem(this.key, String(Math.round(count)));
    } catch {
      // Storage disabled or full — the fallback count is a fine answer.
    }
  }

  private read(): number | null {
    let raw: string | null = null;
    try {
      raw = localStorage.getItem(this.key);
    } catch {
      return null;
    }
    if (raw === null) return null;
    const n = Number(raw);
    return Number.isFinite(n) && n >= 0 ? n : null;
  }

  private clamp(n: number): number {
    return Math.min(Math.max(Math.round(n), 1), this.max);
  }
}
