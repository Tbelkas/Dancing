export interface PracticeSession {
  id: number;
  danceId: number;
  danceName: string;
  date: string;
  durationMinutes?: number;
  notes?: string;
}
