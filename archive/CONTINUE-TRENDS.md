# Trending-Dances Expansion — Continuation Brief (self-contained)

Goal: keep adding **trending dances** (YouTube tutorials, embeddable) across styles, **chip each** with
topical "Sections" (VideoSegments), and add a few TikToks per new style. Repo-root Python scripts do the work.
Site reads the prod DB live — **no deploy**. Full per-round history is in `SECTIONS_FIXUP.md`.

## DB / API
- Prod Postgres `192.168.0.197` db `dancing` user `dance_user`. Password is hardcoded in `apply_sections.py`
  / `insert_picks.py` (`PGPW`) — read it there (rotates). PascalCase, double-quote identifiers. PGCLIENTENCODING=UTF8.
- Verify live: `curl -s https://dance-api.takelord.com/api/videos/dance/<danceId>` → each video's `platform`,`videoId`,`segments`.

## Per-round procedure (≈30–36 dances)
1. **New styles** (optional): `INSERT INTO "Styles"(...DateAdded now())` (and `"MusicalStyles"` if needed — both need DateAdded). Note the returned ids.
2. **Search**: copy `trend_search5.py` → bump number, edit the `C=[(name,styleId,musicId,query),...]` list, run.
   yt-dlp subprocess MUST use `encoding="utf-8", errors="replace"` (non-ASCII titles crash otherwise).
3. **Pick** best per dance from the printed results (prefer clear tutorials 3–12 min for good chips).
4. **Dedup**: query the FULL `Dances` table case-insensitively for ALL candidate names BEFORE inserting.
   `insert_picks.py` only checks slug uniqueness within the dance's OWN style, so a same-named move under
   another style slips through and gets a `-2` slug — that suffix is the tell a cross-style dup was created
   (delete it). Drop colliding names or tag the existing dance with the new style instead.
5. **Verify embeddability**: copy `verify_picks5.py` → bump number, edit PICKS, run. Keep only `playable_in_embed=True`.
   Writes `_proto/picks_verifiedN.tsv`.
6. **Insert**: `cp _proto/picks_verifiedN.tsv _proto/picks_verified.tsv && python insert_picks.py apply`.
   Writes `_proto/inserted.tsv` (ytid,videoDbId,danceId,dur,name).
7. **Chip** each inserted YouTube video:
   - prefetch: loop `python prep_sections.py <ytid>` over `_proto/inserted.tsv` → `_proto/sec_<ytid>.txt` (prints dur/chapters/caplines).
   - **native chapters** clean? `python chapters_spec.py <ytid>` → adopt, lightly cleaned (Untitled→Intro,
     title-case). K-pop tutorials come as 19–27 chapters (Part N × slow+mirrored) — **condense to one chip per part** (≤~13).
   - else **read the transcript** and infer 4–12 topical sections (Intro / each taught move / practice-with-music / outro).
   - apply: `python apply_sections.py <videoDbId> "Label@start-end;Label@start-end;..." apply` (times accept m:ss).
8. **Skip chipping** when: no captions AND no chapters; sub-~90s single-move; garbled/auto-translated captions;
   "challenge" chant captions; music-**production** tutorial (verify the video teaches *dancing*, not beat-making).
9. **TikTok** (a few per new style): WebSearch `"<style> dance tiktok.com/@ video"`, verify each URL with yt-dlp
   (`-J`, errors="replace"); some IPs are blocked—try alternates. Insert as `platform='tiktok'`,
   VideoType `'steps'` (or `'tutorial'`). Chips N/A (too short). Frontend fully supports tiktok embeds.
10. **Log** the round in `SECTIONS_FIXUP.md` + update cumulative totals.

## State after Round 11 (2026-06-30)
- Totals: **1007 dances / 1046 videos / 2891 segments / 15 TikToks / 41 styles** (max dance id 2050). Dances crossed 1000.
- **Round 11 = GENERAL broad #2** (world/folk heavy): 39 dances. `insert_general11.py` (inline). Lesson: YouTube
  videos can go "not available" or lose embedding between search and verify — **re-verify embeddability immediately
  before insert**, keep alternates handy. Re-parent same-style `-2` dupes onto the existing dance as 2nd takes.

