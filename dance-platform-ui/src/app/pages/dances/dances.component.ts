import { Component, OnInit, OnDestroy, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, ParamMap, Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { skip } from 'rxjs/operators';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';
import { DanceService, CreateDancePayload, ImportResult, DanceStatus } from '../../core/services/dance.service';
import { StyleService } from '../../core/services/style.service';
import { MusicalStyleService } from '../../core/services/musical-style.service';
import { InstructorService } from '../../core/services/instructor.service';
import { VideoService, CreateVideoPayload } from '../../core/services/video.service';
import { AuthService } from '../../core/services/auth.service';
import { RoleService } from '../../core/services/role.service';
import { RecentDancesService } from '../../core/services/recent-dances.service';
import { parseVideoUrl } from '../../core/utils/video-url.utils';
import { Dance } from '../../models/dance.model';
import { Style } from '../../models/style.model';
import { MusicalStyle } from '../../models/musical-style.model';
import { Instructor } from '../../models/instructor.model';
import { DIFFICULTY_FILTER_OPTIONS, DIFFICULTY_LEVELS } from '../../core/constants/dance.constants';
import { toggleSet } from '../../core/utils/set.utils';

// Favorited is intentionally not here: it's orthogonal to learning progress and
// rendered as an independent heart toggle instead.
const STATUS_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'notstarted', label: 'Not Started' },
  { value: 'inprogress', label: 'In Progress' },
  { value: 'learned', label: 'Learned' }
];

const FILTERS_KEY = 'dances.filters.v1';

/** First `n` items, but pull the selected item into view if it falls past the cutoff. */
function clampWithSelected<T extends { id: number }>(list: T[], selectedId: number | null, n: number): T[] {
  if (list.length <= n) return list;
  const head = list.slice(0, n);
  if (selectedId != null && !head.some(x => x.id === selectedId)) {
    const selected = list.find(x => x.id === selectedId);
    if (selected) return [selected, ...head.slice(0, n - 1)];
  }
  return head;
}
@Component({
  selector: 'app-dances',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, DancePathPipe],
  templateUrl: './dances.component.html',
  styleUrls: ['./dances.component.css']
})
export class DancesComponent implements OnInit, OnDestroy {
  readonly difficulties = DIFFICULTY_FILTER_OPTIONS;
  readonly difficultyLevels = DIFFICULTY_LEVELS;
  readonly statusOptions = STATUS_OPTIONS;
  readonly skeletonCards = [0, 1, 2, 3, 4, 5];
  readonly PAGE_SIZE = 24;

  // Data
  searchResults = signal<Dance[]>([]);
  searchTotal = signal(0);
  /** Catalog size ignoring filters, for "N of M dances". */
  grandTotal = signal(0);
  currentPage = signal(1);
  /** "Continue learning" rail: the user's in-progress dances (fetched once, authed only). */
  railDances = signal<Dance[]>([]);
  /** True while the in-progress fetch is in flight — holds the rail as a skeleton instead of
   *  painting the recently-viewed fallback and then flipping it to "Continue learning". */
  railPending = signal(false);
  surprising = signal(false);
  styles = signal<Style[]>([]);
  musicalStyles = signal<MusicalStyle[]>([]);
  instructors = signal<Instructor[]>([]);
  loading = signal(true);
  /** False until the first search resolves; skeletons only show for that initial load —
   *  re-searches keep the old grid (dimmed) so the page doesn't blank-flash on every filter. */
  hasLoaded = signal(false);
  /** Cards get their staggered entrance only on the first reveal; after that new cards
   *  appear instantly instead of replaying the fade on every filter/page change. */
  cardsReveal = signal(true);

  // Filters
  searchQuery = signal('');
  selectedStyleId = signal<number | null>(null);
  selectedMusicalStyleId = signal<number | null>(null);
  selectedDifficulty = signal<string | null>(null);
  selectedStatus = signal<string>('all');
  favoritesOnly = signal(false);
  sortBy = signal<string>('recommended');

  styleQuery = signal('');
  musicQuery = signal('');

  /** Mobile-only: the filter rows collapse behind a "Filters" toggle. */
  filtersOpen = signal(false);

