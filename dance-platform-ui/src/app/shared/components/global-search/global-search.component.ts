import { Component, ElementRef, HostListener, ViewChild, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { DanceService } from '../../../core/services/dance.service';
import { Dance } from '../../../models/dance.model';

/** Matches the ≤720px breakpoint the header uses to swap to the mobile layout. */
const NARROW_QUERY = '(max-width: 720px)';
/** Above this the full-bleed header has room to leave the field open; below, it rests as an icon. */
const ROOMY_QUERY = '(min-width: 1200px)';

/**
 * Header-wide dance search with typeahead. Ctrl+K or "/" focuses it from
 * anywhere; Enter on "See all" hands the query off to the Browse page.
 * Between 721px and 1199px it rests as an icon button and expands on click/shortcut;
 * wider than that the header has room to leave the field open, and on mobile
 * (≤720px) CSS keeps it expanded too.
 */
@Component({
  selector: 'app-global-search',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './global-search.component.html',
  styleUrls: ['./global-search.component.css']
})
export class GlobalSearchComponent {
  query = signal('');
  results = signal<Dance[]>([]);
  total = signal(0);
  open = signal(false);
  loading = signal(false);
  activeIndex = signal(-1);
  /** Mid-width desktop only: false renders the search as a lone icon button (CSS ignores this on mobile). */
  expanded = signal(false);

  /**
   * On a phone the header slot is only ~120px wide, and "Search dances…" is clipped to
   * "Search dan". The short form fits; the full wording stays in the aria-label either way.
   */
  private readonly narrow = signal(window.matchMedia(NARROW_QUERY).matches);
  readonly placeholder = computed(() => (this.narrow() ? 'Search…' : 'Search dances…'));

  /**
   * The collapse-to-an-icon exists because the header used to share the content
   * container's width. Now that the bar spans the viewport there is room to spare
   * above 1200px, so the field rests open there — and stays tabbable, which a
   * visible input with tabindex="-1" would not be.
   */
  private readonly roomy = signal(window.matchMedia(ROOMY_QUERY).matches);
  readonly fieldVisible = computed(() => this.expanded() || this.roomy());

  @ViewChild('searchInput') searchInput?: ElementRef<HTMLInputElement>;

  private debounceHandle: ReturnType<typeof setTimeout> | null = null;
  /** Guards against out-of-order responses overwriting newer results. */
  private requestSeq = 0;

  constructor(
    private dances: DanceService,
    private router: Router,
    private host: ElementRef<HTMLElement>
  ) {
    // Rotating a phone crosses the breakpoint without a reload.
    window.matchMedia(NARROW_QUERY).addEventListener('change', e => this.narrow.set(e.matches));
    // Resizing across 1200px likewise swaps the resting state without a reload.
    window.matchMedia(ROOMY_QUERY).addEventListener('change', e => this.roomy.set(e.matches));
  }

  onInput(value: string): void {
    this.query.set(value);
    this.activeIndex.set(-1);
    if (this.debounceHandle) clearTimeout(this.debounceHandle);
    const q = value.trim();
    if (!q) {
      this.results.set([]);
      this.total.set(0);
      this.open.set(false);
      return;
    }
    this.debounceHandle = setTimeout(() => this.search(q), 220);
  }

  private search(q: string): void {
    const seq = ++this.requestSeq;
    this.loading.set(true);
    this.open.set(true);
    this.dances.searchDances({ q, pageSize: 6, sortBy: 'recommended' }).subscribe({
      next: res => {
        if (seq !== this.requestSeq) return;
        this.results.set(res.items);
        this.total.set(res.total);
        this.loading.set(false);
      },
      error: () => {
        if (seq !== this.requestSeq) return;
        this.results.set([]);
        this.total.set(0);
        this.loading.set(false);
      }
    });
  }

  onIconClick(): void {
    this.expanded.set(true);
    this.searchInput?.nativeElement.focus();
  }

  private collapseIfIdle(): void {
    if (!this.query().trim()) this.expanded.set(false);
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      this.close();
      this.searchInput?.nativeElement.blur();
      this.collapseIfIdle();
      return;
    }
    if (!this.open()) {
      if (event.key === 'Enter') this.goToAll();
      return;
    }
    const count = this.results().length;
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        this.activeIndex.set(Math.min(this.activeIndex() + 1, count - 1));
        break;
      case 'ArrowUp':
        event.preventDefault();
        this.activeIndex.set(Math.max(this.activeIndex() - 1, -1));
        break;
      case 'Enter': {
        const idx = this.activeIndex();
        if (idx >= 0 && idx < count) this.pick(this.results()[idx]);
        else this.goToAll();
        break;
      }
    }
  }

  onFocus(): void {
    if (this.query().trim() && this.results().length > 0) this.open.set(true);
  }

  pick(dance: Dance): void {
    this.close();
    this.query.set('');
    this.results.set([]);
    this.expanded.set(false);
    const path = dance.styleSlug ? ['/dances', dance.styleSlug, dance.slug] : ['/dances', dance.slug];
    this.router.navigate(path);
  }

  goToAll(): void {
    const q = this.query().trim();
    if (!q) return;
    this.close();
    // Browse takes over the query; clear so the collapsed icon doesn't hide stale text.
    this.query.set('');
    this.results.set([]);
    this.expanded.set(false);
    this.router.navigate(['/dances'], { queryParams: { q } });
  }

  clear(): void {
    this.query.set('');
    this.results.set([]);
    this.total.set(0);
    this.close();
    this.searchInput?.nativeElement.focus();
  }

  close(): void {
    this.open.set(false);
    this.activeIndex.set(-1);
  }

  thumbnailUrl(dance: Dance): string | null {
    if (dance.thumbnailVideoId && dance.thumbnailPlatform === 'youtube') {
      return `https://i.ytimg.com/vi/${dance.thumbnailVideoId}/default.jpg`;
    }
    return null;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.host.nativeElement.contains(event.target as Node)) {
      this.close();
      this.collapseIfIdle();
    }
  }

  @HostListener('document:keydown', ['$event'])
  onGlobalKeydown(event: KeyboardEvent): void {
    const target = event.target as HTMLElement | null;
    const tag = target?.tagName ?? '';
    const typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target?.isContentEditable;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      this.expanded.set(true);
      this.searchInput?.nativeElement.focus();
    } else if (event.key === '/' && !typing) {
      event.preventDefault();
      this.expanded.set(true);
      this.searchInput?.nativeElement.focus();
    }
  }
}
