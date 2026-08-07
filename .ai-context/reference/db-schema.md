# Reference — Database Schema

PostgreSQL (db `dancing`), EF Core 8. Source of truth: `Models/*.cs` + `Data/AppDbContext.cs`.
All entities carry `DateAdded` (`timestamp`, UTC) unless noted. PKs are `int Id` (identity)
unless a composite key is listed.

## Core entities

### User
| Column | Type | Notes |
|--------|------|-------|
| Id | int PK | |
| Username | string | **unique index** |
| PasswordHash | string | BCrypt |
| Name | string | |
| Nickname | string | |
| IsAdmin | bool | default `false`; the admin gate (checked live, not in JWT) |
| AvatarUrl | string? | |
| Visibility | enum `ProfileVisibility` | **default `Private`** (`Public=0, Private=1`) |
| DateAdded | datetime | |

Nav: FavoriteDances, LearnedDances, InProgressDances, MyStyles, Ratings, PracticeSessions.

### Dance
| Column | Type | Notes |
|--------|------|-------|
| Id | int PK | |
| Name | string | duplicates currently allowed (see known-issues #5) |
| Slug | string | **unique index**; from `SlugGenerator` |
| Description | string? | |
| Difficulty | enum `DifficultyLevel` | `None=0, Beginner=1, Intermediate=2, Advanced=3` |
| DateAdded | datetime | |

Also carries denormalized `FavoriteCount`, `LearnedCount`, and `AverageRating`/`RatingCount`
(the latter aggregated from its videos' ratings). Nav: DanceStyles, DanceMusicalStyles, Videos,
FavoritedBy, LearnedBy, InProgressBy, DanceInstructors, PracticeSessions.

### Video  (one-to-many: Dance → Videos)
| Column | Type | Notes |
|--------|------|-------|
| Id | int PK | |
| Title | string | |
| VideoId | string | the platform's video id / embed id |
| Platform | string | default `"youtube"` (also tiktok, instagram) |
| VideoType | string | default `"steps"` |
| Description | string? | |
| ViewCount | long | default 0; bumped via `POST /videos/{id}/view` |
| StartTime | int? | seconds — clip start |
| EndTime | int? | seconds — clip end |
| AverageRating | double | denormalized; mean of this video's `VideoRating`s |
| RatingCount | int | denormalized; count of this video's `VideoRating`s |
| DanceId | int FK → Dance | |
| DateAdded | datetime | |

Nav: Segments (cascade delete with Video), Ratings (`VideoRating`, cascade delete with Video).

### VideoSegment  (one-to-many: Video → Segments, cascade)
| Column | Type | Notes |
|--------|------|-------|
| Id | int PK | |
| Label | string | e.g. "Chorus", "Basic step" |
| StartTime | int | seconds |
| EndTime | int? | seconds |
| VideoId | int FK → Video | cascade delete |

*(No `DateAdded` on VideoSegment.)*

### Style  (dance category, e.g. Latin, Ballroom)
Id PK · Name · Description? · DateAdded. Nav: DanceStyles, MyStyleUsers.

### MusicalStyle  (music genre, e.g. Salsa, Hip-Hop)
Id PK · Name · Description? · DateAdded. Nav: DanceMusicalStyles.

### Instructor
Id PK · Name · Bio? · AvatarUrl? · Website?. Nav: DanceInstructors. *(No `DateAdded`.)*

### VideoRating
Composite PK **(UserId, VideoId)** · Rating (int, 1–5) · DateAdded. One rating per user per
**video** (upsert). Cascade delete from both User and Video. A video carries its own
denormalized `AverageRating`/`RatingCount`; a dance's `AverageRating`/`RatingCount` aggregate
the ratings across all of its videos (recomputed on rate, video delete, and video move).

### PracticeSession
| Column | Type | Notes |
|--------|------|-------|
| Id | int PK | |
| UserId | int FK → User | cascade |
| DanceId | int FK → Dance | cascade |
| Date | **DateOnly** | the calendar day practiced (not a timestamp) |
| DurationMinutes | int? | |
| Notes | string? | |
| DateAdded | datetime | |

### Roadmap  (a learning path through one style — curated, or a user's own skill tree)
| Column | Type | Notes |
|--------|------|-------|
| Id | int PK | |
| Slug | string | **unique index across both kinds**; curated ones are the style slug (`house`) |
| Title | string | |
| Subtitle | string | one-line pitch |
| Description | string? | intro paragraph |
| StyleId | int FK → Style | cascade |
| OwnerUserId | int? FK → User | **null = curated**; set = a personal tree, cascade, indexed |
| IsPublic | bool | personal trees only; false = private to the owner, true = readable by anyone with the link |
| SortOrder | int | position on the index |
| DateAdded | datetime | |
| DateModified | datetime? | last builder save; null for curated paths |

Nav: Stages. **Two kinds share this table, told apart by `OwnerUserId`:**

- **Curated** (null owner) — content, authored in `Data/Roadmaps/*.json` and upserted on every
  boot by `Data/RoadmapSeeder.cs` (not gated on an empty DB, unlike `SeedData`). The seeder
  matches on `OwnerUserId == null`, so it never touches a personal tree.
- **Personal** (owner set) — user data, written through `POST`/`PUT /roadmaps` by the builder.
  Private to its owner until they set `IsPublic`. Reading one tree allows
  `OwnerUserId == null || OwnerUserId == callerId || IsPublic`; the **index** deliberately drops
  the last clause, so a shared tree never appears on the roadmap list (see the roadmaps module
  context for why).

The unique index stays **global** rather than per-owner so `/roadmaps/{slug}` resolves without
knowing whose path it is. `RoadmapService.UniqueSlugAsync` therefore uniquifies a new personal
slug against both the existing roadmap slugs *and* the style slugs — otherwise a user naming a
tree "Hip Hop" today would sit on the slug tomorrow's authored hip-hop file wants.

### RoadmapStage  (one-to-many: Roadmap → Stages, cascade)
Id PK · RoadmapId FK · Title · Description? · SortOrder · DateAdded. Nav: Steps.

### RoadmapStep  (one-to-many: RoadmapStage → Steps, cascade)
| Column | Type | Notes |
|--------|------|-------|
| Id | int PK | |
| RoadmapStageId | int FK → RoadmapStage | cascade |
| Key | string | stable, unique per roadmap ("jack"); what prerequisites are authored against |
| Title | string | authoritative — a path teaches moves whether or not the catalog covers them |
| Description | string? | |
| SortOrder | int | |
| DanceId | int? FK → Dance | **nullable**, `OnDelete=SetNull`; null renders as "no video yet" |
| VideoSegmentId | int? FK → VideoSegment | **nullable**, `OnDelete=SetNull`; narrows the step to one section of that dance's video |
| DateAdded | datetime | |

Nav: Prerequisites (`RoadmapStepPrerequisite`).

### RoadmapStepPrerequisite  (the skill tree's edges)
Composite PK **(StepId, PrerequisiteStepId)**, both FK → RoadmapStep. `Step` side cascades;
`PrerequisiteStep` side is **NoAction** — two cascade paths into one table is more than Postgres
accepts. Both ends always belong to the same roadmap. *(No `DateAdded`.)*

⚠️ **Anything that deletes a roadmap's steps must delete its edges first.** Deleting a step
cascades away the edges that *start* at it, but the NoAction side doesn't, so an edge still
pointing at a step deleted earlier in the same pass fails its foreign key. `RoadmapSeeder`
and `RoadmapService.RemoveTreeAsync` both clear the edges up front for this reason — and
`RemoveTreeAsync` only works if the caller **`Include`d the stages and steps**, or it sees no
step ids, clears nothing, and the cascade blows up. That was a real bug in `DeleteAsync`.

**The unit tests will not catch this.** SQLite tolerates the ordering Postgres rejects, even
with `PRAGMA foreign_keys = ON` (measured, not assumed). The e2e `personal skill trees` suite,
which runs against real Postgres, is what caught it.

There is no roadmap-progress table: progress is read from the existing
`UserLearnedDances` / `UserInProgressDances` joins via the step's linked dance. A step's
depth and locked/available state are computed per-request in `RoadmapService`, not stored.

## Join entities (explicit, composite keys)

| Entity | Key | Meaning |
|--------|-----|---------|
| DanceStyle | (DanceId, StyleId) | dance ↔ style (many-to-many) |
| DanceMusicalStyle | (DanceId, MusicalStyleId) | dance ↔ musical style |
| DanceInstructor | (DanceId, InstructorId) | dance ↔ instructor; Instructor side `OnDelete=Restrict` |
| UserFavoriteDance | (UserId, DanceId) | user's favorites; + DateAdded |
| UserLearnedDance | (UserId, DanceId) | user marked learned; + DateAdded |
| UserInProgressDance | (UserId, DanceId) | user in progress; + DateAdded |
| UserMyStyle | (UserId, StyleId) | user's preferred styles; + DateAdded |

## Enums
- `DifficultyLevel { None=0, Beginner=1, Intermediate=2, Advanced=3 }`
- `ProfileVisibility { Public=0, Private=1 }` — **default Private**

## Relationship notes (from `OnModelCreating`)
- `Dance.Slug` and `User.Username` are unique indexes.
- VideoSegment, VideoRating, PracticeSession, DanceInstructor(dance side) → cascade delete.
- DanceInstructor → Instructor side is **Restrict** (can't delete an instructor still linked
  to a dance via cascade; remove links first).

## Migrations (chronological, in `Migrations/`)
`InitialCreate` → `AddMusicalStyles` → `AddVideoViewCount` → `AddIsAdminToUser` →
`AddMyStylesAndInProgress` → … (plus later ones for ratings, practice, instructors,
difficulty, visibility — check the folder for the current head). Add new ones with
`dotnet ef migrations add <Name> --no-build`.
