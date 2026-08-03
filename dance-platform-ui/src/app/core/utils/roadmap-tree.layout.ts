import { Roadmap, RoadmapStep } from '../../models/roadmap.model';

/**
 * Lays a roadmap out as a radial skill tree: one root near the bottom centre, rings of
 * increasing depth fanning upward.
 *
 * Progression through a style is a DAG, not a line — the twists and the travelling steps both
 * come off the jack and never touch each other again. A numbered list flattens that away; a fan
 * shows the branches, and shows at a glance how much of the style each one opens up.
 *
 * Pure and deterministic: same roadmap in, same coordinates out. Kept out of the component so
 * the geometry can be reasoned about (and unit-tested) without rendering anything.
 */

/** Angle the fan sweeps, centred on straight up. */
const SPREAD_DEG = 142;
/** Radius of the innermost ring, and the gap between rings. */
const ROOT_RADIUS = 98;
const RING_GAP = 80;
/** Slack around the content, on top of the measured extent of the nodes and their labels. */
const PAD = 12;
/** Outermost thing drawn on a node: the selection halo, not the r=19 disc. */
const NODE_R = 30;
/**
 * How far the label sits from the node centre, along the spoke. Clears the selection halo —
 * at 30 the selected node's label started exactly on the halo's stroke.
 */
const LABEL_OUTWARD = 38;
/**
 * Rough label metrics, used only to keep the text inside the viewBox. The font is the condensed
 * bold UI face at 11.5px, measured at 3.98–4.25px per character across the authored paths. The
 * headroom here is deliberate but not lavish: under-estimating clips the text, and over-
 * estimating widens the viewBox, which shrinks the whole tree at any given render width.
 */
const LABEL_CHAR_W = 4.6;
const LABEL_ASCENT = 12;
const LABEL_DESCENT = 4;
/** Longest label drawn on the tree; the full title lives in the detail panel. */
const LABEL_MAX_CHARS = 18;

/** The label as drawn — truncated here rather than in the view so the bounds can measure it. */
function shortLabel(title: string): string {
  return title.length <= LABEL_MAX_CHARS ? title : `${title.slice(0, LABEL_MAX_CHARS - 1).trimEnd()}…`;
}

export interface TreeNode {
  step: RoadmapStep;
  key: string;
  x: number;
  y: number;
  depth: number;
  stageIndex: number;
  state: string;
  /** True when this node sits on the outer edge of its branch — nothing depends on it. */
  isLeaf: boolean;
  /** The label as drawn, already truncated — the full title is in the detail panel. */
  label: string;
  /** Where the label goes relative to the node, so text never overlaps the circle. */
  labelAnchor: 'start' | 'middle' | 'end';
  labelX: number;
  labelY: number;
}

export interface TreeEdge {
  from: TreeNode;
  to: TreeNode;
  /** SVG path: an arc along the parent's ring, then a spoke out to the child. */
  path: string;
  /**
   * False for a second or later prerequisite. Those are drawn faintly — the layout gives each
   * node one structural parent, so extra edges are cross-links rather than tree branches.
   */
  isPrimary: boolean;
}

export interface TreeLayout {
  nodes: TreeNode[];
  edges: TreeEdge[];
  viewBox: string;
  width: number;
  height: number;
  /** Ring radii, drawn as faint guide circles behind the tree. */
  rings: { r: number; cx: number; cy: number }[];
  centre: { x: number; y: number };
}

