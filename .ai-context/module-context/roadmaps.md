# Module — Roadmaps (curated learning paths, and personal skill trees)

> Load alongside core-context.md when the task touches roadmaps, learning paths, the authored
> content in `Data/Roadmaps/`, or the skill-tree builder.

## What it is

A roadmap is a **skill tree** through one style: **stages** (branches) holding **steps** (the
moves), wired together by explicit **prerequisites**. Each step optionally links to a catalog
`Dance`; when it does, the page shows that move's videos and the user's learned status.

**Two kinds share the same table, DTOs, service and tree renderer**, told apart by
`Roadmap.OwnerUserId`:

- **Curated** (null owner) — the authored paths. Content, seeded from JSON, read by everyone.
- **Personal** (owner set) — a tree a user built for themselves in `/roadmaps/:slug/edit`.
  User data, written over the API, and **private to its owner**.

Keeping them in one table is what makes a personal tree worth having: it renders through the
same fan, unlocks against the same learned flags, and can be forked from a curated path with
one button. See [Personal skill trees](#personal-skill-trees) below.

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

- Controller: `Controllers/RoadmapsController.cs` — the two GETs anonymous, the writes `[Authorize]`
- Service: `IRoadmapService` / `RoadmapService.cs` — `GetAllAsync`, `GetByIdOrSlugAsync`,
  `CreateAsync`, `UpdateAsync`, `DeleteAsync`, `CopyAsync`
- Models: `Roadmap`, `RoadmapStage`, `RoadmapStep`
- DTOs: `DTOs/Roadmap/RoadmapDto.cs` — `RoadmapSummaryDto`, `RoadmapDto`, `RoadmapStageDto`,
  `RoadmapStepDto`, `RoadmapStepDanceDto`, `RoadmapStepVideoDto`;
  `DTOs/Roadmap/SaveRoadmapRequest.cs` — the builder's payload and `RoadmapSaveResult`
- Graph rules shared by the seeder and the write path: `Services/RoadmapGraph.cs`
- Seeder: `Data/RoadmapSeeder.cs`, called from `Program.cs` after `SeedData`
- Migrations: `AddRoadmaps`, `AddRoadmapStepSegment`, `AddRoadmapStepTree`, `AddPersonalRoadmaps`
- Tests: `DancePlatform.Tests/RoadmapServiceTests.cs` (the write path, on SQLite so the FKs bite)
- Endpoints: see api-contracts → Roadmaps.

## Frontend

- Pages: `pages/roadmaps/` (index), `pages/roadmap-detail/` (the path, slug-addressed),
  `pages/roadmap-builder/` (create and edit a personal tree)
- Service: `core/services/roadmap.service.ts` (deliberately uncached — the payload is per-user)
- Model: `models/roadmap.model.ts` — read types plus `SaveRoadmap*`
- Graph rules, client side: `core/utils/roadmap-graph.ts` (`withGraphState`)
- Routes: `/roadmaps`, `/roadmaps/:slug` public; `/roadmaps/new` and `/roadmaps/:slug/edit`
  behind `authGuard`. **`/roadmaps/new` must stay ahead of `/roadmaps/:slug`** in `app.routes.ts`
  or "new" resolves as a slug and 404s. Header nav link `nav-roadmaps`.
- Sign-in wall: `shared/components/sign-in-dialog/` — the `/login` form as a modal, reusable by
  any page that reads signed out but needs an account to act. It signs in *in place*; sending
  someone to `/login` would land them on `/my-dances` and lose the path they were reading.

## The curated content lives in JSON, not the database

*(Personal trees are the exception — they are written over the API and have no file. The seeder
matches on `OwnerUserId == null` so it never sees them.)*

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

**Prefer a real dance per step where the catalog can support one.** Waacking used to lean on
this mechanism for ten of its steps, which is what made its whole path a transcription of one
video's chapter list; seeding the moves properly dropped it to a single pinned step. Reach for
`segmentLabel` when the only good footage for a move is a section of a longer class — not as a
substitute for the move existing in the catalog.

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

`core/utils/roadmap-graph.ts#withGraphState` mirrors both computations client-side, for two
callers: the detail page (so ticking a move off unlocks the next ring without a round trip) and
the builder's preview (whose draft has never been near the server). **If you change the rules on
one side, change them on the other** — a drift shows up as the tree disagreeing with itself
until reload.

Layout is a pure function: `core/utils/roadmap-tree.layout.ts`. Each node gets one *structural*
parent (its first resolvable prerequisite) which decides its angle; extra prerequisites are drawn
as faint cross-links, and only while their lineage is focused, since drawn always they turn the
fan into a web. Labels appear only for the hovered/selected lineage and for learned moves — 31
names on one fan collide however they're placed.

## Personal skill trees

A signed-in user can build their own tree — same renderer, same unlocking, their own content.
Entry points: **Build a skill tree** on the index, and **Make my own version** on any curated
path (a fork, so the curated one is never altered).

### One save replaces the whole tree

`PUT /roadmaps/{id}` takes the entire thing — `SaveRoadmapRequest`, stages → steps → `requires`
— and `RoadmapService.ApplyAsync` rebuilds the stored stages, steps and edges from it. Same
approach the seeder takes with a changed file, and for the same reason: **nothing outside a
roadmap references a stage or step id** (progress hangs off the dance), so recreating them is
safe and keeps the authored order exact without a diff to reason about.

Consequence: a step's row id changes on every save. Don't add anything that stores one.

### Where it forgives and where it refuses

Deliberately split, because the two failure modes read completely differently to the user:

- **Dropped silently** — a blank step title (a row opened and never filled in), an edge naming a
  step that no longer exists (a stale tab), a `danceId` or `videoSegmentId` that has since been
  deleted. None of these are things the user can see or fix, and the seeder treats them the same.
- **400, with a message the builder shows** — a cycle. The user drew that link seconds ago; a
  save that quietly threw it away would read as the save not working. The builder also filters
  cycle-creating options out of the "comes after" dropdown, so it should never come up.

### Keys

The client owns its step keys; the server slugifies and de-duplicates them and **rewrites the
`requires` through the same mapping**, so a client that reuses a key gets a working tree rather
than a 400. A blank key never enters the mapping — nothing can name it.

### Privacy, ownership and sharing

Every **write** matches on `OwnerUserId == callerId`, so a curated path and another user's tree
both just fail to match, and every write answers **404, not 403** — whether a private tree
exists at that id isn't the caller's business either.

**Reads have two different rules, deliberately:**

| | rule |
|---|---|
| `GetByIdOrSlugAsync` (one tree, by URL) | curated **or** mine **or** `IsPublic` |
| `GetAllAsync` (the index) | curated **or** mine — *never* other people's shared trees |

A personal tree is private (`IsPublic = false`) until its owner shares it. Sharing is
**link-and-profile discovery, not a feed**: a shared tree resolves at its own URL for anyone
(signed out included, who get the usual teaser) and is listed on its owner's public profile
(`PublicProfileDto.SharedRoadmaps`), but it never joins the roadmap index. The index is the
curated shelf, nothing here is moderated, and it must not be pushed at people who didn't go
looking for it. If that ever changes, moderation is the thing to build first.

Two rules that keep sharing from leaking:

- **Sharing is its own endpoint** (`PUT /roadmaps/{id}/share`), not a field on
  `SaveRoadmapRequest`. A save replaces the whole tree, so carrying the flag in the payload
  would let a builder tab opened before the toggle silently unshare it again.
- **A fork is always private.** `CopyAsync` goes through `CreateAsync`, which leaves `IsPublic`
  false; inheriting it would republish someone else's work under a new owner by accident.

### The builder

`pages/roadmap-builder/` — form on the left, **live tree preview on the right**. The preview is
the point: sequencing is what a skill tree is for, and a form can't show it. It renders through
the same `app-roadmap-tree` as the real page, via `withGraphState(draft, false)` — *false*
because nothing in a draft is learned, and the signed-in rules would paint every non-root node
locked, turning the preview into a wall of padlocks that says nothing about the structure.

The move picker searches `/search/dances` scoped to the tree's style. Linking is optional, the
same as in the authored files: a path should name the moves the style needs whether or not the
catalog covers them.

Once a step is linked, **"Pin to a section"** narrows it to one `VideoSegment` — the same
`videoSegmentId` the authored files reach through `segmentLabel`. It reads the dance's videos
from `GET /videos/dance/{danceId}` (which already carries `segments`, so there's no new
endpoint) and caches them per dance, since a sliced-up class video usually backs several steps.
Changing the linked move clears the pin: a clip pinned against the old dance means nothing
against a new one. Not every dance has chipped videos, and the picker says so rather than
looking broken — sections come from the `find-chips` skill.

**Unsaved changes are guarded.** `core/guards/unsaved-changes.guard.ts` (`canDeactivate`) plus a
`beforeunload` listener for tab closes, which the router never sees. Dirtiness is a comparison
of a JSON snapshot against the last saved one, not a flag each edit handler sets — there are a
dozen ways to mutate the draft and the thirteenth would forget. Anything that navigates after a
successful save must `hydrate()` first, or the guard challenges its own save on the way out.

### Caps

`MaxTreesPerUser = 50`, 30 branches, 250 moves, and length limits on every text field — well
above any real path (the largest authored one is 7 branches and 46 steps), and enough that one
account can't turn the shared table into its own storage.

## Key behaviours / rules

- **A step's title is authoritative; `danceSlug` is optional.** A path should teach the moves a
  style actually needs. Steps that resolve to nothing render as "no video yet" with a search
  link — that is a feature, not a gap to paper over by inventing catalog entries.
- **Progress is not stored on the roadmap.** `learnedCount` / `isLearned` are computed from
  `UserLearnedDances` / `UserInProgressDances` through the step's dance. Ticking a step off
  calls the same `PUT /dances/{id}/status` as the dance page, so the two never disagree.
  The cost is that progress is per *dance*, not per step: where one dance backs several steps,
  marking it learned flips all of them at once. Hip-hop is now the worst case (`locking` backs
  3 steps); Waacking backs 2 off `waacking`, House none. Fixing it properly means
  a per-step `UserRoadmapStep` table — not built. Until then, prefer one dance per step, and
  read the validator's warnings as a budget rather than noise.
- A move may legitimately appear in more than one stage; `applyFlags` in the detail component
  updates **every** step pointing at that dance so their chips stay in sync.
- Video visibility follows the catalog rule: global videos plus the viewer's own personal ones.
- Unknown slug → not-found panel, **not** a redirect (same contract as dance detail).

## Authoring notes

- **Run `python scripts/validate_roadmaps.py` before deploying a roadmap change.** The seeder
  is deliberately forgiving — a bad `danceSlug`, a `segmentLabel` matching nothing, or an edge
  naming an unknown key is skipped with a logged error rather than failing the boot — so a typo
  ships silently and only shows up as a step with no video. The validator checks slugs, labels,
  keys, cycles, reachability and video coverage against the prod catalog, and exits 1 on error.
  It also warns where one dance backs several steps (see the progress caveat below).
- Only link a `danceSlug` whose video actually teaches that move. Several catalog entries are
  mistagged (a "Gazelle" whose video is a Zootopia clip); linking those makes the path worse
  than leaving the step unlinked. Check the *video title*, not just the dance name — and note
  that `Videos.Title` holds the move name, so a title naming a whole montage
  ("60 Hip Hop Dance Steps") means the row was never cleaned up.
- Prefer a `segmentLabel` over a link to a long class video. A step that points at an
  11-minute lesson tells the reader "watch all of this"; pinning the one relevant section is
  the difference between a curriculum and a playlist.
- Order stages so each assumes the previous one. House leads with the jack because every later
  step rides that pulse.

## Gotchas

- Add a new migration **before** `dotnet run`, then rebuild — `dotnet ef migrations add` after
  a build leaves the migration out of the compiled assembly and `MigrateAsync` silently
  doesn't create the tables.
- The seeder's signature deliberately excludes `danceSlug` (the DB stores the resolved id, not
  the slug, so the two sides can't be compared). Step 3 covers link changes instead.
- **Clear a roadmap's prerequisite edges before deleting its steps**, and `Include` the stages
  and steps in whatever query loaded the roadmap. The `PrerequisiteStep` FK is NoAction, so an
  edge still pointing at a step deleted earlier in the same pass fails its foreign key — and
  `RemoveTreeAsync` can only clear the edges it can see step ids for. `DeleteAsync` shipped
  without the `Include` and 500'd on every delete. **The unit tests can't catch this**: SQLite
  tolerates the ordering Postgres rejects. The e2e suite is the guard.
- `/roadmaps/new` must be declared **before** `/roadmaps/:slug` in `app.routes.ts`.
- Both builder routes carry `canDeactivate: [unsavedChangesGuard]`. A new page that navigates
  away from the builder must leave it clean first (see the builder notes above).
