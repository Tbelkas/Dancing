export type VideoType = 'steps' | 'tutorial';

export interface VideoSegment {
  id: number;
  label: string;
  startTime: number;
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
  danceId: number;
  danceName: string;
  segments: VideoSegment[];
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
