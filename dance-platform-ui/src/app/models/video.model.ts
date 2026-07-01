export type VideoType = 'steps' | 'tutorial';

export interface VideoSegment {
  id: number;
  label: string;
  startTime: number;
  endTime?: number;
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

export function viewCountBucket(count: number): string {
  if (count >= 10_000_000) return '10M+';
  if (count >= 5_000_000) return '5M+';
  if (count >= 100_000) return '100K+';
  if (count >= 10_000) return '10K+';
  if (count >= 1_000) return '1K+';
  if (count >= 100) return '100+';
  return '< 100';
}
