import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { AuthResponse } from '../../models/user.model';
import { environment } from '../../../environments/environment';
import { RoleService } from './role.service';
import { ProfileService } from './profile.service';
import { isTokenExpired } from '../utils/jwt.utils';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'dp_token';
  private readonly USER_KEY = 'dp_user';

  private _token = signal<string | null>(localStorage.getItem(this.TOKEN_KEY));
  readonly isAuthenticated = computed(() => !!this._token() && !isTokenExpired(this._token()));
  readonly currentUserId = signal<number | null>(this.readStoredUser()?.userId ?? null);
  readonly currentUsername = signal<string | null>(this.readStoredUser()?.username ?? null);

  /** Reads the stored user defensively — a corrupt dp_user must not throw during DI construction
   *  (this service is injected app-wide; a throw here white-screens the whole app at bootstrap). */
  private readStoredUser(): { userId: number | null; username: string | null } | null {
    const stored = localStorage.getItem(this.USER_KEY);
    if (!stored) return null;
    try {
      const parsed = JSON.parse(stored);
      return { userId: parsed.userId ?? null, username: parsed.username ?? null };
    } catch {
      localStorage.removeItem(this.USER_KEY);
      return null;
    }
  }

  constructor(private http: HttpClient, private router: Router, private roleService: RoleService,
              private profileService: ProfileService) {
    // If already authenticated on app start, resolve admin from the stored token's claim
    // and pull account preferences (viewer chrome) onto this device. Deferred a tick:
    // an HTTP call here would re-enter DI for this half-constructed service via the
    // auth interceptor.
    if (this._token()) {
      this.roleService.loadFromToken(this._token());
      queueMicrotask(() => this.syncAccountPrefs());
    }
  }

  login(username: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/login`, { username, password })
      .pipe(tap(res => { this.storeAuth(res); this.roleService.loadFromToken(res.token); this.syncAccountPrefs(); }));
  }

  register(data: { username: string; password: string; name: string; nickname: string }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/register`, data)
      .pipe(tap(res => { this.storeAuth(res); this.roleService.loadFromToken(res.token); this.syncAccountPrefs(); }));
  }

  /** Best-effort profile fetch purely for its side effect: ProfileService mirrors
   *  account preferences (beta viewer) into localStorage for the video players. */
  private syncAccountPrefs(): void {
    this.profileService.getProfile().subscribe({ error: () => {} });
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this._token.set(null);
    this.currentUserId.set(null);
    this.currentUsername.set(null);
    this.roleService.clearRole();
    this.router.navigate(['/login']);
  }

  getToken(): string | null { return this._token(); }

  private storeAuth(res: AuthResponse): void {
    localStorage.setItem(this.TOKEN_KEY, res.token);
    localStorage.setItem(this.USER_KEY, JSON.stringify({ userId: res.userId, username: res.username }));
    this._token.set(res.token);
    this.currentUserId.set(res.userId);
    this.currentUsername.set(res.username);
  }
}
