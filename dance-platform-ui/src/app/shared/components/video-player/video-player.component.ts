import { Component, Input, Output, EventEmitter, OnInit, AfterViewInit, OnDestroy, ElementRef, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TrustUrlPipe } from '../../pipes/trust-url.pipe';
import { VideoSegment, VideoChapter, VideoNote } from '../../../models/video.model';
import { ViewerPrefsService } from '../../../core/services/viewer-prefs.service';
import { PlayerBaseComponent } from '../player-base';
import { CameraPaneComponent } from '../camera-pane/camera-pane.component';

@Component({
  selector: 'app-video-player',
  standalone: true,
  imports: [CommonModule, FormsModule, TrustUrlPipe, CameraPaneComponent],
  templateUrl: './video-player.component.html',
  styleUrls: ['./video-player.component.css']
})
export class VideoPlayerComponent extends PlayerBaseComponent implements OnInit, AfterViewInit, OnDestroy {
  @Input({ required: true }) videoId!: string;
  @Input() platform: string = 'youtube';
  @Input() startTime?: number;
  @Input() endTime?: number;
  @Input() segments: VideoSegment[] = [];
  /** Other dances cut from this same source video; includes the one being shown. */
  @Input() chapters: VideoChapter[] = [];
  /** Video row id of the dance currently on the page — used to highlight its chip. */
  @Input() activeVideoId?: number;
  /** Admins can name and persist the current loop region as a global section. */
  @Input() canSaveLoops = false;
  /** This user's private loops for the video; shown alongside the global sections. */
  @Input() personalLoops: VideoSegment[] = [];
  /** Any signed-in user can save the current region as a personal (private) loop. */
  @Input() canSavePersonal = false;
  /** This user's timestamped notes on the video; markers on the beta seek bar + a list below. */
  @Input() personalNotes: VideoNote[] = [];
  /** Any signed-in user can pin notes to moments in the video. */
  @Input() canTakeNotes = false;
  // saveLoop/deleteLoop (inherited): the admin-scoped global sections on this player.
  /** Emits the current loop region when the user saves it to their own account. */
  @Output() savePersonalLoop = new EventEmitter<{ label: string; startTime: number; endTime: number }>();
  /** Emits a personal loop the user wants removed; the parent deletes it. */
  @Output() deletePersonalLoop = new EventEmitter<VideoSegment>();
  /** Emits a new timestamped note; the parent persists it. */
  @Output() saveNote = new EventEmitter<{ timeSeconds: number; text: string }>();
  /** Emits a rewritten note (id + new time/text); the parent persists it. */
  @Output() updateNote = new EventEmitter<{ id: number; timeSeconds: number; text: string }>();
  /** Emits a note the user wants removed; the parent deletes it. */
  @Output() deleteNote = new EventEmitter<VideoNote>();
  @ViewChild('playerContainer', { static: false }) playerContainer?: ElementRef;
  @ViewChild('tiktokFrame', { static: false }) tiktokFrame?: ElementRef<HTMLIFrameElement>;
  @ViewChild('mediaEl', { static: false }) mediaEl?: ElementRef<HTMLElement>;

  constructor(private viewerPrefs: ViewerPrefsService) { super(); }

  activeSegmentId = signal<number | null>(null);
  activePersonalLoopId = signal<number | null>(null);
  loopSegmentId = signal<number | null>(null);
  activeChapterId = signal<number | null>(null);
  chaptersExpanded = signal(false);

  /** Notes fold away behind a toolbar toggle alongside the inherited Loop panel;
   *  the toggle carries the note count, so nothing is hidden, only folded. */
  notesOpen = signal(false);

  /** "Dance Platform video viewer (beta)": hide YouTube's controls and drive the
   *  embed through our own bar. Read once at init — the pref is set on the profile
   *  page, so a player never flips chrome mid-life. YouTube only: TikTok/Instagram
   *  embeds can't hand over their controls. */
  betaChrome = false;

  /** Only worth showing the jump row when the source video holds more than one dance. */
  get hasChapters(): boolean { return this.chapters.length > 1; }

