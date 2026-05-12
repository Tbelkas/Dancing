import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Video } from '../../models/video.model';
import { environment } from '../../../environments/environment';

export interface CreateVideoPayload {
  title: string;
  youTubeId: string;
  description?: string;
  danceId: number;
  startTime?: number;
  endTime?: number;
}

@Injectable({ providedIn: 'root' })
export class VideoService {
  private readonly base = `${environment.apiUrl}/videos`;

  constructor(private http: HttpClient) {}

  getByDance(danceId: number): Observable<Video[]> {
    return this.http.get<Video[]>(`${this.base}/dance/${danceId}`);
  }

  recordView(videoId: number): Observable<void> {
    return this.http.post<void>(`${this.base}/${videoId}/view`, {});
  }

  create(payload: CreateVideoPayload): Observable<Video> {
    return this.http.post<Video>(this.base, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }
}
