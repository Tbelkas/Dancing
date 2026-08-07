# Reference — API Contracts

Base URL: dev `http://localhost:5000/api`, prod `https://dance-api.takelord.com/api`.
Auth column: **—** = anonymous · **Auth** = any logged-in user (`[Authorize]`) ·
**Admin** = `[RequireAdmin]` (DB `IsAdmin` check). Bodies are the `DTOs/` request types;
responses are `XxxDto` (never raw entities).

> ⚠️ **Known auth gaps (see known-issues):** `POST /dances`, `POST /videos`, `POST /styles`
> currently have **no** auth attribute → callable anonymously, even though their
> Update/Delete are Admin-only and the analogous `POST /musicalstyles` & `POST /instructors`
> *are* Admin-only. Treat this as a bug to fix, not a pattern to copy.

## Auth — `/api/auth`
| Method | Path | Auth | Body | Returns |
|--------|------|------|------|---------|
| POST | `/auth/login` | — | `LoginRequest { username, password }` | `AuthResponse { token, userId, username }` (400 on bad creds) |
| POST | `/auth/register` | — | `RegisterRequest { username, password, name, nickname }` | `AuthResponse` |

JWT claims: `NameIdentifier`=userId, `Name`=username, `isAdmin`=`"true"`/`"false"` (signed).
The FE reads admin from the token claim (`jwtIsAdmin()`); there is no role endpoint.

## Dances — `/api/dances`
| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/dances` | — | all dances (`DanceDto[]`) |
| GET | `/dances/{idOrSlug}` | — | by numeric id **or** slug; 404 if missing |
| POST | `/dances` | ⚠️ **none** | `CreateDanceRequest` → created `DanceDto` |
| PUT | `/dances/{id}` | Admin | `UpdateDanceRequest` |
| DELETE | `/dances/{id}` | Admin | |
| POST | `/dances/{id}/favorite` | Auth | toggle favorite for current user |
| POST | `/dances/{id}/learned` | Auth | toggle learned |
| POST | `/dances/{id}/inprogress` | Auth | toggle in-progress |

Ratings are **per video**, not per dance — see `POST /videos/{id}/rate` below. `DanceDto`
still exposes `averageRating`/`ratingCount`, now aggregated from the dance's videos' ratings,
plus per-user status flags when authenticated.

## Search — `/api/search`
| Method | Path | Auth | Query params |
|--------|------|------|--------------|
| GET | `/search/dances` | — | `q?`, `styleId?`, `musicalStyleId?`, `difficulty?` (string), `status?` (`notstarted`/`inprogress`/`learned`/`favorite`) |

`status` filtering is per current user when authenticated. (Note: the dances page also does
some client-side filtering; see module-context/dances-catalog.md.)

## Videos — `/api/videos`
| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/videos/dance/{danceId}` | — | videos for a dance; current user's 4–5★ videos sorted first |
| GET | `/videos/{id}` | — | single video (+ segments) |
| GET | `/videos/youtube/{videoId}/chapters` | Admin | the YouTube video's own chapters → `YoutubeChaptersDto { videoId, duration, source: chapters\|description\|none, chapters: VideoSegmentDto[] }`; empty list when it has none (never errors) |
| POST | `/videos/{id}/view` | — | increment `ViewCount` |
| POST | `/videos/{id}/rate` | Auth | `RateVideoRequest { rating 1–5 }` (upsert; one per user/video) → updated `VideoDto` |
| POST | `/videos` | ⚠️ **none** | `CreateVideoRequest` |
| PUT | `/videos/{id}` | Admin | `UpdateVideoRequest` |
| DELETE | `/videos/{id}` | Admin | cascades to segments |

## Styles — `/api/styles`  (dance categories)
| Method | Path | Auth |
|--------|------|------|
| GET | `/styles` | — |
| GET | `/styles/{id}` | — |
| POST | `/styles` | ⚠️ **none** |
| DELETE | `/styles/{id}` | Admin |
| POST | `/styles/{id}/mystyle` | Auth | toggle style in user's "my styles" |

