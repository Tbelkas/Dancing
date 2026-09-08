import { VideoSegment, VideoType } from './video.model';

/**
 * A video the intake quality gate is holding back, as the review queue sees it. Distinct from
 * `Video`: it carries the rubric's verdict (score + flags) and the reach figures the queue is
 * ordered by, and it is never returned by any public endpoint.
 */
export interface PendingVideo {
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
  durationSeconds?: number;

  reviewState: 'pending' | 'approved' | 'rejected';
  /** The rubric's score, 0–1. Undefined for rows that predate the gate. */
  qualityScore?: number;
  /** The rubric's objections, already split: "too-short", "title-dance-mismatch", … */
  qualityFlags: string[];
  reviewedAt?: string;
  reviewNote?: string;

  danceId: number;
  danceName: string;
  danceSlug: string;
  styleSlug: string;
  /** Favourites on the target dance — the queue's proxy for "how many people this reaches". */
  danceFavoriteCount: number;
  /** Approved videos already on that dance; 0 means the page is empty without this one. */
  danceVideoCount: number;
  segments: VideoSegment[];
}

/**
 * What each gate flag actually means, in words a person can act on. Keys mirror the flags
 * VideoQualityGate.Grade emits (and video_gate.py's tier 0); "same-clip-on-N-dances" carries a
 * count, so it is matched by prefix in `flagLabel`.
 */
const FLAG_LABELS: Record<string, string> = {
  'too-short': 'Under 30 seconds, and not a clip of a longer video',
  'title-dance-mismatch': "The title doesn't mention this dance or its style",
  'promo-title': 'The title reads like an ad for a course',
  'no-transcript': 'No speech could be transcribed',
  'not-instructional': 'The transcript reads as a performance, not teaching',
  'low-audio': 'Little or no usable audio'
};

/** A gate flag rendered for a human; unknown flags fall back to their raw slug. */
export function flagLabel(flag: string): string {
  if (FLAG_LABELS[flag]) return FLAG_LABELS[flag];
  const sameClip = /^same-clip-on-(\d+)-dances$/.exec(flag);
  if (sameClip) return `The same clip is already on ${sameClip[1]} other dances`;
  return flag;
}
