---
name: find-chips
description: Find and add "Sections" chips (VideoSegments) to DancePlatform tutorial videos by transcribing them and inferring topical sections. Use when asked to "find chips", "add sections/chips to videos", "process the chip queue", or chip new tutorial videos that lack a Sections bar.
---

# Find Chips — transcribe tutorials & add topical "Sections" chips

Goal: for a tutorial video with no `VideoSegments`, transcribe it and add 4–12 topical
**Section chips** (label + start/end) so the "Sections" bar renders on the dance page.
The chips = the `VideoSegments` table; distinct from "In this video" chapters (related dances).

## The queue & daily detector
- A local Windows Scheduled Task **`DanceChipCheck`** runs `find_chip_candidates.py` daily (09:00)
  and rewrites the `<!-- CHIP-QUEUE:START/END -->` block in **`SECTIONS_FIXUP.md`** with any
  tutorial videos still missing chips (⭐ = new since last check). Detection only — never writes the DB.
- `find_chip_candidates.py` reads the prod connection string from `DancePlatform.API/appsettings.Development.json`
  (no hardcoded password). State: `_proto/chip_skip.tsv` (deliberately-skipped) + `_proto/chip_seen.tsv`.
- To process: take the queued VideoDbId/YtId rows and run the per-video procedure below. **Must run
  locally** — the prod DB is on the LAN (`192.168.0.197`), unreachable from cloud agents.

## Prod DB / API
- Postgres on `192.168.0.197`, db `dancing`, user `dance_user`; password lives in
  `appsettings.Development.json` (rotates — read it, don't hardcode). PascalCase, double-quote identifiers.
  Site reads the DB live — **no deploy needed**.
- API base `https://dance-api.takelord.com/api` (the `/api` path on the main site returns the SPA).
  Verify a result: `GET /api/videos/dance/<danceId>` → each video's `videoType` + `segments`.

## Per-video procedure
For each queued video `<ytid>` (DB row `<videoDbId>`):

1. **Fetch transcript**: `python prep_sections.py <ytid>`
   Caches yt-dlp metadata + English auto-captions → `_proto/sec_<ytid>.txt`
   (title, duration, native chapters, condensed timestamped transcript). Prints `dur/chapters/caplines`.

2. **Decide the source of sections** by reading `_proto/sec_<ytid>.txt`:
   - **Human-curated native chapters** (clean labels like Intro / move names / Practice) →
     `python chapters_spec.py <ytid>` emits `Label@start-end;...`. Adopt, lightly cleaned
     (rename `<Untitled Chapter 1>`→`Intro`, title-case ALL-CAPS labels).
   - **Auto-generated chapters** (labels are transcript fragments, or course-promo links) → ignore them, infer from transcript.
   - **No usable chapters** → infer from the transcript: an Intro, one section per taught move/concept,
     a "Practice with music", and an Outro. Use the spoken cues ("the next thing", "let's add", "now we",
     "with music") as boundaries; convert m:ss to the section start.

3. **Apply** (dry-run first if unsure — omit `apply`):
   `python apply_sections.py <videoDbId> "Label@start-end;Label@start-end;..." apply`
   Inserts segments + sets `VideoType='tutorial'`. Times accept seconds or `m:ss`; end optional.
   Replaces any existing segments on that video. (The script pipes SQL via psql **stdin with
   PGCLIENTENCODING=UTF8** — required so en/em-dashes & accents in labels don't corrupt on Windows.)

4. **Verify** one or two via the API (`GET /api/videos/dance/<danceId>`), then update the log table in
   `SECTIONS_FIXUP.md`.

## Labeling guidance
- 4–12 sections; each a real topic, not filler. Keep Intro/Outro (useful nav), but fold pure rambling/tangents.
- Concise, specific labels ("Add the heel & toe", "The Jack (the groove)", "Practice with music").
- For multi-move routines/choreo, one chip per move in teaching order. For long combos, mark each new
  footwork addition + drill/music phases.

## When to SKIP (add to `_proto/chip_skip.tsv` so the daily check stops nagging)
- Music montages / performance clips with no spoken breakdown (can't timestamp moves without watching).
- Videos with no captions AND no chapters (no text signal) — note them; only do if worth a multimodal read.
- Sub-~4-min single-move clips (one move, no sub-topics).
- Broken-fetch (dur 0) or multi-dance montage rows.

## Done when
The CHIP-QUEUE block in `SECTIONS_FIXUP.md` shows "No videos awaiting chips." Relates to the
`fix-videos` skill (source correctness) — chips assume the attached video is the right one.