  // --- Personal notes: draft state for the add row and the inline editor. ---
  noteDraftText = '';
  /** Timestamp frozen when the user starts writing, so the note pins the moment
   *  they reacted to, not wherever playback has drifted to by the time they save. */
  noteDraftTime = signal<number | null>(null);
  editingNoteId = signal<number | null>(null);
  editNoteText = '';
  editNoteTime = 0;

  get loopableSegments(): VideoSegment[] {
    return this.segments.filter(s => s.endTime != null);
  }

  get isYouTube(): boolean { return this.platform === 'youtube'; }
  get isTikTok(): boolean { return this.platform === 'tiktok'; }
  get isInstagram(): boolean { return this.platform === 'instagram'; }

  get embedUrl(): string {
    if (this.isTikTok) {
      return `https://www.tiktok.com/player/v1/${this.videoId}?music_info=0&description=0&rel=0&native_context_menu=0&closed_caption=0`;
    }
    if (this.isInstagram) return `https://www.instagram.com/p/${this.videoId}/embed/`;
    return '';
  }

  /** Keyboard shortcuts go to the player the user touched (or played) last, so
   *  pages that render several players don't all react to one keypress. */
  private static activeInstance: VideoPlayerComponent | null = null;

  private player: YT.Player | null = null;
  private repeatInterval: ReturnType<typeof setInterval> | null = null;
  /** Drives the beta chrome's seek bar — the iframe API has no timeupdate event. */
  private chromeTickInterval: ReturnType<typeof setInterval> | null = null;
  private durationPollInterval: ReturnType<typeof setInterval> | null = null;
  private tiktokCurrentTime = 0;
  private hasRealDuration = false;
  private regionInitialised = false;
  // `destroyed` (inherited) guards the deferred iframe-API callback from creating a
  // player, and the camera restore from claiming one, after ngOnDestroy.
  private lastPlayingEmit = false;
  private tiktokStallHandle: ReturnType<typeof setTimeout> | null = null;

  /** Emit play-state transitions only (parent dedupes anyway, but this keeps the stream clean). */
  private emitPlaying(playing: boolean): void {
    if (playing) VideoPlayerComponent.activeInstance = this;
    this.playing.set(playing);
    if (playing === this.lastPlayingEmit) return;
    this.lastPlayingEmit = playing;
    this.playingChange.emit(playing);
  }

  /** Shortcuts only reach the player the user touched last. */
  protected override canHandleKey(): boolean {
    return VideoPlayerComponent.activeInstance === this;
  }

  /** Only the YouTube embed exposes a controllable transport (TikTok/Instagram don't). */
  protected override shouldSkipTransportKeys(_targetTag: string): boolean {
    return !this.isYouTube;
  }

  protected override rateKeysEnabled(): boolean {
    return this.isYouTube;
  }

  override togglePlay(): void {
    if (!this.player || !window.YT) return;
    if (this.player.getPlayerState() === window.YT.PlayerState.PLAYING) {
      this.player.pauseVideo();
    } else {
      this.player.playVideo();
    }
  }

  protected override seekBy(deltaSeconds: number): void {
    if (!this.player) return;
    const t = Math.max(0, (this.player.getCurrentTime() ?? 0) + deltaSeconds);
    this.player.seekTo(t, true);
  }

  protected override seekAndPlay(seconds: number): void {
    if (this.isYouTube) {
      this.seekToTime(seconds);
      this.player?.playVideo();
    } else if (this.isTikTok) {
      this.tiktokCurrentTime = seconds;
      this.tiktokPost({ type: 'seekTo', value: seconds });
      this.tiktokPost({ type: 'play' });
    }
  }

  protected override mediaFrame(): HTMLElement | null {
    return this.mediaEl?.nativeElement ?? null;
  }

  override toggleMirror(): void {
    VideoPlayerComponent.activeInstance = this;
    super.toggleMirror();
  }

  /** Clicking a player's camera button also makes it the target of the shortcut keys. */
  override toggleCamera(): void {
    VideoPlayerComponent.activeInstance = this;
    super.toggleCamera();
  }

