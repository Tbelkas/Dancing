/**
 * Features that are built but deliberately not shown yet.
 *
 * A flag here means "the code stays, the surface goes" — turning one back on must be the whole
 * job, with no markup to reconstruct. Anything that can't be restored by flipping the constant
 * belongs in a revert, not in this file.
 */

/**
 * Personal skill trees: building one, editing it, sharing it, and every place the app lists
 * them (the Roadmaps index, the fork button on a curated path, the Skill Trees card on a public
 * profile). Off since 2026-08-12 — Roadmaps is curated-only for now.
 *
 * The API is untouched and existing trees are still in the database; they are simply invisible.
 * Restoring the feature is this constant plus re-adding the `personal skill trees` block in
 * `e2e/tests/authed.spec.ts` (see git history).
 */
export const PERSONAL_ROADMAPS_ENABLED = false;
