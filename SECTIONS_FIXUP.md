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

### Re-source + short-clip pass 2026-06-29
**Re-sourced 3 wrong-domain videos** (the only ones catalog-wide — scanned cached YT titles): dance 1635
Forward Cross Over (was figure-skating → House cross-step `_HdLEWGpxEc`), 1650 Forward Hip Bump
(was golf → `CtC6GB5XOuk`), 1637 Heel-Toe… (was boxing → heel-toe `sFvnVk9UFv4`). All had zero user
data/segments. Detached bad video + attached correct tutorial (non-destructive). 2 chipped; cross-step
left unchipped (music-only captions). **NOTE: dance 1637 "Heel-Toe, Heel-Toe, Toe-Heel, Toe-Heel" is a
fabricated duplicate among ~10 heel-toe dances — flagged for user to delete/merge.**

**Short single-move clips** (167 total): 11 adopted 2-chapter, 58 heuristic "thin" chips via
`thin_chips.py` (Intro / Tutorial / [Practice with music] / [Outro] from spoken cues). Skipped 92 that
are <90s or no-caption, + 5 too-sparse/performance. **218 videos now have segments (was 21).**

### Full video QA audit 2026-06-29
Integrity clean: 727 videos, 0 null IDs, 0 dances w/o videos, 0 bad segment timings (start≥end /
end>duration), 0 dup ytid-per-dance. Deleted fabricated duplicate dance 1637 (no user data).
**Embeddability scan** (oembed on all 374 distinct YT ids, confirmed via `playable_in_embed`): found
**4 public-but-embedding-disabled** videos (broken in the on-site iframe player). `check_alive.py` added.
- Re-sourced 3 single-dance ones with embeddable equivalents: 822 Footwork→`9m5HftmTcJI` (chapters),
  848 Barrel Roll→`WOVOtEP9pcA` barrelmill (chips), 841 Bachata Body Wave→`30F5806xV4k` (garbled
  captions, left unchipped).
- `xWiAh_EizqI` (Authentic Jazz Vocabulary montage, 24 jazz dances, non-embeddable): per user, re-sourced
  EACH individually with an embeddable dedicated tutorial. **19/24 done** (verified `playable_in_embed=True`
  before attaching). **5 had no dedicated embeddable match — left on the montage: Cross Over, Skating,
  Groove Walk, Rond, Stomps** (still link-out; revisit if standalone tutorials surface). New re-sourced
  jazz videos not yet chipped (mostly short dedicated clips; daily detector will surface any worth chipping).

### Trending-styles expansion 2026-06-29 (new videos + chips)
Added **38 new dances** (37 YouTube + 1 TikTok) across thin + new styles, all embeddability-verified
(`playable_in_embed=True`) before attaching, then chipped. New **Styles**: Amapiano(28), Shuffle(29),
Litefeet(30); new **MusicalStyle**: Amapiano(16). Existing thin styles boosted: Afrobeats 6→13,
Dancehall 2→8, Jazz 8→12, Vogue 8→12, Contemporary 5→8, Flamenco 2→5, Tutting 2→3.

- **27/37 new YouTube videos chipped** (11 native-chapter adopt via `chapters_spec.py`, 16
  transcript-inferred) + Contraction added later = **28 chipped**. Scripts added: `trend_search.py`,
  `verify_picks.py`, `insert_picks.py` (state in `_proto/picks_verified.tsv`, `_proto/inserted.tsv`).
- New dances (dance/video): Gwara Gwara 1714/1746 · Azonto 1715/1747 · Legwork 1716/1748 ·
  Sekem 1717/1749 · Pilolo 1718/1750 · Dutty Wine 1719/1751 · Gully Creeper 1720/1752 ·
  Nuh Linga 1721/1753 · Willie Bounce 1722/1754 · Bogle 1723/1755 · Genna Bounce 1724/1756 ·
  Pas de Bourrée 1725/1757 · Fan Kick 1726/1758 · Chaîné Turns 1727/1759 · Pivot Step 1728/1760 ·
  Duckwalk 1729/1761 · Hand Performance 1730/1762 · Old Way Vogue 1731/1763 · Spin and Dip 1732/1764 ·
  Contraction 1733/1765 · Floor Roll 1734/1766 · Spiral 1735/1767 · Zapateado 1736/1768 ·
  Braceo 1737/1769 · Floreo 1738/1770 · King Tut 1739/1771 · Bacardi 1740/1772 · Pouncing Cat 1741/1773 ·
  Zekethe 1742/1774 · T-Step 1743/1775 · Charleston Shuffle 1744/1776 · Spongebob Shuffle 1745/1777 ·
  Cutting Shapes 1746/1778 · Chicken Noodle Soup 1747/1779 · Toe Wop 1748/1780 · Rev Up 1749/1781 ·
  John Vuli Gate 1750/1782.