  private readonly tiktokMessageHandler = (event: MessageEvent) => {
    // TikTok may emit events as plain objects or as JSON strings
    let data: any;
    try {
      data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
    } catch {
      return;
    }
    if (!data?.['x-tiktok-player']) return;
    const type: string = data.type;
    const value: any = data.value;

    if (type === 'onPlayerReady') {
      const defaultDur = this.endTime ? this.endTime + 10 : 60;
      this.videoDuration.set(defaultDur);
      this.repeatStart = this.startTime ?? 0;
      this.repeatEnd = this.endTime ?? defaultDur;
      if (this.startTime) this.tiktokPost({ type: 'seekTo', value: this.startTime });
      if (this.repeating()) {
        // Clear any interval started before the player was ready, then start fresh.
        this.clearRepeat();
        this.startLoop();
      }
    }

    if (type === 'onCurrentTime') {
      this.tiktokCurrentTime = value as number;
      // TikTok has no clean play/pause event, so treat a flow of time updates as "playing"
      // and fall back to paused when they stall.
      this.emitPlaying(true);
      if (this.tiktokStallHandle) clearTimeout(this.tiktokStallHandle);
      this.tiktokStallHandle = setTimeout(() => this.emitPlaying(false), 1500);
      // Expand duration estimate as we see the video play further
      if (value > this.videoDuration() - 2) {
        const newDur = Math.ceil(value) + 5;
        this.videoDuration.set(newDur);
        if (!this.repeating()) this.repeatEnd = newDur;
      }
    }

    if (type === 'onStateChange' && value === 0) {
      // Video ended — stop the practice clock and lock in actual duration
      if (this.tiktokStallHandle) clearTimeout(this.tiktokStallHandle);
      this.emitPlaying(false);
      const dur = Math.ceil(this.tiktokCurrentTime);
      if (dur > 0) {
        this.videoDuration.set(dur);
        if (!this.repeating()) this.repeatEnd = Math.min(this.repeatEnd, dur);
      }
    }
  };

  ngOnInit(): void {
    this.betaChrome = this.isYouTube && this.viewerPrefs.betaViewer();
    if (this.betaChrome) document.addEventListener('fullscreenchange', this.fullscreenHandler);
    this.activeChapterId.set(this.activeVideoId ?? null);
    // Short lists open by default; long ones (some videos hold dozens of dances)
    // start collapsed so they don't bury the player controls.
    this.chaptersExpanded.set(this.chapters.length > 0 && this.chapters.length <= 6);
    this.restorePlayerPrefs();
    VideoPlayerComponent.activeInstance = this;
    document.addEventListener('keydown', this.keydownHandler);
    void this.restoreCamera();
    if (this.isTikTok) {
      const defaultDur = this.endTime ? this.endTime + 10 : 60;
      this.videoDuration.set(defaultDur);
      this.repeatStart = this.startTime ?? 0;
      this.repeatEnd = this.endTime ?? defaultDur;
      window.addEventListener('message', this.tiktokMessageHandler);
    }
  }

  ngAfterViewInit(): void {
    if (!this.isYouTube || typeof window === 'undefined') return;

    if (window.YT?.Player) {
      this.createPlayer();
    } else {
      if (!document.querySelector('script[src*="youtube.com/iframe_api"]')) {
        const tag = document.createElement('script');
        tag.src = 'https://www.youtube.com/iframe_api';
        document.body.appendChild(tag);
      }
      // Chain rather than overwrite: if several players mount before the API script
      // loads, each previous callback still runs, so every player gets created.
      const prev = (window as any).onYouTubeIframeAPIReady as (() => void) | undefined;
      (window as any).onYouTubeIframeAPIReady = () => {
        prev?.();
        this.createPlayer();
      };
    }
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    this.clearRepeat();
    this.clearDurationPoll();
    if (this.chromeTickInterval) clearInterval(this.chromeTickInterval);
    document.removeEventListener('fullscreenchange', this.fullscreenHandler);
    if (this.tiktokStallHandle) clearTimeout(this.tiktokStallHandle);
    this.clearFlashTimeout();
    document.removeEventListener('keydown', this.keydownHandler);
    // Frees the device: a stream left running keeps the camera light on after navigation.
    this.camera.release(this);
    if (VideoPlayerComponent.activeInstance === this) VideoPlayerComponent.activeInstance = null;
    this.emitPlaying(false);
    this.player?.destroy();
    window.removeEventListener('message', this.tiktokMessageHandler);
  }

