import { Component, OnInit, AfterViewInit, ElementRef, HostListener, ViewChild, WritableSignal, computed, effect, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';
import { switchMap, catchError, throwError } from 'rxjs';
import { parseVideoUrl, parseTimeSecs } from '../../core/utils/video-url.utils';
import { toggleSet } from '../../core/utils/set.utils';
import { ProfileService } from '../../core/services/profile.service';
import { StyleService } from '../../core/services/style.service';
import { DanceService, CreateDancePayload } from '../../core/services/dance.service';
import { VideoService, CreateVideoPayload } from '../../core/services/video.service';
import { RecentDancesService, RecentDance } from '../../core/services/recent-dances.service';
import { ToastService } from '../../core/services/toast.service';
import { MyStyleWithDances } from '../../models/user.model';
import { Style } from '../../models/style.model';
import { Video } from '../../models/video.model';
import { Dance } from '../../models/dance.model';
import { VideoPlayerComponent } from '../../shared/components/video-player/video-player.component';
import { delayedLoading } from '../../core/utils/delayed-loading';
import { SkeletonCount } from '../../core/utils/skeleton-count';

/** A history entry plus the query params that reopen the video it was left on. */
interface ContinueCard extends RecentDance {
  resume: { v?: number };
}

@Component({
  selector: 'app-my-dances',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, VideoPlayerComponent, DancePathPipe],
  templateUrl: './my-dances.component.html',
  styleUrls: ['./my-dances.component.css']
})
export class MyDancesComponent implements OnInit, AfterViewInit {
  private readonly SELECTED_STYLE_KEY = 'dp_mydances_style';
  private readonly EXPANDED_DANCE_KEY = 'dp_mydances_expanded';
  private readonly CONTINUE_STYLE_KEY = 'dp_continue_style';

  myStyles = signal<MyStyleWithDances[]>([]);
  allStyles = signal<Style[]>([]);
  selectedStyleId = signal<number | null>(null);
  loading = signal(true);
  showSkeleton = delayedLoading(this.loading);
  showStylePicker = signal(false);

  // Placeholder counts remembered from the last visit — the tab strip and the row list are
  // both as long as this particular user made them, and a fixed guess is only ever right
  // for one of us. See SkeletonCount.
  readonly tabsSkeleton = new SkeletonCount('mydances-tabs', 4, { max: 10 });
  readonly rowsSkeleton = new SkeletonCount('mydances-rows', 5, { max: 12 });

  /** Sentinel tab id for the cross-style Favorites view. */
  readonly FAVORITES_TAB = -1;
  favoriteDances = signal<Dance[]>([]);
  loadingFavorites = signal(false);
  showFavoritesSkeleton = delayedLoading(this.loadingFavorites);
  readonly favoritesSkeleton = new SkeletonCount('mydances-favorites', 4, { max: 12 });
  private favoritesLoaded = false;

  // Add style form
  showAddStyle = signal(false);
  newStyleName = '';
  newStyleDesc = '';
  addingStyle = signal(false);
  addStyleError = signal('');

  // Add dance form
  showAddDance = signal(false);
  newDanceName = '';
  newDanceDesc = '';
  newDanceStyleIds = signal<Set<number>>(new Set());
  newVideoTitle = '';
  newVideoUrl = '';
  setVideoTime = false;
  newVideoStartTime = '';
  newVideoEndTime = '';
  addingDance = signal(false);
  addDanceError = signal('');

  // Inline video expansion
  expandedDanceId = signal<number | null>(null);
  expandedVideos = signal<Video[]>([]);
  loadingVideos = signal(false);
  private videoCache = new Map<number, Video[]>();

  // "Recommended for you" — untracked dances in the active style, ranked by the
  // catalog's recommended sort. Cached per style for the component's lifetime.
  private readonly RECOMMENDED_SHOWN = 6;
  recommendedDances = signal<Dance[]>([]);
  loadingRecommended = signal(false);
  showRecommendedSkeleton = delayedLoading(this.loadingRecommended);
  /** Never more than the display cap — the row is a fixed shelf, not an open list. */
  readonly recommendedSkeleton = new SkeletonCount('mydances-recommended', 3, { max: this.RECOMMENDED_SHOWN });
  private recCache = new Map<number, Dance[]>();

