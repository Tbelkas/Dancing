import { Component, ElementRef, Input, OnDestroy, ViewChild, effect, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CameraLayout, CameraService } from '../../../core/services/camera.service';

/**
 * Your own camera, beside the instructor's video (or ghosted over it), with an
 * optional delayed replay so you can watch back what you just did without stopping.
 *
 * The stream itself belongs to CameraService — this is the surface that renders it,
 * plus the one piece of machinery it owns outright: the delay loop.
 *
 * ### How the delay works
 * A continuous N-second-behind feed isn't something the web platform gives you.
 * MediaRecorder chunks can't be replayed independently (only the first carries the
 * container header), and a frame ring-buffer costs tens of MB for a few seconds. So
 * the delay runs in cycles: record N seconds, then play that clip on loop while the
 * next N seconds record. You're always watching the window that just finished —
 * which is what the delayed mirrors in dance studios do.
 */
@Component({
  selector: 'app-camera-pane',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './camera-pane.component.html',
  styleUrls: ['./camera-pane.component.css'],
  // Overlay mode lifts the whole host out of the layout and onto the video, so the
  // player's frame keeps its single-column shape underneath.
  host: { '[class.is-overlay]': 'isOverlay' }
})
export class CameraPaneComponent implements OnDestroy {
  /** Resolved by the host player — it also styles its own frame to match. */
  @Input() layout: CameraLayout = 'side';
  /** The host forces the layout (rotated local video can't split), so don't offer the switch. */
  @Input() layoutLocked = false;

  readonly camera = inject(CameraService);

  @ViewChild('camEl', { static: true }) camEl!: ElementRef<HTMLVideoElement>;
  @ViewChild('replayEl', { static: true }) replayEl!: ElementRef<HTMLVideoElement>;

  /** True once the first delayed clip is ready; until then the live feed stays up. */
  readonly showingReplay = signal(false);
  /** Set when the browser has no MediaRecorder to give us. */
  readonly delayUnavailable = signal(false);
  settingsOpen = signal(false);

  private recorder: MediaRecorder | null = null;
  private cycleTimer: ReturnType<typeof setTimeout> | null = null;
  private replayUrl: string | null = null;
  /** Guards the async recorder callbacks against a teardown that already happened. */
  private delayRunning = false;

  constructor() {
    // Attach the live stream to the <video>. srcObject isn't bindable in a template —
    // it takes an object, not an attribute string — so it's assigned here.
    effect(() => {
      const stream = this.camera.stream();
      const el = this.camEl?.nativeElement;
      if (!el) return;
      el.srcObject = stream;
      if (stream) void el.play().catch(() => { /* autoplay is muted, so this is rare */ });
    });

    // Start or stop the delay loop when either the stream or the delay setting changes.
    // Writes signals (the replay is a side-effecting resource this effect owns), hence
    // allowSignalWrites.
    effect(() => {
      const stream = this.camera.stream();
      const seconds = this.camera.delaySeconds();
      this.stopDelay();
      if (!stream || seconds <= 0) return;
      if (!this.camera.delaySupported) {
        this.delayUnavailable.set(true);
        return;
      }
      this.delayUnavailable.set(false);
      this.startDelay(stream, seconds);
    }, { allowSignalWrites: true });
  }

  ngOnDestroy(): void {
    this.stopDelay();
  }

  get isOverlay(): boolean {
    return this.layout === 'overlay';
  }

  /** Cameras are only worth offering a choice between when there's more than one. */
  get showDevicePicker(): boolean {
    return this.camera.devices().length > 1;
  }

  /** Label for a camera; browsers leave it blank until permission has been granted. */
  deviceLabel(device: MediaDeviceInfo, index: number): string {
    return device.label || `Camera ${index + 1}`;
  }

  setLayout(layout: CameraLayout): void {
    this.camera.setLayout(layout);
  }

  onDeviceChange(deviceId: string): void {
    void this.camera.switchDevice(deviceId);
  }

  /** Clicking the armed delay preset again returns to the live feed. */
  toggleDelay(seconds: number): void {
    this.camera.setDelay(this.camera.delaySeconds() === seconds ? 0 : seconds);
  }

  close(): void {
    this.camera.stop();
  }

  retry(): void {
    void this.camera.retry();
  }

  // --- Delayed replay ------------------------------------------------------

  private startDelay(stream: MediaStream, seconds: number): void {
    const mimeType = this.camera.pickMimeType();
    if (!mimeType) {
      this.delayUnavailable.set(true);
      return;
    }
    this.delayRunning = true;

    const spin = () => {
      if (!this.delayRunning) return;
      let chunks: Blob[] = [];
      let recorder: MediaRecorder;
      try {
        recorder = new MediaRecorder(stream, { mimeType });
      } catch {
        this.delayUnavailable.set(true);
        this.delayRunning = false;
        return;
      }
      // addEventListener, not `recorder.onstop =`: zone.js patches addEventListener for
      // every EventTarget, but not MediaRecorder's on* properties. Assigning them left
      // the switch to the replay invisible until some other event happened to trigger
      // change detection — the picture had already swapped, the label hadn't.
      recorder.addEventListener('dataavailable', event => {
        if (event.data.size > 0) chunks.push(event.data);
      });
      recorder.addEventListener('stop', () => {
        const blob = new Blob(chunks, { type: mimeType });
        chunks = [];
        if (this.delayRunning) this.playClip(blob);
      });
      recorder.start();
      this.recorder = recorder;
      this.cycleTimer = setTimeout(() => {
        if (recorder.state !== 'inactive') recorder.stop();
        spin();
      }, seconds * 1000);
    };

    spin();
  }

  /** Swap in the clip that just finished recording and loop it until the next one. */
  private playClip(blob: Blob): void {
    const el = this.replayEl?.nativeElement;
    if (!el || blob.size === 0) return;
    const previous = this.replayUrl;
    this.replayUrl = URL.createObjectURL(blob);
    el.src = this.replayUrl;
    el.currentTime = 0;
    void el.play().catch(() => { /* a clip replaced mid-load; the next cycle recovers */ });
    this.showingReplay.set(true);
    // Revoke only after the element has taken the new source, or the swap can stall.
    if (previous) URL.revokeObjectURL(previous);
  }

  private stopDelay(): void {
    this.delayRunning = false;
    if (this.cycleTimer) {
      clearTimeout(this.cycleTimer);
      this.cycleTimer = null;
    }
    if (this.recorder && this.recorder.state !== 'inactive') this.recorder.stop();
    this.recorder = null;
    const el = this.replayEl?.nativeElement;
    if (el) {
      el.pause();
      el.removeAttribute('src');
      el.load();
    }
    if (this.replayUrl) {
      URL.revokeObjectURL(this.replayUrl);
      this.replayUrl = null;
    }
    this.showingReplay.set(false);
  }
}
