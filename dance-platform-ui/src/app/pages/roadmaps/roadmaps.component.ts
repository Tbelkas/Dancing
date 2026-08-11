import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { RoadmapService } from '../../core/services/roadmap.service';
import { AuthService } from '../../core/services/auth.service';
import { RoadmapSummary } from '../../models/roadmap.model';
import { youtubeThumbUrl } from '../../core/utils/youtube-thumb.utils';
import { ThumbFallback } from '../../core/utils/thumb-fallback';
import { delayedLoading } from '../../core/utils/delayed-loading';
import { SkeletonCount } from '../../core/utils/skeleton-count';
import { PERSONAL_ROADMAPS_ENABLED } from '../../core/constants/feature-flags';

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
  showSkeleton = delayedLoading(this.loading);
  readonly skeleton = new SkeletonCount('roadmaps', 6, { max: 12 });
  failed = signal(false);
  private readonly thumbs = new ThumbFallback();

  /** Gates every personal-tree surface on this page: the build button, the prompt, the grid. */
  readonly personalTrees = PERSONAL_ROADMAPS_ENABLED;

  /**
   * The user's own trees come first and are never mixed into the curated sections — a path
   * someone built is theirs, and burying it under "everything else" would make it feel like
   * the app's content rather than their own work.
   */
  mine = computed(() => this.roadmaps().filter(r => r.isOwned));

  private readonly curated = computed(() => this.roadmaps().filter(r => !r.isOwned));

  /** Curated paths the user has already started, surfaced above the rest. */
  started = computed(() => this.curated().filter(r => r.learnedCount + r.inProgressCount > 0));
  rest = computed(() => this.curated().filter(r => r.learnedCount + r.inProgressCount === 0));

  constructor(private roadmapService: RoadmapService, public auth: AuthService) {}

  ngOnInit(): void {
    this.roadmapService.getAll().subscribe({
      // Filtered here rather than per-section: with personal trees off, an owned tree must not
      // reach any of them — dropping it at the source keeps it out of "Everything else" too,
      // and keeps the empty state honest about what there is to show.
      next: list => {
        const r = this.personalTrees ? list : list.filter(x => !x.isOwned);
        this.roadmaps.set(r); this.skeleton.remember(r.length); this.loading.set(false);
      },
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
