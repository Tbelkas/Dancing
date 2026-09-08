import { Component, HostListener, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { VideoService } from '../../core/services/video.service';
import { PendingVideo, flagLabel } from '../../models/pending-video.model';
import { VideoPlayerComponent } from '../../shared/components/video-player/video-player.component';

type Queue = 'pending' | 'rejected';

/**
 * The intake review queue: videos the quality gate quarantined, judged one at a time.
 *
 * Until this page existed the only way to empty that queue was the Intake tab of
 * scripts/chip_ui.py, which runs on the machine the pipeline runs on — so a decision that
 * needs nothing but a person watching a clip could only be made at that desk.
 *
 * Only the focused row mounts a player. Fifty YouTube iframes at once is minutes of loading
 * and a wedged tab, and the queue is worked one video at a time anyway.
 */
@Component({
  selector: 'app-admin-video-review',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, VideoPlayerComponent],
  templateUrl: './admin-video-review.component.html',
  styleUrls: ['./admin-video-review.component.css']
})
export class AdminVideoReviewComponent implements OnInit {
  queue = signal<Queue>('pending');
  videos = signal<PendingVideo[]>([]);
  loading = signal(true);
  loadError = signal(false);
  busyId = signal<number | null>(null);
  message = signal('');

  /** Index of the row whose player is mounted; -1 while nothing is open. */
  focused = signal(-1);
  note = '';

  readonly flagLabel = flagLabel;

  focusedVideo = computed(() => this.videos()[this.focused()] ?? null);

  constructor(private videoService: VideoService) {}

  ngOnInit(): void {
    this.load();
  }

  switchQueue(queue: Queue): void {
    if (this.queue() === queue) return;
    this.queue.set(queue);
    this.message.set('');
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.focused.set(-1);
    this.videoService.getPending(this.queue()).subscribe({
      next: list => {
        this.videos.set(list);
        this.loading.set(false);
        this.loadError.set(false);
        // Open the first one straight away: the queue is a working surface, and a reviewer
        // who has to click before they can watch anything pays that click every single time.
        this.focused.set(list.length ? 0 : -1);
      },
      error: () => { this.loading.set(false); this.loadError.set(true); }
    });
  }

  focus(index: number): void {
    this.focused.set(this.focused() === index ? -1 : index);
    this.note = '';
  }

  /** Seconds of source this row actually plays — what "is it too short" is really asking. */
  runtime(v: PendingVideo): number | null {
    const start = v.startTime ?? 0;
    if (v.endTime) return Math.max(0, v.endTime - start);
    return v.durationSeconds ? Math.max(0, v.durationSeconds - start) : null;
  }

  /** That runtime as m:ss, or an empty string when the duration was never backfilled. */
  runtimeLabel(v: PendingVideo): string {
    const secs = this.runtime(v);
    if (secs === null) return '';
    return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`;
  }

  scorePercent(v: PendingVideo): number | null {
    return v.qualityScore == null ? null : Math.round(v.qualityScore * 100);
  }

  decide(video: PendingVideo, state: 'approved' | 'rejected' | 'pending'): void {
    if (this.busyId()) return;
    this.busyId.set(video.id);
    const note = this.note.trim();
    this.videoService.review(video.id, state, note || undefined).subscribe({
      next: () => {
        const index = this.videos().findIndex(v => v.id === video.id);
        this.videos.update(list => list.filter(v => v.id !== video.id));
        this.busyId.set(null);
        this.note = '';
        const verb = state === 'approved' ? 'is live' : state === 'rejected' ? 'was rejected' : 'went back in the queue';
        this.message.set(`"${video.title}" ${verb}.`);
        // Hold the position rather than the index: after a removal the next video has slid
        // into this slot, so staying put IS advancing, and clamping keeps the last one valid.
        const remaining = this.videos().length;
        this.focused.set(remaining === 0 ? -1 : Math.min(index, remaining - 1));
      },
      error: () => { this.busyId.set(null); this.message.set('That decision did not save. Try again.'); }
    });
  }

  move(delta: number): void {
    const count = this.videos().length;
    if (!count) return;
    const next = Math.min(count - 1, Math.max(0, this.focused() + delta));
    this.focused.set(next);
    this.note = '';
  }

  /**
   * Keyboard: A approve, R reject, J/K walk the queue. Ignored while the cursor is in the note
   * box — otherwise typing "a reason" would approve the video mid-word.
   */
  @HostListener('window:keydown', ['$event'])
  onKey(event: KeyboardEvent): void {
    const target = event.target as HTMLElement | null;
    if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
    if (event.metaKey || event.ctrlKey || event.altKey) return;

    const video = this.focusedVideo();
    switch (event.key.toLowerCase()) {
      case 'j': this.move(1); break;
      case 'k': this.move(-1); break;
      case 'a': if (video && this.queue() === 'pending') this.decide(video, 'approved'); break;
      case 'r': if (video && this.queue() === 'pending') this.decide(video, 'rejected'); break;
      default: return;
    }
    event.preventDefault();
  }
}
