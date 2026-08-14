import { VideoSegment } from '../../models/video.model';

/**
 * Labels the chipping scripts give an opening talking-head section — 497 of the ~520
 * chipped videos that open with one use exactly these words.
 *
 * Deliberately whole-label: a section is skipped only when preamble is *all* it holds.
 * "Intro to the six-step" is the lesson, and "Intro & basic step" teaches something
 * after the greeting — skipping either would drop content the viewer came for. Those
 * keep their chip in the Sections bar like any other section.
 */
const INTRO_LABEL = /^(intro|introduction|welcome)[\s.:!–—-]*$/i;

/** A section that begins this soon after the opening still counts as starting there. */
const OPENING_TOLERANCE = 2;

/**
 * The longest stretch we'll skip unseen. A handful of chipped videos carry a mislabelled
 * "Intro" running eight minutes; jumping that far would drop the viewer past real content.
 */
export const MAX_INTRO_SKIP = 180;

/** Skipping has to leave more than this much of the dance behind it to be worth doing. */
const MIN_REMAINING = 5;

/**
 * Where playback should open, when the video begins with an intro worth skipping.
 *
 * Returns the second to start at, or null when there's no intro to skip — no sections,
 * an opening section that isn't an intro, or one whose end can't be worked out.
 *
 * `startTime`/`endTime` bound the dance inside the source video (several dances are cut
 * from one video). Section times are absolute within that source, so the intro that
 * matters is the one covering the dance's *own* start — a video whose dance begins at
 * 5:00 is not opened by the "Intro" chip sitting at 0:00.
 */
export function introSkipTarget(
  segments: readonly VideoSegment[],
  startTime?: number,
  endTime?: number
): number | null {
  if (segments.length === 0) return null;

  const start = startTime ?? 0;
  const ordered = [...segments].sort((a, b) => a.startTime - b.startTime);
  const opening = ordered.findIndex((s, i) => {
    // An open-ended section runs to the next one; a trailing one has no known end here
    // (the player's duration isn't in play yet), so it can't be skipped past.
    const end = s.endTime ?? ordered[i + 1]?.startTime;
    return end != null && s.startTime <= start + OPENING_TOLERANCE && end > start + OPENING_TOLERANCE;
  });
  if (opening === -1) return null;

  const section = ordered[opening];
  if (!INTRO_LABEL.test(section.label.trim())) return null;

  const target = Math.round(section.endTime ?? ordered[opening + 1].startTime);
  if (target <= start || target - start > MAX_INTRO_SKIP) return null;
  if (endTime != null && target >= endTime - MIN_REMAINING) return null;
  return target;
}
