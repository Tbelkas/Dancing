import { Component, EventEmitter, Input, Output, computed, signal } from '@angular/core';
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
export class RoadmapTreeComponent {
  private readonly roadmapSignal = signal<Roadmap | null>(null);

  @Input({ required: true }) set roadmap(value: Roadmap) {
    this.roadmapSignal.set(value);
  }

  /** Key of the step the page currently has open, so the tree can ring it. */
  @Input() set selectedKey(value: string | null) {
    this.selected.set(value);
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

  /** Short label for the node; the full title lives in the detail panel and the aria-label. */
  protected shortLabel(node: TreeNode): string {
    const title = node.step.title;
    return title.length <= 18 ? title : `${title.slice(0, 17).trimEnd()}…`;
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

