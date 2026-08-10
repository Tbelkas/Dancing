import { Component, OnDestroy, OnInit, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { Subject, debounceTime, distinctUntilChanged, switchMap } from 'rxjs';
import { RoadmapService } from '../../core/services/roadmap.service';
import { StyleService } from '../../core/services/style.service';
import { DanceService } from '../../core/services/dance.service';
import { VideoService } from '../../core/services/video.service';
import { ToastService } from '../../core/services/toast.service';
import { Style } from '../../models/style.model';
import { Dance } from '../../models/dance.model';
import { Video, VideoSegment } from '../../models/video.model';
import { Roadmap, SaveRoadmap } from '../../models/roadmap.model';
import { withGraphState } from '../../core/utils/roadmap-graph';
import { HasUnsavedChanges } from '../../core/guards/unsaved-changes.guard';
import { RoadmapTreeComponent } from '../roadmap-detail/roadmap-tree.component';
import { delayedLoading } from '../../core/utils/delayed-loading';

/**
 * The draft a tree is edited as. Deliberately not the read model: a step being written has a
 * dance *name* to show in the picker but no videos, no rating and no state, and forcing it into
 * `RoadmapStep` would mean inventing all of that on every keystroke.
 */
interface DraftStep {
  /** Stable within the draft; what `requires` names, and what the server stores as the key. */
  key: string;
  title: string;
  description: string;
  danceId: number | null;
  /** Display only — the picker searched by name, and the payload carries the id. */
  danceName: string;
  /**
   * Narrows the step to one section of one of the dance's videos, or null for the whole move.
   * A tree copied from a curated path arrives with these already set, so they are also carried
   * through untouched by anything that doesn't deliberately change them.
   */
  videoSegmentId: number | null;
  /** Display only — the section's label, so a pinned step reads without a lookup. */
  segmentLabel: string;
  /**
   * Set when this step is a gateway into one of the user's own trees rather than a move.
   * Mutually exclusive with `danceId`; the UI only offers one of the two at a time.
   */
  childRoadmapId: number | null;
  /** Display only — the module's name and URL, so the row reads without another fetch. */
  moduleTitle: string;
  moduleSlug: string;
  requires: string[];
}

interface DraftStage {
  /** Local identity for @for tracking — the title changes as it's typed, so it can't be the key. */
  id: number;
  title: string;
  description: string;
  steps: DraftStep[];
}

@Component({
  selector: 'app-roadmap-builder',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RoadmapTreeComponent],
  templateUrl: './roadmap-builder.component.html',
  styleUrls: ['./roadmap-builder.component.css']
})
export class RoadmapBuilderComponent implements OnInit, OnDestroy, HasUnsavedChanges {
  /** Null while building a new tree; the row id once we're editing a saved one. */
  roadmapId = signal<number | null>(null);
  slug = signal<string | null>(null);

  title = signal('');
  subtitle = signal('');
  description = signal('');
  styleId = signal<number | null>(null);
  stages = signal<DraftStage[]>([]);

  styles = signal<Style[]>([]);
  loading = signal(true);
  showSkeleton = delayedLoading(this.loading);
  saving = signal(false);
  /** Set when the slug isn't a tree the user owns — a curated path lands here too. */
  denied = signal(false);
  error = signal('');

  /** Key of the step whose move picker is open; only ever one, so the results can be shared. */
  pickerFor = signal<string | null>(null);
  danceQuery = signal('');
  danceResults = signal<Dance[]>([]);
  searching = signal(false);

  /** Key of the step whose clip picker is open, and the videos behind it. */
  clipPickerFor = signal<string | null>(null);
  clipVideos = signal<Video[]>([]);
  loadingClips = signal(false);
  /**
   * Videos by dance id, so reopening a picker (or opening it on a second step backed by the
   * same tutorial — which is the normal case for a sliced-up class video) doesn't refetch.
   */
  private readonly videoCache = new Map<number, Video[]>();

  /** Node selected on the preview, mirrored onto the matching row in the form. */
  selectedKey = signal<string | null>(null);

  /** Key of the step whose module is being created, so the button can't be double-fired. */
  moduleBusy = signal<string | null>(null);

  private readonly search$ = new Subject<string>();
  private nextId = 1;

