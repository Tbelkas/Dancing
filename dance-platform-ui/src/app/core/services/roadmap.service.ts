import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Roadmap, RoadmapSummary, SaveRoadmap } from '../../models/roadmap.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class RoadmapService {
  private readonly base = `${environment.apiUrl}/roadmaps`;

  constructor(private http: HttpClient) {}

  // Deliberately uncached (unlike StyleService): the response carries the caller's own
  // learned/in-progress counts and their own skill trees, both of which change as they work.
  getAll(): Observable<RoadmapSummary[]> {
    return this.http.get<RoadmapSummary[]>(this.base);
  }

  getBySlug(slug: string): Observable<Roadmap> {
    return this.http.get<Roadmap>(`${this.base}/${slug}`);
  }

  /** Creates a personal skill tree. The server picks the slug — it has to be unique. */
  create(tree: SaveRoadmap): Observable<Roadmap> {
    return this.http.post<Roadmap>(this.base, tree);
  }

  /** Replaces a personal tree wholesale; anything left out of `tree` is deleted. */
  update(id: number, tree: SaveRoadmap): Observable<Roadmap> {
    return this.http.put<Roadmap>(`${this.base}/${id}`, tree);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  /** Forks a path into one of the caller's own, curated ones included. */
  copy(idOrSlug: string): Observable<Roadmap> {
    return this.http.post<Roadmap>(`${this.base}/${idOrSlug}/copy`, {});
  }
}
