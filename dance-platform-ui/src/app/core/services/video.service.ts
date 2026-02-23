import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Video } from '../../models/video.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class VideoService {
  private readonly base = `${environment.apiUrl}/videos`;

  constructor(private http: HttpClient) {}

  getByDance(danceId: number): Observable<Video[]> {
    return this.http.get<Video[]>(`${this.base}/dance/${danceId}`);
  }
}
