import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Style } from '../../models/style.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class StyleService {
  private readonly base = `${environment.apiUrl}/styles`;

  constructor(private http: HttpClient) {}

  getAll(): Observable<Style[]> {
    return this.http.get<Style[]>(this.base);
  }

  create(name: string, description?: string): Observable<Style> {
    return this.http.post<Style>(this.base, { name, description });
  }

  toggleMyStyle(id: number): Observable<{ isMyStyle: boolean }> {
    return this.http.post<{ isMyStyle: boolean }>(`${this.base}/${id}/mystyle`, {});
  }
}
