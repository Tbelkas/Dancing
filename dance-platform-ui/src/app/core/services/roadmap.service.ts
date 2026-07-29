import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Roadmap, RoadmapSummary } from '../../models/roadmap.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class RoadmapService {
  private readonly base = `${environment.apiUrl}/roadmaps`;

  constructor(private http: HttpClient) {}

  // Deliberately uncached (unlike StyleService): the response carries the caller's own
  // learned/in-progress counts, which change as they work through a path.
  getAll(): Observable<RoadmapSummary[]> {
    return this.http.get<RoadmapSummary[]>(this.base);
  }

  getBySlug(slug: string): Observable<Roadmap> {
    return this.http.get<Roadmap>(`${this.base}/${slug}`);
  }
}
