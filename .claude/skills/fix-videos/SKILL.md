---
name: fix-videos
description: Continue the DancePlatform video-fixup batch — classify each multi-dance YouTube video, correct its dances/timestamps/segments in the prod DB, and mark progress in VIDEO_FIXUP.md. Use when asked to "continue fixing videos", "keep grinding the video queue", "process the next videos", or resume the fixup tracked in VIDEO_FIXUP.md.
---

# Fix Videos — batch classify & repair dance↔video data

Goal: for each multi-dance video, make the DB reflect the *real* moves taught in it, with
accurate timestamps, keeping correct moves and rebuilding only wrong-source ones. Track every
video's outcome in `VIDEO_FIXUP.md`.

## State & source of truth
- **`VIDEO_FIXUP.md`** (repo root) is the live tracker. Each row: `# | VideoId | #Dances | Status | Result | Notes`.
- Pick the next row whose Status is **🎥 REBUILD** or **⚠️ RETRY** (or 🔧 NEEDS-TIMES). Skip ✅/🗑️/❌.
- `_proto/<vid>.json` caches yt-dlp metadata; `_proto/` holds montages (gitignored scratch).

## Prod DB
Postgres `192.168.0.197` db `dancing` user `dance_user` pw `dancebabydance` (PascalCase, double-quote identifiers).
All `Dances` FKs are `ON DELETE CASCADE`, so deleting a dance clears its Videos/DanceStyles/etc.
Identity IDs auto-generate. The site reads the DB live — **no deploy needed**.

## Per-video procedure
For each pending video `<vid>`:

1. **Classify**: `python prep_video.py <vid>`
   Reads chapters + description timestamps + caption availability + current DB dances, prints a VERDICT:
   - `TIMED_OK` → names match + all timed → mark ✅ VERIFIED, no DB change.
   - `NAMES_MATCH_NEED_TIMES` → correct names, missing times → `python map_times.py <vid> apply` (keeps dances, sets StartTime/EndTime from chapters). Mark ✅ DONE.
   - `MISMATCH` / `NEEDS_MULTIMODAL` → wrong-source → **rebuild** (step 2).
   - `FETCH_FAILED` → `rm _proto/<vid>.json` and retry once. If yt-dlp says *"video is not available"* → mark ❌ DEAD, move on.

2. **Decide the rebuild shape** by looking at the title + chapters (and the video itself if needed — step 3):
   - **Single-move tutorial** (title names one move, e.g. "How to Windmill"): the video teaches ONE move.
     - First check for an existing canonical dance: `SELECT "Id","Name" FROM "Dances" WHERE lower("Name")=lower('<move>');`
     - If it exists **and is NOT one of the dances already on this video** → `python rebuild_video.py <vid> attach <existingDanceId> apply` (adds this video as another clip, deletes the wrong dances).
     - If the good dance **is already one of this video's dances** (common for over-split lessons) → `python rebuild_video.py <vid> keep <danceIdToKeep> apply` (deletes the wrong siblings, keeps that dance + its existing video link). Prefer keeping a dance that has multiple videos.
     - Else → `python rebuild_video.py <vid> single "<Move Name>" <styleId> apply`.
   - **Real multi-move list** (e.g. "10 Basic Jazz Dance Moves" with real move chapters): `python rebuild_video.py <vid> tutorial "<Video Title>" <styleId> "Label@start-end;Label@start-end;..." apply`. Build segments from the *real* move chapters only — **drop meta sections** (Intro/Outro/Start/Steps/Tutorial/"Bad Habit"/"How to"/section headers). Use chapter start as segment start and the next chapter start (or duration) as end.
   - **Not a moves video** (technique talk, "5 bad habits", reactions): `python rebuild_video.py <vid> delete apply`.

3. **Multimodal read** (only when there is no usable text signal, or to confirm a mismatch). The move name is usually on-screen as a title card:
   ```
   yt-dlp --no-warnings -f "bv*[height<=480]+ba/b[height<=480]/b" -o "_proto/<vid>.%(ext)s" "https://www.youtube.com/watch?v=<vid>"
   ffmpeg -y -loglevel error -i _proto/<vid>.<ext> -vf \
     "fps=1/2,scale=520:-2,drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='%{pts\:hms}':x=10:y=10:fontsize=30:fontcolor=yellow:box=1:boxcolor=black@0.75,tile=4x4:margin=6:padding=6" \
     -frames:v 4 _proto/<vid>_%02d.png
   ```
   Then `Read` each `_proto/<vid>_NN.png` montage and OCR the on-screen move names + their burned timestamps (top-left). Reject intro/credit cards. Feed the result into the rebuild in step 2 (`single` or `tutorial`). Segment times from 2s sampling are ±2s — acceptable.

4. **Mark the tracker**:
   `python update_tracker.py <vid> "<status emoji+word>" "<result>" "<notes>"`
   Statuses: `✅ DONE`, `✅ VERIFIED`, `🗑️ DELETED`, `❌ DEAD`.

## Style IDs
1 Latin · 2 Ballroom · 3 Street/Urban · 4 Classical/Ballet · 5 Folk/Traditional · 6 Swing ·
7 Contemporary · 8 Waacking · 9 Tektonik · 10 Hip-hop · 11 House · 12 Breakdance · 13 Afrobeats ·
14 Dancehall · 15 Krump · 16 Vogue · 17 Bhangra · 18 Flamenco · 19 Tap · 20 Jazz · 21 K-Pop
(Generic umbrellas Street/Urban and Hip-hop lose to a more specific style.)

## Rules
- **Verify before destroying**: always dry-run `rebuild_video.py`/`map_times.py` (omit `apply`) and read the summary before applying.
- **Don't duplicate**: for any move that already exists as a dance, `attach` rather than create.
- **Keep correct moves**; only rebuild genuinely wrong-source videos (the user chose "fix-broken, keep moves").
- **Checkpoint**: after each batch (~5–10 videos, or each multimodal one), report progress and the updated counts. Stop if the user says so.
- Process biggest `#Dances` first among pending. Single-move/title-resolvable videos are fast (no download); multimodal videos are ~one per turn.

## Done when
All `VIDEO_FIXUP.md` rows are ✅/🗑️/❌. Then offer to tackle the 354 single-move videos (separate, lower-yield tier).
