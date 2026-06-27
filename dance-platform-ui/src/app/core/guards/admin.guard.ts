import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { jwtIsAdmin } from '../utils/jwt.utils';

/** Admin-only route guard. Reads the signed isAdmin claim straight from the JWT — no
 *  network call. Non-admins land on /dances, anonymous users on /login. */
export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.isAuthenticated()) return router.createUrlTree(['/login']);
  return jwtIsAdmin(auth.getToken()) === true ? true : router.createUrlTree(['/dances']);
};
