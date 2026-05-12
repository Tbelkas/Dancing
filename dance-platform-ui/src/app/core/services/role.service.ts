import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

/**
 * Resolves the current user's role flags.
 * Currently fetches from /api/role/me (DB lookup).
 *
 * JWT transition: when the token carries an "isAdmin" claim, swap the
 * loadRole() body to decode the token locally — no HTTP call needed.
 * The rest of the app (components using isAdmin signal) stays unchanged.
 */
@Injectable({ providedIn: 'root' })
export class RoleService {
  readonly isAdmin = signal(false);

  constructor(private http: HttpClient) {}

  loadRole(): void {
    this.http.get<{ isAdmin: boolean }>(`${environment.apiUrl}/role/me`).subscribe({
      next: r => this.isAdmin.set(r.isAdmin),
      error: () => this.isAdmin.set(false)
    });
  }

  clearRole(): void {
    this.isAdmin.set(false);
  }
}
