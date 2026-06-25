import { Component, OnInit, signal, WritableSignal } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';
import { DanceService, UpdateDancePayload, DanceStatus } from '../../core/services/dance.service';
import { VideoService, CreateVideoPayload, SegmentPayload } from '../../core/services/video.service';
import { StyleService } from '../../core/services/style.service';
import { MusicalStyleService } from '../../core/services/musical-style.service';
import { InstructorService } from '../../core/services/instructor.service';
import { AuthService } from '../../core/services/auth.service';
import { RoleService } from '../../core/services/role.service';
import { RecentDancesService } from '../../core/services/recent-dances.service';
import { Dance } from '../../models/dance.model';
import { Video, VideoChapter, VideoSegment, VideoType, viewCountBucket } from '../../models/video.model';
import { Style } from '../../models/style.model';
import { MusicalStyle } from '../../models/musical-style.model';
import { Instructor } from '../../models/instructor.model';
import { VideoPlayerComponent } from '../../shared/components/video-player/video-player.component';
import { DIFFICULTY_LEVELS } from '../../core/constants/dance.constants';
import { parseVideoUrl, parseTimeSecs, formatTimeSecs } from '../../core/utils/video-url.utils';
const DEFAULT_SEGMENT_LABELS = ['Theory', 'Steps', 'Practice'];

interface SegmentRow {
  label: string;
  start: string;
  end: string;
}

@Component({
  selector: 'app-dance-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, VideoPlayerComponent, DancePathPipe],
  templateUrl: './dance-detail.component.html',
  styleUrls: ['./dance-detail.component.css']
})
export class DanceDetailComponent implements OnInit {
  readonly difficulties = DIFFICULTY_LEVELS;
  readonly stars = [1, 2, 3, 4, 5];

  dance = signal<Dance | null>(null);
  notFound = signal(false);
  videos = signal<Video[]>([]);
  selectedVideo = signal<Video | null>(null);
  // Other dances sharing the selected video, for in-place jump chips in the player.
  chapters = signal<VideoChapter[]>([]);
  // The signed-in user's private loops, keyed by video id.
  private personalLoops = signal<Map<number, VideoSegment[]>>(new Map());
  recommended = signal<Dance[]>([]);
  private recThumbFailed = signal<Set<number>>(new Set());
  readonly viewCountBucket = viewCountBucket;

  // Feedback
  actionError = signal('');

  // Admin: add video form
  showAddVideo = signal(false);
  newVideoTitle = '';
  newVideoUrl = '';
  newVideoDesc = '';
  newVideoType: VideoType = 'steps';
  newVideoSegments: SegmentRow[] = [];
  addingVideo = signal(false);
  addVideoError = signal('');

  // Admin: edit dance form
  showEditDance = signal(false);
  editName = '';
  editDescription = '';
  editDifficulty = 'None';
  editStyleIds: number[] = [];
  editMusicalStyleIds: number[] = [];
  editInstructorIds: number[] = [];
  allStyles = signal<Style[]>([]);
  allMusicalStyles = signal<MusicalStyle[]>([]);
  allInstructors = signal<Instructor[]>([]);
  savingDance = signal(false);
  editDanceError = signal('');

  // Admin: edit video time/type/segments
  editingVideoId = signal<number | null>(null);
  editVideoStartTime = '';
  editVideoEndTime = '';
  editVideoType: VideoType = 'steps';
  editVideoSegments: SegmentRow[] = [];
  savingVideoTime = signal(false);
  editVideoTimeError = signal('');

  // Admin: delete dance
  deletingDance = signal(false);

