export interface PracticeSessionItem {
  danceId: number;
  danceName: string;
  danceSlug: string;
  danceStyleSlug: string;
  seconds: number;
  minutes: number;
  notes?: string;
}

export interface PracticeSession {
  id: number;
  date: string;
  startedAt: string;
  lastActivityAt: string;
  notes?: string;
  totalSeconds: number;
  durationMinutes: number;
  items: PracticeSessionItem[];
}
