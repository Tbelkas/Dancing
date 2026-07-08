import { Component, Input, Output, EventEmitter, OnInit, AfterViewInit, OnDestroy, ElementRef, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TrustUrlPipe } from '../../pipes/trust-url.pipe';
import { VideoSegment, VideoChapter, VideoNote } from '../../../models/video.model';
import { formatTimeSecs } from '../../../core/utils/video-url.utils';
import { ViewerPrefsService } from '../../../core/services/viewer-prefs.service';

@Component({
  selector: 'app-video-player',
  standalone: true,
  imports: [CommonModule, FormsModule, TrustUrlPipe],
  templateUrl: './video-player.component.html',
  styleUrls: ['./video-player.component.css']
})
export class VideoPlayerComponent implements OnInit, AfterViewInit, OnDestroy {
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
  /** Emits the current loop region when an admin saves it globally; the parent persists it. */
  @Output() saveLoop = new EventEmitter<{ label: string; startTime: number; endTime: number }>();
  /** Emits a global section an admin wants removed; the parent deletes it. */
  @Output() deleteLoop = new EventEmitter<VideoSegment>();
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
  /** Emits true when the video starts playing, false when it pauses/ends — drives practice timing. */
  @Output() playingChange = new EventEmitter<boolean>();
  @ViewChild('playerContainer', { static: false }) playerContainer?: ElementRef;
  @ViewChild('tiktokFrame', { static: false }) tiktokFrame?: ElementRef<HTMLIFrameElement>;
  @ViewChild('mediaEl', { static: false }) mediaEl?: ElementRef<HTMLElement>;

  constructor(private viewerPrefs: ViewerPrefsService) {}

