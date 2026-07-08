import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PracticeSession } from '../../models/practice-session.model';
import { ReviewDance } from '../../models/review-dance.model';
import { environment } from '../../../environments/environment';

export interface CreatePracticePayload {
  danceId: number;
  date: string;
  durationMinutes?: number;
  notes?: string;
}

export interface UpdatePracticePayload {
  date: string;
  notes?: string;
  /** Only applied server-side when the session holds a single dance. */
  durationMinutes?: number;
}

export interface PracticeHeartbeatPayload {
  /** Exactly one of danceId / choreoId identifies what is being practiced. */
  danceId?: number | null;
  /** Video generating the watch time, so history can follow a video moved to another dance. */
  videoId?: number | null;
  /** Local choreo ("My choreos") generating the watch time. */
  choreoId?: number | null;
  seconds: number;
  localDate: string;
}

@Injectable({ providedIn: 'root' })
export class PracticeService {
  private readonly base = `${environment.apiUrl}/practice`;

  constructor(private http: HttpClient) {}

  getAll(): Observable<PracticeSession[]> {
    return this.http.get<PracticeSession[]>(this.base);
  }

  /** Learned dances gone unpracticed for 3+ weeks, stalest first. */
  getReviewQueue(): Observable<ReviewDance[]> {
    return this.http.get<ReviewDance[]>(`${this.base}/review`);
  }

  create(payload: CreatePracticePayload): Observable<PracticeSession> {
    return this.http.post<PracticeSession>(this.base, payload);
  }

  heartbeat(payload: PracticeHeartbeatPayload): Observable<PracticeSession> {
    return this.http.post<PracticeSession>(`${this.base}/heartbeat`, payload);
  }

  update(id: number, payload: UpdatePracticePayload): Observable<PracticeSession> {
    return this.http.put<PracticeSession>(`${this.base}/${id}`, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }
}
