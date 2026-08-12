import { Component, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

/** Lands the browser after a successful social sign-in. The token arrives in the URL fragment
 *  (never a query param — a fragment is not sent to the server, so it stays out of Apache's
 *  access log and out of Referer headers), is consumed here, and the hash is cleared so a
 *  back-navigation or a shared URL can't replay it. */
@Component({
  selector: 'app-auth-callback',
  standalone: true,
  template: `
    <div class="callback-page" data-testid="auth-callback">
      @if (error()) {
        <p class="callback-error">{{ error() }}</p>
      } @else {
        <p class="callback-status">Signing you in&hellip;</p>
      }
    </div>
  `,
  styles: [`
    .callback-page {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: calc(100vh - 64px);
      padding: 64px 24px;
    }
    .callback-status, .callback-error {
      font-family: var(--font-ui);
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--color-text-muted);
    }
    .callback-error { color: var(--color-danger, #ff6b6b); }
  `]
})
export class AuthCallbackComponent implements OnInit {
  error = signal('');

  constructor(private auth: AuthService, private router: Router) {}

  ngOnInit(): void {
    const token = new URLSearchParams(window.location.hash.replace(/^#/, '')).get('token');
    if (!token) {
      this.router.navigate(['/login'], { queryParams: { error: 'oauth_failed' } });
      return;
    }

    // Drop the token from the address bar before doing anything else, so it can't survive in
    // history or get copied out of the URL bar.
    history.replaceState(null, '', window.location.pathname);

    this.auth.adoptExternalToken(token).subscribe({
      next: () => this.router.navigate(['/my-dances']),
      error: () => {
        this.error.set('Sign-in failed. Redirecting…');
        this.router.navigate(['/login'], { queryParams: { error: 'oauth_failed' } });
      }
    });
  }
}
