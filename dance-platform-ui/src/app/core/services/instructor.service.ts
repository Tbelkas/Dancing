import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
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

  constructor(private http: HttpClient) {}

  getAll(): Observable<Instructor[]> {
    return this.http.get<Instructor[]>(this.base);
  }

  getById(id: number): Observable<Instructor> {
    return this.http.get<Instructor>(`${this.base}/${id}`);
  }

  create(payload: CreateInstructorPayload): Observable<Instructor> {
    return this.http.post<Instructor>(this.base, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }
}
