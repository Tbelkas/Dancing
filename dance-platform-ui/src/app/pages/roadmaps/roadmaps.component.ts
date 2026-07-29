import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { RoadmapService } from '../../core/services/roadmap.service';
import { AuthService } from '../../core/services/auth.service';
import { RoadmapSummary } from '../../models/roadmap.model';
import { youtubeThumbUrl } from '../../core/utils/youtube-thumb.utils';
import { ThumbFallback } from '../../core/utils/thumb-fallback';

@Component({
  selector: 'app-roadmaps',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './roadmaps.component.html',
  styleUrls: ['./roadmaps.component.css']
})
export class RoadmapsComponent implements OnInit {
  roadmaps = signal<RoadmapSummary[]>([]);
  loading = signal(true);
  failed = signal(false);
  private readonly thumbs = new ThumbFallback();

  /** Paths the user has already started, surfaced above the rest. */
  started = computed(() => this.roadmaps().filter(r => r.learnedCount + r.inProgressCount > 0));
  rest = computed(() => this.roadmaps().filter(r => r.learnedCount + r.inProgressCount === 0));

  constructor(private roadmapService: RoadmapService, public auth: AuthService) {}

  ngOnInit(): void {
    this.roadmapService.getAll().subscribe({
      next: r => { this.roadmaps.set(r); this.loading.set(false); },
      error: () => { this.failed.set(true); this.loading.set(false); }
    });
  }

  /** Percent of the path's linked moves marked learned. */
  progressPercent(r: RoadmapSummary): number {
    return r.moveCount === 0 ? 0 : Math.round((r.learnedCount / r.moveCount) * 100);
  }

  thumbnailUrl(r: RoadmapSummary): string | null {
    if (this.thumbs.has(r.id)) return null;
    return youtubeThumbUrl(r.thumbnailVideoId, r.thumbnailPlatform);
  }

  onThumbError(r: RoadmapSummary): void {
    this.thumbs.markFailed(r.id);
  }

  onThumbLoad(event: Event, r: RoadmapSummary): void {
    // YouTube answers a missing thumbnail with a 120x90 grey placeholder rather than a 404,
    // so treat an undersized image as a failure and fall back to the branded tile.
    const img = event.target as HTMLImageElement;
    if (img.naturalHeight > 0 && img.naturalHeight <= 90) this.thumbs.markFailed(r.id);
  }
}
