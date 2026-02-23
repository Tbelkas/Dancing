export interface Dance {
  id: number;
  name: string;
  description?: string;
  dateAdded: string;
  styles: string[];
  videoCount: number;
  isFavorite: boolean;
  isLearned: boolean;
}
