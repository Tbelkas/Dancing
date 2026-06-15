import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Dance } from '../../models/dance.model';
import { environment } from '../../../environments/environment';

export type DanceStatus = 'notstarted' | 'inprogress' | 'learned';

export interface CreateDancePayload {
  name: string;
  description?: string;
  difficulty?: string;
  styleIds: number[];
  musicalStyleIds: number[];
  instructorIds?: number[];
}

export interface UpdateDancePayload {
  name?: string;
  description?: string;
  difficulty?: string;
  styleIds?: number[];
  musicalStyleIds?: number[];
  instructorIds?: number[];
}

export interface ImportResult {
  videoId: string | null;
  created: Dance[];
  errors: string[];
}

@Injectable({ providedIn: 'root' })
export class DanceService {
  private readonly base = `${environment.apiUrl}/dances`;

  constructor(private http: HttpClient) {}

  getAll(): Observable<Dance[]> {
    return this.http.get<Dance[]>(this.base);
  }

  /** Accepts a slug or a numeric id — the API resolves both. */
  getByIdOrSlug(idOrSlug: string | number): Observable<Dance> {
    return this.http.get<Dance>(`${this.base}/${idOrSlug}`);
  }

  search(query: string, styleId?: number, musicalStyleId?: number, difficulty?: string, status?: string): Observable<Dance[]> {
    let params = new HttpParams();
    if (query) params = params.set('q', query);
    if (styleId) params = params.set('styleId', styleId.toString());
    if (musicalStyleId) params = params.set('musicalStyleId', musicalStyleId.toString());
    if (difficulty) params = params.set('difficulty', difficulty);
    if (status) params = params.set('status', status);
    return this.http.get<Dance[]>(`${environment.apiUrl}/search/dances`, { params });
  }

  rate(id: number, rating: number): Observable<Dance> {
    return this.http.post<Dance>(`${this.base}/${id}/rate`, { rating });
  }

  create(payload: CreateDancePayload): Observable<Dance> {
    return this.http.post<Dance>(this.base, payload);
  }

  update(id: number, payload: UpdateDancePayload): Observable<Dance> {
    return this.http.put<Dance>(`${this.base}/${id}`, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  toggleFavorite(id: number): Observable<{ isFavorite: boolean }> {
    return this.http.post<{ isFavorite: boolean }>(`${this.base}/${id}/favorite`, {});
  }

  toggleLearned(id: number): Observable<{ isLearned: boolean }> {
    return this.http.post<{ isLearned: boolean }>(`${this.base}/${id}/learned`, {});
  }

  toggleInProgress(id: number): Observable<{ isInProgress: boolean }> {
    return this.http.post<{ isInProgress: boolean }>(`${this.base}/${id}/inprogress`, {});
  }

  /** Sets the mutually-exclusive learning status atomically (one transaction, server-enforced). */
  setStatus(id: number, status: DanceStatus): Observable<{ isLearned: boolean; isInProgress: boolean }> {
    return this.http.put<{ isLearned: boolean; isInProgress: boolean }>(`${this.base}/${id}/status`, { status });
  }

  importDances(text: string): Observable<ImportResult> {
    return this.http.post<ImportResult>(`${environment.apiUrl}/import/dances`, { text });
  }
}
