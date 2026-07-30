# Module — Roadmaps (curated learning paths per style)

> Load alongside core-context.md when the task touches roadmaps, learning paths, or the
> authored content in `Data/Roadmaps/`.

## What it is

A roadmap is a **skill tree** through one style: **stages** (branches) holding **steps** (the
moves), wired together by explicit **prerequisites**. Each step optionally links to a catalog
`Dance`; when it does, the page shows that move's videos and the user's learned status.

The point is sequencing, and it is deliberately **not linear** — the twists and the travelling
steps both come off the jack and never touch each other again. Browse answers "what exists in
House?"; a roadmap answers "what do I learn first, and what does it unlock?".

Two views, toggled and remembered in `localStorage['dp_roadmap_view']`:
- **Tree** (default) — a radial fan, root at the bottom, one ring per depth, plus a detail panel.
- **List** — the branches as ordered rows, every step's videos on screen at once.

**Signed out, the path is a teaser: the tree and nothing else.** No view toggle, no branch
blurbs, no detail panel — those give the curriculum away with no account to record it against.
Clicking any node opens `SignInDialogComponent` instead of selecting it; succeeding refetches
the roadmap (states and learned flags are per-user) rather than reloading the page. The stored
view preference is left alone, so signing in restores whichever view they last chose.

## Backend

- Controller: `Controllers/RoadmapsController.cs` (both endpoints anonymous, read-only)
- Service: `IRoadmapService` / `RoadmapService.cs` — `GetAllAsync(userId)`, `GetByIdOrSlugAsync(idOrSlug, userId)`
- Models: `Roadmap`, `RoadmapStage`, `RoadmapStep`
- DTOs: `DTOs/Roadmap/RoadmapDto.cs` — `RoadmapSummaryDto`, `RoadmapDto`, `RoadmapStageDto`,
  `RoadmapStepDto`, `RoadmapStepDanceDto`, `RoadmapStepVideoDto`
- Seeder: `Data/RoadmapSeeder.cs`, called from `Program.cs` after `SeedData`
- Migration: `AddRoadmaps`
- Endpoints: see api-contracts → Roadmaps.

## Frontend

- Pages: `pages/roadmaps/` (index), `pages/roadmap-detail/` (the path, slug-addressed)
- Service: `core/services/roadmap.service.ts` (deliberately uncached — the payload is per-user)
- Model: `models/roadmap.model.ts`
- Routes: `/roadmaps`, `/roadmaps/:slug`. Both public. Header nav link `nav-roadmaps`.
- Sign-in wall: `shared/components/sign-in-dialog/` — the `/login` form as a modal, reusable by
  any page that reads signed out but needs an account to act. It signs in *in place*; sending
  someone to `/login` would land them on `/my-dances` and lose the path they were reading.

## The content lives in JSON, not the database

`DancePlatform.API/Data/Roadmaps/<slug>.json` is the source of truth. Shape:

```json
{
  "slug": "house", "styleName": "House", "title": "House",
  "subtitle": "…", "description": "…", "sortOrder": 10,
  "stages": [{ "title": "…", "description": "…",
    "steps": [
      { "title": "The jack", "description": "…", "danceSlug": "house-jack" },
      { "title": "The arm roll", "description": "…",
        "danceSlug": "waacking", "segmentLabel": "Arm Roll" }
    ] }]
}
```

**To add a style's roadmap: drop in a new JSON file and restart the API.** No migration, no
admin UI, no SQL. `csproj` copies `Data/Roadmaps/*.json` to the output so it ships with a publish.

`RoadmapSeeder` runs on **every** boot (unlike `SeedData`, which only fires on an empty DB):

1. Resolves `styleName` against the `Styles` table, case-insensitively. **Unknown style → the
   file is skipped with a logged error**, never auto-created — inventing a style would add a
   bogus filter to Browse.
2. Fingerprints the authored stage/step titles and blurbs. Unchanged → no writes. Changed →
   the roadmap's stages are deleted and rebuilt from the file (nothing outside the file
   references a stage or step id, so recreating them is safe).
3. **Re-resolves every `danceSlug` and `segmentLabel` on every run**, whether or not it
   rebuilt. A step written before its move existed links itself as soon as that move is added
   to the catalog.

Dance slugs are unique *per style*, not globally, so resolution is scoped to the roadmap's
style — otherwise `the-heel-toe` in Waacking would match a same-named hip-hop step.

## `segmentLabel` — pointing a step at part of a video

