import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Choreo } from '../../models/choreo.model';
import { SegmentPayload } from './video.service';
import { environment } from '../../../environments/environment';

export interface CreateChoreoPayload {
  name: string;
  fileName: string;
  durationSeconds?: number;
}

export interface UpdateChoreoPayload {
  name?: string;
  fileName?: string;
  durationSeconds?: number;
}

@Injectable({ providedIn: 'root' })
export class ChoreoService {
  private readonly base = `${environment.apiUrl}/choreos`;

  /** Files picked this session, keyed by choreo id. Browsers can't reopen local files
   *  on their own, so keeping the File here spares a re-pick while the tab lives. */
  private sessionFiles = new Map<number, File>();

  constructor(private http: HttpClient) {}

  getMine(): Observable<Choreo[]> {
    return this.http.get<Choreo[]>(this.base);
  }

  create(payload: CreateChoreoPayload): Observable<Choreo> {
    return this.http.post<Choreo>(this.base, payload);
  }

  update(id: number, payload: UpdateChoreoPayload): Observable<Choreo> {
    return this.http.put<Choreo>(`${this.base}/${id}`, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  /** Save a time slot; resolves to the updated choreo (loops included). */
  addLoop(id: number, payload: SegmentPayload): Observable<Choreo> {
    return this.http.post<Choreo>(`${this.base}/${id}/loops`, payload);
  }

  deleteLoop(id: number, loopId: number): Observable<Choreo> {
    return this.http.delete<Choreo>(`${this.base}/${id}/loops/${loopId}`);
  }

  rememberFile(choreoId: number, file: File): void {
    this.sessionFiles.set(choreoId, file);
  }

  recallFile(choreoId: number): File | undefined {
    return this.sessionFiles.get(choreoId);
  }

  forgetFile(choreoId: number): void {
    this.sessionFiles.delete(choreoId);
  }
}
