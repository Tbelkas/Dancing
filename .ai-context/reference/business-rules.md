# Reference — Business Rules

The rules the system enforces (or should), and *why*. When code and this file disagree,
fix whichever is wrong — but decide deliberately.

## Identity & access
- **Admin is the signed `isAdmin` JWT claim**, stamped from `Users.IsAdmin` at login and
  checked by `RequireAdminAttribute` (no per-request DB lookup). *Why:* the HMAC signature
  makes the claim tamper-proof, and gating is stateless. *Trade-off:* a grant/revoke only
  takes effect on the user's next login (the claim is fixed for the token's 30-day life).
- **`[Authorize]`** = any authenticated user; **`[RequireAdmin]`** = curators only.
- The **current user id always comes from the JWT** (`NameIdentifier`), never from request
  body/route. Users act only on their own favorites/learned/in-progress/ratings/practice.
- Passwords are **BCrypt-hashed**; never stored or logged in plaintext.

## Catalog (dances, videos, styles)
- A dance has a **unique slug** auto-generated from its name (`SlugGenerator`). The public
  detail page is addressed by slug; ids also resolve via `GET /dances/{idOrSlug}`.
- **Difficulty** is one of `None/Beginner/Intermediate/Advanced` (None = unset).
- A dance ↔ styles, ↔ musical styles, ↔ instructors are **many-to-many**; a dance → videos is
  **one-to-many**; a video → segments is **one-to-many** (segments cascade-delete with video).
- **Video clips** can be bounded by `StartTime`/`EndTime` (seconds); **segments** are named
  sub-ranges (e.g. "Chorus") for the player's repeat-region feature.
- `ViewCount` increments via an explicit, unauthenticated `POST /videos/{id}/view`.
- **Duplicate dance names are currently allowed** (API auto-suffixes the slug). This is a
  known data-quality weakness — new create flows *should* warn on name collision
  (known-issues #5). Don't rely on name uniqueness anywhere.

## Engagement (per-user status)
- Favorite / In Progress / Learned are independent **toggles** (composite-key join rows). A
  dance can be in any combination; toggling adds/removes the row.
- **Ratings are 1–5, one per user per video** (composite PK `(UserId, VideoId)` → upsert).
  Each video shows its own average; a dance aggregates its videos' ratings (average + count)
  for cards and detail. On a dance's detail page, the current user's 4–5★ videos sort first.
- "My Styles" lets a user tag preferred dance styles (toggle on `Style`).

## Practice log & streaks  (timezone-sensitive — read carefully)
- A `PracticeSession` records a **calendar `Date` (DateOnly)**, optional duration & notes,
  for one dance, for the current user.
- **Day logic must be local, not UTC.** "Today"/"yesterday" for the streak and the form's
  default date use the **user's local date**. *Why:* using UTC made sessions logged after
  local midnight (but before UTC midnight) count as the wrong day and broke streaks east of
  UTC; and rendering `DateOnly` via `new Date(str)` shifted dates a day west of UTC.
  → FE: default `= local today`; render by parsing `str + 'T00:00:00'` (local midnight).
- Streak = consecutive local days with ≥1 session, anchored on local today/yesterday.

## Profiles & visibility
- **Profiles default to `Private`.** A profile is exposed at `GET /users/{username}` **only
  when `Visibility == Public`**; otherwise the API returns a "not available" response and the
  UI shows "Profile not available" (works for anonymous viewers too).
- Editable profile fields: `name`, `nickname`, `avatarUrl`, `visibility`. Username is the
  unique identity and is not part of the profile edit.

## Data hygiene
- Every entity stamps **`DateAdded` (UTC)** on creation.
- Schema changes go through **EF migrations**; they auto-apply on API startup. One-off
  **production data** fixes are done manually on the Pi **with a backup taken first**
  (precedent: known-issues #5 — duplicate-dance cleanup, backed up before deleting).

## Content / UX
- Design voice: **warm and energetic, no emojis** in product copy.
- Embeds come from third parties (YouTube/TikTok/Instagram); their console noise is out of
  scope (known-issues #6).
