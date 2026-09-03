import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { AuthResponse, UserProfile } from '../../models/user.model';
import { ExternalProvider, LinkedAccounts, SignupTicket } from '../../models/external-auth.model';
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

  register(data: { username: string; email: string; password: string; name: string; nickname: string }): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/register`, data)
      .pipe(tap(res => { this.storeAuth(res); this.roleService.loadFromToken(res.token); this.syncAccountPrefs(); }));
  }

  /** Asks for a reset link. Always succeeds, even for an address with no account — the server
   *  deliberately refuses to say which, so this page must not either. */
  forgotPassword(email: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${environment.apiUrl}/auth/forgot-password`, { email });
  }

  /** Spends a mailed reset token and signs the user in on the new password. */
  resetPassword(token: string, newPassword: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/reset-password`, { token, newPassword })
      .pipe(tap(res => { this.storeAuth(res); this.roleService.loadFromToken(res.token); this.syncAccountPrefs(); }));
  }

  /** Changes the password of the signed-in user. The response carries a replacement token:
   *  the server retires every token issued before the change, including the one this request
   *  was made with, so storing the new one is what keeps this device signed in. */
  changePassword(currentPassword: string, newPassword: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/change-password`, { currentPassword, newPassword })
      .pipe(tap(res => { this.storeAuth(res); this.roleService.loadFromToken(res.token); }));
  }

  /** Providers with credentials configured server-side. Empty on a dev box with no secrets. */
  externalProviders(): Observable<ExternalProvider[]> {
    return this.http.get<ExternalProvider[]>(`${environment.apiUrl}/auth/external/providers`);
  }

  /** Leaves the SPA for the provider's consent screen. A full navigation, not an XHR — the
   *  provider has to see a real browser to show its own UI and set its own cookies. */
  startExternal(provider: string): void {
    window.location.href = `${environment.apiUrl}/auth/external/${provider}/start`;
  }

  /** Completes a social sign-in whose token arrived in the redirect fragment. Identity comes from
   *  /profile rather than an AuthResponse, so this never has to guess how .NET named its claims. */
  adoptExternalToken(token: string): Observable<UserProfile> {
    localStorage.setItem(this.TOKEN_KEY, token);
    this._token.set(token);
    this.roleService.loadFromToken(token);

    return this.profileService.getProfile().pipe(tap(profile => {
      localStorage.setItem(this.USER_KEY,
        JSON.stringify({ userId: profile.id, username: profile.username }));
      this.currentUserId.set(profile.id);
      this.currentUsername.set(profile.username);
    }));
  }

  /** Describes an unspent sign-up ticket so the username step can show who signed in. */
  inspectTicket(ticket: string): Observable<SignupTicket> {
    return this.http.post<SignupTicket>(`${environment.apiUrl}/auth/external/ticket`, { ticket });
  }

  /** Spends the ticket, creating the account under the chosen username. */
  completeExternal(ticket: string, username: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/external/complete`, { ticket, username })
      .pipe(tap(res => { this.storeAuth(res); this.roleService.loadFromToken(res.token); this.syncAccountPrefs(); }));
  }

  linkedAccounts(): Observable<LinkedAccounts> {
    return this.http.get<LinkedAccounts>(`${environment.apiUrl}/auth/external/links`);
  }

  /** Starts a link from the profile page. A POST first, so the bearer token travels in a header
   *  instead of the query string; the server hands back the URL to navigate to. */
  startLink(provider: string): Observable<{ url: string }> {
    return this.http.post<{ url: string }>(
      `${environment.apiUrl}/auth/external/${provider}/link-start`, {});
  }

  unlinkAccount(provider: string): Observable<void> {
    return this.http.delete<void>(`${environment.apiUrl}/auth/external/links/${provider}`);
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