  // Rating hover state
  hoverRating = signal(0);

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private location: Location,
    private title: Title,
    private danceService: DanceService,
    private videoService: VideoService,
    private styleService: StyleService,
    private musicalStyleService: MusicalStyleService,
    private instructorService: InstructorService,
    private recentDances: RecentDancesService,
    public auth: AuthService,
    public role: RoleService
  ) {}

  ngOnInit(): void {
    // React to paramMap (not snapshot) so navigating between dances — e.g. via the
    // "More like this" cards, same route — reloads the page. URLs are either the
    // canonical /dances/{style}/{slug} or the legacy /dances/{slug-or-id}.
    this.route.paramMap.subscribe(pm => this.load(pm.get('style'), pm.get('slug') ?? ''));
    if (this.role.isAdmin()) {
      this.styleService.getAll().subscribe(s => this.allStyles.set(s));
      this.musicalStyleService.getAll().subscribe(s => this.allMusicalStyles.set(s));
      this.instructorService.getAll().subscribe(i => this.allInstructors.set(i));
    }
  }

  private load(style: string | null, slug: string): void {
    // reset per-dance state for re-entry
    this.dance.set(null);
    this.notFound.set(false);
    this.videos.set([]);
    this.selectedVideo.set(null);
    this.chapters.set([]);
    this.personalLoops.set(new Map());
    this.recommended.set([]);
    this.showEditDance.set(false);

    const request$ = style
      ? this.danceService.getByStyleAndSlug(style, slug)
      : this.danceService.getByIdOrSlug(slug);

    request$.subscribe({
      next: d => {
        this.dance.set(d);
        this.recentDances.record(d);
        this.title.setTitle(`${d.name} · Dance Platform`);
        // Normalise the URL to the canonical /dances/{style}/{slug} form (handles legacy
        // numeric ids and single-segment slug links) without triggering a reload.
        const canonical = this.canonicalPath(d);
        if (this.location.path().split('?')[0] !== canonical) {
          this.location.replaceState(canonical);
        }
        this.videoService.getByDance(d.id).subscribe(v => {
          this.videos.set(v);
          if (v.length === 1) {
            this.videoService.recordView(v[0].id).subscribe();
            this.revealVideo(v[0]);
          }
        });
        this.danceService.getRecommended(d.id).subscribe(r => this.recommended.set(r));
      },
      error: err => {
        if (err?.status === 404) {
          this.notFound.set(true);
          this.title.setTitle('Dance not found · Dance Platform');
        } else {
          this.router.navigate(['/dances']);
        }
      }
    });
  }

  /** Canonical URL for a dance: /dances/{styleSlug}/{slug}, or /dances/{slug} if it has no style. */
  private canonicalPath(d: Dance): string {
    return d.styleSlug ? `/dances/${d.styleSlug}/${d.slug}` : `/dances/${d.slug}`;
  }

  /** YouTube thumbnail for a recommended dance, or null if missing/failed to load. */
  recThumbnailUrl(dance: Dance): string | null {
    if (this.recThumbFailed().has(dance.id)) return null;
    if (dance.thumbnailVideoId && dance.thumbnailPlatform === 'youtube') {
      return `https://i.ytimg.com/vi/${dance.thumbnailVideoId}/hqdefault.jpg`;
    }
    return null;
  }

  onRecThumbError(danceId: number): void {
    this.recThumbFailed.update(set => new Set(set).add(danceId));
  }

  selectVideo(video: Video): void {
    if (this.selectedVideo()?.id === video.id) {
      this.selectedVideo.set(null);
      this.chapters.set([]);
      return;
    }
    this.videoService.recordView(video.id).subscribe();
    this.revealVideo(video);
  }

  // Resolve the sibling dances sharing this source video *before* mounting the
  // player: the YouTube player reads `chapters` at creation to decide whether to
  // bound playback at this dance's end, so the chips must be known up front.
  private revealVideo(video: Video): void {
    this.selectedVideo.set(null);
    this.chapters.set([]);
    this.loadPersonalLoops(video.id);
    this.videoService.getRelated(video.id).subscribe({
      next: ch => { this.chapters.set(ch); this.selectedVideo.set(video); },
      error: () => this.selectedVideo.set(video)
    });
  }

  /** Personal loops the signed-in user saved for a given video (empty if none/anon). */
  personalLoopsFor(videoId: number): VideoSegment[] {
    return this.personalLoops().get(videoId) ?? [];
  }

  private setPersonalLoops(videoId: number, loops: VideoSegment[]): void {
    this.personalLoops.update(m => new Map(m).set(videoId, loops));
  }

  private loadPersonalLoops(videoId: number): void {
    if (!this.auth.isAuthenticated()) return;
    this.videoService.getMyLoops(videoId).subscribe({
      next: loops => this.setPersonalLoops(videoId, loops),
      error: () => { /* loops are a nicety; ignore fetch failures */ }
    });
  }

  /** A signed-in user saved a named loop region to their own account. */
  onSavePersonalLoop(video: Video, payload: SegmentPayload): void {
    this.videoService.addMyLoop(video.id, payload).subscribe({
      next: loops => this.setPersonalLoops(video.id, loops),
      error: () => this.actionError.set('Failed to save your loop. Please try again.')
    });
  }

  /** A signed-in user removed one of their own saved loops. */
  onDeletePersonalLoop(video: Video, loop: VideoSegment): void {
    if (!confirm(`Delete your loop "${loop.label}"?`)) return;
    this.videoService.deleteMyLoop(video.id, loop.id).subscribe({
      next: loops => this.setPersonalLoops(video.id, loops),
      error: () => this.actionError.set('Failed to delete your loop. Please try again.')
    });
  }

  toggleFavorite(): void {
    const d = this.dance();
    if (!d) return;
    this.actionError.set('');
    this.danceService.toggleFavorite(d.id).subscribe({
      next: res => this.dance.update(cur => cur ? {
        ...cur,
        isFavorite: res.isFavorite,
        favoriteCount: cur.favoriteCount + (res.isFavorite ? 1 : -1)
      } : cur),
      error: () => this.actionError.set('Action failed. Please log in again.')
    });
  }

  // Learned / In progress are a mutually-exclusive single-select status, set in one
  // atomic server call. The UI flips immediately (optimistic) and reverts on failure.

  toggleLearned(): void {
    const d = this.dance();
    if (!d) return;
    this.setStatus(d.isLearned ? 'notstarted' : 'learned');
  }

  toggleInProgress(): void {
    const d = this.dance();
    if (!d) return;
    this.setStatus(d.isInProgress ? 'notstarted' : 'inprogress');
  }

  private setStatus(status: DanceStatus): void {
    const d = this.dance();
    if (!d) return;
    this.actionError.set('');
    const snap = { isLearned: d.isLearned, isInProgress: d.isInProgress, learnedCount: d.learnedCount };
    const willLearn = status === 'learned';
    const learnedDelta = (willLearn ? 1 : 0) - (d.isLearned ? 1 : 0);

    this.dance.update(cur => cur ? {
      ...cur,
      isLearned: willLearn,
      isInProgress: status === 'inprogress',
      learnedCount: cur.learnedCount + learnedDelta
    } : cur);
    this.recentDances.setLearned(d.id, willLearn);

    this.danceService.setStatus(d.id, status).subscribe({
      error: () => {
        this.dance.update(cur => cur ? { ...cur, ...snap } : cur);
        this.actionError.set('Couldn\'t save that. Check your connection and try again.');
      }
    });
  }

  // Rating
  rateDance(rating: number): void {
    const d = this.dance();
    if (!d) return;
    this.danceService.rate(d.id, rating).subscribe({
      next: updated => this.dance.update(cur => cur ? {
        ...cur,
        userRating: updated.userRating,
        averageRating: updated.averageRating,
        ratingCount: updated.ratingCount
      } : cur),
      error: () => this.actionError.set('Rating failed. Please log in again.')
    });
  }

  // Admin: add video
  toggleAddVideo(): void {
    this.showAddVideo.update(v => !v);
    this.addVideoError.set('');
    this.newVideoTitle = '';
    this.newVideoUrl = '';
    this.newVideoDesc = '';
    this.newVideoType = 'steps';
    this.newVideoSegments = [];
  }

  private defaultSegmentRows(): SegmentRow[] {
    return DEFAULT_SEGMENT_LABELS.map(label => ({ label, start: '', end: '' }));
  }

  onNewVideoTypeChange(): void {
    if (this.newVideoType === 'tutorial' && this.newVideoSegments.length === 0)
      this.newVideoSegments = this.defaultSegmentRows();
  }

  onEditVideoTypeChange(): void {
    if (this.editVideoType === 'tutorial' && this.editVideoSegments.length === 0)
      this.editVideoSegments = this.defaultSegmentRows();
  }

  addSegmentRow(rows: SegmentRow[]): void {
    rows.push({ label: '', start: '', end: '' });
  }

  removeSegmentRow(rows: SegmentRow[], index: number): void {
    rows.splice(index, 1);
  }

  /** Converts editor rows to API payload; returns null (and sets the given error) on invalid input. */
  private buildSegments(videoType: VideoType, rows: SegmentRow[], error: WritableSignal<string>): SegmentPayload[] | null {
    if (videoType !== 'tutorial') return [];
    const segments: SegmentPayload[] = [];
    for (const row of rows) {
      if (!row.label.trim() && !row.start.trim()) continue; // skip empty rows
      const startTime = parseTimeSecs(row.start);
      if (!row.label.trim() || startTime === undefined) {
        error.set('Each section needs a label and a start time (m:ss or seconds).');
        return null;
      }
      segments.push({ label: row.label.trim(), startTime, endTime: parseTimeSecs(row.end) });
    }
    return segments;
  }


  submitAddVideo(): void {
    const danceId = this.dance()?.id;
    if (!danceId) return;
    if (!this.newVideoTitle.trim()) { this.addVideoError.set('Title is required.'); return; }
    if (!this.newVideoUrl.trim()) { this.addVideoError.set('Video URL or ID is required.'); return; }

    const parsed = parseVideoUrl(this.newVideoUrl);
    if (!parsed) { this.addVideoError.set('Unrecognized URL. Paste a YouTube, TikTok, or Instagram link.'); return; }

    const segments = this.buildSegments(this.newVideoType, this.newVideoSegments, this.addVideoError);
    if (segments === null) return;

    const payload: CreateVideoPayload = {
      title: this.newVideoTitle.trim(),
      videoId: parsed.videoId,
      platform: parsed.platform,
      videoType: this.newVideoType,
      description: this.newVideoDesc.trim() || undefined,
      danceId,
      segments
    };

    this.addingVideo.set(true);
    this.addVideoError.set('');
    this.videoService.create(payload).subscribe({
      next: video => {
        this.videos.update(list => [...list, video]);
        this.dance.update(d => d ? { ...d, videoCount: d.videoCount + 1 } : d);
        this.showAddVideo.set(false);
        this.addingVideo.set(false);
        this.newVideoTitle = '';
        this.newVideoUrl = '';
        this.newVideoDesc = '';
        this.newVideoType = 'steps';
        this.newVideoSegments = [];
      },
      error: () => { this.addVideoError.set('Failed to add video.'); this.addingVideo.set(false); }
    });
  }

  // Admin: edit video time/type/segments
  toggleEditVideoTime(video: Video): void {
    if (this.editingVideoId() === video.id) {
      this.editingVideoId.set(null);
      return;
    }
    this.editVideoStartTime = video.startTime != null ? formatTimeSecs(video.startTime) : '';
    this.editVideoEndTime = video.endTime != null ? formatTimeSecs(video.endTime) : '';
    this.editVideoType = video.videoType === 'tutorial' ? 'tutorial' : 'steps';
    this.editVideoSegments = video.segments.map(s => ({
      label: s.label,
      start: formatTimeSecs(s.startTime),
      end: s.endTime != null ? formatTimeSecs(s.endTime) : ''
    }));
    this.editVideoTimeError.set('');
    this.editingVideoId.set(video.id);
  }

  submitEditVideoTime(video: Video): void {
    const startTime = parseTimeSecs(this.editVideoStartTime);
    const endTime = parseTimeSecs(this.editVideoEndTime);
    const segments = this.buildSegments(this.editVideoType, this.editVideoSegments, this.editVideoTimeError);
    if (segments === null) return;
    // The form only edits sections for tutorials; for other types leave segments
    // untouched so admin-saved loops aren't wiped when just changing the time.
    const updateSegments = this.editVideoType === 'tutorial';
    this.savingVideoTime.set(true);
    this.editVideoTimeError.set('');
    this.videoService.update(video.id, {
      updateTimes: true,
      startTime,
      endTime,
      videoType: this.editVideoType,
      updateSegments,
      segments
    }).subscribe({
      next: updated => {
        this.videos.update(list => list.map(v => v.id === updated.id ? updated : v));
        if (this.selectedVideo()?.id === updated.id) this.selectedVideo.set(updated);
        this.editingVideoId.set(null);
        this.savingVideoTime.set(false);
      },
      error: () => { this.editVideoTimeError.set('Failed to save. Please try again.'); this.savingVideoTime.set(false); }
    });
  }

  /** Admin saved a named loop region in the player — persist it as a section. */
  onSaveLoop(video: Video, payload: SegmentPayload): void {
    this.videoService.addSegment(video.id, payload).subscribe({
      next: updated => {
        this.videos.update(list => list.map(v => v.id === updated.id ? updated : v));
        if (this.selectedVideo()?.id === updated.id) this.selectedVideo.set(updated);
      },
      error: () => this.actionError.set('Failed to save loop. Please try again.')
    });
  }

  /** Admin removed a saved loop/section from the player. */
  onDeleteLoop(video: Video, segment: VideoSegment): void {
    if (!confirm(`Delete section "${segment.label}"?`)) return;
    this.videoService.deleteSegment(video.id, segment.id).subscribe({
      next: updated => {
        this.videos.update(list => list.map(v => v.id === updated.id ? updated : v));
        if (this.selectedVideo()?.id === updated.id) this.selectedVideo.set(updated);
      },
      error: () => this.actionError.set('Failed to delete section. Please try again.')
    });
  }

  deleteVideo(video: Video): void {
    if (!confirm(`Delete video "${video.title}"?`)) return;
    this.videoService.delete(video.id).subscribe({
      next: () => {
        this.videos.update(list => list.filter(v => v.id !== video.id));
        this.dance.update(d => d ? { ...d, videoCount: d.videoCount - 1 } : d);
        if (this.selectedVideo()?.id === video.id) this.selectedVideo.set(null);
      },
      error: () => alert('Failed to delete video.')
    });
  }

  // Admin: edit dance
  toggleEditDance(): void {
    const d = this.dance();
    if (!d) return;
    if (this.showEditDance()) {
      this.showEditDance.set(false);
      return;
    }
    this.editName = d.name;
    this.editDescription = d.description ?? '';
    this.editDifficulty = d.difficulty;
    this.editStyleIds = this.allStyles()
      .filter(s => d.styles.includes(s.name))
      .map(s => s.id);
    this.editMusicalStyleIds = this.allMusicalStyles()
      .filter(s => d.musicalStyles.includes(s.name))
      .map(s => s.id);
    this.editInstructorIds = this.allInstructors()
      .filter(i => d.instructors.includes(i.name))
      .map(i => i.id);
    this.editDanceError.set('');
    this.showEditDance.set(true);
  }

  private toggleId(arr: number[], id: number): number[] {
    return arr.includes(id) ? arr.filter(x => x !== id) : [...arr, id];
  }

  toggleEditStyleId(id: number): void { this.editStyleIds = this.toggleId(this.editStyleIds, id); }
  toggleEditMusicalStyleId(id: number): void { this.editMusicalStyleIds = this.toggleId(this.editMusicalStyleIds, id); }
  toggleEditInstructorId(id: number): void { this.editInstructorIds = this.toggleId(this.editInstructorIds, id); }

  submitEditDance(): void {
    if (!this.editName.trim()) { this.editDanceError.set('Name is required.'); return; }
    const d = this.dance();
    if (!d) return;
    const payload: UpdateDancePayload = {
      name: this.editName.trim(),
      description: this.editDescription.trim() || undefined,
      difficulty: this.editDifficulty,
      styleIds: this.editStyleIds,
      musicalStyleIds: this.editMusicalStyleIds,
      instructorIds: this.editInstructorIds
    };
    this.savingDance.set(true);
    this.editDanceError.set('');
    this.danceService.update(d.id, payload).subscribe({
      next: updated => {
        this.dance.set({
          ...updated,
          isFavorite: d.isFavorite,
          isLearned: d.isLearned,
          isInProgress: d.isInProgress,
          favoriteCount: d.favoriteCount,
          learnedCount: d.learnedCount,
          userRating: d.userRating
        });
        if (updated.slug !== d.slug || updated.styleSlug !== d.styleSlug) {
          this.location.replaceState(this.canonicalPath(updated));
        }
        this.showEditDance.set(false);
        this.savingDance.set(false);
      },
      error: () => { this.editDanceError.set('Failed to save changes.'); this.savingDance.set(false); }
    });
  }

  deleteDance(): void {
    const d = this.dance();
    if (!d || !confirm(`Permanently delete "${d.name}"? This cannot be undone.`)) return;
    this.deletingDance.set(true);
    this.danceService.delete(d.id).subscribe({
      next: () => this.router.navigate(['/dances']),
      error: () => { alert('Failed to delete dance.'); this.deletingDance.set(false); }
    });
  }
}
