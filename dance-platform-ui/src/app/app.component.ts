import { Component } from '@angular/core';
import { RouterOutlet, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from './core/services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, CommonModule],
  template: `
    <header class="header">
      <div class="container header__inner">
        <a routerLink="/dances" class="header__logo">Dance Platform</a>
        <nav class="header__nav">
          <a routerLink="/dances">Browse</a>
          @if (auth.isAuthenticated()) {
            <a routerLink="/profile">Profile</a>
            <button class="btn btn--ghost" (click)="auth.logout()">Sign out</button>
          } @else {
            <a routerLink="/login" class="btn btn--primary">Sign in</a>
          }
        </nav>
      </div>
    </header>
    <main class="main">
      <router-outlet />
    </main>
  `,
  styles: [`
    .header {
      background: var(--color-surface);
      border-bottom: 1px solid var(--color-surface-2);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 0 0;
    }
    .header__inner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 64px;
    }
    .header__logo {
      font-family: 'Montserrat', sans-serif;
      font-size: 1.4rem;
      font-weight: 800;
      background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .header__nav {
      display: flex;
      align-items: center;
      gap: 24px;
      a { color: var(--color-text); font-weight: 500; &:hover { color: var(--color-primary); } }
    }
    .main { padding: 40px 0; min-height: calc(100vh - 64px); }
  `]
})
export class AppComponent {
  constructor(public auth: AuthService) {}
}
