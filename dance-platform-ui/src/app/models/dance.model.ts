export interface Dance {
  id: number;
  name: string;
  description?: string;
  dateAdded: string;
  styles: string[];
  musicalStyles: string[];
  videoCount: number;
  isFavorite: boolean;
  isLearned: boolean;
}
