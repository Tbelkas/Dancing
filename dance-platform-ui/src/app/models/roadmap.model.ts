/** A learning path through one style. Mirrors DTOs/Roadmap/RoadmapDto.cs. */
export interface RoadmapSummary {
  id: number;
  slug: string;
  title: string;
  subtitle: string;
  description?: string;

  styleId: number;
  styleName: string;
  styleSlug: string;

  /** True when this is the viewer's own skill tree — i.e. "may I edit it?". */
  isOwned: boolean;

  /** True when it's a personal tree its owner has shared. Always false on a curated path. */
  isPublic: boolean;

  /** Who built it — absent on a curated path. */
  ownerUsername?: string;
  /** Their display name, for "Shared by …". */
  ownerNickname?: string;

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
  /** Steps whose prerequisites are met but which aren't learned yet — what to do next. */
  availableCount: number;
  /**
   * Present only when this path is a *module* of another one. Outermost first, so it renders
   * straight through as a breadcrumb: Waacking › Posing.
   */
  ancestors?: RoadmapCrumb[];
}

/** One rung of a module's breadcrumb. */
export interface RoadmapCrumb {
  slug: string;
  title: string;
  /** Title of the step that opens the next rung down. Empty on the outermost crumb. */
  stepTitle: string;
}

export type RoadmapStepState = 'learned' | 'available' | 'locked';

export interface RoadmapStage {
  id: number;
  title: string;
  description?: string;
  steps: RoadmapStep[];
}

export interface RoadmapStep {
  id: number;
  /** Stable key within the roadmap; what `requires` refers to. */
  key: string;
  /** Keys of steps that come before this one. Empty = a root of the tree. */
  requires: string[];
  /** Index of the owning stage — the tree colours and labels branches by it. */
  stageIndex: number;
  /** Longest distance from a root; the node's ring in the tree. Computed server-side. */
  depth: number;
  /** Advisory: a locked step is dimmed but still markable. */
  state: RoadmapStepState;
  title: string;
  description?: string;
  /** Null when the catalog has no move for this step yet — the node still renders. */
  dance?: RoadmapStepDance;
  /** Set when the step covers one section of one of the dance's videos, not the whole move. */
  segment?: RoadmapStepSegment;
  /**
   * Set when this step is a gateway into a nested path rather than a single move. Mutually
   * exclusive with `dance`. It is learned exactly when the module is complete, so the UI must
   * not offer a manual tick for it.
   */
  module?: RoadmapStepModule;
}

/** A nested path as seen from the step that opens it — enough to draw the gateway and its progress. */
export interface RoadmapStepModule {
  id: number;
  slug: string;
  title: string;
  subtitle: string;
  /** Every step inside, including ones that can never be ticked off. */
  stepCount: number;
  /** Steps that can actually be finished — the denominator in "3 of 7". */
  completableCount: number;
  learnedCount: number;
  /** True when every completable step is done. A module with nothing completable never is. */
  isComplete: boolean;
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

/**
 * A whole personal tree as the builder submits it. Mirrors DTOs/Roadmap/SaveRoadmapRequest.cs.
 * Both create and update take the full shape — the server replaces the stored tree with it
 * rather than diffing, so anything the builder leaves out is deleted.
 */
export interface SaveRoadmap {
  title: string;
  subtitle?: string;
  description?: string;
  styleId: number;
  stages: SaveRoadmapStage[];
}

export interface SaveRoadmapStage {
  title: string;
  description?: string;
  steps: SaveRoadmapStep[];
}

export interface SaveRoadmapStep {
  /** The step's id within the request — what other steps' `requires` name. */
  key: string;
  title: string;
  description?: string;
  /** A catalog move, by id (the picker searches, so it always has one). */
  danceId?: number | null;
  videoSegmentId?: number | null;
  /**
   * One of the user's own trees, making this step a module gateway instead of a move. Ignored
   * when `danceId` is set. Clearing it does not delete the child — it becomes a normal
   * top-level tree the user still owns.
   */
  childRoadmapId?: number | null;
  requires: string[];
}
