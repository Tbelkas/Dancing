import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ExternalProvider } from '../../models/external-auth.model';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent implements OnInit {
  username = '';
  email = '';
  password = '';
  name = '';
  nickname = '';
  isRegister = signal(false);
  loading = signal(false);
  error = signal('');
  providers = signal<ExternalProvider[]>([]);

  /** Why a social sign-in bounced back here. Deliberately vague about the cause: the useful
   *  action is the same either way, and the detail is in the server log. */
  private static readonly OAUTH_ERRORS: Record<string, string> = {
    oauth_state: 'That sign-in link expired. Please try again.',
    oauth_failed: "We couldn't complete that sign-in. Please try again."
  };

  constructor(private auth: AuthService, private router: Router, private route: ActivatedRoute) {}

  ngOnInit(): void {
    if (this.route.snapshot.url[0]?.path === 'register') {
      this.isRegister.set(true);
    }

    const oauthError = this.route.snapshot.queryParamMap.get('error');
    if (oauthError) {
      this.error.set(LoginComponent.OAUTH_ERRORS[oauthError] ?? 'Sign-in failed. Please try again.');
    }

    // Failing quietly is right here: the password form below is fully usable without this.
    this.auth.externalProviders().subscribe({
      next: list => this.providers.set(list),
      error: () => this.providers.set([])
    });
  }

  /** Deliberately loose: the server validates properly, and the only job here is to catch the
   *  obvious typo before a network round-trip (the form is novalidate, so `type=email` alone
   *  blocks nothing — see known-issues #3). */
  private isValidEmail(value: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
  }

  hasProvider(name: string): boolean {
    return this.providers().some(p => p.name === name);
  }

  signInWith(provider: string): void {
    this.loading.set(true);
    this.auth.startExternal(provider);
  }

  toggleMode(): void {
    this.isRegister.update(v => !v);
    this.error.set('');
  }

  submit(): void {
    if (this.isRegister()) {
      if (!this.username || this.username.length < 3) {
        this.error.set('Username must be at least 3 characters.');
        return;
      }
      if (!this.password || this.password.length < 8) {
        this.error.set('Password must be at least 8 characters.');
        return;
      }
      if (!this.isValidEmail(this.email)) {
        this.error.set('A valid email address is required — it is the only way to reset a forgotten password.');
        return;
      }
      if (!this.name) {
        this.error.set('Full name is required.');
        return;
      }
    } else if (!this.username.trim() || !this.password) {
      this.error.set('Please enter your username and password.');
      return;
    }
    this.loading.set(true);
    this.error.set('');

    const obs = this.isRegister()
      ? this.auth.register({ username: this.username, email: this.email.trim(), password: this.password, name: this.name, nickname: this.nickname })
      : this.auth.login(this.username, this.password);

    obs.subscribe({
      next: () => this.router.navigate(['/my-dances']),
      error: (err) => {
        this.error.set(err.error?.message ?? 'An error occurred. Please try again.');
        this.loading.set(false);
      }
    });
  }
}
