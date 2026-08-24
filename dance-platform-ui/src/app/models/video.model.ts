export type VideoType = 'steps' | 'tutorial';

export interface VideoSegment {
  id: number;
  label: string;
  startTime: number;
  endTime?: number;
}

/** A timestamped personal note pinned to a moment in a video — private to the
 *  signed-in user, shown as markers on the beta viewer's seek bar. */
export interface VideoNote {
  id: number;
  videoId: number;
  timeSeconds: number;
  text: string;
}

/** One dance that lives inside a shared source video — used to jump the player
 *  between the dances cut from the same YouTube upload. */
export interface VideoChapter {
  id: number;          // Video row id
  danceId: number;
  danceName: string;
  danceSlug: string;
  startTime?: number;
  endTime?: number;
}

/** Chapters a YouTube upload already publishes, offered as ready-made sections when adding it. */
export interface YoutubeChapters {
  videoId: string;
  duration?: number;
  /** "chapters" (YouTube's own chapter bar), "description" (timestamp list), or "none". */
  source: string;
  chapters: { label: string; startTime: number; endTime?: number }[];
}

export interface Video {
  id: number;
  title: string;
  videoId: string;
  platform: string;
  videoType: VideoType;
  description?: string;
  dateAdded: string;
  viewCount: number;
  startTime?: number;
  endTime?: number;
  /** Length of the whole source upload; clip it with startTime/endTime via `videoRuntime`. */
  durationSeconds?: number;
  averageRating: number;
  ratingCount: number;
  userRating?: number;
  danceId: number;
  danceName: string;
  /** Owner of a personal (private) video; null/undefined for global videos. */
  ownerUserId?: number;
  segments: VideoSegment[];
}

/** A video row in the "added videos" library — personal (own) or global (admin view). */
export interface VideoLibraryItem {
  id: number;
  title: string;
  videoId: string;
  platform: string;
  videoType: VideoType;
  dateAdded: string;
  viewCount: number;
  startTime?: number;
  endTime?: number;
  /** Owner of a personal video; null/undefined for global videos. */
  ownerUserId?: number;
  danceId: number;
  danceName: string;
  danceSlug: string;
  styleSlug: string;
}

/**
 * How long this video actually plays for, in seconds — the source length clipped to the
 * start/end the dance pins it to. 0 when the source duration was never backfilled.
 *
 * Mirrors the sum in DanceService.TotalDurationSeconds so a card's total and the rows behind
 * it can't disagree.
 */
export function videoRuntime(v: Pick<Video, 'startTime' | 'endTime' | 'durationSeconds'>): number {
  const start = v.startTime ?? 0;
  if (v.endTime) return Math.max(0, v.endTime - start);
  return v.durationSeconds ? Math.max(0, v.durationSeconds - start) : 0;
}

export function viewCountBucket(count: number): string {
  if (count >= 10_000_000) return '10M+';
  if (count >= 5_000_000) return '5M+';
  if (count >= 100_000) return '100K+';
  if (count >= 10_000) return '10K+';
  if (count >= 1_000) return '1K+';
  if (count >= 100) return '100+';
  return '< 100';
}
