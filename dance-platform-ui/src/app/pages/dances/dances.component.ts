import { Component, OnInit, OnDestroy, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { skip } from 'rxjs/operators';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';
import { DanceService, ImportResult, DanceStatus, statusFlags } from '../../core/services/dance.service';
import { StyleService } from '../../core/services/style.service';
import { MusicalStyleService } from '../../core/services/musical-style.service';
import { InstructorService } from '../../core/services/instructor.service';
import { AuthService } from '../../core/services/auth.service';
import { RoleService } from '../../core/services/role.service';
import { RecentDancesService } from '../../core/services/recent-dances.service';
import { Dance } from '../../models/dance.model';
import { Style } from '../../models/style.model';
import { MusicalStyle } from '../../models/musical-style.model';
import { Instructor } from '../../models/instructor.model';
import { DIFFICULTY_FILTER_OPTIONS, DIFFICULTY_LEVELS } from '../../core/constants/dance.constants';
import { youtubeThumbUrl } from '../../core/utils/youtube-thumb.utils';
import { UrlFilterSync, idFromParam, pageFromParam } from '../../core/utils/url-filter-sync';
import { ThumbFallback } from '../../core/utils/thumb-fallback';
import { AddStyleFormComponent } from '../../shared/components/add-style-form/add-style-form.component';
import { AddDanceFormComponent } from '../../shared/components/add-dance-form/add-dance-form.component';
import { BulkImportFormComponent } from '../../shared/components/bulk-import-form/bulk-import-form.component';
import { AddVideoFormComponent } from '../../shared/components/add-video-form/add-video-form.component';

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
  // The admin/authoring forms are referenced only inside @defer blocks below, so Angular
  // code-splits them into a lazy chunk — anonymous visitors never download that markup.
  imports: [CommonModule, FormsModule, RouterLink, DancePathPipe,
    AddStyleFormComponent, AddDanceFormComponent, BulkImportFormComponent, AddVideoFormComponent],
  templateUrl: './dances.component.html',
  styleUrls: ['./dances.component.css']
})
export class DancesComponent implements OnInit, OnDestroy {
  readonly difficulties = DIFFICULTY_FILTER_OPTIONS;
  readonly difficultyLevels = DIFFICULTY_LEVELS;
  readonly statusOptions = STATUS_OPTIONS;
  readonly skeletonCards = [0, 1, 2, 3, 4, 5];
  /** Compact rows are much shorter than cards, so the list skeleton needs more of them. */
  readonly skeletonRows = [0, 1, 2, 3, 4, 5, 6, 7];
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
    const musicId = this.selectedMusicalStyleId();
    if (musicId !== null) {
      const ms = this.musicalStyles().find(m => m.id === musicId);
      chips.push({ key: 'music', label: ms?.name ?? 'Music' });
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

  /** Per-dance link params that reopen the video the user last watched there, keyed by dance id.
   *  Rebuilt only when the history trail changes, so the param objects stay reference-stable. */
  private readonly resumeParams = computed(() => {
    const map = new Map<number, { v: number }>();
    for (const r of this.recentDances.recent()) {
      if (r.videoId) map.set(r.id, { v: r.videoId });
    }
    return map;
  });

  /** Query params for a rail card, so it resumes the video rather than the dance's video list. */
  resumeFor(danceId: number): { v: number } | null {
    return this.resumeParams().get(danceId) ?? null;
  }

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

  readonly thumbs = new ThumbFallback();

  private searchDebounce: ReturnType<typeof setTimeout> | null = null;
  private searchSub: Subscription | null = null;
  private urlSub: Subscription | null = null;

  // Open-state for the extracted authoring forms. Each form is a @defer-loaded child that
  // owns its own field/submit state; the parent only toggles visibility and reacts to the
  // child's success events (see the on*Created / onImported handlers below).
  showAddStyle = signal(false);
  showImport = signal(false);
  // Add Video (any authenticated user; admins also choose Global vs Local scope)
  showAddVideo = signal(false);
  showAddDance = signal(false);

  /** Declarative URL/localStorage wiring for every filter — one entry per filter. */
  private readonly filterSync: UrlFilterSync;

  constructor(
    private danceService: DanceService,
    private styleService: StyleService,
    private musicalStyleService: MusicalStyleService,
    private instructorService: InstructorService,
    public auth: AuthService,
    public role: RoleService,
    private recentDances: RecentDancesService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    // Status/favorites only apply to signed-in users; sanitize drops stale personal
    // filters arriving from the URL when logged out.
    const authed = () => this.auth.isAuthenticated();
    this.filterSync = new UrlFilterSync(FILTERS_KEY, this.router, this.route, [
      {
        param: 'q', storageKey: 'searchQuery', signal: this.searchQuery,
        fromParam: raw => raw ?? '',
        toParam: v => v.trim() || null,
        fromStored: raw => typeof raw === 'string' ? raw : undefined,
        // persist() writes the trimmed value, so its URL echo must match untrimmed state.
        equals: (fromUrl, current) => fromUrl === current.trim()
      },
      {
        param: 'style', storageKey: 'selectedStyleId', signal: this.selectedStyleId,
        fromParam: idFromParam,
        toParam: v => v,
        fromStored: raw => raw === null || typeof raw === 'number' ? raw as number | null : undefined
      },
      {
        param: 'music', storageKey: 'selectedMusicalStyleId', signal: this.selectedMusicalStyleId,
        fromParam: idFromParam,
        toParam: v => v,
        fromStored: raw => raw === null || typeof raw === 'number' ? raw as number | null : undefined
      },
      {
        param: 'level', storageKey: 'selectedDifficulty', signal: this.selectedDifficulty,
        fromParam: raw => raw,
        toParam: v => v,
        fromStored: raw => raw === null || typeof raw === 'string' ? raw as string | null : undefined
      },
      {
        param: 'status', storageKey: 'selectedStatus', signal: this.selectedStatus,
        fromParam: raw => raw ?? 'all',
        toParam: v => v !== 'all' ? v : null,
        fromStored: raw => typeof raw === 'string' ? raw : undefined,
        sanitize: v => authed() ? v : 'all'
      },
      {
        param: 'fav', storageKey: 'favoritesOnly', signal: this.favoritesOnly,
        fromParam: raw => raw === '1',
        toParam: v => v ? '1' : null,
        fromStored: raw => typeof raw === 'boolean' ? raw : undefined,
        sanitize: v => authed() ? v : false
      },
      {
        param: 'sort', storageKey: 'sortBy', signal: this.sortBy,
        fromParam: raw => raw || 'recommended',
        toParam: v => v !== 'recommended' ? v : null,
        fromStored: raw => typeof raw === 'string' ? raw : undefined
      },
      {
        param: 'page', storageKey: 'currentPage', signal: this.currentPage,
        fromParam: pageFromParam,
        toParam: v => v > 1 ? v : null,
        fromStored: raw => typeof raw === 'number' && raw >= 1 ? raw : undefined
      }
    ]);
  }

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
    this.urlSub = this.route.queryParamMap.pipe(skip(1)).subscribe(qp => {
      if (this.filterSync.applyIfChanged(qp)) this.runSearch();
    });
    if (this.auth.isAuthenticated()) {
      this.railPending.set(true);
      this.danceService.searchDances({ status: 'inprogress', sortBy: 'name', pageSize: 12 })
        .subscribe({
          next: r => { this.railDances.set(r.items); this.railPending.set(false); },
          error: () => this.railPending.set(false)
        });
    }
  }