export function layoutRoadmapTree(roadmap: Roadmap): TreeLayout {
  const steps = roadmap.stages.flatMap(s => s.steps);
  if (steps.length === 0) {
    return { nodes: [], edges: [], viewBox: '0 0 100 100', width: 100, height: 100, rings: [], centre: { x: 50, y: 50 } };
  }

  const byKey = new Map(steps.map(s => [s.key, s]));

  // One structural parent per node — the first prerequisite that actually exists. Extra
  // prerequisites still get an edge, just not a say in where the node sits.
  const primaryParent = new Map<string, string | null>();
  for (const step of steps) {
    const parent = (step.requires ?? []).find(k => byKey.has(k)) ?? null;
    primaryParent.set(step.key, parent);
  }

  const children = new Map<string, RoadmapStep[]>(steps.map(s => [s.key, []]));
  const roots: RoadmapStep[] = [];
  for (const step of steps) {
    const parent = primaryParent.get(step.key);
    if (parent) children.get(parent)!.push(step);
    else roots.push(step);
  }

  // Leaf counts drive how much of the arc each subtree gets, so dense branches spread out and
  // sparse ones stay narrow instead of every node getting an equal slice.
  const leafCount = new Map<string, number>();
  const countLeaves = (step: RoadmapStep, guard: Set<string>): number => {
    if (leafCount.has(step.key)) return leafCount.get(step.key)!;
    if (guard.has(step.key)) return 1;
    guard.add(step.key);
    const kids = children.get(step.key)!;
    const n = kids.length === 0 ? 1 : kids.reduce((sum, k) => sum + countLeaves(k, guard), 0);
    guard.delete(step.key);
    leafCount.set(step.key, n);
    return n;
  };
  for (const step of steps) countLeaves(step, new Set());

  // Walk the forest assigning each subtree a slice of [0,1]; a node sits at the middle of its own.
  const frac = new Map<string, number>();
  const totalLeaves = roots.reduce((sum, r) => sum + leafCount.get(r.key)!, 0) || 1;
  const assign = (step: RoadmapStep, start: number, end: number, guard: Set<string>): void => {
    if (guard.has(step.key)) return;
    guard.add(step.key);
    frac.set(step.key, (start + end) / 2);
    const kids = children.get(step.key)!;
    const span = end - start;
    const kidLeaves = kids.reduce((sum, k) => sum + leafCount.get(k.key)!, 0) || 1;
    let cursor = start;
    for (const kid of kids) {
      const w = (leafCount.get(kid.key)! / kidLeaves) * span;
      assign(kid, cursor, cursor + w, guard);
      cursor += w;
    }
    guard.delete(step.key);
  };
  let cursor = 0;
  for (const root of roots) {
    const w = leafCount.get(root.key)! / totalLeaves;
    assign(root, cursor, cursor + w, new Set());
    cursor += w;
  }

  const spread = (SPREAD_DEG * Math.PI) / 180;
  // Straight up is -90 degrees in SVG's y-down space.
  const angleOf = (key: string) => -Math.PI / 2 + ((frac.get(key) ?? 0.5) - 0.5) * spread;
  const radiusOf = (depth: number) => ROOT_RADIUS + depth * RING_GAP;

  // Position around an origin, then shift everything so the bounding box starts at 0.
  const raw = steps.map(step => {
    const a = angleOf(step.key);
    const r = radiusOf(step.depth);
    return { step, a, r, x: Math.cos(a) * r, y: Math.sin(a) * r };
  });

  const maxDepth = Math.max(...steps.map(s => s.depth));

  /**
   * Label placement, resolved before the bounds so the bounds can include it. Push the label
   * outward along the spoke, and away from the circle horizontally so the text of a node on the
   * left of the fan reads leftward and vice versa.
   *
   * The extents matter: on the outermost nodes of the fan the label reaches much further than
   * the circle does, and a fixed pad never covered it — the text ran off the edge of the viewBox
   * and was clipped by the svg, with no ellipsis to show that it had been.
   */
  const placed = raw.map(p => {
    const cos = Math.cos(p.a);
    const labelAnchor: TreeNode['labelAnchor'] = cos < -0.35 ? 'end' : cos > 0.35 ? 'start' : 'middle';
    const label = shortLabel(p.step.title);
    const w = label.length * LABEL_CHAR_W;
    const dx = cos * LABEL_OUTWARD;
    const dy = Math.sin(p.a) * LABEL_OUTWARD + (labelAnchor === 'middle' ? -6 : 4);
    return {
      p, label, labelAnchor, dx, dy,
      left: p.x + dx - (labelAnchor === 'end' ? w : labelAnchor === 'middle' ? w / 2 : 0),
      right: p.x + dx + (labelAnchor === 'start' ? w : labelAnchor === 'middle' ? w / 2 : 0),
      top: p.y + dy - LABEL_ASCENT,
      bottom: p.y + dy + LABEL_DESCENT
    };
  });

  const minX = Math.min(...placed.map(q => Math.min(q.p.x - NODE_R, q.left))) - PAD;
  const maxX = Math.max(...placed.map(q => Math.max(q.p.x + NODE_R, q.right))) + PAD;
  const minY = Math.min(...placed.map(q => Math.min(q.p.y - NODE_R, q.top))) - PAD;
  const maxY = Math.max(...placed.map(q => Math.max(q.p.y + NODE_R, q.bottom))) + PAD;
  const originX = -minX;
  const originY = -minY;
  const width = maxX - minX;
  const height = maxY - minY;

  const nodes: TreeNode[] = placed.map(q => {
    const x = q.p.x + originX;
    const y = q.p.y + originY;
    return {
      step: q.p.step,
      key: q.p.step.key,
      x, y,
      depth: q.p.step.depth,
      stageIndex: q.p.step.stageIndex,
      state: q.p.step.state,
      isLeaf: children.get(q.p.step.key)!.length === 0,
      label: q.label,
      labelAnchor: q.labelAnchor,
      labelX: x + q.dx,
      labelY: y + q.dy
    };
  });

  const nodeByKey = new Map(nodes.map(n => [n.key, n]));

  const edges: TreeEdge[] = [];
  for (const node of nodes) {
    const requires = node.step.requires ?? [];
    requires.forEach((key, index) => {
      const parent = nodeByKey.get(key);
      if (!parent) return;
      edges.push({
        from: parent,
        to: node,
        isPrimary: primaryParent.get(node.key) === key,
        path: elbow(parent, node, originX, originY, radiusOf(parent.depth), index === 0)
      });
    });
  }

  const rings = Array.from({ length: maxDepth + 1 }, (_, d) => ({
    r: radiusOf(d), cx: originX, cy: originY
  }));

  return {
    nodes,
    edges,
    viewBox: `0 0 ${round(width)} ${round(height)}`,
    width,
    height,
    rings,
    centre: { x: originX, y: originY }
  };
}

