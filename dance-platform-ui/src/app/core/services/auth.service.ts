import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { AuthResponse } from '../../models/user.model';
import { environment } from '../../../environments/environment';
import { RoleService } from './role.service';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'dp_token';
  private readonly USER_KEY = 'dp_user';

  private _token = signal<string | null>(localStorage.getItem(this.TOKEN_KEY));
  readonly isAuthenticated = computed(() => !!this._token());
  readonly currentUserId = signal<number | null>((() => {
    const stored = localStorage.getItem(this.USER_KEY);
    return stored ? JSON.parse(stored).userId : null;
  })());

  constructor(private http: HttpClient, private router: Router, private roleService: RoleService) {
    // If already authenticated on app start, resolve admin from the stored token's claim.
    if (this._token()) this.roleService.loadFromToken(this._token());
  }

  login(username: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/login`, { username, password })
      .pipe(tap(res => { this.storeAuth(res); this.roleService.loadFromToken(res.token); }));
  }

  register(data: { username: string; password: string; name: string; nickname: string }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/register`, data)
      .pipe(tap(res => { this.storeAuth(res); this.roleService.loadFromToken(res.token); }));
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this._token.set(null);
    this.currentUserId.set(null);
    this.roleService.clearRole();
    this.router.navigate(['/login']);
  }

  getToken(): string | null { return this._token(); }

  private storeAuth(res: AuthResponse): void {
    localStorage.setItem(this.TOKEN_KEY, res.token);
    localStorage.setItem(this.USER_KEY, JSON.stringify({ userId: res.userId, username: res.username }));
    this._token.set(res.token);
    this.currentUserId.set(res.userId);
  }
}
