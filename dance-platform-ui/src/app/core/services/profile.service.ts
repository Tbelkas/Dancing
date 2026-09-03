import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { MyStyleWithDances, UserProfile } from '../../models/user.model';
import { ViewerPrefsService } from './viewer-prefs.service';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ProfileService {
  private readonly base = `${environment.apiUrl}/profile`;

  constructor(private http: HttpClient, private viewerPrefs: ViewerPrefsService) {}

  getProfile(): Observable<UserProfile> {
    return this.http.get<UserProfile>(this.base).pipe(
      tap(p => this.viewerPrefs.syncFromProfile(p))
    );
  }

  updateProfile(data: Partial<Pick<UserProfile, 'name' | 'nickname' | 'avatarUrl' | 'visibility' | 'useBetaViewer'>>): Observable<UserProfile> {
    return this.http.put<UserProfile>(this.base, data).pipe(
      tap(p => this.viewerPrefs.syncFromProfile(p))
    );
  }

  /** Its own endpoint, because it's the only profile field that can collide with another
   *  account (409) rather than simply saving. */
  setEmail(email: string): Observable<UserProfile> {
    return this.http.put<UserProfile>(`${this.base}/email`, { email }).pipe(
      tap(p => this.viewerPrefs.syncFromProfile(p))
    );
  }

  /** Permanent. The password is the confirmation — being signed in isn't enough. */
  deleteAccount(password: string): Observable<void> {
    return this.http.delete<void>(this.base, { body: { password } });
  }

  getMyDances(): Observable<MyStyleWithDances[]> {
    return this.http.get<MyStyleWithDances[]>(`${this.base}/my-dances`);
  }
}
