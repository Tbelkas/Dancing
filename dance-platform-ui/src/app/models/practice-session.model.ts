export interface PracticeSession {
  id: number;
  danceId: number;
  danceName: string;
  danceSlug: string;
  danceStyleSlug: string;
  date: string;
  durationMinutes?: number;
  notes?: string;
}
