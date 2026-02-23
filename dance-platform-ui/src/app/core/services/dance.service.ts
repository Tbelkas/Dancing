import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Dance } from '../../models/dance.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class DanceService {
  private readonly base = `${environment.apiUrl}/dances`;

  constructor(private http: HttpClient) {}

  getAll(): Observable<Dance[]> {
    return this.http.get<Dance[]>(this.base);
  }

  getById(id: number): Observable<Dance> {
    return this.http.get<Dance>(`${this.base}/${id}`);
  }

  search(query: string, styleId?: number): Observable<Dance[]> {
    let params = new HttpParams();
    if (query) params = params.set('q', query);
    if (styleId) params = params.set('styleId', styleId.toString());
    return this.http.get<Dance[]>(`${environment.apiUrl}/search/dances`, { params });
  }

  toggleFavorite(id: number): Observable<{ isFavorite: boolean }> {
    return this.http.post<{ isFavorite: boolean }>(`${this.base}/${id}/favorite`, {});
  }

  toggleLearned(id: number): Observable<{ isLearned: boolean }> {
    return this.http.post<{ isLearned: boolean }>(`${this.base}/${id}/learned`, {});
  }
}