/**
 * Parent to child as a concentric elbow: sweep along the parent's ring until under the child,
 * then run straight out. Reads as a circuit board rather than a spider web, and keeps crossings
 * to a minimum because every segment follows the geometry the rings already imply.
 */
function elbow(parent: TreeNode, child: TreeNode, originX: number, originY: number, parentR: number, primary: boolean): string {
  const pa = Math.atan2(parent.y - originY, parent.x - originX);
  const ca = Math.atan2(child.y - originY, child.x - originX);

  // Where the spoke leaves the parent's ring, at the child's angle.
  const kneeX = originX + Math.cos(ca) * parentR;
  const kneeY = originY + Math.sin(ca) * parentR;

  if (!primary || Math.abs(ca - pa) < 0.001) {
    // Same spoke (or a cross-link we want to read as a shortcut): a gentle curve is clearer
    // than an arc of zero length.
    return `M ${round(parent.x)} ${round(parent.y)} Q ${round(kneeX)} ${round(kneeY)} ${round(child.x)} ${round(child.y)}`;
  }

  // sweep-flag 1 when the child sits clockwise of the parent.
  const sweep = ca > pa ? 1 : 0;
  return [
    `M ${round(parent.x)} ${round(parent.y)}`,
    `A ${round(parentR)} ${round(parentR)} 0 0 ${sweep} ${round(kneeX)} ${round(kneeY)}`,
    `L ${round(child.x)} ${round(child.y)}`
  ].join(' ');
}

const round = (n: number) => Math.round(n * 10) / 10;
