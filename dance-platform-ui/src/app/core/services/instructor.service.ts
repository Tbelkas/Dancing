import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { shareReplay, tap } from 'rxjs/operators';
import { Instructor } from '../../models/instructor.model';
import { environment } from '../../../environments/environment';

export interface CreateInstructorPayload {
  name: string;
  bio?: string;
  avatarUrl?: string;
  website?: string;
}

@Injectable({ providedIn: 'root' })
export class InstructorService {
  private readonly base = `${environment.apiUrl}/instructors`;

  // Cached for the session like the other catalog lookups; invalidated in create()/delete()
  // below so mutations are reflected on the next getAll().
  private all$?: Observable<Instructor[]>;

  constructor(private http: HttpClient) {}

  getAll(): Observable<Instructor[]> {
    return this.all$ ??= this.http.get<Instructor[]>(this.base).pipe(shareReplay(1));
  }

  getById(id: number): Observable<Instructor> {
    return this.http.get<Instructor>(`${this.base}/${id}`);
  }

  create(payload: CreateInstructorPayload): Observable<Instructor> {
    return this.http.post<Instructor>(this.base, payload).pipe(
      tap(() => this.all$ = undefined)
    );
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`).pipe(
      tap(() => this.all$ = undefined)
    );
  }
}
