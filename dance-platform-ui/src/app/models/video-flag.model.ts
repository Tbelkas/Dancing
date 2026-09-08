/** The fixed set of things a viewer can report. Mirrors the regex on ReportVideoRequest. */
export const REPORT_REASONS = [
  { value: 'dead-video', label: "It won't play" },
  { value: 'wrong-dance', label: "It isn't this dance" },
  { value: 'bad-sections', label: 'The sections are wrong' },
  { value: 'wrong-timing', label: 'It starts or ends wrong' },
  { value: 'other', label: 'Something else' }
] as const;

export type ReportReason = (typeof REPORT_REASONS)[number]['value'];

/**
 * A problem report in the admin queue. Raised by a viewer from the video page, or by the nightly
 * availability checker (`source: 'checker'`), which is why one queue serves both.
 */
export interface VideoFlag {
  id: number;
  reason: string;
  /** The reason in words — the API labels it so the queue isn't decoding slugs. */
  reasonLabel: string;
  detail?: string;
  source: 'viewer' | 'checker';
  reportedByUserId?: number;
  reportedByUsername?: string;
  createdAt: string;
  resolvedAt?: string;
  resolution?: string;

  videoId: number;
  videoTitle: string;
  /** The platform's own id (the YouTube/TikTok/Instagram id), for opening the source. */
  sourceVideoId: string;
  platform: string;
  /** Whether the video is still live — a quarantined one needs no fixing. */
  videoReviewState: string;

  danceId: number;
  danceName: string;
  danceSlug: string;
  styleSlug: string;
  /** Other open reports on the same video; three people saying it's dead is a fact. */
  openFlagsOnVideo: number;
}
