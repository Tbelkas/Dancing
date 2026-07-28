import { Injectable, signal } from '@angular/core';

/** Where the camera pane sits relative to the video: beside it, or ghosted over it. */
export type CameraLayout = 'side' | 'overlay';

export type CameraStatus = 'off' | 'starting' | 'on' | 'error';

/**
 * The webcam feed shown next to (or over) a practice video, plus everything the user
 * can tune about it. Nothing here touches the server — the stream is local to the
 * browser and never leaves it.
 *
 * The stream is a singleton on purpose. A dance-detail page can mount several
 * players at once, and each one asking for its own `getUserMedia` would light up the
 * camera N times. Instead one player at a time *owns* the camera (`owner`), the newest
 * asker takes it from the previous one, and the pane renders wherever the owner is.
 *
 * Preferences (layout, mirror, opacity, delay, device) persist in localStorage so the
 * setup carries across videos and pages the way the loop/mirror prefs already do.
 */
@Injectable({ providedIn: 'root' })
export class CameraService {
  private readonly ON_KEY = 'dp_camera_on';
  private readonly LAYOUT_KEY = 'dp_camera_layout';
  private readonly MIRROR_KEY = 'dp_camera_mirror';
  private readonly OPACITY_KEY = 'dp_camera_opacity';
  private readonly DELAY_KEY = 'dp_camera_delay';
  private readonly DEVICE_KEY = 'dp_camera_device';

  /** The live feed, or null whenever the camera is off. */
  readonly stream = signal<MediaStream | null>(null);
  readonly status = signal<CameraStatus>('off');
  /** Human-readable reason the camera isn't running; shown inside the pane. */
  readonly error = signal<string | null>(null);
  /** Cameras to choose between; labels only populate once permission is granted. */
  readonly devices = signal<MediaDeviceInfo[]>([]);
  /** The player component currently showing the feed. */
  readonly owner = signal<object | null>(null);

  readonly layout = signal<CameraLayout>(
    localStorage.getItem(this.LAYOUT_KEY) === 'overlay' ? 'overlay' : 'side'
  );
  /** Default on: an unmirrored selfie view reads backwards to the person in it. */
  readonly mirrored = signal(localStorage.getItem(this.MIRROR_KEY) !== '0');
  readonly opacity = signal(this.readNumber(this.OPACITY_KEY, 0.5, 0.15, 1));
  /** Seconds of replay delay; 0 means show the live feed. */
  readonly delaySeconds = signal(this.readNumber(this.DELAY_KEY, 0, 0, 30));
  readonly deviceId = signal(localStorage.getItem(this.DEVICE_KEY) ?? '');

  readonly delayOptions = [3, 5, 10];

  /** MediaRecorder's container, picked once — Safari records mp4, everyone else webm. */
  private cachedMime: string | null | undefined;

  /** getUserMedia exists only in a secure context: https, or localhost during dev. */
  get supported(): boolean {
    return typeof navigator !== 'undefined'
      && typeof window !== 'undefined'
      && window.isSecureContext
      && !!navigator.mediaDevices?.getUserMedia;
  }

  /** Delayed replay needs MediaRecorder and a container it will actually produce. */
  get delaySupported(): boolean {
    return this.pickMimeType() !== null;
  }

  /** Why the camera can't run here at all, or null when it can. */
  get unsupportedReason(): string | null {
    if (typeof navigator === 'undefined') return 'Camera needs a browser.';
    if (typeof window !== 'undefined' && !window.isSecureContext) {
      return 'Your browser only allows the camera over https. Open the site at its https address.';
    }
    if (!navigator.mediaDevices?.getUserMedia) return "This browser can't share a camera.";
    return null;
  }

  isOwner(candidate: object): boolean {
    return this.owner() === candidate;
  }