  /** Card grid for discovery, compact rows for scanning; remembered across visits. */
  viewMode = signal<'grid' | 'list'>('grid');
  private readonly VIEW_MODE_KEY = 'dances.viewMode';

  /** Active filters excluding the search text (which has its own always-visible box). */
  readonly filterCount = computed(() =>
    this.activeFilterChips().filter(c => c.key !== 'q').length);

  // Collapse the long pill lists to a single row by default so the catalog stays
  // near the fold; the user expands on demand or narrows via the search box.
  stylesExpanded = signal(false);
  musicExpanded = signal(false);
  readonly COLLAPSED_PILLS = 8;

  // Styles the user recently opened (via a dance) float to the front so they land in the
  // collapsed single-row view; everything else keeps the server's original order.
  readonly sortedStyles = computed(() => {
    const styles = this.styles();
    const rank = new Map<string, number>();
    for (const r of this.recentDances.recent()) {
      if (r.styleName && !rank.has(r.styleName)) rank.set(r.styleName, rank.size);
    }
    if (rank.size === 0) return styles;
    return styles
      .map((s, i) => ({ s, i }))
      .sort((a, b) => {
        const ra = rank.get(a.s.name) ?? Infinity;
        const rb = rank.get(b.s.name) ?? Infinity;
        return ra !== rb ? ra - rb : a.i - b.i;
      })
      .map(x => x.s);
  });

  readonly visibleStyles = computed(() => {
    const q = this.styleQuery().trim().toLowerCase();
    if (!q) return this.sortedStyles();
    const sel = this.selectedStyleId();
    return this.sortedStyles().filter(s => s.id === sel || s.name.toLowerCase().includes(q));
  });

  readonly visibleMusicalStyles = computed(() => {
    const q = this.musicQuery().trim().toLowerCase();
    if (!q) return this.musicalStyles();
    const sel = this.selectedMusicalStyleId();
    return this.musicalStyles().filter(ms => ms.id === sel || ms.name.toLowerCase().includes(q));
  });

  // What actually renders: the full list while searching or expanded, otherwise a
  // single-row slice that always keeps the active pill visible.
  readonly displayedStyles = computed(() =>
    this.styleQuery().trim() || this.stylesExpanded()
      ? this.visibleStyles()
      : clampWithSelected(this.visibleStyles(), this.selectedStyleId(), this.COLLAPSED_PILLS)
  );

  readonly displayedMusicalStyles = computed(() =>
    this.musicQuery().trim() || this.musicExpanded()
      ? this.visibleMusicalStyles()
      : clampWithSelected(this.visibleMusicalStyles(), this.selectedMusicalStyleId(), this.COLLAPSED_PILLS)
  );

  readonly hiddenStyleCount = computed(() =>
    this.styleQuery().trim() || this.stylesExpanded()
      ? 0
      : Math.max(0, this.visibleStyles().length - this.COLLAPSED_PILLS)
  );

  readonly hiddenMusicCount = computed(() =>
    this.musicQuery().trim() || this.musicExpanded()
      ? 0
      : Math.max(0, this.visibleMusicalStyles().length - this.COLLAPSED_PILLS)
  );

  readonly hasActiveFilters = computed(() =>
    this.searchQuery().trim() !== '' ||
    this.selectedStyleId() !== null ||
    this.selectedMusicalStyleId() !== null ||
    this.selectedDifficulty() !== null ||
    this.selectedStatus() !== 'all' ||
    this.favoritesOnly()
  );

  /** One chip per active filter, each individually removable. */
  readonly activeFilterChips = computed(() => {
    const chips: { key: string; label: string }[] = [];
    const q = this.searchQuery().trim();
    if (q) chips.push({ key: 'q', label: `"${q}"` });
    const styleId = this.selectedStyleId();
    if (styleId !== null) {
      const style = this.styles().find(s => s.id === styleId);
      chips.push({ key: 'style', label: style?.name ?? 'Style' });
    }
    const diff = this.selectedDifficulty();
    if (diff) chips.push({ key: 'level', label: diff });
    const status = this.selectedStatus();
    if (status !== 'all') {
      const opt = this.statusOptions.find(o => o.value === status);
      chips.push({ key: 'status', label: opt?.label ?? status });
    }
    if (this.favoritesOnly()) chips.push({ key: 'favorites', label: 'Favorites' });
    return chips;
  });

