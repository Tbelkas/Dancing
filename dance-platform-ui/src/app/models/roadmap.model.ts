/** A curated learning path through one style. Mirrors DTOs/Roadmap/RoadmapDto.cs. */
export interface RoadmapSummary {
  id: number;
  slug: string;
  title: string;
  subtitle: string;
  description?: string;

  styleId: number;
  styleName: string;
  styleSlug: string;

  stageCount: number;
  stepCount: number;
  /** Steps backed by a catalog move — the ones that count toward progress. */
  moveCount: number;
  videoCount: number;
  /** Of moveCount, how many the signed-in user has marked (0 when signed out). */
  learnedCount: number;
  inProgressCount: number;

  thumbnailVideoId?: string;
  thumbnailPlatform?: string;
}

export interface Roadmap extends RoadmapSummary {
  stages: RoadmapStage[];
}

export interface RoadmapStage {
  id: number;
  title: string;
  description?: string;
  steps: RoadmapStep[];
}

export interface RoadmapStep {
  id: number;
  title: string;
  description?: string;
  /** Null when the catalog has no move for this step yet — the node still renders. */
  dance?: RoadmapStepDance;
  /** Set when the step covers one section of one of the dance's videos, not the whole move. */
  segment?: RoadmapStepSegment;
}

export interface RoadmapStepSegment {
  id: number;
  label: string;
  startTime: number;
  endTime?: number;
  /** Row id of the owning video — matches one of the step dance's `videos`. */
  videoId: number;
}

export interface RoadmapStepDance {
  id: number;
  name: string;
  slug: string;
  styleSlug: string;
  difficulty: string;
  averageRating: number;
  ratingCount: number;
  isLearned: boolean;
  isInProgress: boolean;
  isFavorite: boolean;
  videos: RoadmapStepVideo[];
}

export interface RoadmapStepVideo {
  id: number;
  title: string;
  videoId: string;
  platform: string;
  videoType: string;
  startTime?: number;
  endTime?: number;
  durationSeconds?: number;
  viewCount: number;
  averageRating: number;
  ratingCount: number;
}
