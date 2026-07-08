/** A learned dance that has gone unpracticed long enough to be due for review. */
export interface ReviewDance {
  danceId: number;
  name: string;
  slug: string;
  styleSlug: string;
  styleName: string;
  thumbnailVideoId?: string | null;
  thumbnailPlatform?: string | null;
  /** Local date (YYYY-MM-DD) of the last meaningful practice; null if never practiced since tracking. */
  lastPracticedOn: string | null;
  /** Days since the dance was last touched (practiced, or marked learned if more recent). */
  daysSince: number;
}
