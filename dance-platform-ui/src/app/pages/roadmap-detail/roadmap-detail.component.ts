import { Component, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { RoadmapService } from '../../core/services/roadmap.service';
import { DanceService, DanceStatus, statusFlags } from '../../core/services/dance.service';
import { AuthService } from '../../core/services/auth.service';
import { ToastService } from '../../core/services/toast.service';
import { Roadmap, RoadmapStep, RoadmapStepVideo } from '../../models/roadmap.model';
import { youtubeThumbUrl } from '../../core/utils/youtube-thumb.utils';
import { ThumbFallback } from '../../core/utils/thumb-fallback';

@Component({
  selector: 'app-roadmap-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './roadmap-detail.component.html',
  styleUrls: ['./roadmap-detail.component.css']
})
export class RoadmapDetailComponent implements OnInit {
  roadmap = signal<Roadmap | null>(null);
  loading = signal(true);
  /** Step ids the user collapsed; everything is open by default — a path is meant to be read. */
  collapsed = signal<Set<number>>(new Set());

  private readonly thumbs = new ThumbFallback();

  private readonly steps = computed(() => this.roadmap()?.stages.flatMap(s => s.steps) ?? []);
  private readonly moves = computed(() => this.steps().map(s => s.dance).filter((d): d is NonNullable<typeof d> => !!d));

  learnedCount = computed(() => this.moves().filter(d => d.isLearned).length);
  inProgressCount = computed(() => this.moves().filter(d => d.isInProgress).length);
  moveCount = computed(() => this.moves().length);
  progressPercent = computed(() =>
    this.moveCount() === 0 ? 0 : Math.round((this.learnedCount() / this.moveCount()) * 100));

  /** First step with a move the user hasn't learned — the "continue" target. */
  nextStep = computed(() => this.steps().find(s => s.dance && !s.dance.isLearned) ?? null);

  constructor(
    private route: ActivatedRoute,
    private roadmapService: RoadmapService,
    private danceService: DanceService,
    private toast: ToastService,
    private title: Title,
    public auth: AuthService
  ) {}

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug') ?? '';
    this.roadmapService.getBySlug(slug).subscribe({
      next: r => {
        this.roadmap.set(r);
        this.loading.set(false);
        this.title.setTitle(`${r.title} roadmap · Dance Platform`);
      },
      error: () => {
        // Same contract as dance detail: show a not-found state rather than silently redirecting.
        // The template keys off roadmap() staying null once loading finishes.
        this.loading.set(false);
        this.title.setTitle('Roadmap not found · Dance Platform');
      }
    });
  }

  /** Running 1-based index of a step across the whole path, for the node markers. */
  stepNumber(step: RoadmapStep): number {
    return this.steps().indexOf(step) + 1;
  }

  isCollapsed(step: RoadmapStep): boolean {
    return this.collapsed().has(step.id);
  }

  toggleCollapsed(step: RoadmapStep): void {
    this.collapsed.update(set => {
      const next = new Set(set);
      if (!next.delete(step.id)) next.add(step.id);
      return next;
    });
  }

  scrollToNext(): void {
    const step = this.nextStep();
    if (!step) return;
    document.getElementById(`step-${step.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  toggleLearned(step: RoadmapStep): void {
    if (!step.dance) return;
    this.setStatus(step, step.dance.isLearned ? 'notstarted' : 'learned');
  }

  toggleInProgress(step: RoadmapStep): void {
    if (!step.dance) return;
    this.setStatus(step, step.dance.isInProgress ? 'notstarted' : 'inprogress');
  }

  // Learned / in-progress are mutually exclusive and set in one atomic call, matching
  // dance detail and Browse. Flip locally first, revert if the save fails.
  private setStatus(step: RoadmapStep, status: DanceStatus): void {
    const dance = step.dance;
    if (!dance) return;
    const snap = { isLearned: dance.isLearned, isInProgress: dance.isInProgress };
    const flags = statusFlags(status);

    this.applyFlags(dance.id, flags);
    this.danceService.setStatus(dance.id, status).subscribe({
      error: () => {
        this.applyFlags(dance.id, snap);
        this.toast.error('Could not save that. Check you are still signed in.');
      }
    });
  }

  /**
   * Writes the flags onto every step pointing at this dance — a move can legitimately appear
   * in more than one stage, and they must not disagree about its status.
   */
  private applyFlags(danceId: number, flags: { isLearned: boolean; isInProgress: boolean }): void {
    this.roadmap.update(r => r && ({
      ...r,
      stages: r.stages.map(stage => ({
        ...stage,
        steps: stage.steps.map(step =>
          step.dance?.id === danceId ? { ...step, dance: { ...step.dance, ...flags } } : step)
      }))
    }));
  }

  videoThumb(videoId: string, platform: string, key: number): string | null {
    if (this.thumbs.has(key)) return null;
    return youtubeThumbUrl(videoId, platform);
  }

  onThumbError(key: number): void {
    this.thumbs.markFailed(key);
  }

  onThumbLoad(event: Event, key: number): void {
    // A missing YouTube thumbnail comes back as a 120x90 grey placeholder, not a 404.
    const img = event.target as HTMLImageElement;
    if (img.naturalHeight > 0 && img.naturalHeight <= 90) this.thumbs.markFailed(key);
  }

  /**
   * The videos a step should show. A step pinned to a segment shows only the video that
   * segment lives in — the rest of the dance's videos belong to other steps of the path.
   */
  stepVideos(step: RoadmapStep): RoadmapStepVideo[] {
    const videos = step.dance?.videos ?? [];
    const segment = step.segment;
    if (!segment) return videos;
    return videos.filter(v => v.id === segment.videoId);
  }

  /** Deep-links the player to this step's clip: the video, and the second it starts at. */
  stepVideoParams(step: RoadmapStep, video: RoadmapStepVideo): Record<string, number> {
    const params: Record<string, number> = { v: video.id };
    if (step.segment && step.segment.videoId === video.id) params['t'] = step.segment.startTime;
    return params;
  }

  /** "4:01 – 5:25" for a segment, so the step says up front how long the clip is. */
  segmentRange(step: RoadmapStep): string | null {
    const segment = step.segment;
    if (!segment) return null;
    const clock = (s: number) => `${Math.floor(s / 60)}:${Math.floor(s % 60).toString().padStart(2, '0')}`;
    return segment.endTime == null
      ? `from ${clock(segment.startTime)}`
      : `${clock(segment.startTime)} – ${clock(segment.endTime)}`;
  }

  /**
   * How long the user is actually being asked to watch. For a segment step that's the
   * segment's own span, not the whole tutorial it was cut from.
   */
  clipLength(step: RoadmapStep, v: RoadmapStepVideo): string | null {
    const segment = step.segment;
    const seconds = segment && segment.videoId === v.id && segment.endTime != null
      ? segment.endTime - segment.startTime
      : v.endTime != null
        ? v.endTime - (v.startTime ?? 0)
        : (v.durationSeconds ?? 0) - (v.startTime ?? 0);
    if (seconds <= 0) return null;
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }
}