- **Not chipped (9)**: 5 sub-80s single-move clips (Sekem, Genna Bounce, T-Step, Chicken Noodle Soup,
  John Vuli Gate); King Tut (video is a series *intro*, no move taught); Toe Wop / Old Way Vogue /
  Chaîné Turns (no captions AND no chapters). All match the find-chips SKIP rules.
- **TikTok (first 5 on the platform — chips N/A, clips too short)**: new dance "5 Easy Afrobeats Steps"
  1751/1783 (`7500003770143837442`); + secondary demo clips on Bacardi 1740 (`7506248734259334406`),
  Pouncing Cat 1741 (`7465787459515780357`), Azonto 1715 (`7367070554966232326`), Zekethe 1742
  (`7491712245194427650`). All fetched OK via yt-dlp.
- Dedup: pre-existing "Shaku Shaku" (929, Hip-hop) already held the same ytid — deleted my dup (1713),
  tagged 929 with Afrobeats instead. Contemporary "Spiral" kept distinct from the House "Spiral" (411).
- **Totals after: 746 dances / 769 videos / 1381 segments.** Verified live via `/api/videos/dance/<id>`.

### Trending-styles expansion — Round 2 (2026-06-29)
Added **26 more dances** (all YouTube, embeddability-verified) + **2 more TikToks**, plus new **Style K-Pop(31)**.
Same pipeline (`trend_search2.py`, `verify_picks2.py`, `insert_picks.py`). **19/26 chipped** (6 native-chapter
adopt, 13 transcript-inferred). New dances 1752–1777 / videos 1788–1813:
Mnike · Sbhujwa · Vrrr · Zenzele (Amapiano) · Running Man Shuffle · V-Step · Diamond Step · Hard Style (Shuffle) ·
Get Lite · Bad One (Litefeet) · Soapy · Kupe (Afrobeats) · Tek Weh Yuhself · Wacky Dip · Skip To Ma Lou ·
Row Di Boat (Dancehall) · Catwalk · Floor Performance (Vogue) · Jazz Pirouette (Jazz) · APT. Challenge ·
Magnetic (ILLIT) · Supernova (aespa) (K-Pop) · Floorwork · Tilt (Contemporary) · Marcaje · Vuelta (Flamenco).
- **Not chipped (7)**: Sbhujwa / Soapy / Row Di Boat / Floorwork / Marcaje (no captions+no chapters),
  Hard Style (captions too sparse), Skip To Ma Lou (105s single move). All match SKIP rules.
- **Dedup**: dropped Chassé / Harlem Shake / Pas de Chat (exist elsewhere); tagged existing Shoki(945)
  Afrobeats instead of duplicating. Swapped dead-end searches (TwaTwa/Mavusana/Tap In/Gwo Gwo Gwo) for
  Mnike/Zenzele/Vrrr.
- **TikTok**: APT. full tutorial + challenge clips added to dance 1771 (K-Pop now has TikTok too).
- **Cumulative after both rounds: 772 dances / 797 videos / 1533 segments / 7 TikToks.** Verified live.

