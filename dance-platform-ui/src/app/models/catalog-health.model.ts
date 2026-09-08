/** The headline counts across the catalogue. */
export interface CatalogTotals {
  dances: number;
  videos: number;
  pendingVideos: number;
  rejectedVideos: number;
  pendingDances: number;
  openFlags: number;
  styles: number;
  instructors: number;
}

/** One example of a finding — a dance, or a video on one. */
export interface HealthItem {
  danceId: number;
  danceName: string;
  danceSlug: string;
  styleSlug: string;
  /** Set when the finding is about one video rather than the dance as a whole. */
  videoId?: number;
  videoTitle?: string;
  /** The value that tripped the check, when a number says it best. */
  note?: string;
}

/** One thing that can be wrong with the catalogue, with the worst examples of it. */
export interface HealthCheck {
  key: string;
  title: string;
  detail: string;
  count: number;
  /** 'warn' — a reader would notice. 'info' — tidiness. Nothing here is an outage. */
  severity: 'warn' | 'info';
  /** A sample, not the whole set; `count` is the real figure. */
  items: HealthItem[];
}

export interface CatalogHealth {
  totals: CatalogTotals;
  checks: HealthCheck[];
  generatedAt: string;
}
