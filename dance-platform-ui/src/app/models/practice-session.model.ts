export interface PracticeSession {
  id: number;
  danceId: number;
  danceName: string;
  danceSlug: string;
  date: string;
  durationMinutes?: number;
  notes?: string;
}