  /** In-progress rail when the user has any; otherwise recently-viewed unlearned dances. */
  readonly recentRail = computed(() =>
    this.recentDances.recent().filter(d => !d.learned).slice(0, 12));

  readonly totalPages = computed(() => Math.ceil(this.searchTotal() / this.PAGE_SIZE));

  readonly pageNumbers = computed(() => {
    const total = this.totalPages();
    const cur = this.currentPage();
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages: (number | null)[] = [];
    pages.push(1);
    if (cur > 3) pages.push(null);
    for (let p = Math.max(2, cur - 1); p <= Math.min(total - 1, cur + 1); p++) pages.push(p);
    if (cur < total - 2) pages.push(null);
    pages.push(total);
    return pages;
  });

  thumbFailed = signal<Set<number>>(new Set());

  private searchDebounce: ReturnType<typeof setTimeout> | null = null;
  private searchSub: Subscription | null = null;
  private urlSub: Subscription | null = null;

  // Admin: add style form
  showAddStyle = signal(false);
  newStyleName = '';
  newStyleDesc = '';
  addingStyle = signal(false);
  addStyleError = signal('');

  // Admin: bulk import form
  showImport = signal(false);
  importText = '';
  importing = signal(false);
  importResult = signal<ImportResult | null>(null);
  importError = signal('');

  // Add Video (any authenticated user; admins also choose Global vs Local scope)
  showAddVideo = signal(false);
  private addVideoDanceNames = signal<{ id: number; name: string }[]>([]);
  addVideoDanceQuery = signal('');
  selectedAddVideoDance = signal<{ id: number; name: string } | null>(null);
  addVideoDanceMatches = computed(() => {
    const q = this.addVideoDanceQuery().trim().toLowerCase();
    if (!q) return [];
    return this.addVideoDanceNames()
      .filter(d => d.name.toLowerCase().includes(q))
      .slice(0, 20);
  });
  newVideoTitle = '';
  newVideoUrl = '';
  newVideoScope: 'global' | 'local' = 'global';
  addingVideo = signal(false);
  addVideoError = signal('');
  addVideoCreated = signal<{ danceId: number; danceName: string; title: string } | null>(null);

  // Admin: add dance form
  showAddDance = signal(false);
  newDanceName = '';
  newDanceDesc = '';
  newDanceDifficulty = 'None';
  newDanceStyleIds = signal<Set<number>>(new Set());
  newDanceMusicalStyleIds = signal<Set<number>>(new Set());
  newDanceInstructorIds = signal<Set<number>>(new Set());
  addingDance = signal(false);
  addDanceError = signal('');

  constructor(
    private danceService: DanceService,
    private styleService: StyleService,
    private musicalStyleService: MusicalStyleService,
    private instructorService: InstructorService,
    private videoService: VideoService,
    public auth: AuthService,
    public role: RoleService,
    private recentDances: RecentDancesService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.styleService.getAll().subscribe(s => this.styles.set(s));
    this.musicalStyleService.getAll().subscribe(ms => this.musicalStyles.set(ms));
    this.instructorService.getAll().subscribe(i => this.instructors.set(i));
    const storedView = localStorage.getItem(this.VIEW_MODE_KEY);
    if (storedView === 'list' || storedView === 'grid') this.viewMode.set(storedView);
    this.restoreFilters();
    this.runSearch();
    // Follow later URL changes (e.g. the header search navigating to /dances?q=…
    // while this page is already showing). The first emission is the snapshot
    // restoreFilters() just consumed, and our own syncUrl() writes always match
    // current state, so both no-op in applyUrlIfChanged.
    this.urlSub = this.route.queryParamMap.pipe(skip(1)).subscribe(qp => this.applyUrlIfChanged(qp));
    if (this.auth.isAuthenticated()) {
      this.railPending.set(true);
      this.danceService.searchDances({ status: 'inprogress', sortBy: 'name', pageSize: 12 })
        .subscribe({
          next: r => { this.railDances.set(r.items); this.railPending.set(false); },
          error: () => this.railPending.set(false)
        });
    }
  }

