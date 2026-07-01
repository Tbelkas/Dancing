import { Component, OnInit, OnDestroy, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
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

const STATUS_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'notstarted', label: 'Not Started' },
  { value: 'inprogress', label: 'In Progress' },
  { value: 'learned', label: 'Learned' },
  { value: 'favorite', label: 'Favorited' }
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
  currentPage = signal(1);
  styles = signal<Style[]>([]);
  musicalStyles = signal<MusicalStyle[]>([]);
  instructors = signal<Instructor[]>([]);
  loading = signal(true);

  // Filters
  searchQuery = signal('');
  selectedStyleId = signal<number | null>(null);
  selectedMusicalStyleId = signal<number | null>(null);
  selectedDifficulty = signal<string | null>(null);
  selectedStatus = signal<string>('all');
  sortBy = signal<string>('recommended');

  styleQuery = signal('');
  musicQuery = signal('');

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
    this.selectedStatus() !== 'all'
  );

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
    private recentDances: RecentDancesService
  ) {}

  ngOnInit(): void {
    this.styleService.getAll().subscribe(s => this.styles.set(s));
    this.musicalStyleService.getAll().subscribe(ms => this.musicalStyles.set(ms));
    this.instructorService.getAll().subscribe(i => this.instructors.set(i));
    this.restoreFilters();
    this.runSearch();
  }

  /** Restore the last-used filters so open/refresh lands where the user left off. */
  private restoreFilters(): void {
    try {
      const raw = localStorage.getItem(FILTERS_KEY);
      if (!raw) return;
      const s = JSON.parse(raw);
      if (typeof s.searchQuery === 'string') this.searchQuery.set(s.searchQuery);
      if (s.selectedStyleId === null || typeof s.selectedStyleId === 'number') this.selectedStyleId.set(s.selectedStyleId);
      if (s.selectedMusicalStyleId === null || typeof s.selectedMusicalStyleId === 'number') this.selectedMusicalStyleId.set(s.selectedMusicalStyleId);
      if (s.selectedDifficulty === null || typeof s.selectedDifficulty === 'string') this.selectedDifficulty.set(s.selectedDifficulty);
      if (typeof s.selectedStatus === 'string') this.selectedStatus.set(s.selectedStatus);
      if (typeof s.sortBy === 'string') this.sortBy.set(s.sortBy);
      if (typeof s.currentPage === 'number' && s.currentPage >= 1) this.currentPage.set(s.currentPage);
    } catch { /* ignore malformed/unavailable storage */ }
    // Status only applies to signed-in users; drop a stale personal filter when logged out.
    if (!this.auth.isAuthenticated()) this.selectedStatus.set('all');
  }

  private persistFilters(): void {
    try {
      localStorage.setItem(FILTERS_KEY, JSON.stringify({
        searchQuery: this.searchQuery(),
        selectedStyleId: this.selectedStyleId(),
        selectedMusicalStyleId: this.selectedMusicalStyleId(),
        selectedDifficulty: this.selectedDifficulty(),
        selectedStatus: this.selectedStatus(),
        sortBy: this.sortBy(),
        currentPage: this.currentPage()
      }));
    } catch { /* storage unavailable (private mode, quota) — non-fatal */ }
  }

  ngOnDestroy(): void {
    if (this.searchDebounce) clearTimeout(this.searchDebounce);
    this.searchSub?.unsubscribe();
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
      sortBy: this.sortBy(),
      page: this.currentPage(),
      pageSize: this.PAGE_SIZE
    }).subscribe({
      next: result => {
        this.searchResults.set(result.items);
        this.searchTotal.set(result.total);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
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
    this.currentPage.set(1);
    this.runSearch();
  }

  thumbnailUrl(dance: Dance): string | null {
    if (this.thumbFailed().has(dance.id)) return null;
    if (dance.thumbnailVideoId && dance.thumbnailPlatform === 'youtube') {
      return `https://i.ytimg.com/vi/${dance.thumbnailVideoId}/hqdefault.jpg`;
    }
    return null;
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

    this.danceService.setStatus(dance.id, status).subscribe({
      error: () => this.searchResults.update(list =>
        list.map(d => d.id === dance.id ? { ...d, ...snap } : d)
      )
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