### Trending-styles expansion — Round 3 (2026-06-29)
Added **18 more dances** (YouTube) + **4 more TikToks**, plus new **Styles Heels(32) & Reggaeton(33)**.
**14/18 chipped** (7 native-chapter, 7 transcript). New dances 1778–1795 / videos 1816–1833:
Heels Walk · Heels Floorwork · Heels Body Roll · Hair Flip (Heels) · Reggaeton Basic · Dembow ·
Reggaeton Hips (Reggaeton) · Whiplash (aespa) · Smart (LE SSERAFIM) · How Sweet (NewJeans) ·
Drip (BABYMONSTER) · Sticky (KISS OF LIFE) (K-Pop) · Heel Toe (Shuffle) · Tshwala Bam · Umlando (Amapiano) ·
Rush · Ginger (Afrobeats) · Pon Di River (Dancehall).
- **Not chipped (4)**: Heels Walk / Dembow / Reggaeton Hips / Ginger (no captions+no chapters).
- **Dedup**: dropped Cross Step (exists, Hip-hop); dropped dead-end searches Perreo/Zapateo/Phonk Shuffle/Out & Bad.
- **TikTok**: Heels choreo on Heels Floorwork(1779) & Heels Body Roll(1780); reggaeton perreo on
  Reggaeton Basic(1782) & Dembow(1783).
- **Cumulative after 3 rounds: 790 dances / 819 videos / 1634 segments / 11 TikToks / 6 new styles**
  (Amapiano, Shuffle, Litefeet, K-Pop, Heels, Reggaeton). Verified live.

### Trending-styles expansion — Round 4 (2026-06-29, double batch)
Added **35 dances** (YouTube) + **2 TikToks**, plus new **Styles Twerk(34) & Jersey Club(35)**.
**27/35 chipped** (11 native-chapter, 16 transcript). New dances 1796–1831 / videos 1838–1873 across:
Twerk (Basic Twerk, Twerk Bounce, Booty Pop) · Jersey Club (Bounce, Top Rock, Footwork) ·
K-Pop (Armageddon, Super Shy, Queencard, Love Dive, OMG → now 13) · Heels (Heels Spin, Knee Spin) ·
Reggaeton (Shoulders, Sandungueo) · Shuffle Spin · Litefeet (Swiss Drop, Hat Trick) · Amapiano (Sgija) ·
Afrobeats (Buga, Soso) · Dancehall (Summer Bounce, Gas) · Jazz (Switch Leap, Pique Turn) · Tap (Cramp Roll,
Shuffle Ball Change) · Vogue (Death Drop) · Flamenco (Llamada) · Contemporary Leap · Salsa Shines ·
Hip-hop (Nae Nae, Two Step, Whip, Stanky Legg).
- **Not chipped (8)**: Reggaeton Shoulders / Sandungueo / Death Drop / Two Step (no captions); Cramp Roll /
  Shuffle Ball Change (sparse captions); Sgija (challenge chant captions); Stanky Legg (garbled auto-translate).
- **Dedup**: Dougie & Time Step already existed → dropped; **Cat Daddy already existed in Hip-hop → deleted my
  dup (1828)** (insert_picks per-style slug gave it `cat-daddy-2`, the tell). Dropped dead-end searches
  (Gum Sole, Heels Hip Sway, Shuffle Slide, Pelo). Whip's first video (glIBSSiCM3Y) failed to fetch → swapped.
- **TikTok**: Jersey Club on dance 1799; twerk tutorial on dance 1796.
- **Cumulative after 4 rounds: 825 dances / 856 videos / 1811 segments / 13 TikToks / 8 new styles**
  (Amapiano, Shuffle, Litefeet, K-Pop, Heels, Reggaeton, Twerk, Jersey Club). Verified live.

### Trending-styles expansion — Round 5 (2026-06-29)
Added **32 dances** (YouTube) + **2 TikToks**, plus new **Styles Bachata(36), Soca(37), Brazilian Funk(38)**
(+ new MusicalStyles Bachata(17), Soca(18)). **27/32 chipped** (9 native-chapter, 18 transcript).
New dances 1832–1864 / videos 1876–1908 across: Bachata (Basic, Side Step, Turn, Dip) · Soca (Wine, Wave,
Bumper, Footwork) · Brazilian Funk (Passinho, Rebolation) · K-Pop (Spicy, Hype Boy, Ditto, Kitsch,
Antifragile → now 18) · Jersey Club (One Leg Get Back, KB Bounce, Sharp Bounce) · Heels (Strut, Chair Dance) ·
Twerk (Heel Twerk) · Amapiano (Ke Star, Phuze) · Afrobeats (Calm Down, Unavailable) · Tap (Buffalo, Wing) ·
Krump (Jab, Chest Pop) · Cumbia · Salsa Cross Body Lead · Attitude Turn.
- **Not chipped (5)**: Bachata Basic / Rebolation / Ke Star / Phuze / Sharp Bounce (no captions+no chapters).
- **Mis-source caught & removed**: "Beat Drop" (Brazilian Funk) — BOTH candidate videos were music-**production**
  tutorials (FL Studio/BPM), not dance (the "brazilian funk how-to" search is dominated by producers). Deleted
  the dance; Passinho + Rebolation cover the style. Lesson: verify the video actually teaches *dancing*.
