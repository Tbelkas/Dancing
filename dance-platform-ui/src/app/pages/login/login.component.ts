import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="login-page">
      <div class="card login-card">
        <h1 class="page-title">{{ isRegister() ? 'Create Account' : 'Welcome Back' }}</h1>
        <p class="subtitle">{{ isRegister() ? 'Start your dance journey' : 'Sign in to continue' }}</p>

        @if (error()) {
          <div class="error-message">{{ error() }}</div>
        }

        <form (ngSubmit)="submit()" #form="ngForm">
          <div class="form-group">
            <label>Username</label>
            <input type="text" [(ngModel)]="username" name="username" required minlength="3" placeholder="your_username" />
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" [(ngModel)]="password" name="password" required placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;" />
          </div>
          @if (isRegister()) {
            <div class="form-group">
              <label>Full Name</label>
              <input type="text" [(ngModel)]="name" name="name" required placeholder="Your Name" />
            </div>
            <div class="form-group">
              <label>Nickname</label>
              <input type="text" [(ngModel)]="nickname" name="nickname" placeholder="Optional nickname" />
            </div>
          }
          <button type="submit" class="btn btn--primary btn--full" [disabled]="loading()">
            {{ loading() ? 'Loading...' : (isRegister() ? 'Create Account' : 'Sign In') }}
          </button>
        </form>

        <p class="toggle-text">
          {{ isRegister() ? 'Already have an account?' : 'New here?' }}
          <a (click)="toggleMode()">{{ isRegister() ? 'Sign in' : 'Create account' }}</a>
        </p>
      </div>
    </div>
  `,
  styles: [`
    .login-page { display: flex; justify-content: center; align-items: flex-start; padding: 60px 24px; }
    .login-card { width: 100%; max-width: 420px; }
    .subtitle { color: var(--color-text-muted); margin-bottom: 28px; }
    .btn--full { width: 100%; margin-top: 8px; padding: 14px; font-size: 1rem; }
    .toggle-text { text-align: center; margin-top: 20px; color: var(--color-text-muted); font-size: 0.9rem;
      a { cursor: pointer; color: var(--color-accent); margin-left: 4px; }
    }
    .error-message { margin-bottom: 16px; }
  `]
})
export class LoginComponent {
  username = '';
  password = '';
  name = '';
  nickname = '';
  isRegister = signal(false);
  loading = signal(false);
  error = signal('');

  constructor(private auth: AuthService, private router: Router) {}

  toggleMode(): void {
    this.isRegister.update(v => !v);
    this.error.set('');
  }

  submit(): void {
    this.loading.set(true);
    this.error.set('');

    const obs = this.isRegister()
      ? this.auth.register({ username: this.username, password: this.password, name: this.name, nickname: this.nickname })
      : this.auth.login(this.username, this.password);

    obs.subscribe({
      next: () => this.router.navigate(['/dances']),
      error: (err) => {
        this.error.set(err.error?.message ?? 'An error occurred. Please try again.');
        this.loading.set(false);
      }
    });
  }
}