`VIDEO_FIXUP.md` deliberately **consolidated** multi-move tutorials onto one canonical dance
rather than splitting them into a dance per move (rows 5, 9, 13 → "Waacking #1676 | attach"),
recording the sub-moves as `VideoSegment`s. So for those styles the curriculum lives *inside*
a video, and a step that could only name a whole dance would say "watch the 12-minute
tutorial" twelve times.

`segmentLabel` narrows a step to one section: the UI then shows only that clip, badges its
time range, and links to `/dances/{style}/{slug}?v={videoId}&t={startTime}`.

- Resolution is **by label within that dance's global videos**, never by segment id — the chip
  scripts rebuild segments wholesale, so ids are not stable. `RoadmapStep.VideoSegmentId` is
  `OnDelete=SetNull`: a re-chipped video widens the step back to the whole move instead of
  deleting it.
- Labels repeat across a dance's videos (`Intro`, `Practice with music`). The seeder takes the
  earliest by video date then start time, and **logs a warning** when a label matched more than
  one. Don't author against a generic label.
- `moveCount` counts *steps* with a dance (so progress reads "8 of 18 steps"), but `videoCount`
  counts **distinct** videos — otherwise one sliced-up tutorial would be counted once per step.

## The tree: keys, prerequisites and node state

Each step carries a `key` (stable, unique per roadmap, defaults to a slug of the title) and
`requires: [key, …]`. Edges live in `RoadmapStepPrerequisites` (composite PK, `Step` cascade /
`PrerequisiteStep` NoAction — two cascade paths into one table is more than Postgres allows).

The seeder **fully replaces** the edges every boot and drops, with a logged error, any edge that
names an unknown key, points at itself, or closes a cycle. A bad edge costs one connector, never
the boot.

`Depth` (longest distance from a root → the node's ring) and `State` are computed **server-side**
in `RoadmapService`, by bounded iterative relaxation rather than recursion — the endpoint is
public and must not be one malformed row away from a stack overflow.

**State is `learned` / `available` / `locked`, and locks are advisory.** A locked step is dimmed
but still markable: someone may already know the Skate. Signed out, nothing is locked — a visitor
sees the whole tree, not a wall of padlocks.

**The subtle rule: an unlinked step passes through.** A step with no catalog move can never be
ticked off, so "satisfied" ≠ "learned" for it — it counts as satisfied exactly when *its own*
prerequisites are. Gate on it directly and its branch locks forever; ignore it entirely and the
branch leaks open early (Lofting, whose only prerequisite is the un-covered Skate, would unlock
before the Slide). The relaxation loop in `AssignStates` exists for this.

`roadmap-detail.component.ts#withStates` mirrors that logic client-side so ticking a move off
unlocks the next ring immediately. **If you change one, change both** — a drift shows up as the
tree disagreeing with itself until reload.

Layout is a pure function: `core/utils/roadmap-tree.layout.ts`. Each node gets one *structural*
parent (its first resolvable prerequisite) which decides its angle; extra prerequisites are drawn
as faint cross-links, and only while their lineage is focused, since drawn always they turn the
fan into a web. Labels appear only for the hovered/selected lineage and for learned moves — 31
names on one fan collide however they're placed.

## Key behaviours / rules

- **A step's title is authoritative; `danceSlug` is optional.** A path should teach the moves a
  style actually needs. Steps that resolve to nothing render as "no video yet" with a search
  link — that is a feature, not a gap to paper over by inventing catalog entries.
- **Progress is not stored on the roadmap.** `learnedCount` / `isLearned` are computed from
  `UserLearnedDances` / `UserInProgressDances` through the step's dance. Ticking a step off
  calls the same `PUT /dances/{id}/status` as the dance page, so the two never disagree.
- A move may legitimately appear in more than one stage; `applyFlags` in the detail component
  updates **every** step pointing at that dance so their chips stay in sync.
- Video visibility follows the catalog rule: global videos plus the viewer's own personal ones.
- Unknown slug → not-found panel, **not** a redirect (same contract as dance detail).

## Authoring notes

- Only link a `danceSlug` whose video actually teaches that move. Several catalog entries are
  mistagged (a "Gazelle" whose video is a Zootopia clip); linking those makes the path worse
  than leaving the step unlinked.
- Order stages so each assumes the previous one. House leads with the jack because every later
  step rides that pulse.

## Gotchas

- Add a new migration **before** `dotnet run`, then rebuild — `dotnet ef migrations add` after
  a build leaves the migration out of the compiled assembly and `MigrateAsync` silently
  doesn't create the tables.
- The seeder's signature deliberately excludes `danceSlug` (the DB stores the resolved id, not
  the slug, so the two sides can't be compared). Step 3 covers link changes instead.