- **Dedup**: Mambo / Shim Sham / Stomp / Suzie Q already existed → dropped. Bachata Body Wave already exists (841).
- **TikTok**: Bachata sensual on dance 1832; soca whine-up on dance 1835.
- **Cumulative after 5 rounds: 857 dances / 890 videos / 1987 segments / 15 TikToks / 11 new styles**
  (Amapiano, Shuffle, Litefeet, K-Pop, Heels, Reggaeton, Twerk, Jersey Club, Bachata, Soca, Brazilian Funk).
  Verified live.

### Trending-styles expansion — Round 6 (2026-06-30)
Added **22 dances** (YouTube), plus new **Styles Kizomba(39), Afro House(40), Gqom(41)** (+ MusicalStyles
Kizomba(19), Afro House(20), Gqom(21)). **18/22 chipped** (9 native-chapter, 9 transcript). New dances
1865–1886 / videos 1911–1932: Kizomba (Basic, Saida, Tarraxinha) · Afro House (Footwork, Bhenga) ·
Gqom (Vosho, Gqom Dance) · Breakdance (Toprock) · Street/Locking (Locking Basics, Wrist Rolls, Whichaway) ·
House (House Jack, Loft) · K-Pop (Pink Venom, Shut Down, Baddie, Boom Boom Bass → now 22) · Tap (Pullback) ·
Popping (Popping Basics, Waving) · Afrobeats (Network, Sare).
- **Not chipped (4)**: Gqom Dance / Loft / Popping Basics (no captions); Sare (dance-class, captions too sparse).
- **Dedup**: 6-Step, Baby Freeze, Cabbage Patch, Chair Freeze, Paddle Turn, Reject, Skate, Smurf, Wu-Tang
  already existed → dropped (catalog already deep in hip-hop/breakdance classics). Snake dropped (weak matches).
- No TikToks this round (YouTube-only).
- **Cumulative after 6 rounds: 879 dances / 912 videos / 2097 segments / 15 TikToks / 14 new styles.** Verified live.

### Trending-styles expansion — Round 7 (2026-06-30, STRETCHING focus)
User asked (with a Browse screenshot) to **focus on stretching** — the Stretching style (id **23**) had only **1 dance**.
Added **15 dances** (YouTube, all embeddability-verified), **all 15 chipped** (125 segments). Stretching now **16 dances**.
New dances 1887–1901 / videos 1933–1947: Front Splits · Middle Splits · Oversplits · Backbend · Bridge Pose ·
Back Flexibility · Hamstring Stretch · Hip Openers · Pancake Stretch · Needle Scale · Shoulder Mobility ·
Ankle & Foot Mobility · Dynamic Warm-Up · Cool-Down Stretch · Spine Mobility.
- **No music tag** on these (matches existing dance 1711) — used `insert_stretch.py` (skips DanceMusicalStyles,
  takes per-dance Difficulty). Repurposed the picks `music` column as **difficulty** (1 beg / 2 int / 3 adv).
- Chips: 7 native-chapter (clean), 2 condensed (Ankle 19→11, Cool-Down 27→13), 2 subdivided (Shoulder, Dynamic
  Warm-Up had too-few chapters), 4 transcript-only (Front Splits, Needle, Spine, Back Flexibility — its chapters
  were background-music track names, ignored). Per-dance segs 5–13.
