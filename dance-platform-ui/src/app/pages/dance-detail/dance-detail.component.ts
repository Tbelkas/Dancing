import { Component, ElementRef, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { Title } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EMPTY, Observable } from 'rxjs';
import { switchMap, catchError } from 'rxjs/operators';
import { DancePathPipe } from '../../shared/pipes/dance-path.pipe';
import { DanceService, DanceStatus, statusFlags } from '../../core/services/dance.service';
import { VideoService, SegmentPayload, NotePayload } from '../../core/services/video.service';
import { StyleService } from '../../core/services/style.service';
import { MusicalStyleService } from '../../core/services/musical-style.service';
import { InstructorService } from '../../core/services/instructor.service';
import { AuthService } from '../../core/services/auth.service';
import { RoleService } from '../../core/services/role.service';
import { RecentDancesService } from '../../core/services/recent-dances.service';
import { PracticeTimerService } from '../../core/services/practice-timer.service';
import { ConfirmService } from '../../core/services/confirm.service';
import { ToastService } from '../../core/services/toast.service';
import { Dance } from '../../models/dance.model';
import { Video, VideoChapter, VideoNote, VideoSegment, viewCountBucket } from '../../models/video.model';
import { Style } from '../../models/style.model';
import { MusicalStyle } from '../../models/musical-style.model';
import { Instructor } from '../../models/instructor.model';
import { VideoPlayerComponent } from '../../shared/components/video-player/video-player.component';
import { AddVideoFormComponent } from '../../shared/components/add-video-form/add-video-form.component';
import { EditDanceFormComponent } from '../../shared/components/edit-dance-form/edit-dance-form.component';
import { EditVideoFormComponent } from '../../shared/components/edit-video-form/edit-video-form.component';
import { MoveVideoPickerComponent } from '../../shared/components/move-video-picker/move-video-picker.component';
import { DIFFICULTY_LEVELS } from '../../core/constants/dance.constants';
import { youtubeThumbUrl } from '../../core/utils/youtube-thumb.utils';
import { ThumbFallback } from '../../core/utils/thumb-fallback';

@Component({
  selector: 'app-dance-detail',
  standalone: true,
  // The admin/authoring forms are used only inside @defer blocks below, so Angular
  // code-splits them out of the eager bundle.
  imports: [CommonModule, RouterLink, VideoPlayerComponent, DancePathPipe,
    AddVideoFormComponent, EditDanceFormComponent, EditVideoFormComponent, MoveVideoPickerComponent],
  templateUrl: './dance-detail.component.html',
  styleUrls: ['./dance-detail.component.css']
})
export class DanceDetailComponent implements OnInit, OnDestroy {
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
  // The signed-in user's timestamped notes, keyed by video id.
  private personalNotes = signal<Map<number, VideoNote[]>>(new Map());
  recommended = signal<Dance[]>([]);
  private readonly recThumbs = new ThumbFallback();
  // Alphabetical neighbours within this dance's canonical style, for prev/next paging.
  prevDance = signal<Dance | null>(null);
  nextDance = signal<Dance | null>(null);
  readonly viewCountBucket = viewCountBucket;

  // Feedback
  actionError = signal('');

  // Open-state for the extracted authoring forms. Each is a @defer-loaded child that owns
  // its own field/submit state; the parent only toggles visibility and applies the child's
  // success events to its own signals (see the on*Updated / on*Moved / onVideoAdded handlers).
  showAddVideo = signal(false);
  showEditDance = signal(false);
  // Catalogs the edit-dance form needs (loaded once for admins in ngOnInit).
  allStyles = signal<Style[]>([]);
  allMusicalStyles = signal<MusicalStyle[]>([]);
  allInstructors = signal<Instructor[]>([]);
  // Which video's inline edit / move panel is open (null = none).
  editingVideoId = signal<number | null>(null);
  movingVideoId = signal<number | null>(null);

  // Admin: delete dance
  deletingDance = signal(false);

  // Per-video rating hover state: which video is being hovered, and at what star.
  hoverRating = signal(0);
  hoverVideoId = signal<number | null>(null);

  /** Video id from the ?v= deep link (history "Continue learning"), opened once the list loads. */
  private resumeVideoId: number | null = null;

  constructor(
    private host: ElementRef<HTMLElement>,
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
    private practiceTimer: PracticeTimerService,
    private confirmSvc: ConfirmService,
    private toast: ToastService,
    public auth: AuthService,
    public role: RoleService
  ) {}

