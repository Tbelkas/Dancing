export interface DanceRef {
  id: number;
  name: string;
}

export interface MyDanceItem {
  id: number;
  name: string;
  status: 'learned' | 'inProgress';
}

export interface MyStyleWithDances {
  styleId: number;
  styleName: string;
  dances: MyDanceItem[];
}

export interface UserProfile {
  id: number;
  username: string;
  name: string;
  nickname: string;
  avatarUrl?: string;
  visibility: 'Public' | 'Private';
  dateAdded: string;
  favoriteDances: DanceRef[];
  learnedDances: DanceRef[];
}

export interface AuthResponse {
  token: string;
  username: string;
  userId: number;
}
