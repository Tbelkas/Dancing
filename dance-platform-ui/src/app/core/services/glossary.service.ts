import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Glossary, GlossarySummary } from '../../models/glossary.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class GlossaryService {
  private readonly base = `${environment.apiUrl}/glossary`;

  constructor(private http: HttpClient) {}

  // Uncached: both responses carry the caller's own learned marks.
  getAll(): Observable<GlossarySummary[]> {
    return this.http.get<GlossarySummary[]>(this.base);
  }

  getByStyle(styleSlug: string): Observable<Glossary> {
    return this.http.get<Glossary>(`${this.base}/${styleSlug}`);
  }

  /** Sets rather than toggles, so a retried request can't flip the mark back. */
  setLearned(termId: number, learned: boolean): Observable<void> {
    return this.http.put<void>(`${this.base}/terms/${termId}/learned`, { learned });
  }
}