  /**
   * Everything a save would send, as one string.
   *
   * Dirtiness is a comparison against the last saved snapshot rather than a flag set by each
   * edit handler: there are a dozen ways to mutate the draft, a flag would be forgotten by the
   * thirteenth, and typing something and typing it back out again would leave the page falsely
   * dirty. `key` is deliberately included — reordering moves changes the payload.
   */
  private readonly snapshot = computed(() => JSON.stringify({
    title: this.title().trim(),
    subtitle: this.subtitle().trim(),
    description: this.description().trim(),
    styleId: this.styleId(),
    stages: this.stages().map(stage => ({
      title: stage.title.trim(),
      description: stage.description.trim(),
      steps: stage.steps.map(step => ({
        key: step.key,
        title: step.title.trim(),
        description: step.description.trim(),
        danceId: step.danceId,
        videoSegmentId: step.videoSegmentId,
        childRoadmapId: step.childRoadmapId,
        requires: step.requires
      }))
    }))
  }));

  /** The snapshot as the server last saw it. Reset on load and after every successful save. */
  private readonly savedSnapshot = signal('');

  readonly dirty = computed(() => this.snapshot() !== this.savedSnapshot());

  hasUnsavedChanges(): boolean {
    // Nothing to lose while the save is in flight — it's about to become the saved state.
    return !this.saving() && this.dirty();
  }

  unsavedChangesMessage(): string {
    return 'This skill tree has changes you haven\'t saved. Leave the page and lose them?';
  }

  /**
   * A tab close or reload never reaches the router, so the guard can't see it. Browsers ignore
   * any custom text here and show their own wording — returning a value is the whole API.
   */
  private readonly beforeUnload = (event: BeforeUnloadEvent) => {
    if (!this.hasUnsavedChanges()) return;
    event.preventDefault();
    event.returnValue = '';
  };

  readonly isNew = computed(() => this.roadmapId() === null);

  /**
   * Whether the *route* is /roadmaps/new — which `isNew()` can't answer during the load, since
   * roadmapId is null until the fetch lands. Editing an existing tree used to spend the whole
   * wait with a breadcrumb reading "Roadmaps / New skill tree". Set in ngOnInit, before the
   * first render, from the same snapshot the loader uses.
   */
  isNewRoute = true;

  /** Placeholder form cards, one array of fields each: "The tree" carries four inputs, then a
   *  branch card apiece. Enough to reserve the fold — the real form runs much longer. */
  readonly skeletonCards = [[0, 1, 2, 3], [0, 1], [0, 1]];

  private readonly allSteps = computed(() =>
    this.stages().flatMap((stage, si) => stage.steps.map(step => ({ step, stage, stageIndex: si }))));

  readonly stepCount = computed(() => this.allSteps().length);
  readonly linkedCount = computed(() => this.allSteps().filter(s => s.step.danceId !== null).length);

  readonly styleName = computed(() =>
    this.styles().find(s => s.id === this.styleId())?.name ?? '');

