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
import { RoadmapTreeComponent } from './roadmap-tree.component';
import { SignInDialogComponent } from '../../shared/components/sign-in-dialog/sign-in-dialog.component';

type RoadmapView = 'tree' | 'list';
const VIEW_KEY = 'dp_roadmap_view';
const BRANCHES_KEY = 'dp_roadmap_branches';

@Component({
  selector: 'app-roadmap-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, RoadmapTreeComponent, SignInDialogComponent],
  templateUrl: './roadmap-detail.component.html',
  styleUrls: ['./roadmap-detail.component.css']
})
export class RoadmapDetailComponent implements OnInit {
  roadmap = signal<Roadmap | null>(null);
  loading = signal(true);

  /** Tree or list. Remembered across visits — it's a strong personal preference either way. */
  private readonly storedView = signal<RoadmapView>('tree');
  /** Key of the step open in the tree's detail panel. */
  selectedKey = signal<string | null>(null);
  /** Step ids the user collapsed; everything is open by default — a path is meant to be read. */
  collapsed = signal<Set<number>>(new Set());
  /** The sign-in dialog, opened by a signed-out visitor touching anything on the tree. */
  signInOpen = signal(false);
  /**
   * The branch blurbs under the detail panel. Closed by default: six titles and six
   * paragraphs is the tallest block on the page, and open it buries whatever the user just
   * clicked on the tree. Remembered, so anyone reading the curriculum keeps it open.
   */
  branchesOpen = signal(false);

  /**
   * Signed out the page is a teaser: the shape of the path and nothing else. The list view,
   * the branch blurbs and the detail panel all give away the curriculum a step at a time, so
   * they only exist once there's an account to record progress against. The stored preference
   * is left untouched — signing in restores whichever view the user last chose.
   */
  readonly view = computed<RoadmapView>(() => this.auth.isAuthenticated() ? this.storedView() : 'tree');

  private readonly thumbs = new ThumbFallback();

  private readonly steps = computed(() => this.roadmap()?.stages.flatMap(s => s.steps) ?? []);
  private readonly moves = computed(() => this.steps().map(s => s.dance).filter((d): d is NonNullable<typeof d> => !!d));

  learnedCount = computed(() => this.moves().filter(d => d.isLearned).length);
  inProgressCount = computed(() => this.moves().filter(d => d.isInProgress).length);
  moveCount = computed(() => this.moves().length);
  progressPercent = computed(() =>
    this.moveCount() === 0 ? 0 : Math.round((this.learnedCount() / this.moveCount()) * 100));

  /**
   * What to do next: the shallowest unlearned move whose prerequisites are already met, so the
   * suggestion respects the tree rather than just reading top-to-bottom. Falls back to any
   * unlearned move when nothing is unlocked (e.g. signed out, where nothing is locked anyway).
   */
  nextStep = computed(() => {
    const unlearned = this.steps().filter(s => s.dance && !s.dance.isLearned);
    const ready = unlearned.filter(s => s.state === 'available');
    return [...(ready.length > 0 ? ready : unlearned)].sort((a, b) => a.depth - b.depth)[0] ?? null;
  });

  /** Branch titles on one line, so the collapsed row still says what the path covers. */
  branchSummary = computed(() => (this.roadmap()?.stages ?? []).map(s => s.title).join(' · '));

  /** The step behind the tree's detail panel. */
  selectedStep = computed(() => {
    const key = this.selectedKey();
    return key === null ? null : this.steps().find(s => s.key === key) ?? null;
  });

  constructor(
    private route: ActivatedRoute,
    private roadmapService: RoadmapService,
    private danceService: DanceService,
    private toast: ToastService,
    private title: Title,
    public auth: AuthService
  ) {}

  ngOnInit(): void {
    const stored = localStorage.getItem(VIEW_KEY);
    if (stored === 'tree' || stored === 'list') this.storedView.set(stored);
    this.branchesOpen.set(localStorage.getItem(BRANCHES_KEY) === '1');

    this.load();
  }

  private load(): void {
    const slug = this.route.snapshot.paramMap.get('slug') ?? '';
    this.roadmapService.getBySlug(slug).subscribe({
      next: r => {
        this.roadmap.set(r);
        this.loading.set(false);
        this.title.setTitle(`${r.title} roadmap · Dance Platform`);
        // Open the tree on the move they should do next, so the panel is never empty on arrival.
        // Signed out there is no panel, and a pre-ringed node would look like a selection that
        // did nothing — the tree rests unselected until they click and sign in.
        this.selectedKey.set(
          this.auth.isAuthenticated() ? this.nextStep()?.key ?? this.steps()[0]?.key ?? null : null);
      },
      error: () => {
        // Same contract as dance detail: show a not-found state rather than silently redirecting.
        // The template keys off roadmap() staying null once loading finishes.
        this.loading.set(false);
        this.title.setTitle('Roadmap not found · Dance Platform');
      }
    });
  }

