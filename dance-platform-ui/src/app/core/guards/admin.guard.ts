import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { RoleService } from '../services/role.service';

/** Admin-only route guard. Reads RoleService rather than the JWT directly, so an admin
 *  who has switched to the normal-user view is bounced from the admin routes too —
 *  otherwise the pages would stay reachable by URL while their nav links were hidden.
 *  Non-admins land on /dances, anonymous users on /login. */
export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const role = inject(RoleService);
  const router = inject(Router);

  if (!auth.isAuthenticated()) return router.createUrlTree(['/login']);
  return role.isAdmin() ? true : router.createUrlTree(['/dances']);
};
