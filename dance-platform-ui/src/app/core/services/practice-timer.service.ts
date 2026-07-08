import { Injectable, NgZone, signal, computed } from '@angular/core';
import { PracticeService } from './practice.service';
import { AuthService } from './auth.service';
import { toPracticeDateString } from '../utils/video-url.utils';

/**
 * Accumulates practice time while a dance video is actually playing and streams it to the API as
 * heartbeats. The server folds consecutive heartbeats into one session and opens a new one once
 * the 10-minute continuation buffer lapses; this service mirrors that buffer client-side so the
 * on-screen clock keeps showing the live session total and clears itself when the session ages out.
 */
@Injectable({ providedIn: 'root' })
export class PracticeTimerService {
  /** Push pending seconds once this many have stacked up, so the clock syncs to the server total. */
  private readonly FLUSH_THRESHOLD = 20;
  /** Mirrors the server's session continuation buffer. */
  private readonly BUFFER_MS = 10 * 60 * 1000;

  private activeDanceId: number | null = null;
  private activeVideoId: number | null = null;
  private activeChoreoId: number | null = null;
  private playing = false;
  private pendingSeconds = 0;
  private serverTotalSeconds = 0;
  private flushing = false;

  private tickHandle: ReturnType<typeof setInterval> | null = null;
  private expiryHandle: ReturnType<typeof setTimeout> | null = null;

  /** Live session total in seconds (server-confirmed + not-yet-flushed), for the clock. */
  readonly liveSeconds = signal(0);
  /** True while the video is playing, so the clock appears on play rather than after the first tick. */
  private readonly watching = signal(false);
  /** Whether a session is live and the clock should be shown. */
  readonly active = computed(() => this.watching() || this.liveSeconds() > 0);

  constructor(private practice: PracticeService, private auth: AuthService, private zone: NgZone) {
    if (typeof document !== 'undefined') {
      // Best-effort flush when the tab is backgrounded or closed.
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') this.flush();
      });
    }
  }

  /** Marks the given dance/video as the one being watched. Flushes the previous one first. */
  setActiveDance(danceId: number, videoId: number | null = null): void {
    if (this.activeDanceId === danceId && this.activeVideoId === videoId && this.activeChoreoId === null) return;
    this.flush();
    this.activeDanceId = danceId;
    this.activeVideoId = videoId;
    this.activeChoreoId = null;
  }

  /** Marks one of the user's local choreos ("My choreos") as the one being practiced. */
  setActiveChoreo(choreoId: number): void {
    if (this.activeChoreoId === choreoId) return;
    this.flush();
    this.activeDanceId = null;
    this.activeVideoId = null;
    this.activeChoreoId = choreoId;
  }

  /** Player play/pause state. Counting only runs while playing.
   *  Runs inside NgZone: callers include YouTube iframe API callbacks, which fire outside the
   *  Angular zone — without re-entering it, the clock's signal updates never trigger a render. */
  setPlaying(playing: boolean): void {
    this.zone.run(() => {
      if (playing === this.playing) return;
      this.playing = playing;
      if (playing) {
        if (!this.auth.isAuthenticated()) return;
        this.watching.set(true);
        this.cancelExpiry();
        this.startTicking();
      } else {
        this.watching.set(false);
        this.stopTicking();
        this.flush();
        this.scheduleExpiry();
      }
    });
  }

  /** Stop watching entirely (e.g. leaving the page): flush and let the buffer expire the clock. */
  stop(): void {
    this.setPlaying(false);
    this.activeDanceId = null;
    this.activeVideoId = null;
    this.activeChoreoId = null;
  }

  private startTicking(): void {
    if (this.tickHandle) return;
    this.tickHandle = setInterval(() => {
      this.pendingSeconds++;
      this.refreshDisplay();
      if (this.pendingSeconds >= this.FLUSH_THRESHOLD) this.flush();
    }, 1000);
  }

  private stopTicking(): void {
    if (this.tickHandle) {
      clearInterval(this.tickHandle);
      this.tickHandle = null;
    }
  }

  private flush(): void {
    if (this.flushing || this.pendingSeconds <= 0 || (this.activeDanceId == null && this.activeChoreoId == null)) return;
    if (!this.auth.isAuthenticated()) return;

    // Cap per beat to the server's accepted range; the remainder drains on the next flush.
    const sent = Math.min(this.pendingSeconds, 600);
    const danceId = this.activeDanceId;
    const videoId = this.activeVideoId;
    const choreoId = this.activeChoreoId;
    this.flushing = true;
    this.practice.heartbeat({ danceId, videoId, choreoId, seconds: sent, localDate: toPracticeDateString(new Date()) }).subscribe({
      next: session => {
        this.serverTotalSeconds = session.totalSeconds;
        // Keep any seconds that accrued while the request was in flight.
        this.pendingSeconds = Math.max(0, this.pendingSeconds - sent);
        this.flushing = false;
        this.refreshDisplay();
      },
      error: () => { this.flushing = false; } // keep pendingSeconds; retried on the next beat
    });
  }

  private refreshDisplay(): void {
    this.liveSeconds.set(this.serverTotalSeconds + this.pendingSeconds);
  }

  private scheduleExpiry(): void {
    this.cancelExpiry();
    this.expiryHandle = setTimeout(() => this.reset(), this.BUFFER_MS);
  }

  private cancelExpiry(): void {
    if (this.expiryHandle) {
      clearTimeout(this.expiryHandle);
      this.expiryHandle = null;
    }
  }

  private reset(): void {
    this.cancelExpiry();
    this.stopTicking();
    this.pendingSeconds = 0;
    this.serverTotalSeconds = 0;
    this.activeDanceId = null;
    this.activeVideoId = null;
    this.activeChoreoId = null;
    this.playing = false;
    this.watching.set(false);
    this.liveSeconds.set(0);
  }
}
