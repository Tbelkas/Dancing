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
}
