import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Video, VideoChapter, VideoType } from '../../models/video.model';
import { environment } from '../../../environments/environment';

export interface SegmentPayload {
  label: string;
  startTime: number;
  endTime?: number;
}

export interface CreateVideoPayload {
  title: string;
  videoId: string;
  platform: string;
  videoType?: VideoType;
  description?: string;
  danceId: number;
  startTime?: number;
  endTime?: number;
  segments?: SegmentPayload[];
}

export interface UpdateVideoPayload {
  title?: string;
  videoId?: string;
  description?: string;
  videoType?: VideoType;
  updateTimes?: boolean;
  startTime?: number;
  endTime?: number;
  updateSegments?: boolean;
  segments?: SegmentPayload[];
}

@Injectable({ providedIn: 'root' })
export class VideoService {
  private readonly base = `${environment.apiUrl}/videos`;

  constructor(private http: HttpClient) {}

  getByDance(danceId: number): Observable<Video[]> {
    return this.http.get<Video[]>(`${this.base}/dance/${danceId}`);
  }

  /** Other dances cut from the same source video as this one (includes itself). */
  getRelated(videoId: number): Observable<VideoChapter[]> {
    return this.http.get<VideoChapter[]>(`${this.base}/${videoId}/related`);
  }

  recordView(videoId: number): Observable<void> {
    return this.http.post<void>(`${this.base}/${videoId}/view`, {});
  }

  create(payload: CreateVideoPayload): Observable<Video> {
    return this.http.post<Video>(this.base, payload);
  }

  update(id: number, payload: UpdateVideoPayload): Observable<Video> {
    return this.http.put<Video>(`${this.base}/${id}`, payload);
  }

  /** Append one named loop region (section) to a video without touching its others. */
  addSegment(id: number, payload: SegmentPayload): Observable<Video> {
    return this.http.post<Video>(`${this.base}/${id}/segments`, payload);
  }

  /** Remove a single section from a video, leaving the rest intact. */
  deleteSegment(id: number, segmentId: number): Observable<Video> {
    return this.http.delete<Video>(`${this.base}/${id}/segments/${segmentId}`);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }
}
