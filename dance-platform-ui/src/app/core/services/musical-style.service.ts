import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { MusicalStyle } from '../../models/musical-style.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class MusicalStyleService {
  private readonly base = `${environment.apiUrl}/musicalstyles`;

  constructor(private http: HttpClient) {}

  getAll(): Observable<MusicalStyle[]> {
    return this.http.get<MusicalStyle[]>(this.base);
  }
}