  ngOnDestroy(): void {
    // Leaving the page ends watching; the session lives on (server-side buffer) for a return visit.
    this.practiceTimer.stop();
  }

  /** Player reported a play/pause transition — feed the practice clock for the current dance. */
  onPlayerPlaying(playing: boolean): void {
    const d = this.dance();
    if (!d || !this.auth.isAuthenticated()) return;
    this.practiceTimer.setActiveDance(d.id, this.selectedVideo()?.id ?? null);
    this.practiceTimer.setPlaying(playing);
  }

  ngOnInit(): void {
    // React to paramMap (not snapshot) so navigating between dances — e.g. via the
    // "More like this" cards, same route — reloads the page. URLs are either the
    // canonical /dances/{style}/{slug} or the legacy /dances/{slug-or-id}.
    // switchMap cancels an in-flight load when the user jumps to another dance, so a
    // slower earlier response can't land last and show the wrong dance under the new URL.
    this.route.paramMap.pipe(
      switchMap(pm => this.load(pm.get('style'), pm.get('slug') ?? ''))
    ).subscribe(d => this.onDanceLoaded(d));
    if (this.role.isAdmin()) {
      // Catalogs for the edit-dance form. (The move-video picker loads its own dance-name
      // list on demand, inside its child component.)
      this.styleService.getAll().subscribe(s => this.allStyles.set(s));
      this.musicalStyleService.getAll().subscribe(s => this.allMusicalStyles.set(s));
      this.instructorService.getAll().subscribe(i => this.allInstructors.set(i));
    }
  }

  /** Resets per-dance state and returns the (cancellable) dance request; errors are handled here so
   *  the outer switchMap stream stays alive for the next navigation. */
  private load(style: string | null, slug: string): Observable<Dance> {
    // Switching dances (same-route nav doesn't re-run ngOnDestroy) ends the current watch;
    // the server buffer keeps the session alive so the next dance continues it.
    this.practiceTimer.stop();
    // reset per-dance state for re-entry
    this.dance.set(null);
    this.notFound.set(false);
    this.videos.set([]);
    this.selectedVideo.set(null);
    this.chapters.set([]);
    this.personalLoops.set(new Map());
    this.personalNotes.set(new Map());
    this.recommended.set([]);
    this.showEditDance.set(false);
    this.movingVideoId.set(null);
    // The snapshot is already on the incoming route by the time paramMap emits.
    this.resumeVideoId = Number(this.route.snapshot.queryParamMap.get('v')) || null;

    const request$ = style
      ? this.danceService.getByStyleAndSlug(style, slug)
      : this.danceService.getByIdOrSlug(slug);

    return request$.pipe(
      catchError(err => {
        if (err?.status === 404) {
          this.notFound.set(true);
          this.title.setTitle('Dance not found · Dance Platform');
        } else {
          this.router.navigate(['/dances']);
        }
        return EMPTY;
      })
    );
  }

