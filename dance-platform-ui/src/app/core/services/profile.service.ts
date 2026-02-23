import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { UserProfile } from '../../models/user.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ProfileService {
  private readonly base = `${environment.apiUrl}/profile`;

  constructor(private http: HttpClient) {}

  getProfile(): Observable<UserProfile> {
    return this.http.get<UserProfile>(this.base);
  }

  updateProfile(data: Partial<Pick<UserProfile, 'name' | 'nickname' | 'avatarUrl' | 'visibility'>>): Observable<UserProfile> {
    return this.http.put<UserProfile>(this.base, data);
  }
}
