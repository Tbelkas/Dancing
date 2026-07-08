export interface PracticeSessionItem {
  /** 0 for local-choreo items — they have no dance to link to. */
  danceId: number;
  /** Set when the time came from one of the user's local choreos ("My choreos"). */
  choreoId?: number | null;
  danceName: string;
  danceSlug: string;
  danceStyleSlug: string;
  /** Display name of the dance's canonical style; empty when untagged. */
  danceStyleName: string;
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
