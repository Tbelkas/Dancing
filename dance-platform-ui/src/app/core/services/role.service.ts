import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

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
