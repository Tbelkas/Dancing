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

export interface SearchDancesParams {
  q?: string;
  styleId?: number | null;
  musicalStyleId?: number | null;
  difficulty?: string | null;
  status?: string;
  sortBy?: string;
  page?: number;
  pageSize?: number;
}

export interface SearchDancesResult {
  items: Dance[];
  total: number;
  page: number;
  pageSize: number;
}

@Injectable({ providedIn: 'root' })
export class DanceService {
  private readonly base = `${environment.apiUrl}/dances`;

  constructor(private http: HttpClient) {}

  getNames(): Observable<{ id: number; name: string }[]> {
    return this.http.get<{ id: number; name: string }[]>(`${this.base}/names`);
  }

  /** Accepts a slug or a numeric id — the API resolves both. */
  getByIdOrSlug(idOrSlug: string | number): Observable<Dance> {
    return this.http.get<Dance>(`${this.base}/${idOrSlug}`);
  }

  /** Resolves the /dances/{styleSlug}/{slug} form, where slug is unique per style. */
  getByStyleAndSlug(styleSlug: string, slug: string): Observable<Dance> {
    return this.http.get<Dance>(`${this.base}/${styleSlug}/${slug}`);
  }

  /** "More like this" — other dances sharing this dance's style, ranked by relevance. */
  getRecommended(id: number): Observable<Dance[]> {
    return this.http.get<Dance[]>(`${this.base}/${id}/recommended`);
  }

  searchDances(p: SearchDancesParams): Observable<SearchDancesResult> {
    let params = new HttpParams();
    if (p.q) params = params.set('q', p.q);
    if (p.styleId) params = params.set('styleId', p.styleId.toString());
    if (p.musicalStyleId) params = params.set('musicalStyleId', p.musicalStyleId.toString());
    if (p.difficulty) params = params.set('difficulty', p.difficulty);
    if (p.status && p.status !== 'all') params = params.set('status', p.status);
    if (p.sortBy) params = params.set('sortBy', p.sortBy);
    if (p.page) params = params.set('page', p.page.toString());
    if (p.pageSize) params = params.set('pageSize', p.pageSize.toString());
    return this.http.get<SearchDancesResult>(`${environment.apiUrl}/search/dances`, { params });
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
