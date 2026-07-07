import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { shareReplay, tap } from 'rxjs/operators';
import { Style } from '../../models/style.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class StyleService {
  private readonly base = `${environment.apiUrl}/styles`;

  // The style catalog is read on nearly every page but changes rarely, so cache the first
  // response and replay it for the rest of the session instead of re-hitting the API each
  // time. Invalidated in create() below so a freshly added style shows up on the next getAll().
  private all$?: Observable<Style[]>;

  constructor(private http: HttpClient) {}

  getAll(): Observable<Style[]> {
    return this.all$ ??= this.http.get<Style[]>(this.base).pipe(shareReplay(1));
  }

  create(name: string, description?: string): Observable<Style> {
    // Adding a style mutates the list — drop the cache so the next getAll() refetches it.
    return this.http.post<Style>(this.base, { name, description }).pipe(
      tap(() => this.all$ = undefined)
    );
  }

  toggleMyStyle(id: number): Observable<{ isMyStyle: boolean }> {
    return this.http.post<{ isMyStyle: boolean }>(`${this.base}/${id}/mystyle`, {});
  }
}