  /**
   * Hand the camera to `owner`, starting it if it isn't already running.
   *
   * On failure the owner is *kept* so the pane stays mounted and can explain itself —
   * a denied permission prompt that silently closed the pane would look like a bug.
   */
  async start(owner: object): Promise<void> {
    this.owner.set(owner);
    const blocked = this.unsupportedReason;
    if (blocked) {
      this.status.set('error');
      this.error.set(blocked);
      return;
    }
    localStorage.setItem(this.ON_KEY, '1');
    if (this.stream()) {
      this.status.set('on');
      return;
    }
    this.status.set('starting');
    this.error.set(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: this.videoConstraints(), audio: false });
      // Turned off (or handed elsewhere) while the permission prompt was up.
      if (this.owner() !== owner) {
        this.stopTracks(stream);
        return;
      }
      this.stream.set(stream);
      this.status.set('on');
      void this.refreshDevices();
    } catch (err) {
      this.status.set('error');
      this.error.set(this.describe(err));
      localStorage.setItem(this.ON_KEY, '0');
    }
  }

  /** User turned the camera off: release the device and forget the preference. */
  stop(): void {
    localStorage.setItem(this.ON_KEY, '0');
    this.teardown();
  }

  /**
   * A player is being destroyed. Release the device — a stream left running keeps the
   * camera light on after navigation — but keep the "camera was on" preference so the
   * next page brings it back.
   */
  release(owner: object): void {
    if (!this.isOwner(owner)) return;
    this.teardown();
  }

  /** Retry after a denied or failed start, without touching the rest of the pane. */
  async retry(): Promise<void> {
    const owner = this.owner();
    if (!owner) return;
    this.teardown();
    await this.start(owner);
  }

  setLayout(layout: CameraLayout): void {
    this.layout.set(layout);
    localStorage.setItem(this.LAYOUT_KEY, layout);
  }

  toggleMirror(): void {
    this.mirrored.update(v => !v);
    localStorage.setItem(this.MIRROR_KEY, this.mirrored() ? '1' : '0');
  }

  setOpacity(value: number): void {
    const clamped = Math.min(1, Math.max(0.15, value));
    this.opacity.set(clamped);
    localStorage.setItem(this.OPACITY_KEY, String(clamped));
  }

  /** 0 turns the delay off and returns the pane to the live feed. */
  setDelay(seconds: number): void {
    this.delaySeconds.set(seconds);
    localStorage.setItem(this.DELAY_KEY, String(seconds));
  }

  /** Switch cameras without dropping ownership — restarts the stream in place. */
  async switchDevice(deviceId: string): Promise<void> {
    this.deviceId.set(deviceId);
    localStorage.setItem(this.DEVICE_KEY, deviceId);
    const owner = this.owner();
    if (!owner || !this.stream()) return;
    this.stopStreamOnly();
    await this.start(owner);
  }

  /**
   * Whether a page load may bring the camera back on its own. Only when it was on
   * before *and* permission is already granted — nobody wants a permission prompt
   * firing at them for merely opening a dance.
   */
  async shouldAutoStart(): Promise<boolean> {
    if (localStorage.getItem(this.ON_KEY) !== '1' || !this.supported) return false;
    try {
      const perm = await navigator.permissions.query({ name: 'camera' as PermissionName });
      return perm.state === 'granted';
    } catch {
      // Firefox and Safari don't answer for 'camera'. Wait for a deliberate click.
      return false;
    }
  }

  /** The first container MediaRecorder admits to supporting, or null if none do. */
  pickMimeType(): string | null {
    if (this.cachedMime !== undefined) return this.cachedMime;
    if (typeof MediaRecorder === 'undefined') {
      this.cachedMime = null;
      return null;
    }
    const candidates = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm', 'video/mp4'];
    this.cachedMime = candidates.find(type => MediaRecorder.isTypeSupported(type)) ?? null;
    return this.cachedMime;
  }

  /** Camera list for the picker. Labels are blank until permission has been granted. */
  async refreshDevices(): Promise<void> {
    if (!navigator.mediaDevices?.enumerateDevices) return;
    try {
      const all = await navigator.mediaDevices.enumerateDevices();
      this.devices.set(all.filter(d => d.kind === 'videoinput'));
    } catch {
      this.devices.set([]);
    }
  }

  private videoConstraints(): MediaTrackConstraints {
    const id = this.deviceId();
    return {
      width: { ideal: 1280 },
      height: { ideal: 720 },
      // Phones default to the selfie camera; that's the one you practise in front of.
      ...(id ? { deviceId: { exact: id } } : { facingMode: 'user' }),
    };
  }

  private teardown(): void {
    this.stopStreamOnly();
    this.owner.set(null);
    this.status.set('off');
    this.error.set(null);
  }

  /** Release the device but keep ownership — used when restarting on another camera. */
  private stopStreamOnly(): void {
    const stream = this.stream();
    if (stream) this.stopTracks(stream);
    this.stream.set(null);
  }

  /** Clearing srcObject is not enough: only stopping every track frees the device. */
  private stopTracks(stream: MediaStream): void {
    for (const track of stream.getTracks()) track.stop();
  }

  private describe(err: unknown): string {
    const name = (err as DOMException | undefined)?.name ?? '';
    switch (name) {
      case 'NotAllowedError':
      case 'SecurityError':
        return 'Camera access was blocked. Allow it in your browser’s address bar, then try again.';
      case 'NotFoundError':
      case 'OverconstrainedError':
        return 'No camera found. Plug one in (or pick another below) and try again.';
      case 'NotReadableError':
        return 'Another app is using the camera. Close it, then try again.';
      default:
        return (err as Error | undefined)?.message || "Couldn't start the camera.";
    }
  }

  private readNumber(key: string, fallback: number, min: number, max: number): number {
    const raw = localStorage.getItem(key);
    // An absent key must fall back, not clamp — Number(null) is 0, which would read as
    // "fully transparent" rather than "never set".
    if (raw === null) return fallback;
    const value = Number(raw);
    if (!isFinite(value)) return fallback;
    return Math.min(max, Math.max(min, value));
  }
}
