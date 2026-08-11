import { describe, it, expect } from 'vitest';
import { layoutRoadmapTree, TreeNode } from './roadmap-tree.layout';
import { Roadmap, RoadmapStep } from '../../models/roadmap.model';

/**
 * The layout's job is geometry, so that's what these assert: labels that stay off the circles,
 * and a viewBox that contains everything drawn. Both regressed silently before — a name that
 * lands on a neighbour's disc is unreadable, and nothing in the app fails when it happens.
 */

/** Same metrics the layout measures with; a spec that guessed differently would prove nothing. */
const LABEL_CHAR_W = 4.6;
const LABEL_ASCENT = 12;
const LABEL_DESCENT = 4;
/** The circle actually drawn on a node. */
const DISC_R = 19;

function step(key: string, depth: number, requires: string[], title = key): RoadmapStep {
  return { id: 0, key, requires, stageIndex: 0, depth, state: 'available', title };
}

/** One roadmap, one stage — the tree only cares about steps, depths and prerequisites. */
function roadmapOf(steps: RoadmapStep[]): Roadmap {
  return {
    id: 1, slug: 'x', title: 'X', subtitle: '', styleId: 1, styleName: 'X', styleSlug: 'x',
    isOwned: false, isPublic: false, stageCount: 1, stepCount: steps.length, moveCount: 0,
    videoCount: 0, learnedCount: 0, inProgressCount: 0, availableCount: 0,
    stages: [{ id: 1, title: 'Stage', steps }]
  };
}

function labelBox(n: TreeNode) {
  const w = n.label.length * LABEL_CHAR_W;
  const left = n.labelX - (n.labelAnchor === 'end' ? w : n.labelAnchor === 'middle' ? w / 2 : 0);
  return { left, right: left + w, top: n.labelY - LABEL_ASCENT, bottom: n.labelY + LABEL_DESCENT };
}

/** Nearest point on the box to the node's centre, compared against the disc radius. */
function hitsDisc(box: ReturnType<typeof labelBox>, node: TreeNode): boolean {
  const nx = Math.min(Math.max(node.x, box.left), box.right);
  const ny = Math.min(Math.max(node.y, box.top), box.bottom);
  return (node.x - nx) ** 2 + (node.y - ny) ** 2 < DISC_R * DISC_R;
}

/** A wide, shallow fan: the shape that crowds labels, because every node shares one ring. */
function fan(width: number): Roadmap {
  const steps = [step('root', 0, [])];
  for (let i = 0; i < width; i++) steps.push(step(`a${i}`, 1, ['root'], `Move number ${i}`));
  return roadmapOf(steps);
}

/** A deep chain: neighbours sit on the same spoke instead of side by side. */
function chain(depth: number): Roadmap {
  const steps = [step('s0', 0, [], 'First move')];
  for (let i = 1; i < depth; i++) steps.push(step(`s${i}`, i, [`s${i - 1}`], `Move ${i} of the chain`));
  return roadmapOf(steps);
}

describe('layoutRoadmapTree label placement', () => {
  for (const [name, roadmap] of [
    ['a wide fan', fan(9)],
    ['a crowded fan', fan(16)],
    ['a deep chain', chain(7)],
    ['a chain with branches', roadmapOf([
      step('root', 0, [], 'What waacking is'),
      step('arms', 1, ['root'], 'The arms'),
      step('hands', 1, ['root'], 'What the hands do'),
      step('form', 2, ['arms'], "Conductor's form"),
      step('pose', 2, ['hands'], 'Posing'),
      step('twirl', 3, ['form', 'pose'], 'The twirl')
    ])]
  ] as [string, Roadmap][]) {
    it(`keeps every label off every disc — ${name}`, () => {
      const { nodes } = layoutRoadmapTree(roadmap);
      const collisions = nodes
        .flatMap(n => nodes.filter(other => hitsDisc(labelBox(n), other)).map(other => `"${n.label}" over "${other.label}"`));
      expect(collisions).toEqual([]);
    });
  }

  it('contains labels and nodes inside the viewBox', () => {
    const { nodes, width, height } = layoutRoadmapTree(fan(12));
    for (const n of nodes) {
      const box = labelBox(n);
      expect(box.left).toBeGreaterThanOrEqual(0);
      expect(box.right).toBeLessThanOrEqual(width);
      expect(box.top).toBeGreaterThanOrEqual(0);
      expect(box.bottom).toBeLessThanOrEqual(height);
      expect(n.x - DISC_R).toBeGreaterThanOrEqual(0);
      expect(n.x + DISC_R).toBeLessThanOrEqual(width);
    }
  });

  it('puts the label outward along the spoke when nothing is in the way', () => {
    // A lone child: no neighbour to dodge, so it must take the first, most legible candidate.
    const { nodes } = layoutRoadmapTree(roadmapOf([step('root', 0, [], 'Root'), step('kid', 1, ['root'], 'Kid')]));
    const kid = nodes.find(n => n.key === 'kid')!;
    const root = nodes.find(n => n.key === 'root')!;
    expect(kid.labelY).toBeLessThan(kid.y);       // pushed up the spoke, away from the centre
    expect(kid.labelY).toBeLessThan(root.y);
  });

  it('is deterministic', () => {
    const a = layoutRoadmapTree(fan(11));
    const b = layoutRoadmapTree(fan(11));
    expect(a.nodes.map(n => [n.labelX, n.labelY, n.labelAnchor]))
      .toEqual(b.nodes.map(n => [n.labelX, n.labelY, n.labelAnchor]));
  });

  it('truncates a long title rather than letting it run', () => {
    const { nodes } = layoutRoadmapTree(roadmapOf([
      step('root', 0, [], 'A title far longer than the tree will ever draw')
    ]));
    expect(nodes[0].label.length).toBeLessThanOrEqual(18);
    expect(nodes[0].label.endsWith('…')).toBe(true);
  });
});