## State after Round 10 (2026-06-30)
- Totals: **968 dances / 1006 videos / 2688 segments / 15 TikToks / 41 styles** (highest style id = 41; max dance id 2010).
- **Round 10 = GENERAL broad batch** (user: "random/general videos, 3x more"): 44 dances across 15 styles
  (world/folk, tap, contemporary, ballroom, swing, latin, etc.). Used `insert_general10.py` (inline picks WITH
  music+difficulty). **Catalog now very deep** — 34/53 candidates were dupes. For general rounds: ALWAYS dedup
  the FULL table incl. `%west coast%`, `%salsa shine%`, `%pas de bourree%`, `%stag leap%`, `%bachata dip%` etc.
  (5 slipped past as `-2` slugs → re-parented onto existing dances as 2nd takes, dupe dance rows deleted).
- Style/Music id maps (for general inserts): Latin1 Ballroom2 Street3 Ballet4 Folk5 Swing6 Contemporary7 Waacking8
  Tektonik9 HipHop10 House11 Breakdance12 Afrobeats13 Dancehall14 Krump15 Vogue16 Bhangra17 Flamenco18 Tap19 Jazz20
  Tutting22 Stretching23 Amapiano28 Shuffle29 Litefeet30 KPop31 Heels32 Reggaeton33 Twerk34 JerseyClub35 Bachata36
  Soca37 BrazilianFunk38 Kizomba39 AfroHouse40 Gqom41. Music: Salsa1 Classical2 HipHop3 Jazz4 Tango5 Electronic6
  Reggaeton8 Flamenco10 Afrobeats11 Dancehall12 Bhangra13 Amapiano16 Bachata17 Soca18 Kizomba19 AfroHouse20 Gqom21.

## State after Round 9 (2026-06-30)
- Totals: **924 dances / 957 videos / 2451 segments / 15 TikToks / 41 styles** (highest style id = 41; max dance id 1961).
- **Rounds 7–9 = STRETCHING focus** (user request): Stretching style **id 23** went 1→**46 dances** (1887–1901, 1932–1961).
  Stretching is now mined deep (splits, oversplits, backbends, hips, hamstrings, calves, feet, neck, wrists, spine,
  warm-ups/cool-downs, yoga poses, CARs, PNF, squat mobility). Further stretching rounds will hit heavy dedup —
  pivot to general trend queue or niche angles (partner stretching, equipment-specific, injury-rehab) if continuing.
  Stretching dances carry **NO music tag** (matches existing) — use `insert_stretch.py`/`insert_stretch8.py` (no
  DanceMusicalStyles, per-dance Difficulty); `trend_search{7,8}.py` / `verify_picks{7,8}.py` repurpose the `music`
  col as difficulty. Stretching tutorials are long follow-alongs (5–23 min) but usually have native chapters → easy chips.
- **⚠️ `cp tsv && python insert` is unreliable here** — the repo path sync-lags, so the insert reads a STALE
  picks_verified.tsv and re-inserts the previous round as `-2` dupes. **Inline the picks in the insert script**
  (see `insert_stretch8.py`) instead of reading an external TSV. If dupes appear (`-2` slugs), delete by id range.
- 14 styles added across rounds 1–6: Amapiano(28), Shuffle(29), Litefeet(30), K-Pop(31), Heels(32),
  Reggaeton(33), Twerk(34), Jersey Club(35), Bachata(36), Soca(37), Brazilian Funk(38), Kizomba(39),
  Afro House(40), Gqom(41).
- MusicalStyles incl. Amapiano(16), Bachata(17), Soca(18), Kizomba(19), Afro House(20), Gqom(21); base set:
  Salsa1 Classical2 HipHop3 Jazz4 Tango5 Electronic6 Reggaeton8 Flamenco10 Afrobeats11 Dancehall12 Bhangra13.
- Per-round scripts now exist through `trend_search6.py` / `verify_picks6.py` — copy the latest, bump the number.
- **Catalog is now deep in hip-hop/breakdance/popping/locking classics** — always full-table dedup-check first;
  round 6 had to drop 9 names (6-Step, Baby Freeze, Cabbage Patch, Chair Freeze, Paddle Turn, Reject, Skate,
  Smurf, Wu-Tang) that already existed.

## Ideas not yet mined (round 6+)
Kizomba, Gqom, Coupé-Décalé, Ndombolo, Salsa shines (more), Bachata footwork combos, more K-pop
(BLACKPINK/IVE/RIIZE/ENHYPEN recent), Heels floor combos, Vogue (Old Way/New Way more), Voguing hands,
Krump (buck/getoff), Tap (pullbacks/paddle), Breaking (toprock/6-step variations), Popping (waving/tutting more),
Locking (points/wrist rolls), House (jacking/footwork more), Afro House, Gwara variations, more Dancehall (Genna/Gallis),
Hip-hop classics still missing (Reject, Cat Daddy done, Jerk, Wu-Tang, Bernie, Cabbage Patch, Smurf).
