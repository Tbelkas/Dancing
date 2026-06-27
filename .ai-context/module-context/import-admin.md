# Module — Import & Admin Tooling

> Load alongside core-context.md for bulk import / admin curation tasks.

## Import
- Controller: `Controllers/ImportController.cs` (both endpoints `[RequireAdmin]`)
- Service: `IImportService` / `ImportService.cs`
- DTOs: `DTOs/Import/` — `BulkImportRequest` → `BulkImportResult`, `YoutubeVideoImportRequest`
- Endpoints:
  - `POST /import/dances` — bulk-create dances (returns a `BulkImportResult` summary)
  - `POST /import/youtube-video` — import a YouTube video onto a dance

## Admin surface in general
- Admin = signed `isAdmin` JWT claim (stamped from `Users.IsAdmin` at login), enforced by
  `RequireAdminAttribute`. FE reads it from the token via `jwtIsAdmin()`.
- Admin-gated writes: dance/video update+delete, style delete, musical-style create+delete,
  instructor create+delete, all import.
- **`POST /dances`, `POST /videos`, `POST /styles` are `[Authorize]` (any signed-in user), by
  design** — the "My Dances" page lets a normal user add their own style/dance/video. They are
  intentionally NOT `[RequireAdmin]`; don't "fix" that without also reworking the My Dances flow.

## Seeding
- `Data/SeedData.cs` runs on API startup **only if the Dances table is empty**
  (`if (await db.Dances.AnyAsync()) return;`). It seeds Styles, Musical Styles, Dances, and an
  admin user. Editing seed data won't affect an already-populated DB.

## Data-cleanup precedent (do it this way)
One-off **production data** fixes are done by hand on the Pi against the `dancing` DB, **after
taking a backup** (e.g. `dances-backup-YYYYMMDD.sql` locally + on the Pi), and after checking
no rows reference what you delete. Precedent: the 2026-06-13 duplicate-dance cleanup
(known-issues #B). **Schema** changes still always go through EF migrations.
