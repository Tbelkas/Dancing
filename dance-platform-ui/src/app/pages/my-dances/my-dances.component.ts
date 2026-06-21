import { Component, OnInit, AfterViewInit, ElementRef, HostListener, ViewChild, computed, effect, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';
import { parseVideoUrl, parseTimeSecs } from '../../core/utils/video-url.utils';
import { toggleSet } from '../../core/utils/set.utils';
import { ProfileService } from '../../core/services/profile.service';
import { StyleService } from '../../core/services/style.service';
import { DanceService, CreateDancePayload } from '../../core/services/dance.service';
import { VideoService, CreateVideoPayload } from '../../core/services/video.service';
import { RecentDancesService } from '../../core/services/recent-dances.service';
import { MyStyleWithDances } from '../../models/user.model';
import { Style } from '../../models/style.model';
import { Video } from '../../models/video.model';
import { VideoPlayerComponent } from '../../shared/components/video-player/video-player.component';

@Component({
  selector: 'app-my-dances',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, VideoPlayerComponent],
  templateUrl: './my-dances.component.html',
  styleUrls: ['./my-dances.component.css']
})
export class MyDancesComponent implements OnInit, AfterViewInit {
  private readonly SELECTED_STYLE_KEY = 'dp_mydances_style';
  private readonly EXPANDED_DANCE_KEY = 'dp_mydances_expanded';

  myStyles = signal<MyStyleWithDances[]>([]);
  allStyles = signal<Style[]>([]);
  selectedStyleId = signal<number | null>(null);
  loading = signal(true);
  showStylePicker = signal(false);

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

  readonly myStyleIds = computed(() => new Set(this.myStyles().map(ms => ms.styleId)));

  /** Upper bound of "Continue Learning" cards; the carousel scrolls through them. */
  private readonly CONTINUE_LIMIT = 20;
  private recThumbFailed = signal<Set<number>>(new Set());

  /** Ids the user has already learned, drawn from the live my-dances data. */
  private readonly learnedIds = computed(() =>
    new Set(this.myStyles().flatMap(ms => ms.dances).filter(d => d.status === 'learned').map(d => d.id))
  );

  /** Most-recently-opened dances the user hasn't learned yet — "pick up where you left off". */
  readonly continueLearning = computed(() => {
    const learned = this.learnedIds();
    return this.recentDances.recent()
      .filter(d => !d.learned && !learned.has(d.id))
      .slice(0, this.CONTINUE_LIMIT);
  });

  // Continue-learning carousel: the track scrolls horizontally; arrows show only
  // when it overflows and disable once you hit either end.
  @ViewChild('historyTrack') private historyTrack?: ElementRef<HTMLElement>;
  readonly historyOverflow = signal(false);
  readonly historyAtStart = signal(true);
  readonly historyAtEnd = signal(false);

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
    private recentDances: RecentDancesService
  ) {
    // The card list grows/shrinks as history loads or a card is dismissed — re-measure
    // the track after the DOM settles so the arrows reflect the new scrollable width.
    effect(() => {
      this.continueLearning();
      setTimeout(() => this.updateHistoryScrollState());
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
    this.recentDances.remove(danceId);
  }

  ngOnInit(): void {
    this.load();
    this.styleService.getAll().subscribe(s => this.allStyles.set(s));
  }

  load(): void {
    this.loading.set(true);
    this.profileService.getMyDances().subscribe({
      next: data => {
        this.myStyles.set(data);
        const exists = (id: number | null) => id != null && data.some(ms => ms.styleId === id);
        if (!exists(this.selectedStyleId())) {
          const stored = localStorage.getItem(this.SELECTED_STYLE_KEY);
          const storedId = stored ? Number(stored) : null;
          this.setSelectedStyle(
            exists(storedId) ? storedId : (data.length > 0 ? data[0].styleId : null)
          );
        }
        // Restore last expanded dance if it's in the current style's dances
        const storedExpanded = localStorage.getItem(this.EXPANDED_DANCE_KEY);
        const expandedId = storedExpanded ? Number(storedExpanded) : null;
        if (expandedId && data.flatMap(ms => ms.dances).some(d => d.id === expandedId)) {
          this.expandDance(expandedId);
        }
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
            switchMap(() => this.danceService.toggleInProgress(dance.id))
          );
        }
        return this.danceService.toggleInProgress(dance.id);
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