  private onDanceLoaded(d: Dance): void {
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
      // Guard against a stale response landing after the user already navigated away.
      if (this.dance()?.id !== d.id) return;
      this.videos.set(v);
      // A ?v= deep link resumes that exact video; otherwise a lone video opens itself.
      const resume = v.find(x => x.id === this.resumeVideoId);
      this.resumeVideoId = null;
      const open = resume ?? (v.length === 1 ? v[0] : null);
      if (open) {
        this.videoService.recordView(open.id).subscribe();
        this.revealVideo(open);
        if (resume && v.length > 1) this.scrollToVideo(open.id);
      }
    });
    this.danceService.getRecommended(d.id).subscribe(r => {
      if (this.dance()?.id === d.id) this.recommended.set(r);
    });
    this.loadNeighbors(d);
  }

  /**
   * Loads this dance's alphabetical prev/next neighbours within its canonical style for the
   * pager. The server resolves them directly (a dedicated /neighbors endpoint), replacing the
   * old approach of fetching up to 500 dances client-side and locating this one. The stale
   * guard drops a response that lands after the user has already navigated to another dance.
   */
  private loadNeighbors(d: Dance): void {
    this.prevDance.set(null);
    this.nextDance.set(null);
    this.danceService.getNeighbors(d.id).subscribe({
      next: n => {
        if (this.dance()?.id !== d.id) return;
        this.prevDance.set(n.prev);
        this.nextDance.set(n.next);
      },
      error: () => { /* pager simply doesn't render */ }
    });
  }

  /** Canonical URL for a dance: /dances/{styleSlug}/{slug}, or /dances/{slug} if it has no style. */
  private canonicalPath(d: Dance): string {
    return d.styleSlug ? `/dances/${d.styleSlug}/${d.slug}` : `/dances/${d.slug}`;
  }

  /** YouTube thumbnail for a recommended dance, or null if missing/failed to load. */
  recThumbnailUrl(dance: Dance): string | null {
    if (this.recThumbs.has(dance.id)) return null;
    return youtubeThumbUrl(dance.thumbnailVideoId, dance.thumbnailPlatform);
  }

  onRecThumbError(danceId: number): void {
    this.recThumbs.markFailed(danceId);
  }

  selectVideo(video: Video): void {
    if (this.selectedVideo()?.id === video.id) {
      this.selectedVideo.set(null);
      this.chapters.set([]);
      this.practiceTimer.stop();
      return;
    }
    this.videoService.recordView(video.id).subscribe();
    this.revealVideo(video);
  }

  // Resolve the sibling dances sharing this source video *before* mounting the
  // player: the YouTube player reads `chapters` at creation to decide whether to
  // bound playback at this dance's end, so the chips must be known up front.
  private revealVideo(video: Video): void {
    const d = this.dance();
    if (d) this.recentDances.setVideo(d.id, video.id);
    this.selectedVideo.set(null);
    this.chapters.set([]);
    this.loadPersonalLoops(video.id);
    this.loadPersonalNotes(video.id);
    this.videoService.getRelated(video.id).subscribe({
      next: ch => { this.chapters.set(ch); this.selectedVideo.set(video); },
      error: () => this.selectedVideo.set(video)
    });
  }

  /** Brings a deep-linked video's row into view, once the list has rendered. */
  private scrollToVideo(videoId: number): void {
    setTimeout(() => {
      this.host.nativeElement
        .querySelector(`[data-video-id="${videoId}"]`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
  async onDeletePersonalLoop(video: Video, loop: VideoSegment): Promise<void> {
    if (!await this.confirmSvc.ask(`Delete your loop "${loop.label}"?`, { title: 'Delete loop' })) return;
    this.videoService.deleteMyLoop(video.id, loop.id).subscribe({
      next: loops => {
        this.setPersonalLoops(video.id, loops);
        this.toast.success('Loop deleted.');
      },
      error: () => this.toast.error('Failed to delete your loop. Please try again.')
    });
  }

  /** Timestamped notes the signed-in user pinned to a given video (empty if none/anon). */
  personalNotesFor(videoId: number): VideoNote[] {
    return this.personalNotes().get(videoId) ?? [];
  }

  private setPersonalNotes(videoId: number, notes: VideoNote[]): void {
    this.personalNotes.update(m => new Map(m).set(videoId, notes));
  }

  private loadPersonalNotes(videoId: number): void {
    if (!this.auth.isAuthenticated()) return;
    this.videoService.getMyNotes(videoId).subscribe({
      next: notes => this.setPersonalNotes(videoId, notes),
      error: () => { /* notes are a nicety; ignore fetch failures */ }
    });
  }

  /** A signed-in user pinned a note to a moment in the video. */
  onSaveNote(video: Video, payload: NotePayload): void {
    this.videoService.addMyNote(video.id, payload).subscribe({
      next: notes => this.setPersonalNotes(video.id, notes),
      error: () => this.actionError.set('Failed to save your note. Please try again.')
    });
  }

  /** A signed-in user rewrote one of their own notes. */
  onUpdateNote(video: Video, payload: { id: number } & NotePayload): void {
    this.videoService.updateMyNote(video.id, payload.id, { timeSeconds: payload.timeSeconds, text: payload.text }).subscribe({
      next: notes => this.setPersonalNotes(video.id, notes),
      error: () => this.toast.error('Failed to update your note. Please try again.')
    });
  }

  /** A signed-in user removed one of their own notes. */
  async onDeleteNote(video: Video, note: VideoNote): Promise<void> {
    if (!await this.confirmSvc.ask('Delete this note?', { title: 'Delete note' })) return;
    this.videoService.deleteMyNote(video.id, note.id).subscribe({
      next: notes => {
        this.setPersonalNotes(video.id, notes);
        this.toast.success('Note deleted.');
      },
      error: () => this.toast.error('Failed to delete your note. Please try again.')
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
    const flags = statusFlags(status);
    const learnedDelta = (flags.isLearned ? 1 : 0) - (d.isLearned ? 1 : 0);

    this.dance.update(cur => cur ? {
      ...cur,
      ...flags,
      learnedCount: cur.learnedCount + learnedDelta
    } : cur);
    this.recentDances.setLearned(d.id, flags.isLearned);

    this.danceService.setStatus(d.id, status).subscribe({
      error: () => {
        this.dance.update(cur => cur ? { ...cur, ...snap } : cur);
        // Revert the carousel's learned flag too, or a failed save would wrongly drop the dance
        // from "Continue Learning" until a hard refresh.
        this.recentDances.setLearned(d.id, snap.isLearned);
        this.actionError.set('Couldn\'t save that. Check your connection and try again.');
      }
    });
  }

  // Rating is per video. Whether a given star should render filled: show the live
  // hover state for the video under the cursor, otherwise the user's saved rating.
  videoStarFilled(video: Video, star: number): boolean {
    const active = this.hoverVideoId() === video.id ? this.hoverRating() : 0;
    return star <= (active || video.userRating || 0);
  }

  onStarHover(video: Video, star: number): void {
    this.hoverVideoId.set(video.id);
    this.hoverRating.set(star);
  }

  onStarLeave(): void {
    this.hoverVideoId.set(null);
    this.hoverRating.set(0);
  }

  rateVideo(video: Video, rating: number): void {
    this.actionError.set('');
    // Optimistic: fill the star immediately, keeping the row in place (the 4–5★-first
    // ordering applies on the next load). Snapshot for revert if the request fails.
    const snapshot: Partial<Video> = {
      userRating: video.userRating,
      averageRating: video.averageRating,
      ratingCount: video.ratingCount
    };
    this.patchVideo(video.id, { userRating: rating });

    this.videoService.rate(video.id, rating).subscribe({
      next: updated => {
        // Reconcile with the server's authoritative figures (new average + count).
        this.patchVideo(updated.id, {
          userRating: updated.userRating,
          averageRating: updated.averageRating,
          ratingCount: updated.ratingCount
        });
        // The dance's community rating aggregates its videos — refresh the header figure.
        this.dance.update(cur => cur ? {
          ...cur,
          averageRating: this.aggregateRating(),
          ratingCount: this.aggregateRatingCount()
        } : cur);
      },
      error: () => {
        this.patchVideo(video.id, snapshot);
        this.actionError.set('Rating failed. Please log in again.');
      }
    });
  }

  /** Merge a partial update into a video wherever it's held (list + open player). */
  private patchVideo(videoId: number, patch: Partial<Video>): void {
    this.videos.update(list => list.map(v => v.id === videoId ? { ...v, ...patch } : v));
    const sel = this.selectedVideo();
    if (sel?.id === videoId) this.selectedVideo.set({ ...sel, ...patch });
  }

  private aggregateRatingCount(): number {
    return this.videos().reduce((sum, v) => sum + v.ratingCount, 0);
  }

  private aggregateRating(): number {
    const totalCount = this.aggregateRatingCount();
    if (totalCount === 0) return 0;
    const weighted = this.videos().reduce((sum, v) => sum + v.averageRating * v.ratingCount, 0);
    return weighted / totalCount;
  }

  // Add video (any authenticated user; non-admins always create personal videos)
  toggleAddVideo(): void {
    this.showAddVideo.update(v => !v);
  }

  /** AddVideoFormComponent created a video for this dance — append it and reflect the counts. */
  onVideoAdded(video: Video): void {
    this.videos.update(list => [...list, video]);
    // Adding a personal video auto-tracks the dance server-side; reflect it now.
    const nowTracked = this.isPersonalVideo(video);
    this.dance.update(d => d ? {
      ...d,
      videoCount: d.videoCount + 1,
      isInProgress: d.isInProgress || (nowTracked && !d.isLearned)
    } : d);
    this.showAddVideo.set(false);
  }

  /** A personal (private) video is visible only to its owner. */
  isPersonalVideo(video: Video): boolean {
    return video.ownerUserId != null;
  }

  /** Admins delete any video; a regular user may delete their own personal one. */
  canDeleteVideo(video: Video): boolean {
    return this.role.isAdmin() || (video.ownerUserId != null && video.ownerUserId === this.auth.currentUserId());
  }

  // Admin: edit video time/type/segments — toggling just opens/closes the inline editor;
  // the EditVideoFormComponent seeds itself from the video and owns the save.
  toggleEditVideoTime(video: Video): void {
    this.editingVideoId.update(id => id === video.id ? null : video.id);
  }

  /** EditVideoFormComponent saved changes — replace the video in the list and open player. */
  onVideoUpdated(updated: Video): void {
    this.videos.update(list => list.map(v => v.id === updated.id ? updated : v));
    if (this.selectedVideo()?.id === updated.id) this.selectedVideo.set(updated);
    this.editingVideoId.set(null);
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
  async onDeleteLoop(video: Video, segment: VideoSegment): Promise<void> {
    if (!await this.confirmSvc.ask(`Delete section "${segment.label}"? Everyone loses this section.`, { title: 'Delete section' })) return;
    this.videoService.deleteSegment(video.id, segment.id).subscribe({
      next: updated => {
        this.videos.update(list => list.map(v => v.id === updated.id ? updated : v));
        if (this.selectedVideo()?.id === updated.id) this.selectedVideo.set(updated);
        this.toast.success('Section deleted.');
      },
      error: () => this.toast.error('Failed to delete section. Please try again.')
    });
  }

  // Admin: move video to a different dance — toggling just opens/closes the picker panel;
  // MoveVideoPickerComponent owns the search and the move call.
  toggleMoveVideo(video: Video): void {
    this.movingVideoId.update(id => id === video.id ? null : video.id);
  }

  /** MoveVideoPickerComponent moved the video onto another dance — drop it from this page. */
  onVideoMoved(video: Video): void {
    this.videos.update(list => list.filter(v => v.id !== video.id));
    this.dance.update(d => d ? { ...d, videoCount: Math.max(0, d.videoCount - 1) } : d);
    if (this.selectedVideo()?.id === video.id) this.selectedVideo.set(null);
    this.movingVideoId.set(null);
    this.actionError.set('');
  }

  async deleteVideo(video: Video): Promise<void> {
    if (!await this.confirmSvc.ask(`Delete video "${video.title}"?`, { title: 'Delete video' })) return;
    this.videoService.delete(video.id).subscribe({
      next: () => {
        this.videos.update(list => list.filter(v => v.id !== video.id));
        this.dance.update(d => d ? { ...d, videoCount: Math.max(0, d.videoCount - 1) } : d);
        if (this.selectedVideo()?.id === video.id) this.selectedVideo.set(null);
        this.toast.success('Video deleted.');
      },
      error: () => this.toast.error('Failed to delete video.')
    });
  }

  // Admin: edit dance — toggling just opens/closes the form; EditDanceFormComponent seeds
  // itself from the current dance and the catalogs, and owns the save.
  toggleEditDance(): void {
    if (!this.dance()) return;
    this.showEditDance.update(v => !v);
  }

  /**
   * EditDanceFormComponent saved changes. The server returns a fresh Dance without the
   * viewer-specific flags, so reconcile it with the ones we already hold (favorite / learned /
   * counts), fix the URL if the slug changed, then close.
   */
  onDanceUpdated(updated: Dance): void {
    const d = this.dance();
    if (!d) return;
    this.dance.set({
      ...updated,
      isFavorite: d.isFavorite,
      isLearned: d.isLearned,
      isInProgress: d.isInProgress,
      favoriteCount: d.favoriteCount,
      learnedCount: d.learnedCount
    });
    if (updated.slug !== d.slug || updated.styleSlug !== d.styleSlug) {
      this.location.replaceState(this.canonicalPath(updated));
    }
    this.showEditDance.set(false);
  }

  async deleteDance(): Promise<void> {
    const d = this.dance();
    if (!d) return;
    const ok = await this.confirmSvc.ask(
      `Permanently delete "${d.name}" and all of its videos? This cannot be undone.`,
      { title: 'Delete dance', confirmLabel: 'Delete forever' }
    );
    if (!ok) return;
    this.deletingDance.set(true);
    this.danceService.delete(d.id).subscribe({
      next: () => {
        this.toast.success(`"${d.name}" deleted.`);
        this.router.navigate(['/dances']);
      },
      error: () => { this.toast.error('Failed to delete dance.'); this.deletingDance.set(false); }
    });
  }
}
