# Reference — API Contracts

Base URL: dev `http://localhost:5000/api`, prod `https://dance-api.takelord.com/api`.
Auth column: **—** = anonymous · **Auth** = any logged-in user (`[Authorize]`) ·
**Admin** = `[RequireAdmin]` (DB `IsAdmin` check). Bodies are the `DTOs/` request types;
responses are `XxxDto` (never raw entities).

> The auth gap this warning used to describe is closed (known-issues A): `POST /dances`,
> `POST /videos` and `POST /styles` are all `[Authorize]`. They are deliberately **not**
> Admin-only — My Dances is a self-service add flow — and what keeps that safe is that a
> non-admin's dance is created `pending` and stays out of every public listing until reviewed.

> **Throttling.** `/auth/*` is capped at 10 requests / 5 min per caller, `/auth/login` at 60
> (guessing is caught by failed-attempt counting in `LoginThrottle`, not by volume),
> `POST /videos/{id}/view` at 30/min, and everything else at 600/min. Over the limit is a **429**
> with `Retry-After`. Partitioning is per signed-in user, else per IP — which depends on
> `UseForwardedHeaders`, since Apache proxies from localhost.

## Auth — `/api/auth`
| Method | Path | Auth | Body | Returns |
|--------|------|------|------|---------|
| POST | `/auth/login` | — | `LoginRequest { username, password }` | `AuthResponse { token, userId, username }` (400 on bad creds) |
| POST | `/auth/register` | — | `RegisterRequest { username, email, password, name, nickname }` | `AuthResponse`; **409** username taken *or* email already registered. `email` is required |
| POST | `/auth/forgot-password` | — | `{ email }` | **202 always**, known address or not. Mails a single-use link valid 2 h; only its SHA-256 is stored |
| POST | `/auth/reset-password` | — | `{ token, newPassword }` | `AuthResponse` (signs them straight in); 400 if the token is unknown, expired, superseded or spent |
| POST | `/auth/change-password` | Auth | `{ currentPassword, newPassword }` | `AuthResponse` — **a new token**, because the change retires every token issued before it, including the caller's. `currentPassword` may be empty for a provider-only account setting one |

JWT claims: `NameIdentifier`=userId, `Name`=username, `isAdmin`=`"true"`/`"false"` (signed),
plus `iat` (stamped explicitly in `TokenService.Write` — the constructor does not add one).
`UserTokenGuard` rejects any token whose `iat` predates `User.TokensValidFrom`, which is how a
password change, a reset, or a deletion signs other devices out of a 30-day stateless token.
The FE reads admin from the token claim (`jwtIsAdmin()`); there is no role endpoint.
All tokens — password *and* social — are issued by `ITokenService.CreateAccessToken`.

## Social sign-in — `/api/auth/external`

Google and Facebook only. **Instagram is not offered**: personal IG accounts have had no API
path since Basic Display shut down on 2024-12-04.

| Method | Path | Auth | Body | Returns |
|--------|------|------|------|---------|
| GET | `/auth/external/providers` | — | — | `ExternalProviderDto[]` — only providers with credentials configured. Empty array is normal on a dev box |
| GET | `/auth/external/{provider}/start` | — | — | **302** to the provider's consent screen (state + PKCE). 404 if the provider is unknown *or* unconfigured |
| POST | `/auth/external/{provider}/link-start` | Bearer | — | `{ url }` to navigate to. A POST so the token rides in a header, not the query string |
| GET | `/auth/external/{provider}/callback` | — | — | **302** to `{ui}/auth/callback#token=…` (known user), `{ui}/finish-signup#ticket=…` (new user), or `{ui}/profile?linked=…` (link flow). Errors bounce to `{ui}/login?error=oauth_state\|oauth_failed` |
| POST | `/auth/external/ticket` | — | `{ ticket }` | `SignupTicketDto { provider, email, name, suggestedUsername }`; 401 if expired/forged |
| POST | `/auth/external/complete` | — | `{ ticket, username }` | `AuthResponse`; 401 bad ticket, 409 username taken, 400 malformed username |
| GET | `/auth/external/links` | Bearer | — | `LinkedAccountsDto { accounts[], hasPassword }` |
| DELETE | `/auth/external/links/{provider}` | Bearer | — | 204; 404 not linked; **409 if it's the account's only way to sign in** |
| POST | `/auth/external/facebook/data-deletion` | — | form `signed_request` | `{ url, confirmation_code }`. Meta requires this before a FB app can go Live; HMAC-verified against the app secret |

The access token is returned in the **URL fragment**, never a query param — a fragment isn't
sent to the server, so it stays out of Apache's access log and out of `Referer` headers.

## Dances — `/api/dances`
| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/dances` | — | all dances (`DanceDto[]`) |
| GET | `/dances/{idOrSlug}` | — | by numeric id **or** slug; 404 if missing |
| POST | `/dances` | Auth | `CreateDanceRequest` → created `DanceDto`. A non-admin's lands `reviewState: "pending"` with `ownerUserId` set. **409** when the name already exists in one of the requested styles — the body carries `{ message, dance }` with the existing one |
| GET | `/dances/pending` | Admin | The review queue (`DanceDto[]`, oldest first) |
| POST | `/dances/{id}/review` | Admin | `{ reviewState: "approved" \| "pending" }` |
| PUT | `/dances/{id}` | Admin | `UpdateDanceRequest` |
| DELETE | `/dances/{id}` | Auth | Admin deletes anything; a contributor may withdraw **their own dance while it is still pending**, otherwise 404 |
| POST | `/dances/{id}/favorite` | Auth | toggle favorite for current user |
| POST | `/dances/{id}/learned` | Auth | toggle learned |
| POST | `/dances/{id}/inprogress` | Auth | toggle in-progress |

Ratings are **per video**, not per dance — see `POST /videos/{id}/rate` below. `DanceDto`
still exposes `averageRating`/`ratingCount`, now aggregated from the dance's videos' ratings,
plus per-user status flags when authenticated.

Every dance read is scoped by `DanceService.Visible(...)`: approved dances, plus the caller's
own pending ones, plus everything for an admin. `grandTotal` counts approved only.

## Health — `/api/health`
| Method | Path | Auth | Returns |
|--------|------|------|---------|
| GET | `/health` | — | `200 { status: "healthy", database: true }`, or **503** `{ status: "degraded", database: false }` when Postgres is unreachable |

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
| PUT | `/profile` | Auth | `UpdateProfileRequest { name, nickname, avatarUrl, visibility, useBetaViewer }` |
| PUT | `/profile/email` | Auth | `{ email }` → `UserProfileDto`; **409** if another account already has that address. Its own endpoint because it is the one profile field that can collide |
| DELETE | `/profile` | Auth | `{ password }` → 204. Erases the account and everything personal by cascade; contributed dances survive with `ownerUserId` cleared. **400** on a wrong password; an empty one is accepted only for a provider-only account |
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