  /** Seek the embedded player to another dance in the same video and arm its loop
   *  region, without leaving the page. */
  jumpToChapter(chapter: VideoChapter): void {
    this.activeChapterId.set(chapter.id);
    const start = chapter.startTime ?? 0;
    this.repeatStart = start;
    if (chapter.endTime != null) {
      this.repeatEnd = chapter.endTime;
      this.loopSegmentId.set(null);
    }
    if (this.isYouTube) {
      this.player?.seekTo(start, true);
      this.player?.playVideo();
    } else if (this.isTikTok) {
      this.tiktokCurrentTime = start;
      this.tiktokPost({ type: 'seekTo', value: start });
      this.tiktokPost({ type: 'play' });
    }
  }

  jumpToSegment(segment: VideoSegment): void {
    VideoPlayerComponent.activeInstance = this;
    this.activeSegmentId.set(segment.id);
    this.activePersonalLoopId.set(null);
    if (segment.endTime != null) {
      this.loopSegmentId.set(segment.id);
      this.repeatStart = segment.startTime;
      this.repeatEnd = segment.endTime;
    }
    if (this.isYouTube) {
      this.player?.seekTo(segment.startTime, true);
      this.player?.playVideo();
    } else if (this.isTikTok) {
      this.tiktokCurrentTime = segment.startTime;
      this.tiktokPost({ type: 'seekTo', value: segment.startTime });
      this.tiktokPost({ type: 'play' });
    }
  }

  override setRate(rate: number): void {
    VideoPlayerComponent.activeInstance = this;
    this.currentRate.set(rate);
    this.player?.setPlaybackRate(rate);
  }

  /** Notes are worth a toolbar slot only when this user can write them or has some. */
  get hasNotesTool(): boolean {
    return this.canTakeNotes || this.personalNotes.length > 0;
  }

  /** Hand-moving a slider handle detaches the region from any armed section chip. */
  override onStartSliderChange(value: number): void {
    super.onStartSliderChange(value);
    this.loopSegmentId.set(null);
  }

  override onEndSliderChange(value: number): void {
    super.onEndSliderChange(value);
    this.loopSegmentId.set(null);
  }

  protected override currentPlaybackTime(): number {
    const t = this.isYouTube ? (this.player?.getCurrentTime() ?? 0) : this.tiktokCurrentTime;
    return Math.max(0, Math.floor(t));
  }

  /** Jump the player to a personal loop and arm its region. Shares jump mechanics
   *  with sections but tracks its own active chip so highlights don't cross over. */
  jumpToPersonalLoop(loop: VideoSegment): void {
    this.jumpToSegment(loop);
    this.activeSegmentId.set(null);
    this.activePersonalLoopId.set(loop.id);
  }

  emitSavePersonalLoop(): void {
    const payload = this.currentLoopPayload();
    if (!payload) return;
    this.savePersonalLoop.emit(payload);
    this.loopName = '';
    this.savingLoop.set(false);
  }

  emitDeletePersonalLoop(event: Event, loop: VideoSegment): void {
    event.stopPropagation();
    this.deletePersonalLoop.emit(loop);
  }

  // --- Personal notes ---

  /** First focus on an empty draft pins the current playback time. */
  onNoteInputFocus(): void {
    if (this.noteDraftTime() === null) this.noteDraftTime.set(this.currentPlaybackTime());
  }

  /** Re-pin the draft note to wherever playback is now. */
  stampNoteTime(): void {
    this.noteDraftTime.set(this.currentPlaybackTime());
  }

  emitSaveNote(): void {
    const text = this.noteDraftText.trim();
    if (!text) return;
    this.saveNote.emit({ timeSeconds: this.noteDraftTime() ?? this.currentPlaybackTime(), text });
    this.noteDraftText = '';
    this.noteDraftTime.set(null);
  }

