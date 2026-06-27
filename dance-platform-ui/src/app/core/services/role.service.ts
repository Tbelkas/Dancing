import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { jwtIsAdmin } from '../utils/jwt.utils';

@Injectable({ providedIn: 'root' })
export class RoleService {
  readonly isAdmin = signal(false);

  constructor(private http: HttpClient) {}

  /** Resolve admin from the signed JWT claim (no network call). Legacy tokens that
   *  predate the claim have none — for those, fall back to the live /role/me endpoint. */
  loadFromToken(token: string | null): void {
    const claim = jwtIsAdmin(token);
    if (claim !== null) { this.isAdmin.set(claim); return; }
    if (!token) { this.isAdmin.set(false); return; }
    this.http.get<{ isAdmin: boolean }>(`${environment.apiUrl}/role/me`).subscribe({
      next: r => this.isAdmin.set(r.isAdmin),
      error: () => this.isAdmin.set(false)
    });
  }

  clearRole(): void {
    this.isAdmin.set(false);
  }
}