- **Dedup**: avoided name collisions with existing Arabesque penchée(688), Parallel Quad Stretch(1455),
  Balance & Stretch(1323), The Ankle Bounce(701). Dropped redundant Splits Warm-Up / Active Flexibility /
  Contortion Basics (overlapped the splits/back entries). No new Style/MusicalStyle, no TikToks.
- **Cumulative after 7 rounds: 894 dances / 927 videos / 2222 segments / 15 TikToks / 14 new styles.** Verified live (API).

### Trending-styles expansion — Round 8 (2026-06-30, STRETCHING focus #2)
User said "More" → second stretching pass. Added **16 dances** (style 23), **all 16 chipped** (124 segments).
Stretching now **32 dances**. New dances 1932–1947 / videos 1978–1993: Deep Splits Stretch · Full Body Mobility
Flow · Hip Flexor Stretch · Frog Stretch · Pigeon Pose · Lizard Pose · Couch Stretch · Calf Stretch ·
IT Band & Glute Stretch · Lower Back Relief · Neck & Traps Release · Wrist & Forearm Mobility ·
Thoracic Rotation · Morning Mobility · Flexibility for High Kicks · Jefferson Curl.
- Chips: 11 native-chapter (clean), 5 transcript/subdivided (Lizard, IT Band, Morning = no chapters; Calf, Neck =
  too-few chapters). Per-dance segs 4–13.
- **⚠️ Tooling gotcha hit + fixed**: `cp picks_verifiedN.tsv picks_verified.tsv && python insert_*.py` read a
  **stale** picks_verified.tsv (sync-lag on the OneDrive-backed repo path) — re-inserted Round 7 twice as
  `-slug-2` dupes (dances 1902–1916, then 1917–1931). Both batches deleted before chipping (no user data; no
  `UserDances` table exists). Fix: `insert_stretch8.py` **inlines the picks** (no external TSV read). Use the
  inline pattern, not the cp-then-read pattern, on this machine.
- No new Style/MusicalStyle, no TikToks. Dedup clean (existing Frog Pose/Neck Roll/Wrist Rolls are different moves).
- **Cumulative after 8 rounds: 910 dances / 943 videos / 2346 segments / 15 TikToks / 14 new styles.** Verified live (API).

### Trending-styles expansion — Round 9 (2026-06-30, STRETCHING focus #3)
User said "Continue and more" → third stretching pass. Added **14 dances** (style 23), **12/14 chipped** (105 segments).
Stretching now **46 dances**. New dances 1948–1961 / videos 1994–2007: Ballet Flexibility Workout · Bedtime
Stretch · Cobra Stretch · Camel Pose · Wheel Pose · Inner Thigh Stretch · Deep Squat Mobility · Chest Opener ·
Leg Extension Hold · Hip CARs · Daily Full Body Stretch · PNF Stretching · Cossack Squat · Resistance Band Stretch.
- Chips: 9 native-chapter (Chest Opener 16→12, Camel 12→7 condensed), 3 transcript (Leg Extension Hold, Hip CARs,
  Daily Full Body Stretch). Per-dance segs 3–14.
- **Not chipped (2)**: Bedtime Stretch (no captions, no chapters) · Resistance Band Stretch (no chapters, captions
  too sparse — "no talking" music video).
- Used `insert_stretch9.py` (**inlined picks**, no TSV read — the fix for the round-8 stale-file dupe bug; clean this time).
- Dedup-checked names vs full table (avoided existing Butterfly/Developpé/Handstand/Camel Walk — used distinct
  names Butterfly→Inner Thigh, Leg Extension Hold, Camel Pose). Dropped Standing Splits / Side Body (only weak
  or core-workout matches). No new Style/MusicalStyle, no TikToks.
- **Cumulative after 9 rounds: 924 dances / 957 videos / 2451 segments / 15 TikToks / 14 new styles.** Verified live (API). No `-N` dupe slugs.

