import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/**
 * Sends signed-in dancers from "/" straight to their dances.
 *
 * This has to be a guard rather than a redirect in LandingComponent.ngOnInit: the component's
 * template renders before `router.navigate` resolves, so a returning user got ~50ms of the
 * marketing hero before My Dances replaced it. A guard runs before the component is created,
 * so there is nothing to flash.
 */
export const landingGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) return router.createUrlTree(['/my-dances']);
  return true;
};
