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
  /** Everything the pipeline stamped on the row — verdicts, evidence and objections mixed. */
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
 * What a flag means, and whether it argues for or against the video.
 *
 * `QualityFlags` is not a list of objections — it's whatever the last pipeline stage stamped on
 * the row, and the three writers disagree about what they put there. VideoQualityGate.Grade
 * (the API's tier 0) writes only complaints; verify_intake.py writes its *verdict*, which is as
 * often "confirmed" as it is a problem, plus a `core-N` count of dance-teaching terms it found in
 * the transcript; verify_visual.py writes a `visual:` verdict from contact sheets of frames.
 *
 * Rendering all of that as objections would put "confirmed" in the same red pill as
 * "not a dance video", which is worse than showing nothing — it teaches the reviewer that the
 * flags mean nothing. So each is classified:
 *
 *   concern   a reason to doubt this video
 *   evidence  something the pipeline established in its favour, or a neutral observation
 */
export type FlagKind = 'concern' | 'evidence';

interface FlagMeaning {
  kind: FlagKind;
  label: string;
}

const FLAGS: Record<string, FlagMeaning> = {
  // --- VideoQualityGate.Grade (the API's own tier 0) — all complaints -------
  'too-short': { kind: 'concern', label: 'Under 30 seconds, and not a clip of a longer video' },
  'title-dance-mismatch': { kind: 'concern', label: "The title doesn't mention this dance or its style" },
  'promo-title': { kind: 'concern', label: 'The title reads like an ad for a course' },

  // --- verify_intake.py verdicts (from the transcript) ---------------------
  confirmed: { kind: 'evidence', label: 'Transcript confirms it teaches this move' },
  partial: { kind: 'evidence', label: 'Transcript partly matches this move' },
  unconfirmed: { kind: 'concern', label: "The transcript doesn't confirm this move" },
  'dance-but-unnamed': { kind: 'concern', label: 'A dance video, but it never names this move' },
  'not-a-dance-video': { kind: 'concern', label: 'Not a dance video at all' },
  'video-unavailable': { kind: 'concern', label: "The source won't play — nothing can fix this but removal" },
  'no-transcript': { kind: 'evidence', label: 'No speech to transcribe — judged on the video alone' },
  silent: { kind: 'evidence', label: 'Silent — judged on the video alone' },
  unclear: { kind: 'evidence', label: 'The transcript was unreadable — nothing learned either way' },

  // --- verify_visual.py verdicts (from frames) -----------------------------
  'visual:teaches-this-move': { kind: 'evidence', label: 'The frames show it teaching this move' },
  'visual:dance-but-other-move': { kind: 'concern', label: 'The frames show a dance, but a different move' },
  'visual:dance-performance': { kind: 'concern', label: 'The frames show a performance, not teaching' },
  'visual:not-a-dance-video': { kind: 'concern', label: 'The frames show no dancing' },
  'visual:cannot-tell': { kind: 'evidence', label: 'The frames were inconclusive' },
  'has-onscreen-text': { kind: 'evidence', label: 'Carries on-screen text — often a silent tutorial' },

  // --- low-level gate observations -----------------------------------------
  'not-instructional': { kind: 'concern', label: 'The transcript reads as a performance, not teaching' },
  'low-audio': { kind: 'evidence', label: 'Little usable audio' }
};

/** A flag as a person should read it. Unknown flags are shown raw and treated as neutral. */
export function flagMeaning(flag: string): FlagMeaning {
  const known = FLAGS[flag];
  if (known) return known;

  // "same-clip-on-N-dances" carries a count, so it can't be a fixed key.
  const sameClip = /^same-clip-on-(\d+)-dances$/.exec(flag);
  if (sameClip) {
    return { kind: 'concern', label: `The same clip is already on ${sameClip[1]} other dances` };
  }

  // verify_intake counts the distinct dance-teaching terms it found in the transcript. More is
  // better, so it's evidence — but only worth showing when there's something to show.
  const core = /^core-(\d+)$/.exec(flag);
  if (core) {
    const n = Number(core[1]);
    return {
      kind: n > 0 ? 'evidence' : 'concern',
      label: n === 0
        ? 'No dance-teaching terms found in the transcript'
        : `${n} dance-teaching term${n === 1 ? '' : 's'} in the transcript`
    };
  }

  return { kind: 'evidence', label: flag };
}

/** Only the flags arguing against the video — what the reviewer has to weigh. */
export function concerns(video: PendingVideo): string[] {
  return video.qualityFlags.filter(f => flagMeaning(f).kind === 'concern');
}

/** Everything else the pipeline recorded: supporting findings and neutral observations. */
export function evidence(video: PendingVideo): string[] {
  return video.qualityFlags.filter(f => flagMeaning(f).kind === 'evidence');
}
