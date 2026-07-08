import { Injectable, signal } from '@angular/core';
import { UserProfile } from '../../models/user.model';

/**
 * The "Dance Platform video viewer (beta)" preference: replace an embed's native
 * controls with the platform's own player chrome wherever the embed's API allows
 * it (YouTube today; TikTok/Instagram can't be driven externally).
 *
 * The account value lives on the profile; it's mirrored to localStorage so the
 * video player can read it synchronously on any page, before (or without) a
 * profile fetch. Signed-out visitors get the plain embeds.
 */
@Injectable({ providedIn: 'root' })
export class ViewerPrefsService {
  private readonly BETA_VIEWER_KEY = 'dp_beta_viewer';

  readonly betaViewer = signal(localStorage.getItem(this.BETA_VIEWER_KEY) === '1');

  /** Called whenever the profile is loaded or saved, so the cached value follows the account. */
  syncFromProfile(profile: UserProfile): void {
    this.setLocal(profile.useBetaViewer);
  }

  setLocal(value: boolean): void {
    this.betaViewer.set(value);
    localStorage.setItem(this.BETA_VIEWER_KEY, value ? '1' : '0');
  }
}
