import { Component, Input, Output, EventEmitter, OnInit, OnDestroy, ElementRef, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { VideoSegment } from '../../../models/video.model';
import { PlayerBaseComponent } from '../player-base';
import { CameraPaneComponent } from '../camera-pane/camera-pane.component';
import { CameraLayout } from '../../../core/services/camera.service';

/**
 * Player for videos that live on the user's own disk. The file is handed to us as an
 * object URL and plays in a native <video> — nothing is streamed to or from the server.
 * Mirrors the loop/speed/mirror controls of the YouTube player so practice feels the same.
 */
@Component({
  selector: 'app-local-video-player',
  standalone: true,
  imports: [CommonModule, FormsModule, CameraPaneComponent],
  templateUrl: './local-video-player.component.html',
  styleUrls: ['../video-player/video-player.component.css', './local-video-player.component.css']
})
export class LocalVideoPlayerComponent extends PlayerBaseComponent implements OnInit, OnDestroy {
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
  // saveLoop/deleteLoop (inherited): the user's saved time slots for this choreo.
  /** Emits the video duration once metadata loads, so the parent can persist it. */
  @Output() durationDetected = new EventEmitter<number>();
  @ViewChild('videoEl', { static: true }) videoEl!: ElementRef<HTMLVideoElement>;
  @ViewChild('mediaEl', { static: true }) mediaEl!: ElementRef<HTMLElement>;

  readonly rotationOptions = [0, 90, 180, 270];
  readonly zoomOptions = [1, 1.5, 2, 3];
  readonly minRate = 0.25;
  readonly maxRate = 2;
  rotationDeg = signal(0);
  activeLoopId = signal<number | null>(null);
  zoom = signal(1);
  /** Pan of the zoomed picture, screen pixels from center; 0,0 when not zoomed. */
  panX = signal(0);
  panY = signal(0);

  private dragging = false;
  private dragMoved = false;
  private dragStartX = 0;
  private dragStartY = 0;

  /** Native pixel size of the file, read from metadata; drives the sideways layout. */
  private naturalWidth = signal(0);
  private naturalHeight = signal(0);

  private get video(): HTMLVideoElement { return this.videoEl.nativeElement; }

  ngOnInit(): void {
    this.restorePlayerPrefs();
    document.addEventListener('keydown', this.keydownHandler);
    document.addEventListener('fullscreenchange', this.fullscreenHandler);
    void this.restoreCamera();
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    document.removeEventListener('keydown', this.keydownHandler);
    document.removeEventListener('fullscreenchange', this.fullscreenHandler);
    // Frees the device: a stream left running keeps the camera light on after navigation.
    this.camera.release(this);
    this.clearFlashTimeout();
    // The <video> is torn down without firing pause — tell the parent playback ended.
    if (this.playing()) this.playingChange.emit(false);
  }

  onPlayStateChange(playing: boolean): void {
    this.playing.set(playing);
    this.playingChange.emit(playing);
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
  override setRate(rate: number): void {
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

  /** Mirror, rotation, and zoom combined into one transform: rotate the picture first,
   *  then flip it across the screen's horizontal axis so "mirror" always reads
   *  left↔right. Zoom scales innermost (uniform, so it commutes with both) and pans
   *  outermost in screen pixels, so drag deltas apply 1:1 whatever the rotation. */
  videoTransform(): string | null {
    const parts: string[] = [];
    const z = this.zoom();
    if (z > 1) parts.push(`translate(${this.panX()}px, ${this.panY()}px)`);
    if (this.sideways()) parts.push('translate(-50%, -50%)');
    if (this.mirrored()) parts.push('scaleX(-1)');
    const r = this.rotationDeg();
    if (r !== 0) parts.push(`rotate(${r}deg)`);
    if (z > 1) parts.push(`scale(${z})`);
    return parts.length ? parts.join(' ') : null;
  }

  /** When sideways, the frame takes the rotated picture's aspect (height / width). */
  sidewaysAspect(): string | null {
    if (!this.sideways()) return null;
    const w = this.naturalWidth();
    const h = this.naturalHeight();
    return w > 0 && h > 0 ? `${h} / ${w}` : '9 / 16';
  }

  /** Rotation turns the native control bar with the picture (vertical seek bar,
   *  sideways time) and zoom would magnify it, so both swap in our own controls. */
  customControls(): boolean {
    return this.rotationDeg() !== 0 || this.zoom() > 1;
  }

  setZoom(level: number): void {
    this.zoom.set(level);
    if (level <= 1) {
      this.panX.set(0);
      this.panY.set(0);
    } else {
      this.clampPan();
    }
  }

  /** Drag the zoomed picture to choose the visible area. */
  onVideoPointerDown(event: PointerEvent): void {
    if (this.zoom() <= 1) return;
    this.dragging = true;
    this.dragMoved = false;
    this.dragStartX = event.clientX - this.panX();
    this.dragStartY = event.clientY - this.panY();
    this.video.setPointerCapture(event.pointerId);
  }

  onVideoPointerMove(event: PointerEvent): void {
    if (!this.dragging) return;
    const x = event.clientX - this.dragStartX;
    const y = event.clientY - this.dragStartY;
    if (Math.abs(x - this.panX()) + Math.abs(y - this.panY()) > 3) this.dragMoved = true;
    this.panX.set(x);
    this.panY.set(y);
    this.clampPan();
  }

  onVideoPointerUp(): void {
    this.dragging = false;
  }

  /** With native controls hidden, clicking the picture still toggles playback —
   *  unless the click was really the tail end of a pan drag. */
  onVideoClick(): void {
    if (this.dragMoved) {
      this.dragMoved = false;
      return;
    }
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

  seekTo(seconds: number): void {
    this.video.currentTime = seconds;
    this.currentTime.set(seconds);
  }

  toggleMute(): void {
    this.video.muted = !this.video.muted;
  }

  /**
   * A rotated picture is positioned against the whole media frame, so splitting that
   * frame into columns would leave the video lying across the camera. Ghost the camera
   * over it instead, and hide the switch that can't work here.
   */
  override cameraLayout(): CameraLayout {
    return this.sideways() ? 'overlay' : this.camera.layout();
  }

  override cameraLayoutLocked(): boolean {
    return this.sideways();
  }

  /** The media frame (not the raw <video>) fullscreens, so the rotation layout carries over. */
  protected override mediaFrame(): HTMLElement | null {
    return this.mediaEl.nativeElement;
  }

  protected override onRepeatArmed(): void {
    this.video.currentTime = this.repeatStart;
    void this.video.play();
  }

  protected override seekAndPlay(seconds: number): void {
    this.video.currentTime = seconds;
    this.currentTime.set(seconds);
    void this.video.play();
  }

  jumpToLoop(loop: VideoSegment): void {
    this.activeLoopId.set(loop.id);
    this.repeatStart = loop.startTime;
    if (loop.endTime != null) this.repeatEnd = loop.endTime;
    this.video.currentTime = loop.startTime;
    void this.video.play();
  }

  protected override currentPlaybackTime(): number {
    return Math.floor(this.video.currentTime);
  }

  override togglePlay(): void {
    if (this.video.paused) void this.video.play();
    else this.video.pause();
  }

  protected override seekBy(deltaSeconds: number): void {
    this.video.currentTime = Math.max(0, this.video.currentTime + deltaSeconds);
  }

  /** The zoomed picture fills the frame ×zoom, so panning past (zoom−1)/2 of the
   *  frame in any direction would drag its edge into view — clamp there. */
  private clampPan(): void {
    const frame = this.mediaEl.nativeElement;
    const maxX = ((this.zoom() - 1) / 2) * frame.clientWidth;
    const maxY = ((this.zoom() - 1) / 2) * frame.clientHeight;
    this.panX.update(v => Math.max(-maxX, Math.min(maxX, v)));
    this.panY.update(v => Math.max(-maxY, Math.min(maxY, v)));
  }

  /** A focused native <video> handles space/arrows itself — don't double-handle. */
  protected override shouldSkipTransportKeys(targetTag: string): boolean {
    return targetTag === 'VIDEO';
  }

  /** Local-only shortcut: Z cycles the zoom presets. */
  protected override handleExtraKey(e: KeyboardEvent): boolean {
    if (e.key !== 'z' && e.key !== 'Z') return false;
    const next = (this.zoomOptions.indexOf(this.zoom()) + 1) % this.zoomOptions.length;
    this.setZoom(this.zoomOptions[next]);
    return true;
  }
}
