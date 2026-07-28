import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Video, VideoChapter, VideoLibraryItem, VideoNote, VideoSegment, VideoType, YoutubeChapters } from '../../models/video.model';
import { environment } from '../../../environments/environment';

export interface SegmentPayload {
  label: string;
  startTime: number;
  endTime?: number;
}

export interface NotePayload {
  timeSeconds: number;
  text: string;
}

export interface CreateVideoPayload {
  title: string;
  videoId: string;
  platform: string;
  videoType?: VideoType;
  description?: string;
  danceId: number;
  /** Admin-only: 'global' (everyone) or 'local' (just me). Ignored for non-admins (always personal). */
  scope?: 'global' | 'local';
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

  /** The current user's own privately-added videos. */
  getMine(): Observable<VideoLibraryItem[]> {
    return this.http.get<VideoLibraryItem[]>(`${this.base}/mine`);
  }

  /** All global (curated) videos — admin only. */
  getGlobal(): Observable<VideoLibraryItem[]> {
    return this.http.get<VideoLibraryItem[]>(`${this.base}/global`);
  }

  /** Other dances cut from the same source video as this one (includes itself). */
  getRelated(videoId: number): Observable<VideoChapter[]> {
    return this.http.get<VideoChapter[]>(`${this.base}/${videoId}/related`);
  }

  recordView(videoId: number): Observable<void> {
    return this.http.post<void>(`${this.base}/${videoId}/view`, {});
  }

  /** Rate a single video 1–5; resolves to the updated video (new average + the user's rating). */
  rate(videoId: number, rating: number): Observable<Video> {
    return this.http.post<Video>(`${this.base}/${videoId}/rate`, { rating });
  }

  /**
   * Admin: the chapters a YouTube video already publishes, so a well-chaptered upload can be
   * added with its sections ready-made. Resolves with an empty `chapters` list when it has none.
   */
  getYoutubeChapters(videoId: string): Observable<YoutubeChapters> {
    return this.http.get<YoutubeChapters>(`${this.base}/youtube/${videoId}/chapters`);
  }

  create(payload: CreateVideoPayload): Observable<Video> {
    return this.http.post<Video>(this.base, payload);
  }

  update(id: number, payload: UpdateVideoPayload): Observable<Video> {
    return this.http.put<Video>(`${this.base}/${id}`, payload);
  }

  /** Admin: reassign a video to a different dance (it inherits that dance's style/category). */
  moveToDance(id: number, danceId: number): Observable<Video> {
    return this.http.put<Video>(`${this.base}/${id}/dance`, { danceId });
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

  // --- Personal loops: saved to the current user's account, private to them ---

  /** The signed-in user's saved loops for this video. */
  getMyLoops(videoId: number): Observable<VideoSegment[]> {
    return this.http.get<VideoSegment[]>(`${this.base}/${videoId}/loops`);
  }

  /** Save a personal loop; resolves to the user's updated loop list for the video. */
  addMyLoop(videoId: number, payload: SegmentPayload): Observable<VideoSegment[]> {
    return this.http.post<VideoSegment[]>(`${this.base}/${videoId}/loops`, payload);
  }

  /** Delete one of the user's own loops; resolves to the updated loop list. */
  deleteMyLoop(videoId: number, loopId: number): Observable<VideoSegment[]> {
    return this.http.delete<VideoSegment[]>(`${this.base}/${videoId}/loops/${loopId}`);
  }

  // --- Personal notes: timestamped, private to the current user ---

  /** The signed-in user's notes for this video, earliest first. */
  getMyNotes(videoId: number): Observable<VideoNote[]> {
    return this.http.get<VideoNote[]>(`${this.base}/${videoId}/notes`);
  }

  /** Pin a note to a moment; resolves to the user's updated note list for the video. */
  addMyNote(videoId: number, payload: NotePayload): Observable<VideoNote[]> {
    return this.http.post<VideoNote[]>(`${this.base}/${videoId}/notes`, payload);
  }

  /** Rewrite one of the user's own notes; resolves to the updated note list. */
  updateMyNote(videoId: number, noteId: number, payload: NotePayload): Observable<VideoNote[]> {
    return this.http.put<VideoNote[]>(`${this.base}/${videoId}/notes/${noteId}`, payload);
  }

  /** Delete one of the user's own notes; resolves to the updated note list. */
  deleteMyNote(videoId: number, noteId: number): Observable<VideoNote[]> {
    return this.http.delete<VideoNote[]>(`${this.base}/${videoId}/notes/${noteId}`);
  }
}
