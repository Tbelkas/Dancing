import { Component, Input, Output, EventEmitter, OnInit, OnDestroy, ElementRef, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { VideoSegment } from '../../../models/video.model';
import { formatTimeSecs } from '../../../core/utils/video-url.utils';

/**
 * Player for videos that live on the user's own disk. The file is handed to us as an
 * object URL and plays in a native <video> — nothing is streamed to or from the server.
 * Mirrors the loop/speed/mirror controls of the YouTube player so practice feels the same.
 */
@Component({
  selector: 'app-local-video-player',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './local-video-player.component.html',
  styleUrls: ['../video-player/video-player.component.css', './local-video-player.component.css']
})
export class LocalVideoPlayerComponent implements OnInit, OnDestroy {
  /** Object URL of the locally picked file. */
  @Input({ required: true }) src!: string;
  /** The user's saved time slots for this choreo. */
  @Input() loops: VideoSegment[] = [];
  /** Saved clockwise rotation for the choreo; 0/90/180/270. */
  @Input() set rotation(value: number | undefined) {
    this.rotationDeg.set(value === 90 || value === 180 || value === 270 ? value : 0);
  }
  /** Emits the new rotation when the user changes it; the parent persists it. */
  @Output() rotationChange = new EventEmitter<number>();
  /** Emits the current loop region when the user saves it; the parent persists it. */
  @Output() saveLoop = new EventEmitter<{ label: string; startTime: number; endTime: number }>();
  /** Emits a saved loop the user wants removed; the parent deletes it. */
  @Output() deleteLoop = new EventEmitter<VideoSegment>();
  /** Emits the video duration once metadata loads, so the parent can persist it. */
  @Output() durationDetected = new EventEmitter<number>();
  @ViewChild('videoEl', { static: true }) videoEl!: ElementRef<HTMLVideoElement>;
  @ViewChild('mediaEl', { static: true }) mediaEl!: ElementRef<HTMLElement>;

  readonly playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2];
  readonly rotationOptions = [0, 90, 180, 270];
  readonly minRate = 0.25;
  readonly maxRate = 2;
  currentRate = signal(1);
  rotationDeg = signal(0);
  repeating = signal(false);
  videoDuration = signal(0);
  activeLoopId = signal<number | null>(null);
  mirrored = signal(false);
  shortcutsOpen = signal(false);
  loopFlash = signal(false);
  playing = signal(false);
  currentTime = signal(0);
  muted = signal(false);
  volume = signal(1);
  fullscreen = signal(false);

  repeatStart = 0;
  repeatEnd = 0;
  loopName = '';

  /** Native pixel size of the file, read from metadata; drives the sideways layout. */
  private naturalWidth = signal(0);
  private naturalHeight = signal(0);

  // Same keys as the YouTube player, so loop/mirror preferences carry across both.
  private readonly LOOP_PREF_KEY = 'dp_player_loop';
  private readonly MIRROR_PREF_KEY = 'dp_player_mirror';

  private flashTimeout: ReturnType<typeof setTimeout> | null = null;

  private get video(): HTMLVideoElement { return this.videoEl.nativeElement; }

  formatTime = formatTimeSecs;

  ngOnInit(): void {
    this.repeating.set(localStorage.getItem(this.LOOP_PREF_KEY) === '1');
    this.mirrored.set(localStorage.getItem(this.MIRROR_PREF_KEY) === '1');
    document.addEventListener('keydown', this.keydownHandler);
    document.addEventListener('fullscreenchange', this.fullscreenHandler);
  }

  ngOnDestroy(): void {
    document.removeEventListener('keydown', this.keydownHandler);
    document.removeEventListener('fullscreenchange', this.fullscreenHandler);
    if (this.flashTimeout) clearTimeout(this.flashTimeout);
  }

  onLoadedMetadata(): void {
    this.naturalWidth.set(this.video.videoWidth);
    this.naturalHeight.set(this.video.videoHeight);
    this.muted.set(this.video.muted);
    this.volume.set(this.video.volume);
    const dur = Math.floor(this.video.duration);
    if (!isFinite(dur) || dur <= 0) return;
    this.videoDuration.set(dur);
    this.repeatStart = Math.min(this.repeatStart, dur);
    this.repeatEnd = this.repeatEnd > 0 ? Math.min(this.repeatEnd, dur) : dur;
    this.durationDetected.emit(dur);
  }

  /** Native timeupdate fires ~4×/s — plenty to wrap an A→B loop and drive the seek bar. */
  onTimeUpdate(): void {
    this.currentTime.set(this.video.currentTime);
    if (!this.repeating() || this.repeatEnd <= this.repeatStart) return;
    if (this.video.currentTime >= this.repeatEnd) {
      this.video.currentTime = this.repeatStart;
      void this.video.play();
      this.pulseLoopFlash();
    }
  }

  onEnded(): void {
    if (this.repeating() && this.repeatEnd > this.repeatStart) {
      this.video.currentTime = this.repeatStart;
      void this.video.play();
      this.pulseLoopFlash();
    }
  }

  /** The native element takes any playbackRate, so speed is a continuous slider
   *  here (unlike the YouTube player, whose API only accepts its preset rates). */
  setRate(rate: number): void {
    const clamped = Math.round(Math.min(this.maxRate, Math.max(this.minRate, rate)) * 100) / 100;
    this.currentRate.set(clamped);
    this.video.playbackRate = clamped;
  }

  /** Fill percentage for the speed slider's track, 0.25x→0%, 2x→100%. */
  ratePct(): number {
    return ((this.currentRate() - this.minRate) / (this.maxRate - this.minRate)) * 100;
  }

  setRotation(deg: number): void {
    if (this.rotationDeg() === deg) return;
    this.rotationDeg.set(deg);
    this.rotationChange.emit(deg);
  }

  /** 90° and 270° swap the picture's width and height, so they need a resized frame. */
  sideways(): boolean {
    const r = this.rotationDeg();
    return r === 90 || r === 270;
  }

  /** Mirror and rotation combined into one transform: rotate the picture first, then
   *  flip it across the screen's horizontal axis so "mirror" always reads left↔right. */
  videoTransform(): string | null {
    const parts: string[] = [];
    if (this.sideways()) parts.push('translate(-50%, -50%)');
    if (this.mirrored()) parts.push('scaleX(-1)');
    const r = this.rotationDeg();
    if (r !== 0) parts.push(`rotate(${r}deg)`);
    return parts.length ? parts.join(' ') : null;
  }

  /** When sideways, the frame takes the rotated picture's aspect (height / width). */
  sidewaysAspect(): string | null {
    if (!this.sideways()) return null;
    const w = this.naturalWidth();
    const h = this.naturalHeight();
    return w > 0 && h > 0 ? `${h} / ${w}` : '9 / 16';
  }

  /** Any rotation turns the native control bar with the picture (vertical seek bar,
   *  sideways time), so rotated playback swaps in our own horizontal controls. */
  customControls(): boolean {
    return this.rotationDeg() !== 0;
  }

  /** With native controls hidden, clicking the picture still toggles playback. */
  onVideoClick(): void {
    if (this.customControls()) this.togglePlay();
  }

  onVolumeChange(): void {
    this.muted.set(this.video.muted);
    this.volume.set(this.video.volume);
  }

  /** Dragging to 0 mutes; dragging up from 0 unmutes — matches native player behavior. */
  setVolume(level: number): void {
    this.video.volume = level;
    this.video.muted = level === 0;
  }

  volumeIcon(): string {
    if (this.muted() || this.volume() === 0) return 'fa-volume-xmark';
    return this.volume() < 0.5 ? 'fa-volume-low' : 'fa-volume-high';
  }

  /** Displayed volume: 0 while muted so the slider reads as silent. */
  volumePct(): number {
    return Math.round((this.muted() ? 0 : this.volume()) * 100);
  }

  seekTo(seconds: number): void {
    this.video.currentTime = seconds;
    this.currentTime.set(seconds);
  }

  toggleMute(): void {
    this.video.muted = !this.video.muted;
  }

  /** Fullscreens the media frame (not the <video>) so the rotation layout carries over. */
  toggleFullscreen(): void {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void this.mediaEl.nativeElement.requestFullscreen();
    }
  }

  toggleMirror(): void {
    this.mirrored.set(!this.mirrored());
    localStorage.setItem(this.MIRROR_PREF_KEY, this.mirrored() ? '1' : '0');
  }

  toggleRepeat(): void {
    if (this.repeating()) {
      this.repeating.set(false);
      localStorage.setItem(this.LOOP_PREF_KEY, '0');
    } else if (this.repeatEnd > this.repeatStart) {
      this.repeating.set(true);
      localStorage.setItem(this.LOOP_PREF_KEY, '1');
      this.video.currentTime = this.repeatStart;
      void this.video.play();
    }
  }

  jumpToLoop(loop: VideoSegment): void {
    this.activeLoopId.set(loop.id);
    this.repeatStart = loop.startTime;
    if (loop.endTime != null) this.repeatEnd = loop.endTime;
    this.video.currentTime = loop.startTime;
    void this.video.play();
  }

  onStartSliderChange(value: number): void {
    this.repeatStart = Math.min(value, this.repeatEnd > 0 ? this.repeatEnd - 1 : value);
  }

  onEndSliderChange(value: number): void {
    this.repeatEnd = Math.max(value, this.repeatStart + 1);
  }

  setStartToCurrent(): void { this.onStartSliderChange(Math.floor(this.video.currentTime)); }
  setEndToCurrent(): void { this.onEndSliderChange(Math.floor(this.video.currentTime)); }

  emitSaveLoop(): void {
    const label = this.loopName.trim();
    if (!label || this.repeatEnd <= this.repeatStart) return;
    this.saveLoop.emit({ label, startTime: this.repeatStart, endTime: this.repeatEnd });
    this.loopName = '';
  }

  emitDeleteLoop(event: Event, loop: VideoSegment): void {
    event.stopPropagation();
    this.deleteLoop.emit(loop);
  }

  // Percent positions feeding the highlighted A→B region on the dual slider.
  loopStartPct(): number {
    const d = this.videoDuration();
    return d > 0 ? Math.min(100, (this.repeatStart / d) * 100) : 0;
  }

  loopWidthPct(): number {
    const d = this.videoDuration();
    if (d <= 0) return 0;
    return Math.max(0, Math.min(100, ((this.repeatEnd - this.repeatStart) / d) * 100));
  }

  startThumbOnTop(): boolean {
    const d = this.videoDuration();
    return d > 0 && this.repeatStart > d * 0.9;
  }

  togglePlay(): void {
    if (this.video.paused) void this.video.play();
    else this.video.pause();
  }

  private seekBy(deltaSeconds: number): void {
    this.video.currentTime = Math.max(0, this.video.currentTime + deltaSeconds);
  }

  private pulseLoopFlash(): void {
    if (this.flashTimeout) clearTimeout(this.flashTimeout);
    this.loopFlash.set(true);
    this.flashTimeout = setTimeout(() => this.loopFlash.set(false), 700);
  }

  private readonly fullscreenHandler = () => {
    this.fullscreen.set(document.fullscreenElement != null);
  };

  private readonly keydownHandler = (e: KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const target = e.target as HTMLElement | null;
    const tag = target?.tagName ?? '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target?.isContentEditable) return;

    switch (e.key) {
      case ' ':
        if (tag === 'BUTTON' || tag === 'VIDEO') return; // native handling wins
        e.preventDefault();
        this.togglePlay();
        break;
      case 'ArrowLeft':
        if (tag === 'VIDEO') return;
        e.preventDefault();
        this.seekBy(-5);
        break;
      case 'ArrowRight':
        if (tag === 'VIDEO') return;
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
        if (digit >= 1 && digit <= this.playbackRates.length) {
          this.setRate(this.playbackRates[digit - 1]);
        }
      }
    }
  };
}
