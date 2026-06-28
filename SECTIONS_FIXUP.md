# Section Chips — transcript-inferred VideoSegments for tutorials

Goal: for full-tutorial videos with no `VideoSegments`, transcribe the video and add
topical section chips (label + start/end) so the "Sections" bar renders on the dance page.

## Workflow
1. `python prep_sections.py <ytid>` → caches metadata + auto-captions, writes `_proto/sec_<ytid>.txt`
   (title, duration, native chapters, condensed timestamped transcript).
2. Read the transcript, infer 4–10 meaningful topical sections (drop pure filler).
   Skip videos under ~3 min or with no real sub-topics.
3. `python apply_sections.py <videoDbId> "Label@start-end;..." apply` → inserts segments,
   sets `VideoType='tutorial'`. Dry-run without `apply`. Times accept seconds or m:ss.
4. Mark the row below.

Scope chosen by user: **full tutorials first** (titles ILIKE '%tutorial%' or VideoType=tutorial,
no existing segments). 99 distinct YouTube videos / 106 Videos rows. Live DB, no deploy.

## Log
| VideoDbId | YtId | Dance | Status | Sections | Notes |
|---|---|---|---|---|---|
| 17 | 1dQxTwiPQkg | Loose legs | ✅ DONE | 9 | House tutorial; demo case |
| 364 | jFPijt5ocPE | Slide Step | ✅ DONE | 5 | native chapters |
| 297 | ovNk6AFbLfI | Pivot Turn | ✅ DONE | 10 | native chapters |
| 1708 | hBt4BU3CE4U | Tutting | ✅ DONE | 6 | native chapters |
| 301 | __F7mK9-myA | Cross-Step Backward | ✅ DONE | 16 | native chapters (tango ocho) |
| 977 | XZMkyZk9Go8 | Dance for Me | ✅ DONE | 5 | native chapters (afrobeat moves) |
| 1657 | 0dB7JjpBMtI | Windmill | ✅ DONE | 3 | native chapters |
| 315 | 5eXMcG1HvyM | Milkshake | ✅ DONE | 25 | native chapters (long choreo) |
| 698 | -lrINh3JetY | Arm Wave Wide | ✅ DONE | 7 | transcript |
| 404 | EfkgoZbVL98 | The Robot | ✅ DONE | 8 | transcript |
| 980 | Q_Slhxjp3tU | Ikawe | ✅ DONE | 14 | transcript (Cut It choreo) |
| 815 | U5BZPTS_htM | Rumba Alemana | ✅ DONE | 11 | transcript (chapters were promos) |
| 1671 | Rq0ovsiB4MQ | Pirouettes/Fouettés | ✅ DONE | 8 | transcript |
| 1676 | Z5ZKDmc6sNE | Waacking | ✅ DONE | 8 | transcript |
| 957 | ZubfOGRpWRk | Gbe Gbe | ✅ DONE | 8 | transcript (3 amapiano moves) |

### Batch 2 — chapter-based (reviewed & adopted)
839 Double Flare · 585 Running Man Variation · 817 Bachata Body Wave · 1665 Tap Dance Basics ·
324 Chest Slide · 448 Moonwalk · 307 Headspin · 827 Blade · 944 Wawo · 760 Toe Touch ·
1 Salsa Basic · 342 Fouetté sauté · 1668 Body Roll — all ✅ DONE.

### Batch 3 — transcript-inferred
434 Body Wave · 1670 Waist Whine · 267 Cuban Motion · 869 Windmill(Hurricane) · 244 Hip Twist ·
309 Arm Wave · 1677 Arm Wave(Steffanina) · 1697 Lasso · 454 Milly Rock · 331 Fouetté · 1679 Hardstyle Shuffle ·
403 Chicken · 663 Rond de Jambe · 1684 3 Beginner Moves · 1709 Tutting · 863 Helicopter · 1608 Pin Drop ·
384 Heel Toe · 1707 Tutting Combo · 256 Honey Dipper · 910 Gbe Body · 1702 Ska · 463 Waacking Pt4 ·
799 Bachata Footwork (38-min combo, 11 sections) — all ✅ DONE.

**Total this session: ~51 videos given section chips (72 videos now have segments, was 21).**

### Skipped (no usable signal — would need visual/multimodal)
- 1686 "10 Bachata Moves", 325 Bounce Back, 457 The Bop, 807 The Wave, 820 Airfreeze,
  385 Flicks, 1682 Heels Dance Basics, 1704 Meneo, 1684-area — music montages or no captions/chapters.
- 8mWyE6aBHio (617–621) multi-dance montage; h3DSYn2jIKE (358/433/464/916) broken fetch (dur 0).
- Sub-4-min single-move clips left as-is (one move, no sub-topics needed).

### Full-catalog expansion 2026-06-29 (beyond tutorial-titled)
Triaged ALL 304 distinct chip-less YouTube videos (`triage_meta.py` → `_proto/triage_meta.tsv`).
Of 95 single-dance videos with real content: **53 clean-chapter** (adopted via `clean_apply.py`,
which title-cases ALL-CAPS, renames Untitled→Intro, drops promo chapters), **5 descriptive-fragment
chapters**, **17 transcript-inferred** (incl. the 38-min "Jamaican Dance Moves" → 4 named moves, and
the 22-min salsa workout). **147 videos now have segments** (was 21).

Excluded (NOT chipped): 30 multi-dance montages (→ "In this video" chapters feature handles those);
11 long no-caption/no-chapter; wrong-domain mis-sourced (db1580 figure-skating, db1581 boxing jump-rope,
db1594 golf); music videos/performances (737 Pitbull, 913 K9, 689 JumpStyle, 792/1686/oj 25-move
bachata montages); garbled-caption (1710 Portuguese auto-translate); talk-show (316 Juju). Notation-/
Turkish-messy chapters (285/286/276/369) left. New helpers: `triage_meta.py`, `clean_apply.py`.

<!-- CHIP-QUEUE:START -->
## Auto-detected chip queue _(last checked 2026-06-29 02:02)_

No videos awaiting chips. ✅
<!-- CHIP-QUEUE:END -->
