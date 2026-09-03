export interface DanceRef {
  id: number;
  name: string;
  slug: string;
  styleSlug: string;
}

export interface MyDanceItem {
  id: number;
  name: string;
  slug: string;
  styleSlug: string;
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
  /** Absent on accounts created before an address was collected — those can't be recovered
   *  until one is added, which is why the profile page nags for it. */
  email?: string;
  name: string;
  nickname: string;
  avatarUrl?: string;
  visibility: 'Public' | 'Private';
  useBetaViewer: boolean;
  dateAdded: string;
  favoriteDances: DanceRef[];
  learnedDances: DanceRef[];
  inProgressDances: DanceRef[];
}

export interface PracticeStats {
  streak: number;
  totalSessions: number;
  totalMinutes: number;
}

export interface AuthResponse {
  token: string;
  username: string;
  userId: number;
}
