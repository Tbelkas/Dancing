import { PRACTICE_DAY_START_HOUR, toLocalDateString, toPracticeDateString } from './video-url.utils';

/** Sub-minute blips — a stray watch, a mis-tap — aren't practice, so they never count. */
const MEANINGFUL_SECONDS = 60;

/** The sessions worth counting or showing. One threshold, so every page agrees on "a session". */
export function meaningfulSessions<T extends { totalSeconds: number }>(sessions: T[]): T[] {
  return sessions.filter(s => s.totalSeconds > MEANINGFUL_SECONDS);
}

export interface Streak {
  /** Consecutive practice days ending today or yesterday; 0 once the run is broken. */
  current: number;
  /** Longest run anywhere in the history — the personal record. */
  longest: number;
  /** A live streak with nothing logged today: it survives only if the user practices. */
  atRisk: boolean;
}

/** Same calendar day shifted by whole days. Goes through local date fields rather than
 *  ±86400000ms so a 23- or 25-hour DST day still moves exactly one day. */
function shiftDay(dateStr: string, days: number): string {
  const d = new Date(dateStr + 'T00:00:00');
  d.setDate(d.getDate() + days);
  return toLocalDateString(d);
}

/**
 * The one place a streak is computed. Every surface that shows one reads this, so the number
 * can't drift between the Practice Log and the profile.
 *
 * Takes raw sessions and applies the meaningful-session rule itself — a caller can't get the
 * input set wrong. Days are practice days (local, 4 AM boundary), never UTC.
 */
export function practiceStreak(
  sessions: { date: string; totalSeconds: number }[],
  now: Date = new Date()
): Streak {
  const today = toPracticeDateString(now);
  const dates = [...new Set(meaningfulSessions(sessions).map(s => s.date))]
    // A date ahead of today (device clock, or a hand-typed date) is not a gap in the run —
    // ignore it rather than letting it read as a break.
    .filter(d => d <= today)
    .sort();
  if (dates.length === 0) return { current: 0, longest: 0, atRisk: false };

  let longest = 1;
  let run = 1;
  for (let i = 1; i < dates.length; i++) {
    run = dates[i] === shiftDay(dates[i - 1], 1) ? run + 1 : 1;
    if (run > longest) longest = run;
  }

  // Yesterday still counts: the streak is only over once a whole day has passed unlogged.
  const newest = dates[dates.length - 1];
  let current = 0;
  if (newest === today || newest === shiftDay(today, -1)) {
    current = 1;
    for (let i = dates.length - 2; i >= 0; i--) {
      if (dates[i] !== shiftDay(dates[i + 1], -1)) break;
      current++;
    }
  }

  return { current, longest, atRisk: current > 0 && newest !== today };
}

/** How long is left to log something and keep the day: the practice day ends at the next 4 AM. */
export function minutesLeftInPracticeDay(now: Date = new Date()): number {
  const end = new Date(toPracticeDateString(now) + 'T00:00:00');
  end.setDate(end.getDate() + 1);
  end.setHours(PRACTICE_DAY_START_HOUR, 0, 0, 0);
  return Math.max(0, (end.getTime() - now.getTime()) / 60000);
}

/**
 * Countdown for the at-risk nudge — `null` until the deadline is close enough to be worth a
 * number, then hours, then minutes inside the last hour. Both round down: better to under-
 * promise the time left than to tell someone they have an hour when they have sixty seconds.
 *
 * The deadline is the practice day's 4 AM end, so an 8-hour window starts the countdown at
 * 8 PM — the evening, while there's still time to do something about it.
 */
export function streakTimeLeftLabel(now: Date = new Date(), warnWithinHours = 8): string | null {
  const minutes = minutesLeftInPracticeDay(now);
  if (minutes > warnWithinHours * 60) return null;
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60);
    return `${hours} hour${hours === 1 ? '' : 's'} left`;
  }
  return `${Math.max(1, Math.floor(minutes))} min left`;
}

/** Below this the streak isn't yet worth defending, and saying so is just noise. */
export const STREAK_WARNING_MIN_DAYS = 7;

/**
 * Whether to nag, and what the countdown reads — `null` for "say nothing".
 *
 * Two gates, because a warning that fires on a 2-day streak at noon trains people to ignore
 * it: the streak has to be long enough to be worth losing, and the day has to be running out.
 * Returns the label rather than a boolean so the banner can't render without its countdown.
 */
export function streakWarningLabel(
  streak: Streak,
  now: Date = new Date(),
  warnWithinHours = 8
): string | null {
  if (!streak.atRisk || streak.current < STREAK_WARNING_MIN_DAYS) return null;
  return streakTimeLeftLabel(now, warnWithinHours);
}