  readonly playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2];
  currentRate = signal(1);
  repeating = signal(false);
  videoDuration = signal(0);
  activeSegmentId = signal<number | null>(null);
  activePersonalLoopId = signal<number | null>(null);
  loopSegmentId = signal<number | null>(null);
  activeChapterId = signal<number | null>(null);
  chaptersExpanded = signal(false);
  /** Flip the video horizontally so the instructor's left matches the viewer's left. */
  mirrored = signal(false);
  shortcutsOpen = signal(false);
  /** Brief visual pulse each time the loop wraps back to its start. */
  loopFlash = signal(false);

  /** "Dance Platform video viewer (beta)": hide YouTube's controls and drive the
   *  embed through our own bar. Read once at init — the pref is set on the profile
   *  page, so a player never flips chrome mid-life. YouTube only: TikTok/Instagram
   *  embeds can't hand over their controls. */
  betaChrome = false;
  playing = signal(false);
  currentTime = signal(0);
  muted = signal(false);
  volume = signal(1);
  fullscreen = signal(false);

  /** Only worth showing the jump row when the source video holds more than one dance. */
  get hasChapters(): boolean { return this.chapters.length > 1; }

  repeatStart = 0;
  repeatEnd = 0;
  loopName = '';

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

  private readonly LOOP_PREF_KEY = 'dp_player_loop';
  private readonly MIRROR_PREF_KEY = 'dp_player_mirror';

  /** Keyboard shortcuts go to the player the user touched (or played) last, so
   *  pages that render several players don't all react to one keypress. */
  private static activeInstance: VideoPlayerComponent | null = null;

  private player: YT.Player | null = null;
  private flashTimeout: ReturnType<typeof setTimeout> | null = null;
  private repeatInterval: ReturnType<typeof setInterval> | null = null;
  /** Drives the beta chrome's seek bar — the iframe API has no timeupdate event. */
  private chromeTickInterval: ReturnType<typeof setInterval> | null = null;
  private durationPollInterval: ReturnType<typeof setInterval> | null = null;
  private tiktokCurrentTime = 0;
  private hasRealDuration = false;
  private regionInitialised = false;
  /** Guards the deferred iframe-API callback from creating a player after ngOnDestroy. */
  private destroyed = false;
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

  private readonly keydownHandler = (e: KeyboardEvent) => {
    if (VideoPlayerComponent.activeInstance !== this) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const target = e.target as HTMLElement | null;
    const tag = target?.tagName ?? '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target?.isContentEditable) return;

    switch (e.key) {
      case ' ':
        // Let a focused button keep its native space behaviour.
        if (tag === 'BUTTON') return;
        if (!this.isYouTube) return;
        e.preventDefault();
        this.togglePlay();
        break;
      case 'ArrowLeft':
        if (!this.isYouTube) return;
        e.preventDefault();
        this.seekBy(-5);
        break;
      case 'ArrowRight':
        if (!this.isYouTube) return;
        e.preventDefault();
        this.seekBy(5);
        break;
      case '[':
        this.setStartToCurrent();
        break;
      case ']':
        this.setEndToCurrent();
        break;
      case 'l': case 'L':
        this.toggleRepeat();
        break;
      case 'm': case 'M':
        this.toggleMirror();
        break;
      case '?':
        this.shortcutsOpen.set(!this.shortcutsOpen());
        break;
      default: {
        const digit = parseInt(e.key, 10);
        if (this.isYouTube && digit >= 1 && digit <= this.playbackRates.length) {
          this.setRate(this.playbackRates[digit - 1]);
        }
      }
    }
  };

  togglePlay(): void {
    if (!this.player || !window.YT) return;
    if (this.player.getPlayerState() === window.YT.PlayerState.PLAYING) {
      this.player.pauseVideo();
    } else {
      this.player.playVideo();
    }
  }

  private seekBy(deltaSeconds: number): void {
    if (!this.player) return;
    const t = Math.max(0, (this.player.getCurrentTime() ?? 0) + deltaSeconds);
    this.player.seekTo(t, true);
  }

  toggleMirror(): void {
    VideoPlayerComponent.activeInstance = this;
    this.mirrored.set(!this.mirrored());
    localStorage.setItem(this.MIRROR_PREF_KEY, this.mirrored() ? '1' : '0');
  }

  /** Percent positions feeding the highlighted A→B region on the dual slider. */
  loopStartPct(): number {
    const d = this.videoDuration();
    return d > 0 ? Math.min(100, (this.repeatStart / d) * 100) : 0;
  }

  loopWidthPct(): number {
    const d = this.videoDuration();
    if (d <= 0) return 0;
    return Math.max(0, Math.min(100, ((this.repeatEnd - this.repeatStart) / d) * 100));
  }

  /** When both handles sit near the far end, the start handle must win the
   *  pointer, or the region can never be reopened. */
  startThumbOnTop(): boolean {
    const d = this.videoDuration();
    return d > 0 && this.repeatStart > d * 0.9;
  }

  private pulseLoopFlash(): void {
    if (this.flashTimeout) clearTimeout(this.flashTimeout);
    this.loopFlash.set(true);
    this.flashTimeout = setTimeout(() => this.loopFlash.set(false), 700);
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
    this.repeating.set(localStorage.getItem(this.LOOP_PREF_KEY) === '1');
    this.mirrored.set(localStorage.getItem(this.MIRROR_PREF_KEY) === '1');
    VideoPlayerComponent.activeInstance = this;
    document.addEventListener('keydown', this.keydownHandler);
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
    if (this.flashTimeout) clearTimeout(this.flashTimeout);
    document.removeEventListener('keydown', this.keydownHandler);
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

  setRate(rate: number): void {
    VideoPlayerComponent.activeInstance = this;
    this.currentRate.set(rate);
    this.player?.setPlaybackRate(rate);
  }

  onStartSliderChange(value: number): void {
    this.repeatStart = Math.min(value, this.repeatEnd > 0 ? this.repeatEnd - 1 : value);
    this.loopSegmentId.set(null);
  }

  onEndSliderChange(value: number): void {
    this.repeatEnd = Math.max(value, this.repeatStart + 1);
    this.loopSegmentId.set(null);
  }

  /** Current playback position, floored to whole seconds. */
  private currentPlaybackTime(): number {
    const t = this.isYouTube ? (this.player?.getCurrentTime() ?? 0) : this.tiktokCurrentTime;
    return Math.max(0, Math.floor(t));
  }

  setStartToCurrent(): void { this.onStartSliderChange(this.currentPlaybackTime()); }
  setEndToCurrent(): void { this.onEndSliderChange(this.currentPlaybackTime()); }

  /** Jump the player to a personal loop and arm its region. Shares jump mechanics
   *  with sections but tracks its own active chip so highlights don't cross over. */
  jumpToPersonalLoop(loop: VideoSegment): void {
    this.jumpToSegment(loop);
    this.activeSegmentId.set(null);
    this.activePersonalLoopId.set(loop.id);
  }

  /** Current loop region, or null when it isn't a valid (named, non-empty) range. */
  private currentLoopPayload(): { label: string; startTime: number; endTime: number } | null {
    const label = this.loopName.trim();
    if (!label || this.repeatEnd <= this.repeatStart) return null;
    return { label, startTime: this.repeatStart, endTime: this.repeatEnd };
  }

  emitSaveLoop(): void {
    const payload = this.currentLoopPayload();
    if (!payload) return;
    this.saveLoop.emit(payload);
    this.loopName = '';
  }

  emitSavePersonalLoop(): void {
    const payload = this.currentLoopPayload();
    if (!payload) return;
    this.savePersonalLoop.emit(payload);
    this.loopName = '';
  }

  emitDeleteLoop(event: Event, segment: VideoSegment): void {
    event.stopPropagation();
    this.deleteLoop.emit(segment);
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

  formatTime = formatTimeSecs;

  toggleRepeat(): void {
    if (this.repeating()) {
      this.clearRepeat();
      this.repeating.set(false);
      this.loopSegmentId.set(null);
      localStorage.setItem(this.LOOP_PREF_KEY, '0');
    } else if (this.repeatEnd > this.repeatStart) {
      this.repeating.set(true);
      localStorage.setItem(this.LOOP_PREF_KEY, '1');
      this.startLoop();
    }
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

  /** The loop sliders live below the video and vanish in fullscreen, so the bar
   *  carries its own way back to the armed region's start. */
  jumpToLoopStart(): void {
    this.seekToTime(this.repeatStart);
    this.player?.playVideo();
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

  volumeIcon(): string {
    if (this.muted() || this.volume() === 0) return 'fa-volume-xmark';
    return this.volume() < 0.5 ? 'fa-volume-low' : 'fa-volume-high';
  }

  /** Displayed volume: 0 while muted so the slider reads as silent. */
  volumePct(): number {
    return Math.round((this.muted() ? 0 : this.volume()) * 100);
  }

  /** Fullscreens the media frame (not the iframe) so our bar rides along. */
  toggleFullscreen(): void {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void this.mediaEl?.nativeElement.requestFullscreen();
    }
  }

  private readonly fullscreenHandler = () => {
    this.fullscreen.set(document.fullscreenElement != null);
  };
}