  /**
   * Refetches the path now that there's a user on the request: states, learned flags and the
   * available count are all computed per-user server-side, so the signed-out payload is stale
   * the moment the dialog succeeds.
   */
  onSignedIn(): void {
    this.signInOpen.set(false);
    this.loading.set(true);
    this.roadmap.set(null);
    this.load();
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

  toggleBranches(): void {
    this.branchesOpen.update(open => !open);
    localStorage.setItem(BRANCHES_KEY, this.branchesOpen() ? '1' : '0');
  }

  setView(view: RoadmapView): void {
    this.storedView.set(view);
    localStorage.setItem(VIEW_KEY, view);
  }

  /**
   * Signed out, a node is the invitation to sign in rather than a way to read the move —
   * that's the only interactive thing left on the page, so it's where the wall goes.
   */
  onTreeSelect(step: RoadmapStep): void {
    if (!this.auth.isAuthenticated()) {
      this.signInOpen.set(true);
      return;
    }
    this.selectedKey.set(step.key);
  }

  /** Branch (stage) a step belongs to, for the detail panel's subtitle. */
  branchTitle(step: RoadmapStep): string {
    return this.roadmap()?.stages[step.stageIndex]?.title ?? '';
  }

  /** The steps this one comes after, resolved to titles so the panel can link back to them. */
  requiredTitles(step: RoadmapStep): { key: string; title: string; step: RoadmapStep }[] {
    const all = this.steps();
    return (step.requires ?? [])
      .map(key => all.find(s => s.key === key))
      .filter((s): s is RoadmapStep => !!s)
      .map(s => ({ key: s.key, title: s.title, step: s }));
  }

  /** Jumps to a step in whichever view is open — selecting it on the tree, scrolling to it in the list. */
  focusStep(step: RoadmapStep): void {
    if (this.view() === 'tree') {
      this.selectedKey.set(step.key);
      document.querySelector('[data-testid="roadmap-detail-panel"]')
        ?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      return;
    }
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
    this.roadmap.update(r => r && this.withStates({
      ...r,
      stages: r.stages.map(stage => ({
        ...stage,
        steps: stage.steps.map(step =>
          step.dance?.id === danceId ? { ...step, dance: { ...step.dance, ...flags } } : step)
      }))
    }));
  }

  /**
   * Recomputes every step's locked/available/learned state after a status change, mirroring
   * `RoadmapService.AssignStates`. Without this the tree wouldn't unlock the next branch until
   * a reload — the whole point of the tree is that ticking a move off opens what it leads to.
   *
   * A prerequisite with no catalog move can't be ticked off, so it never gates.
   */
  private withStates(roadmap: Roadmap): Roadmap {
    const steps = roadmap.stages.flatMap(s => s.steps);
    const known = new Set(steps.map(s => s.key));
    const authed = this.auth.isAuthenticated();

    // Mirrors RoadmapService.AssignStates. A step with no catalog move can't be ticked off, so it
    // passes through: satisfied exactly when its own prerequisites are.
    const satisfied = new Map(steps.map(s => [s.key, !!s.dance?.isLearned]));
    if (authed) {
      for (let pass = 0; pass < steps.length; pass++) {
        let changed = false;
        for (const step of steps) {
          if (step.dance) continue;
          const ok = (step.requires ?? []).every(key => !known.has(key) || satisfied.get(key) === true);
          if (ok !== satisfied.get(step.key)) { satisfied.set(step.key, ok); changed = true; }
        }
        if (!changed) break;
      }
    }

    let available = 0;
    const stages = roadmap.stages.map(stage => ({
      ...stage,
      steps: stage.steps.map(step => {
        let state: RoadmapStep['state'];
        if (step.dance?.isLearned) {
          state = 'learned';
        } else if (!authed) {
          state = 'available';
        } else {
          const blocked = (step.requires ?? []).some(key => known.has(key) && satisfied.get(key) !== true);
          state = blocked ? 'locked' : 'available';
        }
        if (state === 'available') available++;
        return step.state === state ? step : { ...step, state };
      })
    }));

    return { ...roadmap, stages, availableCount: available };
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
