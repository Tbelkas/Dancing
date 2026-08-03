import { AfterViewInit, Component, ElementRef, EventEmitter, Input, OnDestroy, OnInit, Output, ViewChild, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Roadmap, RoadmapStep } from '../../models/roadmap.model';
import { TreeNode, layoutRoadmapTree } from '../../core/utils/roadmap-tree.layout';

const LEGEND_KEY = 'dp_roadmap_legend';

/**
 * The roadmap as a radial skill tree. Presentation only — it owns hover/focus and the geometry,
 * and hands selection back up so the page can render the detail panel and the status controls.
 */
@Component({
  selector: 'app-roadmap-tree',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './roadmap-tree.component.html',
  styleUrls: ['./roadmap-tree.component.css']
})
export class RoadmapTreeComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly roadmapSignal = signal<Roadmap | null>(null);

  @Input({ required: true }) set roadmap(value: Roadmap) {
    this.roadmapSignal.set(value);
  }

  /** Key of the step the page currently has open, so the tree can ring it. */
  @Input() set selectedKey(value: string | null) {
    this.selected.set(value);
    // A different step means different panel content, so the overflow state is stale.
    this.scheduleAsideMeasure();
  }

  @Output() stepSelected = new EventEmitter<RoadmapStep>();

  protected readonly selected = signal<string | null>(null);
  protected readonly hovered = signal<string | null>(null);

  /**
   * The colour key. Folded away by default — it's a one-time read, and left open it costs the
   * same vertical space on every visit as the detail panel it pushes down. Remembered so the
   * people who do want it standing open only have to say so once.
   */
  protected readonly legendOpen = signal(localStorage.getItem(LEGEND_KEY) === '1');

  protected toggleLegend(): void {
    this.legendOpen.update(open => !open);
    localStorage.setItem(LEGEND_KEY, this.legendOpen() ? '1' : '0');
  }

  /**
   * The tree is the one thing on the page that is always too small — 31 nodes on a fan, capped
   * by the column width, with the labels suppressed to stop them colliding. Fullscreen gives it
   * the whole viewport, which is enough room for the lineage highlighting to actually be read.
   *
   * The whole `.tree` block goes fullscreen rather than the bare <svg>: a fullscreened <svg> takes
   * the page background with it (black) and leaves the key behind.
   */
  @ViewChild('treeRoot') private treeRoot?: ElementRef<HTMLElement>;

  protected readonly isFullscreen = signal(false);

  /** iOS Safari fullscreens only <video>, so the button is hidden there rather than left dead. */
  protected get canFullscreen(): boolean {
    return typeof document !== 'undefined' && document.fullscreenEnabled;
  }

  protected toggleFullscreen(): void {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void this.treeRoot?.nativeElement.requestFullscreen();
    }
  }

  /** Esc and the browser's own exit affordance both bypass the button — follow the document. */
  private readonly fullscreenHandler = () => {
    this.isFullscreen.set(document.fullscreenElement != null);
    this.scheduleAsideMeasure();
  };

  /**
   * Whether the detail panel has content below the fold. In fullscreen the panel is capped by
   * the screen height, and a long step simply ran off the bottom edge with nothing to say so —
   * it read as the end of the text. This drives a fade at the bottom edge; `has-more` clears
   * once you reach the end, so a panel that fits is never decorated.
   */
  @ViewChild('treeAside') private treeAside?: ElementRef<HTMLElement>;
  protected readonly asideMore = signal(false);

  protected onAsideScroll(): void {
    this.measureAside();
  }

  private measureAside(): void {
    const el = this.treeAside?.nativeElement;
    // Out of fullscreen the aside is display:contents and never scrolls, so scrollHeight
    // tracks clientHeight and this is false — no need to special-case it.
    this.asideMore.set(!!el && el.scrollHeight - el.clientHeight - el.scrollTop > 1);
  }

  /** Re-measure after the DOM settles — entering fullscreen and swapping step both resize it. */
  private scheduleAsideMeasure(): void {
    setTimeout(() => this.measureAside());
  }

  private readonly resizeHandler = () => this.measureAside();
  private asideObserver?: ResizeObserver;

  ngOnInit(): void {
    document.addEventListener('fullscreenchange', this.fullscreenHandler);
    window.addEventListener('resize', this.resizeHandler);
  }

  /**
   * The panel's height also changes from inside it — expanding a step's videos, say — and that
   * click never reaches this component. An observer catches those; the scroll and selection
   * hooks alone would leave the fade stale.
   */
  ngAfterViewInit(): void {
    const el = this.treeAside?.nativeElement;
    if (!el || typeof ResizeObserver === 'undefined') return;
    this.asideObserver = new ResizeObserver(() => this.measureAside());
    this.asideObserver.observe(el);
    if (el.firstElementChild) this.asideObserver.observe(el.firstElementChild);
  }

  ngOnDestroy(): void {
    document.removeEventListener('fullscreenchange', this.fullscreenHandler);
    window.removeEventListener('resize', this.resizeHandler);
    this.asideObserver?.disconnect();
    // Navigating away from a fullscreened tree would otherwise leave the next page fullscreen.
    if (document.fullscreenElement === this.treeRoot?.nativeElement) void document.exitFullscreen();
  }

  protected readonly layout = computed(() => {
    const roadmap = this.roadmapSignal();
    return roadmap ? layoutRoadmapTree(roadmap) : null;
  });

  /** Stage titles, used for the branch legend under the tree. */
  protected readonly stages = computed(() => this.roadmapSignal()?.stages.map(s => s.title) ?? []);

  /**
   * The keys on the path from a root to the hovered/selected node. Highlighting the whole
   * lineage is what makes a tree readable — you see what a move is built on, not just where it sits.
   */
  protected readonly lineage = computed(() => {
    const focus = this.hovered() ?? this.selected();
    const roadmap = this.roadmapSignal();
    if (!focus || !roadmap) return new Set<string>();

    const byKey = new Map(roadmap.stages.flatMap(s => s.steps).map(s => [s.key, s]));
    const chain = new Set<string>();
    const walk = (key: string) => {
      if (chain.has(key)) return;
      chain.add(key);
      for (const parent of byKey.get(key)?.requires ?? []) walk(parent);
    };
    walk(focus);
    return chain;
  });

  /**
   * A label is shown for the node under the pointer/selection and its ancestry, and for anything
   * already learned. Everything else stays a bare circle — the reference skill trees label
   * nothing at all, and at this density any always-on label overlaps its neighbours.
   */
  protected showLabel(node: TreeNode): boolean {
    return node.state === 'learned'
      || this.selected() === node.key
      || this.hovered() === node.key
      || this.lineage().has(node.key);
  }

  /**
   * Dimming keys off hover only, never selection. The page pre-selects a step so the detail panel
   * isn't empty on arrival — if that also dimmed, the resting state of the whole tree would be
   * 90% faded before the user has done anything.
   */
  protected isDimmed(node: TreeNode): boolean {
    return this.hovered() !== null && !this.lineage().has(node.key);
  }

  protected edgeActive(fromKey: string, toKey: string): boolean {
    const chain = this.lineage();
    return chain.has(fromKey) && chain.has(toKey);
  }

  /**
   * Controlled selection: emit and let the page decide. It doesn't always select — signed out
   * a node opens the sign-in dialog instead — and a tree that ringed the node anyway would be
   * showing a selection nothing is displaying.
   */
  protected select(node: TreeNode): void {
    this.stepSelected.emit(node.step);
  }

  protected ariaLabel(node: TreeNode): string {
    const state = node.state === 'learned' ? 'learned'
      : node.state === 'locked' ? 'not yet unlocked'
      : 'ready to learn';
    const requires = node.step.requires ?? [];
    const after = requires.length > 0 ? `, follows ${requires.length} earlier ${requires.length === 1 ? 'move' : 'moves'}` : '';
    return `${node.step.title} — ${state}${after}`;
  }
}