### Trending-styles expansion — Round 10 (2026-06-30, GENERAL broad ~3x batch)
User: "Even more random videos... find general videos as well. Also 3x more." Pivoted off stretching to a broad
cross-style batch. **44 new dances + 49 videos** (dances 1962–2010), **33/49 chipped** (~237 segments). Spanned
**15 styles**: Folk/World (12: Belly Dance Hip Drop/Shimmy/Figure 8/Snake Arms, Dabke, Tahitian Otea, Capoeira
Ginga, Tinikling, Kathak Spins, Irish Jig, Hula, Country Two-Step), Tap (5: Tap Wings, Shuffle Off to Buffalo,
Shim Sham, Maxie Ford, Paddle and Roll), Contemporary (4: Floor Work, Lyrical, Tilt Jump, Floor Rolls), Ballroom
(Viennese Waltz, Waltz Natural Turn, Tango Promenade), Swing (Lindy Hop Swingout, Balboa, Hustle), Latin (Gancho,
Samba Whisk, Bolero), + Heels, Afrobeats (Ndombolo, Coupe-Decale), Bhangra (Bollywood, Garba), Dancehall (Gallis,
Wine), Bachata (Sensual, Footwork), Kizomba (Virgula), Reggaeton (Perreo), Jazz (Jazz Funk), Flamenco (Sevillanas).
- **Used `insert_general10.py`** (inlined picks, WITH music tag + per-dance difficulty — general dances need music).
- **Heavy dedup**: 34 of original 53 candidates already existed (catalog deep in ballroom/Latin/swing/tap/K-pop/
  recent-K-pop) → replaced with niche/world picks. Garba re-sourced (first pick had embedding disabled).
- **5 same-style dupes slipped past dedup** (West Coast Swing, Salsa Shines, Bachata Dip, Pas de Bourree, Stag Leap
  — got `-2` slugs). Instead of deleting, **re-parented each new video onto the existing same-named dance** as a
  2nd instructor take (soft-dupes are a feature per user), then deleted the 5 empty dupe dances.
- Not chipped (16): short single-move clips (<~3.5 min) or no captions/chapters (Jazz Funk, Reggaeton Perreo,
  Heels Choreography, Tilt Jump, Salsa Shines, etc.).
- **Cumulative after 10 rounds: 968 dances / 1006 videos / 2688 segments / 15 TikToks / 14 new styles.** Verified live (API). Videos crossed 1000.

### Trending-styles expansion — Round 11 (2026-06-30, GENERAL broad #2, world/folk)
User: "Find more." **39 new dances + 40 videos** (dances 2011–2050), **30/40 chipped** (~203 segments). Heavy on
world/folk: Haka, Sirtaki, Tarantella, Kalbeliya, Mexican Folklorico, Jarabe Tapatio, Adowa, Kpanlogo, Soukous,
Kuduro, Bharatanatyam Adavu, Highland Fling, Clogging, Hopak; + Latin (Salsa Enchufla/Setenta/Cuban Dile Que No,
Tango Boleo/Sacada/Corte, Milonga, Cha Cha New York, Rumba Walks, Samba Voltas), Ballroom (Foxtrot Feather,
Quickstep Lock Step, Jive Kicks), Swing (Jitterbug, Collegiate Shag, Boogie Woogie), Tap (Riff, Flaps, Scuff),
Ballet (Grand Jete), Vogue (Spins and Dips), Soca (Chipping), Bhangra (Dandiya Raas), Belly (Undulation, Maya).
- `insert_general11.py` (inline picks). 17 dedup collisions dropped up front; 4 picks re-sourced (3 videos went
  "not available" between search and verify, 1 embedding-disabled) — **always re-verify right before insert**.
- 1 same-style dupe (Bachata Turn) re-parented onto existing dance 1834 as 2nd take; dupe row deleted.
- Not chipped (10): no-caption "no talking" videos or sub-~3.5 min single-move clips (Sirtaki, Tarantella, Jarabe,
  Dandiya Raas, Adowa, Kpanlogo, Kuduro, Salsa Enchufla, Boogie Woogie, Hopak).
- **Cumulative after 11 rounds: 1007 dances / 1046 videos / 2891 segments / 15 TikToks / 14 new styles.** Verified live (API). Dances crossed 1000.

<!-- CHIP-QUEUE:START -->
## Auto-detected chip queue _(last checked 2026-06-29 11:51)_

No videos awaiting chips. ✅
<!-- CHIP-QUEUE:END -->
