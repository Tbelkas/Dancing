import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { SignupTicket } from '../../models/external-auth.model';

/** The one step between "signed in with Google" and having an account. The username is the
 *  permanent public handle at /users/:username, so it is worth a screen rather than being
 *  generated silently — but it arrives prefilled so accepting it is a single click. */
@Component({
  selector: 'app-finish-signup',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './finish-signup.component.html',
  styleUrls: ['../login/login.component.css']
})
export class FinishSignupComponent implements OnInit {
  username = '';
  ticket = signal<SignupTicket | null>(null);
  loading = signal(false);
  error = signal('');

  private token = '';

  constructor(private auth: AuthService, private router: Router) {}

  ngOnInit(): void {
    const token = new URLSearchParams(window.location.hash.replace(/^#/, '')).get('ticket');
    if (!token) {
      this.router.navigate(['/login']);
      return;
    }

    this.token = token;
    // Keep the ticket out of the address bar, same reasoning as the token on /auth/callback.
    history.replaceState(null, '', window.location.pathname);

    this.auth.inspectTicket(token).subscribe({
      next: t => { this.ticket.set(t); this.username = t.suggestedUsername; },
      error: () => this.error.set('This sign-up link has expired. Please sign in again.')
    });
  }

  submit(): void {
    const username = this.username.trim();
    if (username.length < 3) {
      this.error.set('Username must be at least 3 characters.');
      return;
    }
    if (!/^[A-Za-z0-9_-]+$/.test(username)) {
      this.error.set('Username can only contain letters, numbers, _ and -.');
      return;
    }

    this.loading.set(true);
    this.error.set('');

    this.auth.completeExternal(this.token, username).subscribe({
      next: () => this.router.navigate(['/my-dances']),
      error: err => {
        this.error.set(err.error?.message ?? 'Could not create your account. Please try again.');
        this.loading.set(false);
      }
    });
  }
}
