import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { VideoService } from '../../core/services/video.service';
import { VideoFlag } from '../../models/video-flag.model';

type Queue = 'open' | 'resolved';

/**
 * Problem reports: what viewers said is broken, plus whatever the nightly availability checker
 * found. One queue for both — a dead embed and a mis-filed clip are the same job for whoever
 * clears them, and two queues would mean one of them going unread.
 */
@Component({
  selector: 'app-admin-flags',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './admin-flags.component.html',
  styleUrls: ['./admin-flags.component.css']
})
export class AdminFlagsComponent implements OnInit {
  queue = signal<Queue>('open');
  flags = signal<VideoFlag[]>([]);
  loading = signal(true);
  loadError = signal(false);
  busyId = signal<number | null>(null);
  message = signal('');

  /** Per-flag resolution text, keyed by flag id — each row keeps its own half-typed note. */
  resolutions: Record<number, string> = {};

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
    this.videoService.getFlags(this.queue()).subscribe({
      next: list => { this.flags.set(list); this.loading.set(false); this.loadError.set(false); },
      error: () => { this.loading.set(false); this.loadError.set(true); }
    });
  }

  /** Where the source actually lives, so a dead-video report can be checked at the source. */
  sourceUrl(flag: VideoFlag): string {
    switch (flag.platform) {
      case 'tiktok': return `https://www.tiktok.com/embed/${flag.sourceVideoId}`;
      case 'instagram': return `https://www.instagram.com/reel/${flag.sourceVideoId}/`;
      default: return `https://www.youtube.com/watch?v=${flag.sourceVideoId}`;
    }
  }

  resolve(flag: VideoFlag, fallback: string): void {
    if (this.busyId()) return;
    this.busyId.set(flag.id);
    const resolution = (this.resolutions[flag.id] ?? '').trim() || fallback;
    this.videoService.resolveFlag(flag.id, resolution).subscribe({
      next: () => {
        this.flags.update(list => list.filter(f => f.id !== flag.id));
        delete this.resolutions[flag.id];
        this.busyId.set(null);
        this.message.set(`Closed the report on "${flag.videoTitle}" as ${resolution}.`);
      },
      error: () => { this.busyId.set(null); this.message.set("That didn't save. Try again."); }
    });
  }
}
