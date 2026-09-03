export interface Dance {
  id: number;
  name: string;
  slug: string;
  /** Slug of the canonical style, for the /dances/{styleSlug}/{slug} URL. */
  styleSlug: string;
  description?: string;
  dateAdded: string;
  difficulty: string;
  styles: string[];
  musicalStyles: string[];
  instructors: string[];
  videoCount: number;
  /** Total watchable seconds across the dance's visible videos; 0 when unknown. */
  totalDurationSeconds: number;
  thumbnailVideoId?: string;
  thumbnailPlatform?: string;
  favoriteCount: number;
  learnedCount: number;
  averageRating: number;
  ratingCount: number;
  isFavorite: boolean;
  isLearned: boolean;
  isInProgress: boolean;
  /** "approved" (in the public catalogue) or "pending" (waiting for review). You only ever see
   *  "pending" on a dance you added yourself, or as an admin. */
  reviewState: string;
  /** Who added it; absent for the curated catalogue. */
  ownerUserId?: number;
}