  private restoreFilters(): void {
    this.filterSync.restore();
    // Legacy stored/linked value from when Favorited lived inside status.
    if (this.selectedStatus() === 'favorite') {
      this.selectedStatus.set('all');
      this.favoritesOnly.set(true);
    }
    // Status/favorites only apply to signed-in users; drop stale personal filters when
    // logged out (also covers values restored from the localStorage snapshot).
    if (!this.auth.isAuthenticated()) {
      this.selectedStatus.set('all');
      this.favoritesOnly.set(false);
    }
  }

  ngOnDestroy(): void {
    if (this.searchDebounce) clearTimeout(this.searchDebounce);
    this.searchSub?.unsubscribe();
    this.urlSub?.unsubscribe();
    this.clearHoverTimer();
  }

  setViewMode(mode: 'grid' | 'list'): void {
    this.viewMode.set(mode);
    try { localStorage.setItem(this.VIEW_MODE_KEY, mode); } catch { /* non-fatal */ }
  }

  private runSearch(): void {
    this.filterSync.persist();
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
      case 'music': this.selectedMusicalStyleId.set(null); break;
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
    if (!dance.thumbnailVideoId || dance.thumbnailPlatform !== 'youtube' || this.thumbs.has(dance.id)) return;
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
    if (this.thumbs.has(dance.id)) return null;
    // Hovering this card cycles storyboard frames (mq1–mq3); otherwise the static poster.
    const frame = this.hoverDanceId() === dance.id ? this.hoverFrame() : 0;
    return youtubeThumbUrl(dance.thumbnailVideoId, dance.thumbnailPlatform, frame);
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
    this.thumbs.markFailed(danceId);
  }

  /** YouTube serves a tiny grey placeholder for missing thumbs — treat it as a failure. */
  onThumbLoad(danceId: number, event: Event): void {
    const img = event.target as HTMLImageElement;
    if (img.naturalHeight > 0 && img.naturalHeight <= 90) {
      this.thumbs.markFailed(danceId);
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
    const flags = statusFlags(status);

    this.searchResults.update(list =>
      list.map(d => d.id === dance.id ? { ...d, ...flags } : d)
    );
    // Keep the local recently-viewed trail in step so the "Recently viewed" rows don't
    // briefly show a dance that the server then reports as learned (or vice versa).
    this.recentDances.setLearned(dance.id, flags.isLearned);

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
  }

  /** BulkImportFormComponent finished an import — splice the created dances into the grid. */
  onImported(result: ImportResult): void {
    this.searchResults.update(list => [...result.created, ...list]);
    this.searchTotal.update(t => t + result.created.length);
  }

  // --- Admin: Add Style ---
  toggleAddStyle(): void {
    this.showAddStyle.update(v => !v);
  }

  /** AddStyleFormComponent created a style — add it to the list and close the form. */
  onStyleCreated(style: Style): void {
    this.styles.update(list => [...list, style]);
    this.showAddStyle.set(false);
  }

  // --- Add Video ---
  toggleAddVideo(): void {
    this.showAddVideo.update(v => !v);
  }

  /** AddVideoFormComponent created a dance inline (from its picker) — surface it in the grid. */
  onVideoDanceCreated(dance: Dance): void {
    this.searchResults.update(list => [dance, ...list]);
    this.searchTotal.update(t => t + 1);
  }

  // --- Admin: Add Dance ---
  toggleAddDance(): void {
    this.showAddDance.update(v => !v);
  }

  /** AddDanceFormComponent created a dance — prepend it and close the form. */
  onDanceCreated(dance: Dance): void {
    this.searchResults.update(list => [dance, ...list]);
    this.searchTotal.update(t => t + 1);
    this.showAddDance.set(false);
  }
}
