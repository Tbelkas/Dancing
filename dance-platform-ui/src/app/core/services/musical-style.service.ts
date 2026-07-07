import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { shareReplay } from 'rxjs/operators';
import { MusicalStyle } from '../../models/musical-style.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class MusicalStyleService {
  private readonly base = `${environment.apiUrl}/musicalstyles`;

  // Musical styles are read-only from the client (no create/delete), so a plain
  // session-lifetime cache is safe — the first response is replayed to every caller.
  private all$?: Observable<MusicalStyle[]>;

  constructor(private http: HttpClient) {}

  getAll(): Observable<MusicalStyle[]> {
    return this.all$ ??= this.http.get<MusicalStyle[]>(this.base).pipe(shareReplay(1));
  }
}