  /**
   * Restore filters: an explicit URL (shared link, back button) wins; otherwise fall back to
   * the last-used set in localStorage so open/refresh lands where the user left off.
   */
  private restoreFilters(): void {
    const qp = this.route.snapshot.queryParamMap;
    const urlHasFilters = ['q', 'style', 'level', 'status', 'fav', 'sort', 'page'].some(k => qp.has(k));
    if (urlHasFilters) {
      this.searchQuery.set(qp.get('q') ?? '');
      const style = Number(qp.get('style'));
      this.selectedStyleId.set(Number.isInteger(style) && style > 0 ? style : null);
      this.selectedDifficulty.set(qp.get('level'));
      this.selectedStatus.set(qp.get('status') ?? 'all');
      this.favoritesOnly.set(qp.get('fav') === '1');
      if (qp.get('sort')) this.sortBy.set(qp.get('sort')!);
      const page = Number(qp.get('page'));
      if (Number.isInteger(page) && page >= 1) this.currentPage.set(page);
    } else {
      try {
        const raw = localStorage.getItem(FILTERS_KEY);
        if (raw) {
          const s = JSON.parse(raw);
          if (typeof s.searchQuery === 'string') this.searchQuery.set(s.searchQuery);
          if (s.selectedStyleId === null || typeof s.selectedStyleId === 'number') this.selectedStyleId.set(s.selectedStyleId);
          if (s.selectedMusicalStyleId === null || typeof s.selectedMusicalStyleId === 'number') this.selectedMusicalStyleId.set(s.selectedMusicalStyleId);
          if (s.selectedDifficulty === null || typeof s.selectedDifficulty === 'string') this.selectedDifficulty.set(s.selectedDifficulty);
          if (typeof s.selectedStatus === 'string') this.selectedStatus.set(s.selectedStatus);
          if (typeof s.favoritesOnly === 'boolean') this.favoritesOnly.set(s.favoritesOnly);
          if (typeof s.sortBy === 'string') this.sortBy.set(s.sortBy);
          if (typeof s.currentPage === 'number' && s.currentPage >= 1) this.currentPage.set(s.currentPage);
        }
      } catch { /* ignore malformed/unavailable storage */ }
    }
    // Legacy stored/linked value from when Favorited lived inside status.
    if (this.selectedStatus() === 'favorite') {
      this.selectedStatus.set('all');
      this.favoritesOnly.set(true);
    }
    // Status/favorites only apply to signed-in users; drop stale personal filters when logged out.
    if (!this.auth.isAuthenticated()) {
      this.selectedStatus.set('all');
      this.favoritesOnly.set(false);
    }
  }

  private persistFilters(): void {
    try {
      localStorage.setItem(FILTERS_KEY, JSON.stringify({
        searchQuery: this.searchQuery(),
        selectedStyleId: this.selectedStyleId(),
        selectedMusicalStyleId: this.selectedMusicalStyleId(),
        selectedDifficulty: this.selectedDifficulty(),
        selectedStatus: this.selectedStatus(),
        favoritesOnly: this.favoritesOnly(),
        sortBy: this.sortBy(),
        currentPage: this.currentPage()
      }));
    } catch { /* storage unavailable (private mode, quota) — non-fatal */ }
    this.syncUrl();
  }

  /** Mirror the filters into the URL so any filtered view is shareable and back-button-safe. */
  private syncUrl(): void {
    this.router.navigate([], {
      relativeTo: this.route,
      replaceUrl: true,
      queryParams: {
        q: this.searchQuery().trim() || null,
        style: this.selectedStyleId(),
        level: this.selectedDifficulty(),
        status: this.selectedStatus() !== 'all' ? this.selectedStatus() : null,
        fav: this.favoritesOnly() ? '1' : null,
        sort: this.sortBy() !== 'recommended' ? this.sortBy() : null,
        page: this.currentPage() > 1 ? this.currentPage() : null
      }
    });
  }

  ngOnDestroy(): void {
    if (this.searchDebounce) clearTimeout(this.searchDebounce);
    this.searchSub?.unsubscribe();
    this.urlSub?.unsubscribe();
    this.clearHoverTimer();
  }

