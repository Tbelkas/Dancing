export interface Dance {
  id: number;
  name: string;
  slug: string;
  description?: string;
  dateAdded: string;
  difficulty: string;
  styles: string[];
  musicalStyles: string[];
  instructors: string[];
  videoCount: number;
  thumbnailVideoId?: string;
  thumbnailPlatform?: string;
  favoriteCount: number;
  learnedCount: number;
  averageRating: number;
  ratingCount: number;
  userRating?: number;
  isFavorite: boolean;
  isLearned: boolean;
  isInProgress: boolean;
}