  /** Every dance the user tracks in any style — recommendations must never repeat these. */
  private readonly trackedIds = computed(() =>
    new Set(this.myStyles().flatMap(ms => ms.dances).map(d => d.id))
  );

  /**
   * The server already filters to notstarted, but a dance tracked right here (Add Dance,
   * status set elsewhere) would go stale in the cache — re-filter against live my-dances data.
   */
  readonly recommendedVisible = computed(() => {
    const tracked = this.trackedIds();
    return this.recommendedDances().filter(d => !tracked.has(d.id)).slice(0, this.RECOMMENDED_SHOWN);
  });

  readonly myStyleIds = computed(() => new Set(this.myStyles().map(ms => ms.styleId)));

  /** Upper bound of "Recently viewed" cards; the carousel scrolls through them. */
  private readonly CONTINUE_LIMIT = 20;
  private recThumbFailed = signal<Set<number>>(new Set());

  /** Ids the user has already learned, drawn from the live my-dances data. */
  private readonly learnedIds = computed(() =>
    new Set(this.myStyles().flatMap(ms => ms.dances).filter(d => d.status === 'learned').map(d => d.id))
  );

  /**
   * Most-recently-opened dances the user hasn't learned yet — the local view history, shown as
   * "Recently viewed". Distinct from the browse page's "Continue learning" rail, which is the
   * server's in-progress list; only the browse *fallback* rail shares this source.
   * Each card carries the query params that reopen the video they were last watching (when we
   * know it), built here so the objects stay reference-stable across change detection.
   */
  readonly continueLearning = computed<ContinueCard[]>(() => {
    const learned = this.learnedIds();
    return this.recentDances.recent()
      .filter(d => !d.learned && !learned.has(d.id))
      .slice(0, this.CONTINUE_LIMIT)
      .map(d => ({ ...d, resume: d.videoId ? { v: d.videoId } : {} }));
  });

  // Recently-viewed carousel: the track scrolls horizontally; arrows show only
  // when it overflows and disable once you hit either end.
  @ViewChild('historyTrack') private historyTrack?: ElementRef<HTMLElement>;
  readonly historyOverflow = signal(false);
  readonly historyAtStart = signal(true);
  readonly historyAtEnd = signal(false);

  /**
   * Style narrows the trail; it never re-orders it. Grouping by style used to fan the row out
   * into one grid per style, which cost the section its height ceiling and threw away the only
   * thing it knows — what you did last. As a filter it still answers "what was I doing in
   * House?" while the rail stays one card tall and stays in recency order. Remembered, so
   * someone who thinks in styles doesn't re-pick it every visit.
   */
  readonly historyStyle = signal<string>(localStorage.getItem(this.CONTINUE_STYLE_KEY) ?? '');