  /** Adopt filters arriving via the URL (header search, back button) when they
   *  differ from current state; identical params (our own syncUrl echoes) no-op. */
  private applyUrlIfChanged(qp: ParamMap): void {
    const q = qp.get('q') ?? '';
    const styleRaw = Number(qp.get('style'));
    const style = Number.isInteger(styleRaw) && styleRaw > 0 ? styleRaw : null;
    const level = qp.get('level');
    const status = qp.get('status') ?? 'all';
    const fav = qp.get('fav') === '1';
    const sort = qp.get('sort') ?? 'recommended';
    const pageRaw = Number(qp.get('page'));
    const page = Number.isInteger(pageRaw) && pageRaw >= 1 ? pageRaw : 1;

    if (q === this.searchQuery().trim() &&
        style === this.selectedStyleId() &&
        level === this.selectedDifficulty() &&
        status === this.selectedStatus() &&
        fav === this.favoritesOnly() &&
        sort === this.sortBy() &&
        page === this.currentPage()) return;

    this.searchQuery.set(q);
    this.selectedStyleId.set(style);
    this.selectedDifficulty.set(level);
    this.selectedStatus.set(this.auth.isAuthenticated() ? status : 'all');
    this.favoritesOnly.set(this.auth.isAuthenticated() ? fav : false);
    this.sortBy.set(sort);
    this.currentPage.set(page);
    this.runSearch();
  }

  setViewMode(mode: 'grid' | 'list'): void {
    this.viewMode.set(mode);
    try { localStorage.setItem(this.VIEW_MODE_KEY, mode); } catch { /* non-fatal */ }
  }

  private runSearch(): void {
    this.persistFilters();
    this.loading.set(true);
    // Cancel any in-flight search so a slower earlier response can't overwrite a newer filter's
    // results (HttpClient aborts the request on unsubscribe).
    this.searchSub?.unsubscribe();
    this.searchSub = this.danceService.searchDances({
      q: this.searchQuery().trim() || undefined,
      styleId: this.selectedStyleId(),
      musicalStyleId: this.selectedMusicalStyleId(),
      difficulty: this.selectedDifficulty() ?? undefined,
      status: this.selectedStatus(),
      favoritesOnly: this.favoritesOnly(),
      sortBy: this.sortBy(),
      page: this.currentPage(),
      pageSize: this.PAGE_SIZE
    }).subscribe({
      next: result => {
        this.searchResults.set(result.items);
        this.searchTotal.set(result.total);
        this.grandTotal.set(result.grandTotal ?? result.total);
        this.loading.set(false);
        this.markLoaded();
      },
      error: () => { this.loading.set(false); this.markLoaded(); }
    });
  }

  private markLoaded(): void {
    if (this.hasLoaded()) return;
    this.hasLoaded.set(true);
    // Let the initial staggered entrance play out, then stop animating card insertions.
    setTimeout(() => this.cardsReveal.set(false), 900);
  }

  onSearchInput(value: string): void {
    this.searchQuery.set(value);
    this.currentPage.set(1);
    if (this.searchDebounce) clearTimeout(this.searchDebounce);
    this.searchDebounce = setTimeout(() => this.runSearch(), 300);
  }

  filterByStyle(styleId: number | null): void {
    this.selectedStyleId.set(styleId);
    this.currentPage.set(1);
    this.runSearch();
  }

  filterByMusicalStyle(msId: number | null): void {
    this.selectedMusicalStyleId.set(msId);
    this.currentPage.set(1);
    this.runSearch();
  }

  filterByDifficulty(difficulty: string | null): void {
    this.selectedDifficulty.set(difficulty);
    this.currentPage.set(1);
    this.runSearch();
  }

  filterByStatus(status: string): void {
    this.selectedStatus.set(status);
    this.currentPage.set(1);
    this.runSearch();
  }

  toggleFavoritesOnly(): void {
    this.favoritesOnly.update(v => !v);
    this.currentPage.set(1);
    this.runSearch();
  }

  /** Removes one active-filter chip by key. */
  removeFilter(key: string): void {
    switch (key) {
      case 'q': this.searchQuery.set(''); break;
      case 'style': this.selectedStyleId.set(null); break;
      case 'level': this.selectedDifficulty.set(null); break;
      case 'status': this.selectedStatus.set('all'); break;
      case 'favorites': this.favoritesOnly.set(false); break;
    }
    this.currentPage.set(1);
    this.runSearch();
  }