  jumpToNote(note: VideoNote): void {
    VideoPlayerComponent.activeInstance = this;
    if (this.isYouTube) {
      this.player?.seekTo(note.timeSeconds, true);
      this.currentTime.set(note.timeSeconds);
      this.player?.playVideo();
    } else if (this.isTikTok) {
      this.tiktokCurrentTime = note.timeSeconds;
      this.tiktokPost({ type: 'seekTo', value: note.timeSeconds });
      this.tiktokPost({ type: 'play' });
    }
  }

  startEditNote(note: VideoNote): void {
    this.editingNoteId.set(note.id);
    this.editNoteText = note.text;
    this.editNoteTime = note.timeSeconds;
  }

  cancelEditNote(): void {
    this.editingNoteId.set(null);
  }

  /** Move the note being edited to the current playback position. */
  stampEditNoteTime(): void {
    this.editNoteTime = this.currentPlaybackTime();
  }

  emitUpdateNote(): void {
    const id = this.editingNoteId();
    const text = this.editNoteText.trim();
    if (id === null || !text) return;
    this.updateNote.emit({ id, timeSeconds: this.editNoteTime, text });
    this.editingNoteId.set(null);
  }

  emitDeleteNote(event: Event, note: VideoNote): void {
    event.stopPropagation();
    this.deleteNote.emit(note);
  }

  /** Marker position on the beta seek bar, as a percentage of the video. */
  noteMarkerPct(note: VideoNote): number {
    const d = this.videoDuration();
    return d > 0 ? Math.max(0, Math.min(100, (note.timeSeconds / d) * 100)) : 0;
  }

  protected override onRepeatArmed(): void {
    this.startLoop();
  }

  protected override onRepeatDisarmed(): void {
    this.clearRepeat();
    this.loopSegmentId.set(null);
  }

  selectLoopSegment(segment: VideoSegment): void {
    this.loopSegmentId.set(segment.id);
    this.repeatStart = segment.startTime;
    this.repeatEnd = segment.endTime!;
    this.clearRepeat();
    this.repeating.set(true);
    localStorage.setItem(this.LOOP_PREF_KEY, '1');
    this.startLoop();
  }

  private tiktokPost(data: object): void {
    this.tiktokFrame?.nativeElement?.contentWindow?.postMessage(
      { ...data, 'x-tiktok-player': true },
      '*'
    );
  }

  private createPlayer(): void {
    if (this.destroyed || !this.playerContainer) return;
    const playerVars: YT.PlayerVars = { rel: 0, modestbranding: 1 };
    if (this.betaChrome) {
      // Our bar takes over: no native controls, no double keyboard handling
      // (the document-level shortcuts stay), no annotations, no native fullscreen.
      playerVars['controls'] = 0;
      playerVars['disablekb'] = 1;
      playerVars['fs'] = 0;
      playerVars['iv_load_policy'] = 3;
      playerVars['playsinline'] = 1;
    }
    if (this.startTime != null) playerVars['start'] = this.startTime;
    // With multiple dances in one video the player must stay seekable past this
    // dance's end, so don't hard-bound it — the loop region handles section limits.
    if (this.endTime != null && !this.hasChapters) playerVars['end'] = this.endTime;

    this.player = new window.YT.Player(this.playerContainer.nativeElement, {
      videoId: this.videoId,
      playerVars,
      events: {
        onReady: () => {
          this.player?.setPlaybackRate(this.currentRate());
          if (this.betaChrome) this.initChrome();
          this.pollForDuration();
        },
        onStateChange: (e: YT.OnStateChangeEvent) => {
          if (!this.hasRealDuration) this.tryCaptureDuration();
          const State = window.YT.PlayerState;
          if (e.data === State.PLAYING) this.emitPlaying(true);
          else if (e.data === State.PAUSED || e.data === State.ENDED) this.emitPlaying(false);
        }
      }
    });
  }

  private tryCaptureDuration(): boolean {
    const dur = this.player?.getDuration() ?? 0;
    if (dur <= 0) return false;
    this.hasRealDuration = true;
    this.videoDuration.set(Math.floor(dur));
    this.initRegion(Math.floor(dur));
    return true;
  }

