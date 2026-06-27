import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { map, catchError, of } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { environment } from '../../../environments/environment';

/** Admin-only route guard. Resolves the role live from the API (the JWT carries no
 *  admin claim), so it's correct even on a hard refresh before the cached signal loads. */
export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const http = inject(HttpClient);

  if (!auth.isAuthenticated()) return of(router.createUrlTree(['/login']));

  return http.get<{ isAdmin: boolean }>(`${environment.apiUrl}/role/me`).pipe(
    map(r => (r.isAdmin ? true : router.createUrlTree(['/dances']))),
    catchError(() => of(router.createUrlTree(['/dances'])))
  );
};
