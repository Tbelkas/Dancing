import { Roadmap, RoadmapStep, RoadmapStepState } from '../../models/roadmap.model';

/**
 * The client-side mirror of `RoadmapService.AssignDepths` / `AssignStates`.
 *
 * The server computes both when it serves a path, and for a read that would be enough. Two things
 * need them recomputed without a round trip:
 *
 * - **Ticking a move off.** The whole point of the tree is that learning something opens what it
 *   leads to; waiting for a reload to show that would make the tree feel dead.
 * - **The builder's preview.** A tree being drawn has never been near the server, so nothing has
 *   assigned its rings yet.
 *
 * It lives here rather than in either component so there is one copy to keep in step with the
 * C#. **If you change the rules on one side, change them on the other** — a drift shows up as the
 * tree disagreeing with itself until reload.
 */

/**
 * Longest distance from a root, which is what puts a node on the right ring: a step must sit
 * outside every prerequisite, so the *max* depth is the correct one.
 *
 * Iterative relaxation rather than recursion, and bounded by the step count — the builder can
 * hold a half-drawn graph that briefly cycles, and that must yield odd rings, never a hang.
 */
function depths(steps: RoadmapStep[]): Map<string, number> {
  const byKey = new Map(steps.map(s => [s.key, s]));
  const depth = new Map(steps.map(s => [s.key, 0]));

  for (let pass = 0; pass < steps.length; pass++) {
    let changed = false;
    for (const step of steps) {
      let d = 0;
      for (const key of step.requires ?? []) {
        if (byKey.has(key)) d = Math.max(d, (depth.get(key) ?? 0) + 1);
      }
      if (d !== depth.get(step.key)) { depth.set(step.key, d); changed = true; }
    }
    if (!changed) break;
  }

  return depth;
}

/**
 * Which steps count as done, for the purpose of unlocking what comes after them.
 *
 * "Satisfied" is not the same as "learned". A step with no catalog move behind it can never be
 * ticked off, so it passes through: it counts as satisfied exactly when the things IT depends on
 * are. Without the pass-through, one un-covered concept would either lock its whole branch
 * forever (if it gated) or leak the branch open early (if it didn't).
 */
function satisfied(steps: RoadmapStep[], signedIn: boolean): Map<string, boolean> {
  const byKey = new Map(steps.map(s => [s.key, s]));
  const done = new Map(steps.map(s => [s.key, !!s.dance?.isLearned]));
  if (!signedIn) return done;

  for (let pass = 0; pass < steps.length; pass++) {
    let changed = false;
    for (const step of steps) {
      if (step.dance) continue; // fixed by its own learned flag
      const ok = (step.requires ?? []).every(key => !byKey.has(key) || done.get(key) === true);
      if (ok !== done.get(step.key)) { done.set(step.key, ok); changed = true; }
    }
    if (!changed) break;
  }

  return done;
}

/**
 * Returns the roadmap with every step's `depth` and `state` recomputed, and `availableCount`
 * with it. Steps whose values didn't change keep their identity, so Angular re-renders only what
 * actually moved.
 *
 * Signed out nothing is locked — a visitor should see the whole tree, not a wall of padlocks.
 */
export function withGraphState(roadmap: Roadmap, signedIn: boolean): Roadmap {
  const steps = roadmap.stages.flatMap(s => s.steps);
  const known = new Set(steps.map(s => s.key));
  const depth = depths(steps);
  const done = satisfied(steps, signedIn);

  let available = 0;
  const stages = roadmap.stages.map(stage => ({
    ...stage,
    steps: stage.steps.map(step => {
      let state: RoadmapStepState;
      if (step.dance?.isLearned) {
        state = 'learned';
      } else if (!signedIn) {
        state = 'available';
      } else {
        const blocked = (step.requires ?? []).some(key => known.has(key) && done.get(key) !== true);
        state = blocked ? 'locked' : 'available';
      }
      if (state === 'available') available++;

      const d = depth.get(step.key) ?? 0;
      return step.state === state && step.depth === d ? step : { ...step, state, depth: d };
    })
  }));

  return { ...roadmap, stages, availableCount: available };
}
