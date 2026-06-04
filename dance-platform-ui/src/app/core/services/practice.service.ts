import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PracticeSession } from '../../models/practice-session.model';
import { environment } from '../../../environments/environment';

export interface CreatePracticePayload {
  danceId: number;
  date: string;
  durationMinutes?: number;
  notes?: string;
}

@Injectable({ providedIn: 'root' })
export class PracticeService {
  private readonly base = `${environment.apiUrl}/practice`;

  constructor(private http: HttpClient) {}

  getAll(): Observable<PracticeSession[]> {
    return this.http.get<PracticeSession[]>(this.base);
  }

  create(payload: CreatePracticePayload): Observable<PracticeSession> {
    return this.http.post<PracticeSession>(this.base, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }
}
