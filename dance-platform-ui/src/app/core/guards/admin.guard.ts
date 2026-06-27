import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { map, catchError, of } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { jwtIsAdmin } from '../utils/jwt.utils';
import { environment } from '../../../environments/environment';

/** Admin-only route guard. Reads the signed isAdmin claim straight from the JWT — no
 *  network call — and only falls back to the live /role/me endpoint for legacy tokens
 *  issued before the claim existed. */
export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const http = inject(HttpClient);

  if (!auth.isAuthenticated()) return of(router.createUrlTree(['/login']));

  const claim = jwtIsAdmin(auth.getToken());
  if (claim !== null) return claim ? true : router.createUrlTree(['/dances']);

  return http.get<{ isAdmin: boolean }>(`${environment.apiUrl}/role/me`).pipe(
    map(r => (r.isAdmin ? true : router.createUrlTree(['/dances']))),
    catchError(() => of(router.createUrlTree(['/dances'])))
  );
};
