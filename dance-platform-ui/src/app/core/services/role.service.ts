import { Injectable, computed, signal } from '@angular/core';
import { jwtIsAdmin } from '../utils/jwt.utils';

/**
 * Two different questions, deliberately kept apart:
 *
 *   isSuperAdmin  may this account administer the catalogue? (signed JWT claim)
 *   adminMode     does it want to see the admin UI right now? (per-device preference)
 *   isAdmin       both — the one every admin affordance in the app reads.
 *
 * Turning admin mode off is a *view*, not a demotion: it hides the edit, review and
 * import surfaces so the site can be walked the way a normal user meets it. The API is
 * unchanged and still honours the token's claim, so this is a UI gate and never a
 * security boundary — see RequireAdminAttribute for the one that is.
 */
@Injectable({ providedIn: 'root' })
export class RoleService {
  private readonly ADMIN_MODE_KEY = 'dp_admin_mode';

  /** The capability itself, straight from the signed claim. Only the settings toggle
   *  reads this; everything else wants isAdmin. */
  readonly isSuperAdmin = signal(false);

  /** Per-device, and survives sign-out on purpose: someone who switched to the user's
   *  view to check a page expects it to still be that way after logging back in.
   *  Defaults on, so an admin who never touches the toggle sees no change. */
  readonly adminMode = signal(localStorage.getItem(this.ADMIN_MODE_KEY) !== '0');

  readonly isAdmin = computed(() => this.isSuperAdmin() && this.adminMode());

  /** Resolve admin from the signed JWT claim — no network call. A token without the claim
   *  (legacy or anonymous) reads as non-admin; the user re-logs in to get a claim token. */
  loadFromToken(token: string | null): void {
    this.isSuperAdmin.set(jwtIsAdmin(token) === true);
  }

  setAdminMode(value: boolean): void {
    this.adminMode.set(value);
    localStorage.setItem(this.ADMIN_MODE_KEY, value ? '1' : '0');
  }

  clearRole(): void {
    this.isSuperAdmin.set(false);
  }
}
