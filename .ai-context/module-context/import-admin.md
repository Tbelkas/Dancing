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

## Adding videos — the current flow (2026-08-26)

`archive/SEED_FLOW.md` is **history, not instructions**. It searched YouTube for a move name
and inserted whatever came back; nothing checked that the video taught the move, and its
success criteria were counts ("50 dances, 60% with a video"). That is how the catalogue got
1,153 videos nobody had watched. Don't run it.

Four stages, and the order is the point — nothing is written before it is judged:

| Stage | Script | Writes |
|---|---|---|
| 1 find | `scripts/find_videos.py` | `Videos` rows as `ReviewState='pending'` |
| 2 verify | `scripts/verify_intake.py` | `QualityScore` / `QualityFlags` / `ReviewNote` only |
| 3 review | Intake tab in `scripts/chip_ui.py` | `ReviewState` — **a human, never a script** |
| 4 chip | `/find-chips` → `apply_sections.py` | `VideoSegments` |

- **Nothing reaches the site on a search engine's say-so.** Raw inserts default to `pending`
  (`QuarantineRawInsertsByDefault`) and the global query filter in `AppDbContext` hides
  anything not `approved` from every public read.
- **`POST /import/youtube-video` honours the gate** (`honourGate: true`); the add-video form
  does not, by design — a person already looked at it. Both record a score.
- **Titles are a claim; audio is the evidence.** Searching the Breakdance move "Blade" returns
  a Super Smash Bros guide to Marth's "Dancing Blade" that scores 0.90 on every title signal.
  Only `verify_intake.py` can reject it. Never promote on title score alone.
- Two judgements show side by side in Intake and they mean different things: the rubric
  (`video_gate.py`, tiers 0–2) says whether a video is thin/dead/duplicated; the audio verdict
  says whether it is a dance video that teaches *this* move. Disagreement is the signal.

### Rules of thumb learned the hard way
- **Calibrate on the distribution you'll meet, not the one you have.** A vocabulary threshold
  tuned on 49 catalogue videos (long, clean, English) rejected three genuine tutorials in the
  first ten rows of the real queue.
- **Don't widen a rule to fix false rejects** — that let the Smash guide back in. Split it:
  dance-specific terms decide, generic motion verbs only corroborate.
- **Absence of evidence is not evidence.** `silent` and `no-transcript` score at the review
  boundary, not low; wordless mirrored walkthroughs are a real tutorial format.
- **Re-score after any bulk change**, then `enrich_views.py` and `backfill_durations.py`
  (see the seeding-pitfalls notes).

## Data-cleanup precedent (do it this way)
One-off **production data** fixes are done by hand on the Pi against the `dancing` DB, **after
taking a backup** (e.g. `dances-backup-YYYYMMDD.sql` locally + on the Pi), and after checking
no rows reference what you delete. Precedent: the 2026-06-13 duplicate-dance cleanup
(known-issues #B). **Schema** changes still always go through EF migrations.
