export interface UserProfile {
  id: number;
  username: string;
  name: string;
  nickname: string;
  avatarUrl?: string;
  visibility: 'Public' | 'Private';
  dateAdded: string;
  favoriteDances: string[];
  learnedDances: string[];
}

export interface AuthResponse {
  token: string;
  username: string;
  userId: number;
}
