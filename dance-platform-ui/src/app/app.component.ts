import { Component, ElementRef, HostListener, signal } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from './core/services/auth.service';
import { RoleService } from './core/services/role.service';
import { PracticeTimerService } from './core/services/practice-timer.service';
import { formatClock } from './core/utils/video-url.utils';
import { GlobalSearchComponent } from './shared/components/global-search/global-search.component';
import { FeedbackComponent } from './shared/components/feedback/feedback.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule, GlobalSearchComponent, FeedbackComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  menuOpen = signal(false);
  userMenuOpen = signal(false);
  readonly formatClock = formatClock;

  constructor(
    public auth: AuthService,
    public role: RoleService,
    public practiceTimer: PracticeTimerService,
    private host: ElementRef<HTMLElement>
  ) {}

  userInitial(): string {
    return this.auth.currentUsername()?.charAt(0).toUpperCase() ?? '?';
  }

  toggleMenu(): void {
    this.menuOpen.update(v => !v);
  }

  closeMenu(): void {
    this.menuOpen.set(false);
  }

  toggleUserMenu(): void {
    this.userMenuOpen.update(v => !v);
  }

  closeUserMenu(): void {
    this.userMenuOpen.set(false);
  }

  signOut(): void {
    this.closeUserMenu();
    this.auth.logout();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.userMenuOpen()) return;
    const user = this.host.nativeElement.querySelector('.header__user');
    if (user && !user.contains(event.target as Node)) this.userMenuOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.userMenuOpen.set(false);
  }
}
