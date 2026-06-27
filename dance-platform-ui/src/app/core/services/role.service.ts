import { Injectable, signal } from '@angular/core';
import { jwtIsAdmin } from '../utils/jwt.utils';

@Injectable({ providedIn: 'root' })
export class RoleService {
  readonly isAdmin = signal(false);

  /** Resolve admin from the signed JWT claim — no network call. A token without the claim
   *  (legacy or anonymous) reads as non-admin; the user re-logs in to get a claim token. */
  loadFromToken(token: string | null): void {
    this.isAdmin.set(jwtIsAdmin(token) === true);
  }

  clearRole(): void {
    this.isAdmin.set(false);
  }
}
