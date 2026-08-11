import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { PERSONAL_ROADMAPS_ENABLED } from '../constants/feature-flags';

/**
 * Keeps the builder unreachable while personal skill trees are switched off.
 *
 * Hiding the buttons is not enough on its own — /roadmaps/new is a URL people have bookmarked
 * and the fork button used to hand out /roadmaps/:slug/edit links. Sending them to the index
 * beats a builder that can still write rows the app no longer shows.
 */
export const personalRoadmapsGuard: CanActivateFn = () => {
  if (PERSONAL_ROADMAPS_ENABLED) return true;
  return inject(Router).createUrlTree(['/roadmaps']);
};