  /**
   * The draft as the tree component wants it, so the shape being built is on screen while it is
   * being built — the sequencing is the whole point of a skill tree and a form can't show it.
   *
   * Rendered as if signed out (`withGraphState(…, false)`): nothing in a draft is learned, so the
   * signed-in rules would paint every non-root node locked and the preview would be a wall of
   * padlocks that says nothing about the structure.
   */
  readonly preview = computed<Roadmap | null>(() => {
    const rows = this.allSteps();
    if (rows.length === 0) return null;

    const draft: Roadmap = {
      id: this.roadmapId() ?? 0,
      slug: this.slug() ?? 'draft',
      title: this.title(),
      subtitle: this.subtitle(),
      styleId: this.styleId() ?? 0,
      styleName: this.styleName(),
      styleSlug: '',
      isOwned: true,
      // A draft is never shared — sharing is toggled on the saved tree, not in here.
      isPublic: false,
      stageCount: this.stages().length,
      stepCount: rows.length,
      moveCount: this.linkedCount(),
      videoCount: 0,
      learnedCount: 0,
      inProgressCount: 0,
      availableCount: 0,
      stages: this.stages().map((stage, si) => ({
        id: stage.id,
        title: stage.title,
        description: stage.description,
        steps: stage.steps.map((step, pi) => ({
          id: si * 1000 + pi,
          key: step.key,
          requires: step.requires,
          stageIndex: si,
          depth: 0,          // withGraphState assigns the real ring
          state: 'available' as const,
          title: step.title || 'Untitled move',
          description: step.description,
          // Only its truthiness is read by the tree (it drives the "no video yet" dot), so a
          // stub is enough — the draft has no videos or ratings to put in a real one.
          dance: step.danceId === null ? undefined : {
            id: step.danceId, name: step.danceName, slug: '', styleSlug: '',
            difficulty: '', averageRating: 0, ratingCount: 0,
            isLearned: false, isInProgress: false, isFavorite: false, videos: []
          },
          // Enough for the preview to draw the gateway glyph. Counts are zero because the draft
          // has never asked the server what is inside the module — and the preview renders as
          // signed out anyway, where no progress is shown.
          module: step.childRoadmapId === null ? undefined : {
            id: step.childRoadmapId, slug: step.moduleSlug, title: step.moduleTitle,
            subtitle: '', stepCount: 0, completableCount: 0, learnedCount: 0, isComplete: false
          }
        }))
      }))
    };

    return withGraphState(draft, false);
  });

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private roadmapService: RoadmapService,
    private styleService: StyleService,
    private danceService: DanceService,
    private videoService: VideoService,
    private toast: ToastService,
    private titleService: Title
  ) {}

  ngOnInit(): void {
    this.isNewRoute = !this.route.snapshot.paramMap.get('slug');
    window.addEventListener('beforeunload', this.beforeUnload);
    this.styleService.getAll().subscribe(s => this.styles.set(s));

    this.search$.pipe(
      debounceTime(250),
      distinctUntilChanged(),
      switchMap(q => {
        this.searching.set(true);
        // Scoped to the tree's style: a House path shouldn't be offering waacking moves, and
        // the unscoped catalog is 700 rows deep.
        return this.danceService.searchDances({ q, styleId: this.styleId(), pageSize: 10, sortBy: 'name' });
      })
    ).subscribe({
      next: r => { this.danceResults.set(r.items); this.searching.set(false); },
      error: () => { this.danceResults.set([]); this.searching.set(false); }
    });

    const slug = this.route.snapshot.paramMap.get('slug');
    if (!slug) {
      // A blank tree still opens with one branch and one move: an empty form gives no clue that
      // branches are the thing you fill in.
      this.stages.set([this.blankStage('Getting started')]);
      // The blank form is the baseline, so opening the builder and leaving without typing
      // anything doesn't count as unsaved work.
      this.markClean();
      this.loading.set(false);
      this.titleService.setTitle('New skill tree · Dance Platform');
      return;
    }

    this.roadmapService.getBySlug(slug).subscribe({
      next: r => {
        // Curated paths are authored content, edited by editing their JSON file. The API refuses
        // the save anyway; catching it here means not letting someone fill a form that can't save.
        if (!r.isOwned) { this.denied.set(true); this.loading.set(false); return; }
        this.hydrate(r);
        this.loading.set(false);
        this.titleService.setTitle(`Editing ${r.title} · Dance Platform`);
      },
      error: () => { this.denied.set(true); this.loading.set(false); }
    });
  }

  /** Loads a saved tree into the draft, keeping the server's keys so `requires` still resolves. */
  private hydrate(r: Roadmap): void {
    this.roadmapId.set(r.id);
    this.slug.set(r.slug);
    this.title.set(r.title);
    this.subtitle.set(r.subtitle ?? '');
    this.description.set(r.description ?? '');
    this.styleId.set(r.styleId);
    this.stages.set(r.stages.map(stage => ({
      id: this.nextId++,
      title: stage.title,
      description: stage.description ?? '',
      steps: stage.steps.map(step => ({
        key: step.key,
        title: step.title,
        description: step.description ?? '',
        danceId: step.dance?.id ?? null,
        childRoadmapId: step.module?.id ?? null,
        moduleTitle: step.module?.title ?? '',
        moduleSlug: step.module?.slug ?? '',
        danceName: step.dance?.name ?? '',
        videoSegmentId: step.segment?.id ?? null,
        segmentLabel: step.segment?.label ?? '',
        requires: [...step.requires]
      }))
    })));
    this.markClean();
  }

  /** Takes what's on screen as the saved state. */
  private markClean(): void {
    this.savedSnapshot.set(this.snapshot());
  }

  ngOnDestroy(): void {
    window.removeEventListener('beforeunload', this.beforeUnload);
  }

  // ---- Branches ---------------------------------------------------------------------------

  private blankStage(title: string): DraftStage {
    return { id: this.nextId++, title, description: '', steps: [this.blankStep()] };
  }

  private blankStep(): DraftStep {
    return {
      key: this.freshKey(), title: '', description: '',
      danceId: null, danceName: '', videoSegmentId: null, segmentLabel: '',
      childRoadmapId: null, moduleTitle: '', moduleSlug: '', requires: []
    };
  }

  /**
   * A key nothing else in the draft is using. It never has to be pretty — the server slugifies
   * what it stores — only unique, so a `requires` can't land on two steps.
   */
  private freshKey(): string {
    const taken = new Set(this.stages().flatMap(s => s.steps.map(p => p.key)));
    let key = `move-${this.nextId++}`;
    while (taken.has(key)) key = `move-${this.nextId++}`;
    return key;
  }

  addStage(): void {
    this.stages.update(list => [...list, this.blankStage('')]);
  }

  removeStage(index: number): void {
    const doomed = new Set(this.stages()[index]?.steps.map(s => s.key) ?? []);
    this.stages.update(list => list
      .filter((_, i) => i !== index)
      // Prune the edges into the branch that just went, or they'd be dropped silently on save
      // and the preview would disagree with the form until then.
      .map(stage => ({ ...stage, steps: stage.steps.map(step => ({
        ...step, requires: step.requires.filter(k => !doomed.has(k))
      })) })));
  }

  moveStage(index: number, delta: number): void {
    this.stages.update(list => {
      const next = [...list];
      const target = index + delta;
      if (target < 0 || target >= next.length) return list;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  setStage(index: number, patch: Partial<DraftStage>): void {
    this.stages.update(list => list.map((stage, i) => i === index ? { ...stage, ...patch } : stage));
  }

  // ---- Moves ------------------------------------------------------------------------------

  addStep(stageIndex: number): void {
    const step = this.blankStep();
    this.stages.update(list => list.map((stage, i) =>
      i === stageIndex ? { ...stage, steps: [...stage.steps, step] } : stage));
  }

  removeStep(stageIndex: number, key: string): void {
    this.stages.update(list => list.map((stage, i) => ({
      ...stage,
      steps: (i === stageIndex ? stage.steps.filter(s => s.key !== key) : stage.steps)
        .map(step => ({ ...step, requires: step.requires.filter(k => k !== key) }))
    })));
  }

  moveStep(stageIndex: number, index: number, delta: number): void {
    this.stages.update(list => list.map((stage, i) => {
      if (i !== stageIndex) return stage;
      const steps = [...stage.steps];
      const target = index + delta;
      if (target < 0 || target >= steps.length) return stage;
      [steps[index], steps[target]] = [steps[target], steps[index]];
      return { ...stage, steps };
    }));
  }

  setStep(key: string, patch: Partial<DraftStep>): void {
    this.stages.update(list => list.map(stage => ({
      ...stage,
      steps: stage.steps.map(step => step.key === key ? { ...step, ...patch } : step)
    })));
  }

  // ---- Prerequisites ----------------------------------------------------------------------

  /**
   * The moves this one could be made to come after: everything except itself, what it already
   * comes after, and anything that already comes after it.
   *
   * Filtering the cycles out of the dropdown rather than rejecting them on save is the point —
   * the server refuses a cycle, and finding that out at save time means being told a tree you
   * spent ten minutes on won't store.
   */
  prerequisiteOptions(step: DraftStep): { key: string; label: string }[] {
    return this.allSteps()
      .filter(row => row.step.key !== step.key)
      .filter(row => !step.requires.includes(row.step.key))
      .filter(row => !this.reaches(row.step.key, step.key))
      .map(row => ({
        key: row.step.key,
        label: `${row.step.title || 'Untitled move'} — ${row.stage.title || 'unnamed branch'}`
      }));
  }

  /** True when `to` is reachable from `from` by following `requires` — i.e. adding the reverse cycles. */
  private reaches(from: string, to: string): boolean {
    const byKey = new Map(this.allSteps().map(r => [r.step.key, r.step]));
    const seen = new Set<string>();
    const stack = [from];
    while (stack.length > 0) {
      const current = stack.pop()!;
      if (current === to) return true;
      if (seen.has(current)) continue;
      seen.add(current);
      for (const key of byKey.get(current)?.requires ?? []) stack.push(key);
    }
    return false;
  }

  addPrerequisite(step: DraftStep, key: string): void {
    if (!key || step.requires.includes(key)) return;
    this.setStep(step.key, { requires: [...step.requires, key] });
  }

  /** The dropdown is a command rather than a field, so it snaps back to its placeholder. */
  addPrerequisiteFrom(step: DraftStep, select: HTMLSelectElement): void {
    this.addPrerequisite(step, select.value);
    select.value = '';
  }

  removePrerequisite(step: DraftStep, key: string): void {
    this.setStep(step.key, { requires: step.requires.filter(k => k !== key) });
  }

  /** The title behind a `requires` key, for the chips. */
  stepTitle(key: string): string {
    return this.allSteps().find(r => r.step.key === key)?.step.title || 'Untitled move';
  }

  // ---- The move picker --------------------------------------------------------------------

  openPicker(step: DraftStep): void {
    this.pickerFor.set(step.key);
    this.danceQuery.set(step.title);
    this.danceResults.set([]);
    // Seed the results from the step's own title — nine times in ten that's what it's called.
    if (step.title.trim()) this.search$.next(step.title.trim());
  }

  onDanceQuery(value: string): void {
    this.danceQuery.set(value);
    this.search$.next(value.trim());
  }

  chooseDance(step: DraftStep, dance: Dance): void {
    this.setStep(step.key, {
      danceId: dance.id,
      danceName: dance.name,
      // A clip pinned against the old move means nothing against a new one.
      videoSegmentId: null,
      segmentLabel: '',
      // An untitled step takes the move's name; a titled one keeps what the author wrote, which
      // is the rule the curated paths follow — the step's title is the teaching, not the label.
      title: step.title.trim() || dance.name
    });
    this.pickerFor.set(null);
  }

  clearDance(step: DraftStep): void {
    this.setStep(step.key, { danceId: null, danceName: '', videoSegmentId: null, segmentLabel: '' });
  }

  // ---- The clip picker --------------------------------------------------------------------

  /**
   * Pinning a step to one section of a video is the difference between a curriculum and a
   * playlist: without it a step backed by an 11-minute class says "watch all of this" — and the
   * consolidated tutorials mean that is the common case, not the exception (see VIDEO_FIXUP.md).
   */
  openClipPicker(step: DraftStep): void {
    if (step.danceId === null) return;
    this.clipPickerFor.set(step.key);

    const cached = this.videoCache.get(step.danceId);
    if (cached) { this.clipVideos.set(cached); return; }

    this.clipVideos.set([]);
    this.loadingClips.set(true);
    const danceId = step.danceId;
    this.videoService.getByDance(danceId).subscribe({
      next: videos => {
        this.videoCache.set(danceId, videos);
        // Still the open one? A fast click through two steps could land these out of order.
        if (this.clipPickerFor() === step.key) this.clipVideos.set(videos);
        this.loadingClips.set(false);
      },
      error: () => { this.loadingClips.set(false); this.toast.error('Could not load that move’s videos.'); }
    });
  }

  /** Videos of the open picker's dance that actually have sections to pin to. */
  readonly clipVideosWithSections = computed(() => this.clipVideos().filter(v => v.segments.length > 0));

  chooseSegment(step: DraftStep, segment: VideoSegment): void {
    this.setStep(step.key, { videoSegmentId: segment.id, segmentLabel: segment.label });
    this.clipPickerFor.set(null);
  }

  /**
   * Turns a step into a module gateway by creating a fresh tree for it and linking the two.
   *
   * The child is created and the parent saved in one go, deliberately. The alternative — link
   * now, save later — leaves a tree on the user's index that nothing points at if they wander
   * off, and the link itself only means anything once the parent is stored.
   *
   * Requires the parent to be saved already: a module is a link between two rows, and a tree
   * being built for the first time has no row to link from.
   */
  makeModule(step: DraftStep): void {
    const styleId = this.styleId();
    if (this.roadmapId() === null) {
      this.error.set('Save the tree once before adding a module to it.');
      return;
    }
    if (!styleId) { this.error.set('Pick a style for the tree first.'); return; }
    if (this.moduleBusy() !== null) return;

    this.moduleBusy.set(step.key);
    this.error.set('');
    this.roadmapService.create({
      title: step.title.trim() || 'New module',
      subtitle: `Part of ${this.title().trim() || 'a skill tree'}`,
      styleId,
      stages: [{ title: 'First branch', description: '', steps: [] }]
    }).subscribe({
      next: created => {
        this.moduleBusy.set(null);
        // A module replaces the move — "learned" would otherwise have two definitions.
        this.setStep(step.key, {
          childRoadmapId: created.id,
          moduleTitle: created.title,
          moduleSlug: created.slug,
          danceId: null, danceName: '', videoSegmentId: null, segmentLabel: ''
        });
        this.save();
      },
      error: () => {
        this.moduleBusy.set(null);
        this.error.set('Could not create the module. Check you are still signed in.');
      }
    });
  }

  /**
   * Unlinks a module without deleting it: it becomes a normal tree on the user's index, which
   * they can open, keep or delete. Silently destroying a subtree on a mis-click would be a far
   * worse default than an extra row on the shelf.
   */
  clearModule(step: DraftStep): void {
    this.setStep(step.key, { childRoadmapId: null, moduleTitle: '', moduleSlug: '' });
  }

  /**
   * Saves the parent, then opens the module's own builder. Saving first is not optional — both
   * builder routes carry the unsaved-changes guard, so navigating dirty would challenge the user
   * over changes they are about to keep anyway.
   */
  editModule(step: DraftStep): void {
    if (!step.moduleSlug) return;
    const go = () => void this.router.navigate(['/roadmaps', step.moduleSlug, 'edit']);
    if (!this.dirty()) { go(); return; }
    this.save(go);
  }

  clearSegment(step: DraftStep): void {
    this.setStep(step.key, { videoSegmentId: null, segmentLabel: '' });
  }

  /** "4:01 – 5:25", or "from 4:01" for a section with no end. */
  segmentRange(segment: VideoSegment): string {
    const clock = (s: number) => `${Math.floor(s / 60)}:${Math.floor(s % 60).toString().padStart(2, '0')}`;
    return segment.endTime == null
      ? `from ${clock(segment.startTime)}`
      : `${clock(segment.startTime)} – ${clock(segment.endTime)}`;
  }

  // ---- Saving -----------------------------------------------------------------------------

  /** Jumps the form to the step clicked on the preview. */
  onPreviewSelect(step: { key: string }): void {
    this.selectedKey.set(step.key);
    document.getElementById(`draft-${step.key}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  save(then?: () => void): void {
    if (this.saving()) return;

    const title = this.title().trim();
    if (!title) { this.error.set('Give the tree a name.'); return; }
    const styleId = this.styleId();
    if (!styleId) { this.error.set('Pick a style for the tree.'); return; }

    this.error.set('');
    this.saving.set(true);

    const payload: SaveRoadmap = {
      title,
      subtitle: this.subtitle().trim(),
      description: this.description().trim(),
      styleId,
      stages: this.stages().map(stage => ({
        title: stage.title.trim(),
        description: stage.description.trim(),
        steps: stage.steps
          // Rows never filled in are dropped rather than saved as nameless nodes. The server
          // does the same, but doing it here keeps what's sent and what's stored the same shape.
          .filter(step => step.title.trim().length > 0)
          .map(step => ({
            key: step.key,
            title: step.title.trim(),
            description: step.description.trim(),
            danceId: step.danceId,
            videoSegmentId: step.videoSegmentId,
            childRoadmapId: step.childRoadmapId,
            requires: step.requires
          }))
      }))
    };

    const id = this.roadmapId();
    const request = id === null
      ? this.roadmapService.create(payload)
      : this.roadmapService.update(id, payload);

    request.subscribe({
      next: saved => {
        this.saving.set(false);
        // Rehydrate rather than leave the draft as typed: the server rewrites keys, drops empty
        // rows and prunes stale edges, and the form should show what is actually stored. It also
        // clears the dirty flag, which the navigation below depends on — otherwise saving a new
        // tree would immediately be challenged by the unsaved-changes guard on the way out.
        this.hydrate(saved);

        if (id === null) {
          // Straight to the tree on the first save: the payoff for filling the form in is seeing
          // the thing you built, not the form again with a toast over it.
          this.toast.success('Skill tree created.');
          if (then) { then(); return; }
          void this.router.navigate(['/roadmaps', saved.slug]);
          return;
        }
        this.toast.success('Saved.');
        then?.();
      },
      error: err => {
        this.saving.set(false);
        this.error.set(err?.error?.message ?? 'Could not save the tree. Check you are still signed in.');
      }
    });
  }
}
