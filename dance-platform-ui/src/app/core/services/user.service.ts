import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface PublicProfile {
  id: number;
  username: string;
  nickname: string;
  avatarUrl?: string;
  learnedDances: { id: number; name: string; slug: string; styleSlug: string }[];
  /**
   * Skill trees this user has shared. Shared trees stay off the roadmap index by design, so
   * this and the tree's own link are the only ways to reach one.
   */
  sharedRoadmaps: SharedRoadmapRef[];
}

export interface SharedRoadmapRef {
  slug: string;
  title: string;
  subtitle: string;
  styleName: string;
  stepCount: number;
}

@Injectable({ providedIn: 'root' })
export class UserService {
  constructor(private http: HttpClient) {}

  getPublicProfile(username: string): Observable<PublicProfile> {
    return this.http.get<PublicProfile>(`${environment.apiUrl}/users/${username}`);
  }
}