  /** Jump to a random dance matching the current filters — for the "what do I practice?" moment. */
  surpriseMe(): void {
    if (this.surprising()) return;
    this.surprising.set(true);
    this.danceService.randomDance({
      q: this.searchQuery().trim() || undefined,
      styleId: this.selectedStyleId(),
      musicalStyleId: this.selectedMusicalStyleId(),
      difficulty: this.selectedDifficulty() ?? undefined,
      status: this.selectedStatus(),
      favoritesOnly: this.favoritesOnly()
    }).subscribe({
      next: dance => {
        this.surprising.set(false);
        this.router.navigate(dance.styleSlug ? ['/dances', dance.styleSlug, dance.slug] : ['/dances', dance.slug]);
      },
      error: () => this.surprising.set(false)
    });
  }

  onSortChange(value: string): void {
    this.sortBy.set(value);
    this.currentPage.set(1);
    this.runSearch();
  }

  goToPage(page: number | null): void {
    if (page === null || page < 1 || page > this.totalPages()) return;
    this.currentPage.set(page);
    this.runSearch();
  }

  clearFilters(): void {
    this.searchQuery.set('');
    this.selectedStyleId.set(null);
    this.selectedMusicalStyleId.set(null);
    this.selectedDifficulty.set(null);
    this.selectedStatus.set('all');
    this.favoritesOnly.set(false);
    this.currentPage.set(1);
    this.runSearch();
  }

  // Hovering a card cycles through YouTube's storyboard frames (mq1–mq3) as a lightweight
  // motion preview; leaving restores the default thumbnail.
  private hoverDanceId = signal<number | null>(null);
  private hoverFrame = signal(0);
  private hoverTimer: ReturnType<typeof setInterval> | null = null;

  onMediaEnter(dance: Dance): void {
    if (!dance.thumbnailVideoId || dance.thumbnailPlatform !== 'youtube' || this.thumbFailed().has(dance.id)) return;
    this.hoverDanceId.set(dance.id);
    this.hoverFrame.set(1);
    this.clearHoverTimer();
    this.hoverTimer = setInterval(() => this.hoverFrame.update(f => f % 3 + 1), 800);
  }

  onMediaLeave(): void {
    this.clearHoverTimer();
    this.hoverDanceId.set(null);
    this.hoverFrame.set(0);
  }

  private clearHoverTimer(): void {
    if (this.hoverTimer) {
      clearInterval(this.hoverTimer);
      this.hoverTimer = null;
    }
  }

  thumbnailUrl(dance: Dance): string | null {
    if (this.thumbFailed().has(dance.id)) return null;
    if (dance.thumbnailVideoId && dance.thumbnailPlatform === 'youtube') {
      if (this.hoverDanceId() === dance.id && this.hoverFrame() > 0) {
        return `https://i.ytimg.com/vi/${dance.thumbnailVideoId}/mq${this.hoverFrame()}.jpg`;
      }
      return `https://i.ytimg.com/vi/${dance.thumbnailVideoId}/hqdefault.jpg`;
    }
    return null;
  }

  /** Style badges minus any that just repeat the dance's own name (pure noise on the card). */
  styleBadges(dance: Dance): string[] {
    return dance.styles.filter(s => s.toLowerCase() !== dance.name.toLowerCase());
  }

  /** " · 24 min" suffix for the media badge; empty when the duration is unknown. */
  durationLabel(dance: Dance): string {
    const s = dance.totalDurationSeconds ?? 0;
    if (s < 60) return '';
    const m = Math.round(s / 60);
    return m < 60 ? ` · ${m} min` : ` · ${Math.floor(m / 60)} h ${m % 60 ? (m % 60) + ' min' : ''}`.trimEnd();
  }

  onThumbError(danceId: number): void {
    this.thumbFailed.update(set => {
      const next = new Set(set);
      next.add(danceId);
      return next;
    });
  }

  onThumbLoad(danceId: number, event: Event): void {
    const img = event.target as HTMLImageElement;
    if (img.naturalHeight > 0 && img.naturalHeight <= 90) {
      this.onThumbError(danceId);
    }
  }

  starLabel(rating: number): string {
    return rating > 0 ? rating.toFixed(1) : '—';
  }

