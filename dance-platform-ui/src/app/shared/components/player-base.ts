import { Directive, EventEmitter, Output, signal } from '@angular/core';
import { VideoSegment } from '../../models/video.model';
import { formatTimeSecs } from '../../core/utils/video-url.utils';

/**
 * Everything the embed player (YouTube/TikTok/Instagram) and the local-file player
 * share: the playback-rate presets, the A→B loop region and its slider math, the
 * mirror/loop preferences, volume/fullscreen display state, the loop-wrap flash,
 * and the document-level keyboard shortcuts. Subclasses supply the transport
 * (seek/play/pause against their backend) through the abstract members and can
 * tune the key map through the protected hooks.
 *
 * Both players persist loop/mirror under the same keys, so the preference carries
 * across them.
 */
@Directive()
export abstract class PlayerBaseComponent {
  /** Emits the current loop region when the user saves it; the parent persists it. */
  @Output() saveLoop = new EventEmitter<{ label: string; startTime: number; endTime: number }>();
  /** Emits a saved loop the user wants removed; the parent deletes it. */
  @Output() deleteLoop = new EventEmitter<VideoSegment>();
  /** Emits play/pause transitions, so the parent can track practice time. */
  @Output() playingChange = new EventEmitter<boolean>();

  readonly playbackRates = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2];
  currentRate = signal(1);
  repeating = signal(false);
  videoDuration = signal(0);
  /** Flip the video horizontally so the instructor's left matches the viewer's left. */
  mirrored = signal(false);
  shortcutsOpen = signal(false);
  /** Brief visual pulse each time the loop wraps back to its start. */
  loopFlash = signal(false);
  playing = signal(false);
  currentTime = signal(0);
  muted = signal(false);
  volume = signal(1);
  fullscreen = signal(false);

  /** Loop is a panel behind a toolbar toggle, not a permanent fixture under every
   *  video — most watching is just watching. The toggle reports the armed state,
   *  so nothing is hidden, only folded. */
  loopOpen = signal(false);
  /** The name field inside the loop panel only appears once you ask to save. */
  savingLoop = signal(false);

  repeatStart = 0;
  repeatEnd = 0;
  loopName = '';

  protected readonly LOOP_PREF_KEY = 'dp_player_loop';
  protected readonly MIRROR_PREF_KEY = 'dp_player_mirror';

  private flashTimeout: ReturnType<typeof setTimeout> | null = null;

  formatTime = formatTimeSecs;

  // --- Transport: how the concrete player actually moves its video. ---

  abstract togglePlay(): void;
  abstract setRate(rate: number): void;
  protected abstract seekBy(deltaSeconds: number): void;
  /** Jump playback to a position and start playing (loop restarts, chip jumps). */
  protected abstract seekAndPlay(seconds: number): void;
  /** Current playback position, floored to whole seconds. */
  protected abstract currentPlaybackTime(): number;
  /** The frame that fullscreens — the wrapper, not the raw video/iframe, so our controls ride along. */
  protected abstract mediaFrame(): HTMLElement | null;
  /** True when the transport keys (space/arrows) must be left alone for this key target —
   *  e.g. a focused native <video> handles them itself, or the embed can't be driven at all. */
  protected abstract shouldSkipTransportKeys(targetTag: string): boolean;

  // --- Hooks subclasses may override to tune shared behavior. ---

  /** Whether this instance should react to a document-level keypress at all. */
  protected canHandleKey(): boolean { return true; }
  /** Handle a player-specific key before the shared map; return true when consumed. */
  protected handleExtraKey(_e: KeyboardEvent): boolean { return false; }
  /** Whether the 1–9 rate-preset keys apply (embeds without rate control say no). */
  protected rateKeysEnabled(): boolean { return true; }
  /** The loop was just armed — start whatever wraps playback back to the region start. */
  protected onRepeatArmed(): void {}
  /** The loop was just disarmed — tear down any wrap machinery. */
  protected onRepeatDisarmed(): void {}

  // --- Shared behavior. ---

  /** Restore the loop/mirror preferences persisted by any player instance. */
  protected restorePlayerPrefs(): void {
    this.repeating.set(localStorage.getItem(this.LOOP_PREF_KEY) === '1');
    this.mirrored.set(localStorage.getItem(this.MIRROR_PREF_KEY) === '1');
  }

  toggleMirror(): void {
    this.mirrored.set(!this.mirrored());
    localStorage.setItem(this.MIRROR_PREF_KEY, this.mirrored() ? '1' : '0');
  }

  toggleRepeat(): void {
    if (this.repeating()) {
      this.repeating.set(false);
      localStorage.setItem(this.LOOP_PREF_KEY, '0');
      this.onRepeatDisarmed();
    } else if (this.repeatEnd > this.repeatStart) {
      this.repeating.set(true);
      localStorage.setItem(this.LOOP_PREF_KEY, '1');
      this.loopOpen.set(true);
      this.onRepeatArmed();
    }
  }

  /** The loop sliders live below the video and vanish in fullscreen, so the bar
   *  carries its own way back to the armed region's start. */
  jumpToLoopStart(): void {
    this.seekAndPlay(this.repeatStart);
  }

  onStartSliderChange(value: number): void {
    this.repeatStart = Math.min(value, this.repeatEnd > 0 ? this.repeatEnd - 1 : value);
  }

  onEndSliderChange(value: number): void {
    this.repeatEnd = Math.max(value, this.repeatStart + 1);
  }

  /* Working the region (by button or by [ ] key) means the user wants the panel:
     show them the numbers they're editing rather than leaving them to guess. */
  setStartToCurrent(): void {
    this.onStartSliderChange(this.currentPlaybackTime());
    this.loopOpen.set(true);
  }

  setEndToCurrent(): void {
    this.onEndSliderChange(this.currentPlaybackTime());
    this.loopOpen.set(true);
  }

  /** Current loop region, or null when it isn't a valid (named, non-empty) range. */
  protected currentLoopPayload(): { label: string; startTime: number; endTime: number } | null {
    const label = this.loopName.trim();
    if (!label || this.repeatEnd <= this.repeatStart) return null;
    return { label, startTime: this.repeatStart, endTime: this.repeatEnd };
  }

  emitSaveLoop(): void {
    const payload = this.currentLoopPayload();
    if (!payload) return;
    this.saveLoop.emit(payload);
    this.loopName = '';
    this.savingLoop.set(false);
  }

  emitDeleteLoop(event: Event, segment: VideoSegment): void {
    event.stopPropagation();
    this.deleteLoop.emit(segment);
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

  /** When both handles sit near the far end, the start handle must win the
   *  pointer, or the region can never be reopened. */
  startThumbOnTop(): boolean {
    const d = this.videoDuration();
    return d > 0 && this.repeatStart > d * 0.9;
  }

  protected pulseLoopFlash(): void {
    if (this.flashTimeout) clearTimeout(this.flashTimeout);
    this.loopFlash.set(true);
    this.flashTimeout = setTimeout(() => this.loopFlash.set(false), 700);
  }

  /** Subclasses call this from their ngOnDestroy. */
  protected clearFlashTimeout(): void {
    if (this.flashTimeout) clearTimeout(this.flashTimeout);
  }

  volumeIcon(): string {
    if (this.muted() || this.volume() === 0) return 'fa-volume-xmark';
    return this.volume() < 0.5 ? 'fa-volume-low' : 'fa-volume-high';
  }

  /** Displayed volume: 0 while muted so the slider reads as silent. */
  volumePct(): number {
    return Math.round((this.muted() ? 0 : this.volume()) * 100);
  }

  /** Fullscreens the media frame (not the video/iframe) so our controls ride along. */
  toggleFullscreen(): void {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void this.mediaFrame()?.requestFullscreen();
    }
  }

  protected readonly fullscreenHandler = () => {
    this.fullscreen.set(document.fullscreenElement != null);
  };

  /** Document-level shortcuts; subclasses register/unregister it in their lifecycle. */
  protected readonly keydownHandler = (e: KeyboardEvent) => {
    if (!this.canHandleKey()) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const target = e.target as HTMLElement | null;
    const tag = target?.tagName ?? '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target?.isContentEditable) return;
    if (this.handleExtraKey(e)) return;

    switch (e.key) {
      case ' ':
        // Let a focused button (or a native video) keep its own space behaviour.
        if (tag === 'BUTTON' || this.shouldSkipTransportKeys(tag)) return;
        e.preventDefault();
        this.togglePlay();
        break;
      case 'ArrowLeft':
        if (this.shouldSkipTransportKeys(tag)) return;
        e.preventDefault();
        this.seekBy(-5);
        break;
      case 'ArrowRight':
        if (this.shouldSkipTransportKeys(tag)) return;
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
        if (this.rateKeysEnabled() && digit >= 1 && digit <= this.playbackRates.length) {
          this.setRate(this.playbackRates[digit - 1]);
        }
      }
    }
  };
}
