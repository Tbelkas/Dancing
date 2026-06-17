import { Component, Input, OnInit, AfterViewInit, OnDestroy, ElementRef, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TrustUrlPipe } from '../../pipes/trust-url.pipe';
import { VideoSegment } from '../../../models/video.model';


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
  @ViewChild('playerContainer', { static: false }) playerContainer?: ElementRef;
  @ViewChild('tiktokFrame', { static: false }) tiktokFrame?: ElementRef<HTMLIFrameElement>;

  readonly playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2];
  currentRate = signal(1);
  repeating = signal(false);
  videoDuration = signal(0);
  activeSegmentId = signal<number | null>(null);

  repeatStart = 0;
  repeatEnd = 0;

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
      if (this.repeating() && !this.repeatInterval && this.repeatEnd > this.repeatStart) {
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

  jumpToSegment(segment: VideoSegment): void {
    this.activeSegmentId.set(segment.id);
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
  }

  onEndSliderChange(value: number): void {
    this.repeatEnd = Math.max(value, this.repeatStart + 1);
  }

  formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  toggleRepeat(): void {
    if (this.repeating()) {
      this.clearRepeat();
      this.repeating.set(false);
      localStorage.setItem(this.LOOP_PREF_KEY, '0');
    } else if (this.repeatEnd > this.repeatStart) {
      this.repeating.set(true);
      localStorage.setItem(this.LOOP_PREF_KEY, '1');
      if (this.isYouTube) {
        this.player?.seekTo(this.repeatStart, true);
        this.player?.playVideo();
        this.repeatInterval = setInterval(() => {
          const current = this.player?.getCurrentTime() ?? 0;
          if (current >= this.repeatEnd) {
            this.player?.seekTo(this.repeatStart, true);
          }
        }, 250);
      } else if (this.isTikTok) {
        // Reset so elapsed-time fallback starts from 0
        this.tiktokCurrentTime = this.repeatStart;
        this.tiktokPost({ type: 'seekTo', value: this.repeatStart });
        this.tiktokPost({ type: 'play' });

        // Drive looping via interval — works whether or not onCurrentTime events fire.
        // Uses actual position from events when available, elapsed wall-clock time otherwise.
        let segmentStartedAt = Date.now();
        this.repeatInterval = setInterval(() => {
          // If onCurrentTime events are arriving, use them; otherwise estimate from elapsed time.
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
    if (this.endTime != null) playerVars['end'] = this.endTime;

    this.player = new window.YT.Player(this.playerContainer.nativeElement, {
      videoId: this.videoId,
      playerVars,
      events: {
        onReady: () => {
          this.player?.setPlaybackRate(this.currentRate());
          this.pollForDuration();
        },
        onStateChange: () => {
          if (this.videoDuration() === 0) this.tryCaptureDuration();
        }
      }
    });
  }

  private tryCaptureDuration(): boolean {
    const dur = this.player?.getDuration() ?? 0;
    if (dur <= 0) return false;
    this.videoDuration.set(Math.floor(dur));
    this.repeatStart = this.startTime ?? 0;
    this.repeatEnd = this.endTime ?? Math.floor(dur);
    if (this.repeating() && !this.repeatInterval && this.repeatEnd > this.repeatStart) {
      this.player?.seekTo(this.repeatStart, true);
      this.player?.playVideo();
      this.repeatInterval = setInterval(() => {
        const current = this.player?.getCurrentTime() ?? 0;
        if (current >= this.repeatEnd) {
          this.player?.seekTo(this.repeatStart, true);
        }
      }, 250);
    }
    return true;
  }

  // getDuration() returns 0 until the video's metadata loads, which can
  // happen well after onReady — poll until it reports a real value.
  private pollForDuration(): void {
    if (this.tryCaptureDuration()) return;
    this.durationPollInterval = setInterval(() => {
      if (this.tryCaptureDuration()) this.clearDurationPoll();
    }, 250);
  }

  private clearDurationPoll(): void {
    if (this.durationPollInterval) {
      clearInterval(this.durationPollInterval);
      this.durationPollInterval = null;
    }
  }

  private clearRepeat(): void {
    if (this.repeatInterval) {
      clearInterval(this.repeatInterval);
      this.repeatInterval = null;
    }
  }
}
