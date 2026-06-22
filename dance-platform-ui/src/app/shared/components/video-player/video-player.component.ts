import { Component, Input, Output, EventEmitter, OnInit, AfterViewInit, OnDestroy, ElementRef, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TrustUrlPipe } from '../../pipes/trust-url.pipe';
import { VideoSegment, VideoChapter } from '../../../models/video.model';
import { formatTimeSecs } from '../../../core/utils/video-url.utils';

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
  /** Admins can name and persist the current loop region as a reusable section. */
  @Input() canSaveLoops = false;
  /** Emits the current loop region when an admin saves it; the parent persists it. */
  @Output() saveLoop = new EventEmitter<{ label: string; startTime: number; endTime: number }>();
  /** Emits a section an admin wants removed; the parent deletes it. */
  @Output() deleteLoop = new EventEmitter<VideoSegment>();
  @ViewChild('playerContainer', { static: false }) playerContainer?: ElementRef;
  @ViewChild('tiktokFrame', { static: false }) tiktokFrame?: ElementRef<HTMLIFrameElement>;

  readonly playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2];
  currentRate = signal(1);
  repeating = signal(false);
  videoDuration = signal(0);
  activeSegmentId = signal<number | null>(null);
  loopSegmentId = signal<number | null>(null);
  activeChapterId = signal<number | null>(null);
  chaptersExpanded = signal(false);

  /** Only worth showing the jump row when the source video holds more than one dance. */
  get hasChapters(): boolean { return this.chapters.length > 1; }

  repeatStart = 0;
  repeatEnd = 0;
  loopName = '';

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

  private player: YT.Player | null = null;
  private repeatInterval: ReturnType<typeof setInterval> | null = null;
  private durationPollInterval: ReturnType<typeof setInterval> | null = null;
  private tiktokCurrentTime = 0;
  private hasRealDuration = false;
  private regionInitialised = false;

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
      // Expand duration estimate as we see the video play further
      if (value > this.videoDuration() - 2) {
        const newDur = Math.ceil(value) + 5;
        this.videoDuration.set(newDur);
        if (!this.repeating()) this.repeatEnd = newDur;
      }
    }

    if (type === 'onStateChange' && value === 0) {
      // Video ended — lock in actual duration
      const dur = Math.ceil(this.tiktokCurrentTime);
      if (dur > 0) {
        this.videoDuration.set(dur);
        if (!this.repeating()) this.repeatEnd = Math.min(this.repeatEnd, dur);
      }
    }
  };

  ngOnInit(): void {
    this.activeChapterId.set(this.activeVideoId ?? null);
    // Short lists open by default; long ones (some videos hold dozens of dances)
    // start collapsed so they don't bury the player controls.
    this.chaptersExpanded.set(this.chapters.length > 0 && this.chapters.length <= 6);
    this.repeating.set(localStorage.getItem(this.LOOP_PREF_KEY) === '1');
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
      (window as any).onYouTubeIframeAPIReady = () => this.createPlayer();
    }
  }

  ngOnDestroy(): void {
    this.clearRepeat();
    this.clearDurationPoll();
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
    this.activeSegmentId.set(segment.id);
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

  emitSaveLoop(): void {
    const label = this.loopName.trim();
    if (!label || this.repeatEnd <= this.repeatStart) return;
    this.saveLoop.emit({ label, startTime: this.repeatStart, endTime: this.repeatEnd });
    this.loopName = '';
  }

  emitDeleteLoop(event: Event, segment: VideoSegment): void {
    event.stopPropagation();
    this.deleteLoop.emit(segment);
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
    if (!this.playerContainer) return;
    const playerVars: YT.PlayerVars = { rel: 0, modestbranding: 1 };
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
          this.pollForDuration();
        },
        onStateChange: () => {
          if (!this.hasRealDuration) this.tryCaptureDuration();
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
}
