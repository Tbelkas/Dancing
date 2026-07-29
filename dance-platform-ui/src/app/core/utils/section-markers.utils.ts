import { VideoSegment } from '../../models/video.model';

/** One section, placed on the player's seek bar. */
export interface SectionMarker {
  id: number;
  label: string;
  /** Where the section starts, as a percentage of the whole video. */
  startPct: number;
  /** True when the playhead is inside this section. */
  current: boolean;
}

/**
 * Places the "Sections" chips onto a seek bar.
 *
 * Segment times are absolute within the source video (that's what jumpToSegment seeks to),
 * so they're measured against the full duration the player reports — the same basis the
 * note markers use.
 *
 * A segment with no endTime runs until the next one starts, or to the end of the video if
 * it's the last. Sections are stored in whatever order they were added, so they're sorted
 * before that gap-filling: taking "the next one" from an unsorted list would hand a
 * section an end time earlier than its own start.
 *
 * Returns [] when the duration isn't known yet — early on, the player reports 0 and every
 * marker would otherwise pile up at the left edge.
 */
export function sectionMarkers(
  segments: readonly VideoSegment[],
  duration: number,
  currentTime: number
): SectionMarker[] {
  if (duration <= 0 || segments.length === 0) return [];

  const ordered = [...segments].sort((a, b) => a.startTime - b.startTime);
  return ordered.map((seg, i) => {
    const end = seg.endTime ?? ordered[i + 1]?.startTime ?? duration;
    return {
      id: seg.id,
      label: seg.label,
      startPct: Math.max(0, Math.min(100, (seg.startTime / duration) * 100)),
      current: currentTime >= seg.startTime && currentTime < end
    };
  });
}
