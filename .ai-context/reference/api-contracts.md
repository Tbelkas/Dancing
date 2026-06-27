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
