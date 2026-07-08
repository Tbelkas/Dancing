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

  getMyDances(): Observable<MyStyleWithDances[]> {
    return this.http.get<MyStyleWithDances[]>(`${this.base}/my-dances`);
  }
}