  toggleFavorite(dance: Dance, event: Event): void {
    event.stopPropagation();
    event.preventDefault();
    this.danceService.toggleFavorite(dance.id).subscribe(res => {
      this.searchResults.update(list =>
        list.map(d => d.id === dance.id ? { ...d, isFavorite: res.isFavorite } : d)
      );
    });
  }

  toggleLearned(dance: Dance, event: Event): void {
    event.stopPropagation();
    event.preventDefault();
    const snap = { isLearned: dance.isLearned, isInProgress: dance.isInProgress };
    const status: DanceStatus = dance.isLearned ? 'notstarted' : 'learned';
    const willLearn = status === 'learned';

    this.searchResults.update(list =>
      list.map(d => d.id === dance.id
        ? { ...d, isLearned: willLearn, isInProgress: willLearn ? false : d.isInProgress }
        : d)
    );
    // Keep the local recently-viewed trail in step so "Continue learning" rails don't
    // briefly show a dance that the server then reports as learned (or vice versa).
    this.recentDances.setLearned(dance.id, willLearn);

    this.danceService.setStatus(dance.id, status).subscribe({
      error: () => {
        this.searchResults.update(list =>
          list.map(d => d.id === dance.id ? { ...d, ...snap } : d)
        );
        this.recentDances.setLearned(dance.id, snap.isLearned);
      }
    });
  }

  // --- Admin: Bulk Import ---
  toggleImport(): void {
    this.showImport.update(v => !v);
    this.importText = '';
    this.importResult.set(null);
    this.importError.set('');
  }

  submitImport(): void {
    if (!this.importText.trim()) { this.importError.set('Paste some text to import.'); return; }
    this.importing.set(true);
    this.importError.set('');
    this.importResult.set(null);
    this.danceService.importDances(this.importText).subscribe({
      next: result => {
        this.importResult.set(result);
        this.importing.set(false);
        if (result.created.length > 0) {
          this.searchResults.update(list => [...result.created, ...list]);
          this.searchTotal.update(t => t + result.created.length);
          this.importText = '';
        }
      },
      error: () => { this.importError.set('Import failed. Make sure you are logged in as admin.'); this.importing.set(false); }
    });
  }

  // --- Admin: Add Style ---
  toggleAddStyle(): void {
    this.showAddStyle.update(v => !v);
    this.addStyleError.set('');
    this.newStyleName = '';
    this.newStyleDesc = '';
  }

  submitAddStyle(): void {
    if (!this.newStyleName.trim()) { this.addStyleError.set('Name is required.'); return; }
    this.addingStyle.set(true);
    this.addStyleError.set('');
    this.styleService.create(this.newStyleName.trim(), this.newStyleDesc.trim() || undefined).subscribe({
      next: style => {
        this.styles.update(list => [...list, style]);
        this.showAddStyle.set(false);
        this.addingStyle.set(false);
        this.newStyleName = '';
        this.newStyleDesc = '';
      },
      error: () => { this.addStyleError.set('Failed to create style.'); this.addingStyle.set(false); }
    });
  }

  // --- Add Video ---
  toggleAddVideo(): void {
    const open = !this.showAddVideo();
    this.showAddVideo.set(open);
    this.addVideoError.set('');
    this.addVideoCreated.set(null);
    this.addVideoDanceQuery.set('');
    this.selectedAddVideoDance.set(null);
    this.newVideoTitle = '';
    this.newVideoUrl = '';
    this.newVideoScope = 'global';
    // Lazy-load the dance name list the picker searches over, once.
    if (open && this.addVideoDanceNames().length === 0) {
      this.danceService.getNames().subscribe(n => this.addVideoDanceNames.set(n));
    }
  }

  pickAddVideoDance(d: { id: number; name: string }): void {
    this.selectedAddVideoDance.set(d);
    this.addVideoDanceQuery.set('');
  }

  clearAddVideoDance(): void {
    this.selectedAddVideoDance.set(null);
  }

  // Inline dance creation: when the search finds no dance, create one (name only) and select it.
  creatingAddVideoDance = signal(false);

