# Module — Dances Catalog (browse, detail, search, ratings, status)

> Load alongside core-context.md when the task touches browsing, dance detail, search/filter,
> ratings, or favorite/learned/in-progress.

## Backend
- Controller: `Controllers/DancesController.cs`, `Controllers/SearchController.cs`
- Service: `IDanceService` / `DanceService.cs` (browse, get-by-id-or-slug, create/update/delete,
  toggles, rate, **`SearchAsync(q, styleId, musicalStyleId, difficulty, status, currentUserId)`**)
- Slug: `Services/SlugGenerator.Slugify`
- Models: `Dance`, `DanceRating`, joins `DanceStyle`/`DanceMusicalStyle`/`DanceInstructor`,
  status joins `UserFavoriteDance`/`UserLearnedDance`/`UserInProgressDance`
- DTOs: `DTOs/Dance/` — `DanceDto`, `CreateDanceRequest`, `UpdateDanceRequest`, `RateDanceRequest`
- Endpoints: see api-contracts → Dances + Search.

## Frontend
- Pages: `pages/dances/` (list + filters), `pages/dance-detail/` (slug-addressed),
  `pages/my-dances/` (the user's favorites/learned/in-progress; default landing route)
- Service: `core/services/dance.service.ts`
- Model: `models/dance.model.ts`
- Routes: `/dances`, `/dances/:slug`, `/my-dances` (guarded). `''` redirects to `/my-dances`.

## Key behaviours / rules
- Detail is by **slug**; on API **404** the page shows a "Dance not found" state with a Browse
  link (do not silently redirect — known-issues #4).
- **Difficulty** filter pills: None/Beginner/Intermediate/Advanced.
- Filters: name (`q`), style, musical style, difficulty, and **status**
  (`notstarted`/`inprogress`/`learned`/`favorite`). `status` is per-user when authed.
  Some filtering is also done client-side on the dances page — keep server + client in sync
  if you change filter semantics.
- **Ratings:** 1–5, one per user/dance (upsert via `POST /dances/{id}/rate`); aggregate
  average + count shown on cards and detail.
- Favorite/Learned/In-Progress are independent toggles (`POST /dances/{id}/{favorite|learned|inprogress}`).

## Gotchas
- `POST /dances` is currently **unauthenticated** (known-issues #A) and allows duplicate names
  (known-issues #B). If you build a create UI, gate it and warn on name collision.
