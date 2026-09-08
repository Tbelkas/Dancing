import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CatalogHealth } from '../../models/catalog-health.model';
import { MergeTagResult, TagAdmin, TagKind, TagUsage } from '../../models/tag-admin.model';
import { environment } from '../../../environments/environment';

/** Admin surfaces that span the whole catalogue rather than one dance or video. */
@Injectable({ providedIn: 'root' })
export class AdminService {
  private readonly base = `${environment.apiUrl}/admin`;

  constructor(private http: HttpClient) {}

  /** Catalogue health: headline counts plus every standing check. */
  getHealth(): Observable<CatalogHealth> {
    return this.http.get<CatalogHealth>(`${this.base}/health`);
  }

  /** Both tag vocabularies with their dance counts. */
  getTags(): Observable<TagAdmin> {
    return this.http.get<TagAdmin>(`${this.base}/tags`);
  }

  /**
   * Rename a tag. For a style this changes the {style} segment of every dance URL under it —
   * the old links stop resolving.
   */
  renameTag(kind: TagKind, id: number, name: string): Observable<TagUsage> {
    return this.http.put<TagUsage>(`${this.base}/tags/${kind}/${id}`, { name });
  }

  /** Fold one tag into another: the dances move across, the source tag is deleted. */
  mergeTag(kind: TagKind, id: number, targetId: number): Observable<MergeTagResult> {
    return this.http.post<MergeTagResult>(`${this.base}/tags/${kind}/${id}/merge`, { targetId });
  }

  /** Delete an unused tag. Refused with a 409 while any dance still carries it. */
  deleteTag(kind: TagKind, id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/tags/${kind}/${id}`);
  }
}