  private applyFallbackDuration(): void {
    const fallback = this.endTime ? this.endTime + 10 : 60;
    this.videoDuration.set(fallback);
    this.initRegion(fallback);
  }

  private initRegion(duration: number): void {
    if (!this.regionInitialised) {
      this.repeatStart = this.startTime ?? 0;
      this.repeatEnd = this.endTime ?? duration;
      this.regionInitialised = true;
    }
    if (this.repeating() && !this.repeatInterval && this.repeatEnd > this.repeatStart) {
      this.startLoop();
    }
  }

  private pollForDuration(): void {
    if (this.tryCaptureDuration()) return;
    let attempts = 0;
    this.durationPollInterval = setInterval(() => {
      attempts++;
      if (this.tryCaptureDuration()) {
        this.clearDurationPoll();
      } else if (attempts === 12) {
        this.applyFallbackDuration();
      } else if (attempts >= 40) {
        this.clearDurationPoll();
      }
    }, 250);
  }

  private clearDurationPoll(): void {
    if (this.durationPollInterval) {
      clearInterval(this.durationPollInterval);
      this.durationPollInterval = null;
    }
  }

  private startLoop(): void {
    if (this.isYouTube) {
      this.player?.seekTo(this.repeatStart, true);
      this.player?.playVideo();
      this.repeatInterval = setInterval(() => {
        const current = this.player?.getCurrentTime() ?? 0;
        if (current >= this.repeatEnd) {
          this.player?.seekTo(this.repeatStart, true);
          this.player?.playVideo();
          this.pulseLoopFlash();
        }
      }, 250);
    } else if (this.isTikTok) {
      this.tiktokCurrentTime = this.repeatStart;
      this.tiktokPost({ type: 'seekTo', value: this.repeatStart });
      this.tiktokPost({ type: 'play' });
      let segmentStartedAt = Date.now();
      this.repeatInterval = setInterval(() => {
        const elapsed = (Date.now() - segmentStartedAt) / 1000;
        const eventsArrive = this.tiktokCurrentTime > this.repeatStart + 0.15;
        const pos = eventsArrive ? this.tiktokCurrentTime : this.repeatStart + elapsed;
        if (pos >= this.repeatEnd) {
          segmentStartedAt = Date.now();
          this.tiktokCurrentTime = this.repeatStart;
          this.tiktokPost({ type: 'seekTo', value: this.repeatStart });
          this.tiktokPost({ type: 'play' });
          this.pulseLoopFlash();
        }
      }, 200);
    }
  }

  private clearRepeat(): void {
    if (this.repeatInterval) {
      clearInterval(this.repeatInterval);
      this.repeatInterval = null;
    }
  }

  // --- Beta chrome: the platform's own bar over a controls-less YouTube embed. ---

  /** Volume mirrored from the player once; afterwards only our bar changes it. */
  private initChrome(): void {
    this.volume.set((this.player?.getVolume() ?? 100) / 100);
    this.muted.set(this.player?.isMuted() ?? false);
    this.chromeTickInterval = setInterval(() => {
      this.currentTime.set(this.player?.getCurrentTime() ?? 0);
    }, 250);
  }

  seekToTime(seconds: number): void {
    VideoPlayerComponent.activeInstance = this;
    this.player?.seekTo(seconds, true);
    this.currentTime.set(seconds);
  }

  toggleMute(): void {
    if (!this.player) return;
    if (this.player.isMuted()) {
      this.player.unMute();
      this.muted.set(false);
    } else {
      this.player.mute();
      this.muted.set(true);
    }
  }

  /** Dragging to 0 mutes; dragging up from 0 unmutes — matches the local player. */
  setVolume(level: number): void {
    if (!this.player) return;
    this.player.setVolume(Math.round(level * 100));
    if (level === 0) {
      this.player.mute();
      this.muted.set(true);
    } else if (this.muted()) {
      this.player.unMute();
      this.muted.set(false);
    }
    this.volume.set(level);
  }
}