## Roadmaps — `/api/roadmaps`  (curated learning paths + personal skill trees)
| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/roadmaps` | — | `RoadmapSummaryDto[]`; curated paths **plus the caller's own trees** |
| GET | `/roadmaps/{idOrSlug}` | — | `RoadmapDto` (stages → steps → dance → videos); 404 if missing |
| POST | `/roadmaps` | User | `SaveRoadmapRequest` → 201 `RoadmapDto`; creates a personal tree |
| PUT | `/roadmaps/{id}` | User | `SaveRoadmapRequest` → `RoadmapDto`; **replaces the whole tree** |
| DELETE | `/roadmaps/{id}` | User | 204; own trees only |
| PUT | `/roadmaps/{id}/share` | User | `{ shared }` → `RoadmapDto`; own trees only |
| POST | `/roadmaps/{idOrSlug}/copy` | User | 201 `RoadmapDto`; forks any readable path into one of the caller's own |

**Reads use two different visibility rules.** `GET /roadmaps/{idOrSlug}` serves curated paths,
the caller's own trees, **and** any tree its owner has shared. `GET /roadmaps` (the index) serves
curated paths and the caller's own **only** — a shared tree is reachable by its link and listed
on its owner's profile (`GET /users/{username}` → `sharedRoadmaps`), never on the index.

Sharing is its own endpoint rather than a field on `SaveRoadmapRequest`, because a save replaces
the whole tree and would otherwise let a stale builder tab unshare one. A fork is always private
regardless of what it was forked from.

The two GETs are anonymous but **not** response-cached — `learnedCount` / `inProgressCount`,
`availableCount` and each step's `isLearned` / `isInProgress` / `state` are per current user.
Progress is written through the existing `PUT /dances/{id}/status`, not a roadmap endpoint.

`isOwned` on both DTOs means "the caller built this" and is what the UI gates its edit / delete /
share affordances on. `isPublic` + `ownerUsername` / `ownerNickname` carry the sharing state and
attribution; on a curated path `isOwned` and `isPublic` are false and the owner fields are null. **Curated paths are not API-editable** — they are seeded
from `Data/Roadmaps/*.json`, and the write endpoints match on `OwnerUserId == callerId`, so a
curated path and another user's tree both simply fail to match. Every write therefore answers
**404, not 403**: whether a private tree exists at that id isn't the caller's business either.

A save is all-or-nothing and takes the whole tree (`SaveRoadmapRequest`: stages → steps, each
step carrying `key`, `requires`, optional `danceId` / `videoSegmentId`). The service replaces
the stored stages, steps and edges wholesale. It is forgiving about stale input — a blank step
title, an edge naming a step that no longer exists, or a `danceId` that has since been deleted
are dropped — but **refuses a cycle with a 400** and `{ message }`, since the user drew that
link deliberately and dropping it silently would read as the save not working.

A step carries the skill tree: `key`, `requires` (keys of earlier steps), `stageIndex`, `depth`
(ring) and `state` (`learned` / `available` / `locked`). `depth` and `state` are **computed
per-request**, not stored. `dance` is null when the catalog has no move for the step yet;
`segment` is set when it's pinned to one section of a video.

## Musical Styles — `/api/musicalstyles`
| Method | Path | Auth |
|--------|------|------|
| GET | `/musicalstyles` | — |
| GET | `/musicalstyles/{id}` | — |
| POST | `/musicalstyles` | Admin |
| DELETE | `/musicalstyles/{id}` | Admin |

## Instructors — `/api/instructors`
| Method | Path | Auth |
|--------|------|------|
| GET | `/instructors` | — |
| GET | `/instructors/{id}` | — |
| POST | `/instructors` | Admin (`CreateInstructorRequest`) |
| DELETE | `/instructors/{id}` | Admin |

## Practice — `/api/practice`  (controller is `[Authorize]` at class level)
| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/practice` | Auth | current user's sessions (`PracticeSessionDto[]`) |
| POST | `/practice` | Auth | `CreatePracticeSessionRequest { danceId, date (DateOnly), durationMinutes?, notes? }` |
| DELETE | `/practice/{id}` | Auth | own sessions |

## Profile — `/api/profile`  (class-level `[Authorize]`)
| Method | Path | Auth | Returns |
|--------|------|------|---------|
| GET | `/profile` | Auth | `UserProfileDto` (own profile) |
| PUT | `/profile` | Auth | `UpdateProfileRequest { name, nickname, avatarUrl, visibility }` |
| GET | `/profile/my-dances` | Auth | `MyDancesDto` (favorites / learned / in-progress lists) |

## Public users — `/api/users`
| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/users/{username}` | — | `PublicProfileDto` **only if `Visibility == Public`**, else not-available response |

## Import (admin tooling) — `/api/import`
| Method | Path | Auth | Body |
|--------|------|------|------|
| POST | `/import/dances` | Admin | `BulkImportRequest` → `BulkImportResult` |
| POST | `/import/youtube-video` | Admin | `YoutubeVideoImportRequest` |