  /** Styles present in the trail, first-seen (so most-recent) first, with their card counts. */
  readonly continueStyleFacets = computed(() => {
    const counts = new Map<string, number>();
    for (const dance of this.continueLearning()) {
      const key = dance.styleName || 'Other';
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return [...counts].map(([name, count]) => ({ name, count }));
  });

  /**
   * The stored filter resolved against what's actually in the trail. A style drops out as soon
   * as its last card is dismissed or learned, and a filter pinned to a style that is no longer
   * there would show an empty rail with no way back — fall through to all instead.
   */
  readonly activeHistoryStyle = computed(() => {
    const chosen = this.historyStyle();
    return chosen && this.continueStyleFacets().some(f => f.name === chosen) ? chosen : '';
  });

  readonly continueVisible = computed(() => {
    const style = this.activeHistoryStyle();
    if (!style) return this.continueLearning();
    return this.continueLearning().filter(d => (d.styleName || 'Other') === style);
  });

  /**
   * The rail's structure is time, not style: consecutive cards from the same age band are
   * collected so the track can set a marker down where the band changes. The source list is
   * recency-sorted, so bands come out in order and each appears at most once.
   *
   * `fade` is how far the band's thumbnails are dimmed — the trail decays as it goes back,
   * which is what makes 20 equally loud cards read as one gradient with a lit head.
   */
  readonly continueBands = computed(() => {
    const bands: { label: string; fade: number; dances: ContinueCard[] }[] = [];
    for (const dance of this.continueVisible()) {
      const index = this.ageBand(dance.viewedAt);
      const label = this.AGE_BANDS[index];
      const open = bands[bands.length - 1];
      if (open && open.label === label) open.dances.push(dance);
      else bands.push({ label, fade: Math.min(index, 2), dances: [dance] });
    }
    return bands;
  });

  private readonly AGE_BANDS = ['Today', 'Yesterday', 'This week', 'Earlier'];

  /** Which age band a view falls in, counted in calendar days rather than elapsed hours. */
  private ageBand(viewedAt: number): number {
    const now = new Date();
    const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const day = 86_400_000;
    if (viewedAt >= midnight) return 0;
    if (viewedAt >= midnight - day) return 1;
    if (viewedAt >= midnight - 6 * day) return 2;
    return 3;
  }

  // Cards mid-animation. Kept as id sets rather than a flag on the card because the
  // cards are recomputed objects — the transition has to survive their identity changing.
  // Both durations must stay >= the CSS ones in my-dances.component.css.
  private readonly DISMISS_ANIM_MS = 180;
  private readonly RESTORE_ANIM_MS = 220;
  readonly dismissingIds = signal<ReadonlySet<number>>(new Set());
  readonly restoringIds = signal<ReadonlySet<number>>(new Set());
  private dismissTimers = new Map<number, ReturnType<typeof setTimeout>>();

  /** Empty string is the unfiltered trail. */
  setHistoryStyle(name: string): void {
    this.historyStyle.set(name);
    if (name) localStorage.setItem(this.CONTINUE_STYLE_KEY, name);
    else localStorage.removeItem(this.CONTINUE_STYLE_KEY);
  }

  readonly selectedStyle = computed(() => {
    const id = this.selectedStyleId();
    return id ? this.myStyles().find(ms => ms.styleId === id) ?? null : null;
  });

  readonly learnedDances = computed(() =>
    this.selectedStyle()?.dances.filter(d => d.status === 'learned') ?? []
  );

  readonly inProgressDances = computed(() =>
    this.selectedStyle()?.dances.filter(d => d.status === 'inProgress') ?? []
  );

  /** Tracked = moves you're learning or have learned in this style. */
  readonly trackedCount = computed(() => this.learnedDances().length + this.inProgressDances().length);

  readonly learnedPct = computed(() => {
    const total = this.trackedCount();
    return total === 0 ? 0 : Math.round((this.learnedDances().length / total) * 100);
  });

  constructor(
    private profileService: ProfileService,
    private styleService: StyleService,
    private danceService: DanceService,
    private videoService: VideoService,
    private recentDances: RecentDancesService,
    private toast: ToastService,
    private route: ActivatedRoute
  ) {
    // The card list grows/shrinks as history loads or a card is dismissed — re-measure
    // the track after the DOM settles so the arrows reflect the new scrollable width.
    effect(() => {
      this.continueVisible();
      setTimeout(() => this.updateHistoryScrollState());
    });

    // Fetch recommendations whenever a real style tab becomes active (not Favorites).
    effect(() => {
      const id = this.selectedStyleId();
      if (id !== null && id !== this.FAVORITES_TAB) this.loadRecommended(id);
    }, { allowSignalWrites: true });
  }

  private loadRecommended(styleId: number): void {
    const cached = this.recCache.get(styleId);
    if (cached) {
      this.recommendedDances.set(cached);
      return;
    }
    this.recommendedDances.set([]);
    this.loadingRecommended.set(true);
    // Over-fetch past the display cap so client-side re-filtering still fills the row.
    this.danceService.searchDances({
      styleId, status: 'notstarted', sortBy: 'recommended', pageSize: this.RECOMMENDED_SHOWN * 2
    }).subscribe({
      next: res => {
        this.recCache.set(styleId, res.items);
        if (this.selectedStyleId() === styleId) {
          this.recommendedDances.set(res.items);
          this.recommendedSkeleton.remember(this.recommendedVisible().length);
          this.loadingRecommended.set(false);
        }
      },
      error: () => {
        if (this.selectedStyleId() === styleId) this.loadingRecommended.set(false);
      }
    });
  }

  ngAfterViewInit(): void {
    this.updateHistoryScrollState();
  }

  @HostListener('window:resize')
  onResize(): void {
    this.updateHistoryScrollState();
  }

  onHistoryScroll(): void {
    this.updateHistoryScrollState();
  }

  /** Scroll the history track by most of its width — dir -1 is newer, +1 is older. */
  scrollHistory(dir: -1 | 1): void {
    const el = this.historyTrack?.nativeElement;
    if (!el) return;
    el.scrollBy({ left: dir * el.clientWidth * 0.8, behavior: 'smooth' });
  }

  private updateHistoryScrollState(): void {
    const el = this.historyTrack?.nativeElement;
    if (!el) { this.historyOverflow.set(false); return; }
    const maxScroll = el.scrollWidth - el.clientWidth;
    this.historyOverflow.set(maxScroll > 1);
    this.historyAtStart.set(el.scrollLeft <= 1);
    this.historyAtEnd.set(el.scrollLeft >= maxScroll - 1);
  }

  /** YouTube thumbnail for a recently-viewed dance, or null if missing/failed to load. */
  continueThumbnailUrl(dance: { id: number; thumbnailVideoId?: string; thumbnailPlatform?: string }): string | null {
    if (this.recThumbFailed().has(dance.id)) return null;
    if (dance.thumbnailVideoId && dance.thumbnailPlatform === 'youtube') {
      return `https://i.ytimg.com/vi/${dance.thumbnailVideoId}/hqdefault.jpg`;
    }
    return null;
  }

  onContinueThumbError(danceId: number): void {
    this.recThumbFailed.update(set => new Set(set).add(danceId));
  }

  dismissContinue(danceId: number, event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    if (this.dismissingIds().has(danceId)) return;
    const name = this.continueLearning().find(d => d.id === danceId)?.name;
    // Purely local, so the removal has already happened and there is nothing to defer —
    // undo just puts the trail back the way it was.
    const before = this.recentDances.snapshot();

    // Let the card fade before it leaves the list; the real removal waits out the
    // transition so the row doesn't close up under a still-visible card.
    this.setCardFlag(this.dismissingIds, danceId, true);
    this.dismissTimers.set(danceId, setTimeout(() => {
      this.dismissTimers.delete(danceId);
      this.recentDances.remove(danceId);
      this.setCardFlag(this.dismissingIds, danceId, false);
    }, this.DISMISS_ANIM_MS));

    this.toast.undoable(name ? `Removed "${name}" from Recently viewed.` : 'Removed from Recently viewed.', {
      commit: () => {},
      undo: () => this.undoDismiss(danceId, before)
    });
  }

  /**
   * Undo can land either mid-fade (card still on screen — just stop fading it) or after
   * the card is gone, in which case it comes back on a matching fade-in.
   */
  private undoDismiss(danceId: number, before: RecentDance[]): void {
    const pending = this.dismissTimers.get(danceId);
    if (pending !== undefined) {
      clearTimeout(pending);
      this.dismissTimers.delete(danceId);
      this.setCardFlag(this.dismissingIds, danceId, false);
      return;
    }
    this.recentDances.restore(before);
    this.setCardFlag(this.restoringIds, danceId, true);
    setTimeout(() => this.setCardFlag(this.restoringIds, danceId, false), this.RESTORE_ANIM_MS);
  }

  private setCardFlag(set: WritableSignal<ReadonlySet<number>>, danceId: number, on: boolean): void {
    set.update(ids => {
      const next = new Set(ids);
      if (on) next.add(danceId); else next.delete(danceId);
      return next;
    });
  }

  ngOnInit(): void {
    // Deep link from Profile: /my-dances?tab=favorites opens the Favorites view.
    if (this.route.snapshot.queryParamMap.get('tab') === 'favorites') {
      this.selectFavorites();
    }
    this.load();
    this.styleService.getAll().subscribe(s => this.allStyles.set(s));
  }

  selectFavorites(): void {
    this.setSelectedStyle(this.FAVORITES_TAB);
    this.showAddDance.set(false);
    this.expandedDanceId.set(null);
    if (!this.favoritesLoaded) this.loadFavorites();
  }

  private loadFavorites(): void {
    this.loadingFavorites.set(true);
    this.danceService.searchDances({ favoritesOnly: true, sortBy: 'name', pageSize: 200 }).subscribe({
      next: res => {
        this.favoriteDances.set(res.items);
        this.favoritesSkeleton.remember(res.items.length);
        this.favoritesLoaded = true;
        this.loadingFavorites.set(false);
      },
      error: () => this.loadingFavorites.set(false)
    });
  }

  load(): void {
    this.loading.set(true);
    this.profileService.getMyDances().subscribe({
      next: data => {
        this.myStyles.set(data);
        const exists = (id: number | null) => id != null && data.some(ms => ms.styleId === id);
        const current = this.selectedStyleId();
        if (current !== this.FAVORITES_TAB && !exists(current)) {
          const stored = localStorage.getItem(this.SELECTED_STYLE_KEY);
          const storedId = stored ? Number(stored) : null;
          if (storedId === this.FAVORITES_TAB) {
            this.selectFavorites();
          } else {
            this.setSelectedStyle(
              exists(storedId) ? storedId : (data.length > 0 ? data[0].styleId : null)
            );
          }
        }
        // Restore last expanded dance if it's in the current style's dances
        const storedExpanded = localStorage.getItem(this.EXPANDED_DANCE_KEY);
        const expandedId = storedExpanded ? Number(storedExpanded) : null;
        if (expandedId && data.flatMap(ms => ms.dances).some(d => d.id === expandedId)) {
          this.expandDance(expandedId);
        }
        this.tabsSkeleton.remember(data.length + 1); // + the Favorites tab, always present
        // Only when a real style is open — on the Favorites tab there are no style rows to
        // measure, and recording a zero would shrink the placeholder for everyone who lands here.
        const style = this.selectedStyle();
        if (style) this.rowsSkeleton.remember(style.dances.length);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  /** Re-pull my-dances without the full-page loading flash; keeps the chosen tab selected. */
  private refreshMyStyles(preferStyleId?: number): void {
    this.profileService.getMyDances().subscribe(data => {
      this.myStyles.set(data);
      const exists = (id: number | null | undefined) => id != null && data.some(ms => ms.styleId === id);
      if (exists(preferStyleId)) {
        this.setSelectedStyle(preferStyleId!);
      } else if (!exists(this.selectedStyleId())) {
        this.setSelectedStyle(data.length > 0 ? data[0].styleId : null);
      }
    });
  }

  selectStyle(id: number): void {
    this.setSelectedStyle(id);
    this.showAddDance.set(false);
    this.expandedDanceId.set(null);
  }

  /** Sets the active style tab and remembers it across visits/reloads. */
  private setSelectedStyle(id: number | null): void {
    this.selectedStyleId.set(id);
    if (id === null) {
      localStorage.removeItem(this.SELECTED_STYLE_KEY);
    } else {
      localStorage.setItem(this.SELECTED_STYLE_KEY, String(id));
    }
  }

  toggleExpand(danceId: number, event: Event): void {
    event.preventDefault();
    event.stopPropagation();

    if (this.expandedDanceId() === danceId) {
      this.expandedDanceId.set(null);
      localStorage.removeItem(this.EXPANDED_DANCE_KEY);
      return;
    }

    localStorage.setItem(this.EXPANDED_DANCE_KEY, String(danceId));
    this.expandDance(danceId);
  }

  private expandDance(danceId: number): void {
    this.expandedDanceId.set(danceId);
    const cached = this.videoCache.get(danceId);
    if (cached) {
      this.expandedVideos.set(cached);
      return;
    }

    this.expandedVideos.set([]);
    this.loadingVideos.set(true);
    this.videoService.getByDance(danceId).subscribe({
      next: videos => {
        this.videoCache.set(danceId, videos);
        if (this.expandedDanceId() === danceId) {
          this.expandedVideos.set(videos);
          this.loadingVideos.set(false);
        }
      },
      error: () => {
        if (this.expandedDanceId() === danceId) this.loadingVideos.set(false);
      }
    });
  }

  toggleMyStyle(style: Style): void {
    this.styleService.toggleMyStyle(style.id).subscribe(res => {
      if (res.isMyStyle) {
        // Show the tab instantly, then refresh from the server so any dances
        // already learned / in progress in this style populate it (otherwise the
        // tab reads "no tracked moves" until a full reload).
        this.myStyles.update(list =>
          list.some(ms => ms.styleId === style.id)
            ? list
            : [...list, { styleId: style.id, styleName: style.name, dances: [] }]);
        this.setSelectedStyle(style.id);
        this.refreshMyStyles(style.id);
      } else {
        const prevId = this.selectedStyleId();
        this.myStyles.update(list => list.filter(ms => ms.styleId !== style.id));
        if (prevId === style.id) {
          const remaining = this.myStyles();
          this.setSelectedStyle(remaining.length > 0 ? remaining[0].styleId : null);
        }
      }
    });
  }

  // --- Add Style ---
  toggleAddStyle(): void {
    this.showAddStyle.set(!this.showAddStyle());
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
        this.allStyles.update(list => [...list, style]);
        this.showAddStyle.set(false);
        this.addingStyle.set(false);
        this.newStyleName = '';
        this.newStyleDesc = '';
      },
      error: () => { this.addStyleError.set('Failed to create style.'); this.addingStyle.set(false); }
    });
  }

  // --- Add Dance ---
  toggleAddDance(): void {
    const open = !this.showAddDance();
    this.showAddDance.set(open);
    if (open) {
      const sid = this.selectedStyleId();
      this.newDanceStyleIds.set(sid ? new Set([sid]) : new Set());
    }
    this.addDanceError.set('');
    this.newDanceName = '';
    this.newDanceDesc = '';
    this.newVideoTitle = '';
    this.newVideoUrl = '';
    this.setVideoTime = false;
    this.newVideoStartTime = '';
    this.newVideoEndTime = '';
  }

  toggleNewDanceStyle(id: number): void {
    this.newDanceStyleIds.update(s => toggleSet(s, id));
  }

  submitAddDance(): void {
    const danceName = this.newDanceName.trim();
    if (!danceName) { this.addDanceError.set('Dance name is required.'); return; }
    const videoUrl = this.newVideoUrl.trim();
    // Title is optional — default it to the dance name so pasting only a URL still saves the video.
    const videoTitle = this.newVideoTitle.trim() || danceName;

    // Validate the URL up-front so a bad link doesn't leave a dance with no video.
    const parsedVideo = videoUrl ? parseVideoUrl(videoUrl) : null;
    if (videoUrl && !parsedVideo) {
      this.addDanceError.set('Unrecognized URL. Paste a YouTube, TikTok, or Instagram link.');
      return;
    }

    this.addingDance.set(true);
    this.addDanceError.set('');

    const dancePayload: CreateDancePayload = {
      name: danceName,
      description: this.newDanceDesc.trim() || undefined,
      styleIds: [...this.newDanceStyleIds()],
      musicalStyleIds: []
    };

    this.danceService.create(dancePayload).pipe(
      switchMap(dance => {
        if (parsedVideo) {
          const videoPayload: CreateVideoPayload = {
            title: videoTitle,
            videoId: parsedVideo.videoId,
            platform: parsedVideo.platform,
            danceId: dance.id,
            ...(this.setVideoTime && parsedVideo.platform === 'youtube' ? {
              startTime: parseTimeSecs(this.newVideoStartTime),
              endTime: parseTimeSecs(this.newVideoEndTime)
            } : {})
          };
          return this.videoService.create(videoPayload).pipe(
            // If the video step fails, the dance was already created — roll it back so we don't
            // leave a video-less orphan that a retry would duplicate.
            catchError(err => {
              this.danceService.delete(dance.id).subscribe({ error: () => {} });
              return throwError(() => err);
            }),
            // setStatus is idempotent — the server may have already marked the dance
            // In Progress when the personal video was created, and this must not undo it.
            switchMap(() => this.danceService.setStatus(dance.id, 'inprogress'))
          );
        }
        return this.danceService.setStatus(dance.id, 'inprogress');
      })
    ).subscribe({
      next: () => {
        this.addingDance.set(false);
        this.showAddDance.set(false);
        this.newDanceName = '';
        this.newDanceDesc = '';
        this.newVideoTitle = '';
        this.newVideoUrl = '';
        this.setVideoTime = false;
        this.newVideoStartTime = '';
        this.newVideoEndTime = '';
        this.load();
      },
      error: () => {
        this.addDanceError.set('Failed to create dance. Please try again.');
        this.addingDance.set(false);
      }
    });
  }
}