  createAddVideoDanceFromQuery(): void {
    const name = this.addVideoDanceQuery().trim();
    if (!name || this.creatingAddVideoDance()) return;
    this.creatingAddVideoDance.set(true);
    this.addVideoError.set('');
    this.danceService.create({ name, styleIds: [], musicalStyleIds: [] }).subscribe({
      next: dance => {
        const created = { id: dance.id, name: dance.name };
        this.addVideoDanceNames.update(list => [...list, created]);
        this.selectedAddVideoDance.set(created);
        this.addVideoDanceQuery.set('');
        this.creatingAddVideoDance.set(false);
        // Surface the new dance in the catalog list too.
        this.searchResults.update(list => [dance, ...list]);
        this.searchTotal.update(t => t + 1);
      },
      error: () => { this.addVideoError.set('Failed to create dance. Please try again.'); this.creatingAddVideoDance.set(false); }
    });
  }

  submitAddVideo(): void {
    const dance = this.selectedAddVideoDance();
    if (!dance) { this.addVideoError.set('Pick a dance to attach this video to.'); return; }
    if (!this.newVideoUrl.trim()) { this.addVideoError.set('Video URL or ID is required.'); return; }

    const parsed = parseVideoUrl(this.newVideoUrl);
    if (!parsed) { this.addVideoError.set('Unrecognized URL. Paste a YouTube, TikTok, or Instagram link.'); return; }

    const payload: CreateVideoPayload = {
      title: this.newVideoTitle.trim() || dance.name,
      videoId: parsed.videoId,
      platform: parsed.platform,
      danceId: dance.id,
      // Scope only matters for admins; the server ignores it for everyone else (always personal).
      ...(this.role.isAdmin() ? { scope: this.newVideoScope } : {})
    };

    this.addingVideo.set(true);
    this.addVideoError.set('');
    this.videoService.create(payload).subscribe({
      next: video => {
        this.addVideoCreated.set({ danceId: video.danceId, danceName: video.danceName, title: video.title });
        this.addingVideo.set(false);
        // Keep the dance selected for adding another; clear the per-video inputs.
        this.newVideoTitle = '';
        this.newVideoUrl = '';
      },
      error: () => { this.addVideoError.set('Failed to add video. Please try again.'); this.addingVideo.set(false); }
    });
  }

  // --- Admin: Add Dance ---
  toggleAddDance(): void {
    this.showAddDance.update(v => !v);
    this.addDanceError.set('');
    this.newDanceName = '';
    this.newDanceDesc = '';
    this.newDanceDifficulty = 'None';
    this.newDanceStyleIds.set(new Set());
    this.newDanceMusicalStyleIds.set(new Set());
    this.newDanceInstructorIds.set(new Set());
  }

  toggleDanceStyle(id: number): void {
    this.newDanceStyleIds.update(s => toggleSet(s, id));
  }

  toggleDanceMusicalStyle(id: number): void {
    this.newDanceMusicalStyleIds.update(s => toggleSet(s, id));
  }

  toggleDanceInstructor(id: number): void {
    this.newDanceInstructorIds.update(s => toggleSet(s, id));
  }

  submitAddDance(): void {
    if (!this.newDanceName.trim()) { this.addDanceError.set('Name is required.'); return; }
    const payload: CreateDancePayload = {
      name: this.newDanceName.trim(),
      description: this.newDanceDesc.trim() || undefined,
      difficulty: this.newDanceDifficulty,
      styleIds: [...this.newDanceStyleIds()],
      musicalStyleIds: [...this.newDanceMusicalStyleIds()],
      instructorIds: [...this.newDanceInstructorIds()]
    };
    this.addingDance.set(true);
    this.addDanceError.set('');
    this.danceService.create(payload).subscribe({
      next: dance => {
        this.searchResults.update(list => [dance, ...list]);
        this.searchTotal.update(t => t + 1);
        this.showAddDance.set(false);
        this.addingDance.set(false);
        this.newDanceName = '';
        this.newDanceDesc = '';
        this.newDanceDifficulty = 'None';
        this.newDanceStyleIds.set(new Set());
        this.newDanceMusicalStyleIds.set(new Set());
        this.newDanceInstructorIds.set(new Set());
      },
      error: () => { this.addDanceError.set('Failed to create dance.'); this.addingDance.set(false); }
    });
  }
}
