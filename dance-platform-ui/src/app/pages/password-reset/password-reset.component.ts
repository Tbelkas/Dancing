import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

/**
 * Both halves of "I forgot my password", in one component because they are one flow and share
 * a card: `/forgot-password` asks for the address, `/reset-password?token=…` is where the mailed
 * link lands. Which mode it is comes from the route, not from a query param, so a missing token
 * shows a real explanation instead of a form that cannot work.
 */
@Component({
  selector: 'app-password-reset',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './password-reset.component.html',
  styleUrls: ['./password-reset.component.css']
})
export class PasswordResetComponent implements OnInit {
  email = '';
  password = '';
  confirmPassword = '';

  mode = signal<'request' | 'reset'>('request');
  loading = signal(false);
  error = signal('');
  /** Set once the request is accepted — the form is replaced by the confirmation, so nobody
   *  wonders whether the second click worked. */
  sent = signal(false);

  private token = '';

  constructor(private auth: AuthService, private route: ActivatedRoute, private router: Router) {}

  ngOnInit(): void {
    const isResetRoute = this.route.snapshot.url[0]?.path === 'reset-password';
    this.mode.set(isResetRoute ? 'reset' : 'request');
    this.token = this.route.snapshot.queryParamMap.get('token') ?? '';

    if (isResetRoute && !this.token) {
      this.error.set('That link is incomplete. Request a new one below.');
    }
  }

  requestLink(): void {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.email.trim())) {
      this.error.set('Enter the email address on your account.');
      return;
    }
    this.loading.set(true);
    this.error.set('');

    this.auth.forgotPassword(this.email.trim()).subscribe({
      // Success and "no such account" are the same answer on purpose — the server won't say
      // which, and neither should this page.
      next: () => { this.sent.set(true); this.loading.set(false); },
      error: err => {
        this.error.set(err.status === 429
          ? 'Too many requests. Wait a few minutes and try again.'
          : 'Something went wrong. Please try again.');
        this.loading.set(false);
      }
    });
  }

  setNewPassword(): void {
    if (!this.token) {
      this.error.set('That link is incomplete. Request a new one.');
      return;
    }
    if (this.password.length < 8) {
      this.error.set('Password must be at least 8 characters.');
      return;
    }
    if (this.password !== this.confirmPassword) {
      this.error.set('The two passwords do not match.');
      return;
    }
    this.loading.set(true);
    this.error.set('');

    // A successful reset signs the user straight in (AuthService stores the returned token),
    // so there is no second trip through the login form.
    this.auth.resetPassword(this.token, this.password).subscribe({
      next: () => this.router.navigate(['/my-dances']),
      error: err => {
        this.error.set(err.error?.message ?? 'That reset link is no longer valid.');
        this.loading.set(false);
      }
    });
  }
}
