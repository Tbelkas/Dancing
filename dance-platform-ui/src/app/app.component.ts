import { Component, ElementRef, HostListener, computed, signal } from '@angular/core';
import { NavigationEnd, Router, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { filter } from 'rxjs/operators';
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

  /**
   * The current URL, so Browse and Roadmaps can compute their own active state instead of
   * leaving it to `routerLinkActive`.
   *
   * A move opened from a path is a `/dances/...` URL carrying `?roadmap=`, and prefix matching
   * would light up Browse for it — telling someone three moves into a tree that they are in the
   * catalog. The rest of the nav still uses `routerLinkActive`; only these two overlap.
   */
  private readonly url = signal('/');

  private readonly onPath = computed(() =>
    new URLSearchParams(this.url().split('?')[1] ?? '').has('roadmap'));

  readonly browseActive = computed(() =>
    this.url().split('?')[0].startsWith('/dances') && !this.onPath());

  readonly roadmapsActive = computed(() =>
    this.url().split('?')[0].startsWith('/roadmaps') || this.onPath());

  constructor(
    public auth: AuthService,
    public role: RoleService,
    public practiceTimer: PracticeTimerService,
    private router: Router,
    private host: ElementRef<HTMLElement>
  ) {
    this.url.set(this.router.url);
    this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe(e => this.url.set(e.urlAfterRedirects));
  }

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
