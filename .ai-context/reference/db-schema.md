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
