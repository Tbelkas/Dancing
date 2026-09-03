# Section Chips — transcript-inferred VideoSegments for tutorials

Goal: for full-tutorial videos with no `VideoSegments`, transcribe the video and add
topical section chips (label + start/end) so the "Sections" bar renders on the dance page.

## Workflow
1. `python scripts/prep_sections.py <ytid>` → caches metadata + auto-captions, writes `_proto/sec_<ytid>.txt`
   (title, duration, native chapters, condensed timestamped transcript).
2. Read the transcript, infer 4–10 meaningful topical sections (drop pure filler).
   Skip videos under ~3 min or with no real sub-topics.
3. `python scripts/apply_sections.py <videoDbId> "Label@start-end;..." apply` → inserts segments,
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
| 2111 | 1fGERdWc_6Q | Go Down | ✅ DONE | 8 | native chapters (5 beginner go downs) |
| 2113 | MTMcRWMsvW8 | The Whack | ✅ DONE | 8 | transcript (VersaStyle waacking) |
| 2114 | XXI5YCKAbMA | Overheads | ✅ DONE | 10 | transcript (VersaStyle waacking) |
| 319 | hyxUBMVd0_Y | Waacking | ⏭️ SKIP | – | 40s K-pop clip, no spoken breakdown |
| 2110 | i6TzP2COtow | Balance & Stretch | ⏭️ SKIP | – | 15-min stretch to music, lyrics-only captions |
| 2116 | LRdc1wxBYTY | Punking | ✅ DONE | 10 | transcript (VersaStyle, history + character + music drill) |
| 2115 | z1KObpZM6Lk | Overheads | ⏭️ SKIP | – | 4:44, 0 captions + 0 chapters |
| 2117 | 5AQ2TxY1Tt4 | Waacking Hand Positions | ⏭️ SKIP | – | 1:50 single topic, no text signal |
| 2118 | wfet71YbQi8 | Waacking Warm-Up | ⏭️ SKIP | – | 2:49, no text signal |
| 2119 | fPVgWK6P1ss | Waacking Warm-Up | ⏭️ SKIP | – | 3:59, no text signal |
| 2120 | kpTDmW44lBQ | Waacking Lines | ✅ DONE | 6 | transcript (2:39 but real sub-topics: path, force, wall, music) |
| 2121 | lTZm0GVg6as | Waacking Lines | ✅ DONE | 11 | transcript (Rachel, lines & twirls) — replaced 8 pipeline chips |
| 2122 | ndAZQ4VBV2k | Arm Rolls | ⏭️ SKIP | – | 4:35, 0 captions + 0 chapters |
| 2124 | 1FEOjMPhxLE | Waacking Arm Drills | ⏭️ SKIP | – | 6:09, captions are song lyrics only; pipeline logged no-candidates |
| 2125 | jWq5B8Z3ig4 | Waacking Arm Drills | ✅ DONE | 11 | transcript (basics drills) — replaced 12 pipeline chips |
| 2126 | R8YMW9ypfJI | Show the Music | ✅ DONE | 7 | transcript (Bagsy #1) — conductor's form + hand vocabulary |
| 2134 | kRU9wl7926Q | The Butterfly | ✅ DONE | 11 | transcript (Bagsy #11) — bolos, butterfly, single/alternating |
| 2135 | QK-MSyX4Lns | Three-Point Waack Attack | ✅ DONE | 7 | native chapters (no captions) — adopted, Untitled→Intro |
| 2136 | cTOEgW6NKQw | Waacking Gestures | ✅ DONE | 10 | transcript (Rachel) — the flick, directions, rhythms |
| 2138 | l3PfYPUt_bQ | Waacking Poses | ✅ DONE | 9 | transcript (Versa Style) — R/L/front poses, character, face |
| 2139 | IAEV8KrZ4hY | The Hit | ⏭️ SKIP | – | 1:49 talking-head intro, no discrete moves taught |
| 2140 | ycPeDQUKjq4 | The Hit | ✅ DONE | 11 | transcript (ABM/Dementia) — tutting routine, 8-count breakdowns |
| 2141 | BVLh5Xiuioo | Right Angles | ⏭️ SKIP | – | 3:18, 2min silent freestyle demo + course promo |
| 2142 | wJdGN1gviko | Tutting Stretches | ⏭️ SKIP | – | 2:23 request video, one tip (bent wrists) |
| 2143 | nXnfZ0WjvOg | Tutting Stretches | ⏭️ SKIP | – | 0:54, two wrist stretches only |
| 2144 | iEcQPvvrfNM | Tutting Stretches | ✅ DONE | 11 | transcript (TuTCeption) — 6 hand stretches + native shoutout chapters |
| 2145 | dz3axgdqaIA | Tutting Stretches | ✅ DONE | 5 | transcript — 3 levels of wrist/knuckle stretches |
| 2146 | wegRpQ-V4fM | Wrist Rolls | ⏭️ SKIP | – | 1:14 "1 minute tutorial", one move, no sub-topics |
| 2147 | B0pQQysjOZA | Fixed Points | ✅ DONE | 7 | transcript (TUTdemic) — theory: points recap, orbiting, 3D, recovery |
| 2148 | vOzWGnvtyVk | Fixed Points | ✅ DONE | 4 | native chapters (RYOGA/XTRAP, JP, no captions) — English halves kept |

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

### Full video-quality audit + cleanup (2026-06-30)
User: "go through all stored videos, find low-quality ones (really short, bad/no chips, not in correct place)."
Audited all 1,046 videos (698 distinct YT ids) via `audit_videos.py` / `fetch_durations.py` / `check_alive.py`.
Findings + fixes (all defect targets had **zero user data**):
- **Embeddability clean** — only known `xWiAh_EizqI` jazz montage remains. Big vocabulary montages
  (jAIwJd2tQo0 etc.) correctly per-move sliced via `StartTime` — not defects.
- **8 duplicate dances deleted** (round 10–11 dupes that got the identical video as an older dance):
  Heels Hair Flip, Floor Rolls, Vogue Spins and Dips, Tap Wings, Locking Basics, Salsa Cross Body Lead,
  Krump-"Attitude", Jazz-"Heels Basics". Cross-Body Lead's 6 chips copied onto the kept dance first.
- **1 duplicate video ROW deleted** (Pas de Bourrée d1725 had `d5-TKHTOTdU` twice).
- **4 re-sourced** to verified-embeddable tutorials: Knee Slide d446, The Slide d477, House "Spiral"
  d411 (was a Contemporary clip), Backward Shuffle d1639. Scripts `resource_search.py`/`resource_apply.py`.
- **2 fabricated montage-artifact dances deleted** (Lift-Off, Small Thing — generic kids routine, not real moves).
- **Chipped 14 long (≥4 min) no-chip tutorials** (`batch_prep.py` triage → 20 chippable / 55 no-signal):
  8 chapter-adopt (En pointe 10, Half Break, Tap Steps in Place, Fishtail, Knee Slide, Tango Backward
  Walk, Free Style Salsa, Dancer's Stretching Routine 11) + 6 transcript-inferred (Cultural Dance/African
  clock, Lock Turn, Dembow, Tahitian Otea, Capoeira Ginga, Hula Basics). Skipped Heels Walk (1 giant
  chapter), Stag Leap (anatomy chapters), Loko Loko/Bachata Dip/Bachata Body Wave/Juju (garbled/lyrics/talk).
- 50 no-signal videos appended to `_proto/chip_skip.tsv`.
- **Totals after: 997 dances / 1035 videos / 2924 segments / 15 TikToks / 461 videos chipped.** Verified live.

### Tutting sweep + catalog 0-seg pass 2026-06-30
- Tutting (#1710) already well covered (vids 1706/1707/1708/1709 chipped 3–8); the 3 remaining
  tutting tutorials (h98tavLjL8o garbled PT captions, YMrANzoXy-c 0:25, qhc_VouKj4g 0:54/no-caps)
  were already in `chip_skip.tsv` — confirmed still correct.
- Broadened to all 30 tutorial-type 0-seg videos not yet skipped → triaged via `prep_sections`.
- **Chipped 7 transcript-inferred** (4–6 sections each, verified live via API):
  Backward Shuffle d1639 (v1583), Argentine Tango Gancho d1963 (v2009), Balboa Basic d1965 (v2011),
  Shuffle Off to Buffalo d1969 (v2015), Tarantella d2013 (v2059), Jarabe Tapatio d2016 (v2062),
  Salsa Enchufla d2023 (v2069).
- **3 skipped** (no usable section structure): King Tut v1771 (program promo intro, no move),
  Skip To Ma Lou v1802 (garbled lyric captions), Sgija v1856 (hype-callout challenge).
- **16 no-caption + 4 TikTok-fetch-fail rows appended to `_proto/chip_skip.tsv`** (no text signal;
  flagged "needs multimodal" for a future watch-the-video pass).

### 10x catalog sweep + multimodal pass 2026-07-01
Goal: maximize chips across as many dance categories as possible.
- **Widened scope to ALL 0-seg full videos (both `tutorial` + `steps` types)** — 217 total, 104 not-yet-skipped,
  93 fetchable. Batch-triaged via `prep_sections` (`_proto/_cand3_triage.tsv`). Most `steps` rows are genuine
  sub-90s single-move clips → correct to skip.
- **Chipped 5 from captions/chapters**: Waltz Jump v369 (chapters), Quickstep v276 (chapters),
  6-Step v818, Side-to-Side/Charleston v1573, Popping Basics v1929 (en auto-sub pulled via yt-dlp).
- **`p2JrE6JICKk` = 31-chapter shuffle-moves compilation wrongly attached to 6 unrelated dances**
  (Scrape/Ankle Bounce/Pocket Drop/Knee Slide Sway/Fwd Knee Slide/Fwd Shuffle) → wrong-video, fix-videos
  territory, not chipped.
- **Multimodal contact-sheet pipeline** (yt-dlp low-res dl → `ffmpeg fps=1/12,scale,tile=5x4` → read one
  tiled PNG/video). Verdict: works great ONLY when the video burns on-screen move labels.
  - **Chipped 1**: Old Way Vogue v1763 (10 segs) — richly text-labeled arm-drills tutorial.
  - **9 skipped after eyeballing** (continuous performance/class footage, no labels): Kuduro, Sbhujwa,
    Toe Wop, Soapy, Row Di Boat, Gqom, Dancehall Gallis, Sirtaki, Loft(403). Notes updated in `chip_skip.tsv`.
- **This session total: 6 videos chipped** (13 across the conversation). Removed 2 now-chipped rows from skip.
- **Totals after: 1036 videos / 475 chipped / 2996 segments.** Verified live via API.

### Queue run 2026-07-13 (multimodal)
- **2026 / 3gBbvQ_mgjw "Heels Choreography" (d1980) ✅ DONE — 8 segments via contact-sheet read.**
  No captions + no chapters, but the video burns on-screen move labels (the chippable multimodal case):
  Intro / The Walk / Hip Slide / Hip Deep Slide / Hair Whip (on-screen typo "Hair Wripe") /
  Go Down + Switch / Combo / Outro. Verified live via API.
- Removed stale `chip_skip.tsv` row `1682 3gBbvQ_mgjw` — that Video row no longer exists in the DB
  (same ytid, now only on video 2026, which is chipped).

<!-- CHIP-QUEUE:START -->
## Auto-detected chip queue _(last checked 2026-08-31 12:11)_

450 tutorial video(s) awaiting section chips (0 new since last check):

| VideoDbId | YtId | Dance |
|---|---|---|
| 2144 | iEcQPvvrfNM | Tutting Stretches |
| 2145 | dz3axgdqaIA | Tutting Stretches |
| 2146 | wegRpQ-V4fM | Wrist Rolls |
| 2147 | B0pQQysjOZA | Fixed Points |
| 2148 | vOzWGnvtyVk | Fixed Points |
| 2149 | QISey0UTy7c | Four Body Points |
| 2150 | _IjKj2kteSY | The Four Square |
| 2151 | rX_Unv9M0HA | The Four Square |
| 2152 | OO3Z0ILaONA | The Four Square |
| 2153 | bqGEzcFYpJw | The Grid |
| 2154 | yDIL5pNT3KQ | Box Tuts |
| 2155 | c47gWAwQtgY | Box Tuts |
| 2156 | lnK2pKtyBG0 | Squaring the Boxes |
| 2157 | 3WThD9uy4AY | The Magic Box |
| 2158 | 5Zk9zvEt02U | Advanced Four Square |
| 2159 | fk7mA7BgnLU | Tutting Transitions |
| 2160 | r_7zXbpBf2U | Tracing |
| 2161 | l85Mc7hALw4 | Tracing |
| 2162 | s62WZrPeLV4 | Tracing |
| 2163 | A4viOzllZNM | Isolation Points |
| 2164 | A4viOzllZNM | Hinges |
| 2165 | bb-ohIks-hM | Hinges |
| 2166 | -tsf1UzJKLw | Folds and Unfolds |
| 2167 | 2UkfqGko9tw | Folds and Unfolds |
| 2168 | 2UkfqGko9tw | Crumbling |
| 2169 | XZR8h_0rUR8 | 3D Space |
| 2170 | 751f7MqhXB4 | 3D Space |
| 2171 | wSn9tUNCv4Y | Back Tuts |
| 2172 | h8BPawC_iXk | Floor Tuts |
| 2173 | FiT3L6q5gr8 | Tutting Patterns |
| 2174 | NTpbV--zJYU | Tutting Combo |
| 2175 | 5QkCBJ1GJtc | Tutting Combo |
| 2176 | WTS1f1zcf2A | Tutting Musicality |
| 2177 | lQgGOEcs6Is | Tutting Musicality |
| 2178 | _WEYSsmAg6A | Freestyle Tutting |
| 2179 | SJpdilUrnG0 | Freestyle Tutting |
| 2180 | onJahzd74_E | Freestyle Tutting |
| 2181 | 5FX5H72B71k | Finger Tuts |
| 2182 | 5FX5H72B71k | Digits |
| 2183 | y2H95jnZf0Y | Digits |
| 2184 | NIKS_Mop1lw | Digits |
| 2185 | 5FX5H72B71k | Monstas |
| 2186 | esysjy9XKn8 | Finger Stacking |
| 2187 | 8vpUHRvPn5w | Tunneling |
| 2188 | fP-ERh8RXFo | Finger Tutting Combo |
| 2189 | JWZY0ZBL8Sw | King Tut |
| 2190 | 2gxZfHRvJ5w | Finger Tutting |
| 2191 | n1YsuRczyyU | Finger Tutting |
| 2192 | f8MtG1ErtwY | Finger Tutting |
| 2193 | c2uAf7aLX24 | What Vogue Is |
| 2194 | XJ6fqQX_e9U | What Vogue Is |
| 2195 | vt9AwsS0_6A | What Vogue Is |
| 2196 | zjfzvo-zRPo | Ballroom Herstory |
| 2197 | vbaCmDvrFxw | Ballroom Herstory |
| 2198 | cL5uGHqhnYw | Ballroom Herstory |
| 2199 | cL5uGHqhnYw | Houses and Balls |
| 2200 | 8ej86oHMJ8o | Houses and Balls |
| 2201 | QS5j7PCSdtg | Houses and Balls |
| 2202 | cL5uGHqhnYw | Ballroom Categories |
| 2203 | cL5uGHqhnYw | Realness |
| 2204 | fBCgb7A466o | Runway |
| 2205 | h2U3i30ZCf4 | Vogue Arm Lines |
| 2206 | wnSMHrmYqVs | Vogue Poses |
| 2207 | y3Uk_ZxiLV0 | Vogue Musicality |
| 2208 | iVmvapZhoJg | Pop, Dip and Spin |
| 2209 | eBCs9n0p93E | Old Way Switches |
| 2210 | eBCs9n0p93E | Pose to the Beat |
| 2211 | eBCs9n0p93E | Old Way Slides |
| 2212 | J39Drfl1dM8 | New Way Vogue |
| 2213 | JqnXibZ8QKM | Arms Control |
| 2214 | gbtpL86VLHE | Arms Control |
| 2215 | zYsz9s8Pv3k | New Way Lines |
| 2216 | zYsz9s8Pv3k | New Way Boxes |
| 2217 | vySNZKVK2xY | Vogue Fem |
| 2218 | VDMFYe7UOtQ | Vogue Fem |
| 2219 | D-s3gsiKpDM | Vogue Fem Dramatics |
| 2220 | kAx5xUA_PEo | Vogue Fem Dramatics |
| 2221 | tqUEcEsA3gQ | Fan Kick |
| 2222 | tqUEcEsA3gQ | Leg Circles |
| 2223 | tqUEcEsA3gQ | Knee Moves |
| 2224 | dLWhfvs-t-k | Catwalk |
| 2225 | ZJzwq0Aj_V0 | Duckwalk |
| 2226 | qzdXauUVYoI | Duckwalk |
| 2227 | 1E3xsNHT-Hc | Floor Performance |
| 2228 | Mp5LFK_BYNI | Hand Performance |
| 2229 | ln8msNBsWk0 | Hand Performance |
| 2230 | LwpLdzz0muI | Spin and Dip |
| 2231 | U_R3mOnIVLg | Old Way Vogue |
| 2233 | DcNz6mbir93 | Waacking Arm Drills |
| 2244 | hPe9tlc7_gY | Jab Jab |
| 2247 | RGw3I466nkE | Windmill |
| 2248 | Y9zWV-Slz6I | Drop it Low |
| 2249 | 09ibzsU5fRY | Tap Dance Basics |
| 2250 | vS0uuoIVoXg | Flicks |
| 2251 | JJ6-j4bf2v0 | Stanky Leg |
| 2252 | Baaw5SSoQsU | Slide Step |
| 2253 | 5rRGW71L1kE | Cross Step |
| 2254 | SarxqLwK_u0 | Charleston Variation |
| 2255 | l5Xbkogz5xk | T-Step Reverse |
| 2256 | hm6GIUrGpbM | Spongebob Shuffle Hop |
| 2257 | bsVUsSnbGqE | Charleston & Running Man |
| 2258 | b6075roLFmo | Running Man & T-Step |
| 2259 | mQqUaORggzw | Pin Drop |
| 2260 | tnNNxRr-0Tw | Garba |
| 2261 | c7zLOz75g1Y | Box Step |
| 2262 | k70uyYKlIU0 | Plié |
| 2274 | FltxXCoxJ0A | Stick and Roll |
| 2275 | 5lRJ51DnGMI | Kick It |
| 2276 | ry3zVZm2GQo | Elbows Up |
| 2277 | M4bMFdLH3FU | Drop Dance |
| 2278 | 611BmoPoo8s | Creep |
| 2279 | sW9wqxX6wd4 | Monastery |
| 2280 | EXh42q4jDBc | Kick Step / Kick Ball Change |
| 2281 | bOaG7SylhQ0 | Row Di Boat |
| 2282 | oPKfdtRctp8 | Locking |
| 2283 | N4STZCPuhf0 | Reebok Hop / Cabbage Patch |
| 2284 | MRjzecRlVGc | Running Man & Kick |
| 2285 | ZgWJoLAP73o | The Moonwalk |
| 2286 | Zh_z7cZxY10 | Juju Step |
| 2287 | GIuiGVYr7ho | Hip Openers |
| 2288 | yYgVl5Dsf4o | The Bop |
| 2289 | sFvnVk9UFv4 | Heel Toe |
| 2290 | UVKooAlER20 | Cupid Shuffle |
| 2296 | pJYwmLxTHFE | The Dab |
| 2300 | fo1XNw1LG-o | Heel Toe Snake |
| 2302 | ApIVO-1kVzY | The Robot |
| 2304 | brdrobXPFq0 | Hopak |
| 2305 | crUWEBFBrSQ | Waist Whine |
| 2306 | _TlYM3k9EOk | Fouetté |
| 2307 | 6fkq5MBLD0M | Spongebob Shuffle |
| 2308 | CqZRVCi6_34 | The Side-To-Side Rock Step |
| 2309 | ExEXc5kCuG0 | Shut Down |
| 2310 | HYxQMbsmPaw | Dabke |
| 2312 | Qj2TevFCLkw | Middle Splits |
| 2313 | KZvPapgwWzw | Love Dive (IVE) |
| 2314 | id-Bvcc6YbQ | Haka |
| 2315 | VImXG8A0snw | Hip Swivel |
| 2316 | 6Pk9L6lAP70 | Gucci / Reebok |
| 2317 | bEp2oBM47C0 | Typewriter |
| 2320 | PLAWTUKO2Vk | Carlton |
| 2329 | _c4WdMKPIoA | Running Man Reverse |
| 2330 | oCrGcuaJ6OE | Happy Feet Combo |
| 2331 | K3IfCgFJ85I | Heel Toe Hop |
| 2332 | HDdB71xNeqw | Criss Cross Variation |
| 2333 | VDBkB5Ouxig | Running Man & Stepback |
| 2334 | 3Yp2_zyCD7Q | Running Man Heel |
| 2335 | A5AtD6MrSCU | Chest Pop with Rotation |
| 2336 | 06TJG76UR8k | Lock It Down (Variation) |
| 2337 | WGrIM2bjJIk | Grapevines |
| 2338 | M-Ej1XFLIYg | Ke Star |
| 2339 | c_WI6ySxeb8 | Quick-Quick-Slow |
| 2340 | l-agmlAGtEM | Arabesque |
| 2341 | S_kb4RpZJIA | 20s Charleston |
| 2342 | _O62qLcMWcw | Vaina Loca |
| 2343 | qXByhRSdeYE | Bharatanatyam Adavu |
| 2344 | FTgPGsxEjVI | Bourrée |
| 2347 | NtBqKGXtZSg | Toe Taps |
| 2356 | HyS6uKrS0mw | Millie Rock |
| 2357 | _mF5s-JjJ8Q | Forward Knee Slide |
| 2358 | sFpcX-MCcEY | La Gozadera |
| 2359 | rEmjtWZM-UA | Pirouette |
| 2360 | DRwsTajIULI | Do the Wop |
| 2361 | S9Umewra2ro | Shake Your Hips |
| 2362 | hQbHbmyspQs | Diagonal Running Man & Flick |
| 2363 | Y3Wzzjs9ih8 | Pa' Lante |
| 2364 | cacwri2wio4 | Morning Mobility |
| 2365 | OS6MhBfs800 | Bedtime Stretch |
| 2366 | mhQDOPyxX8g | The Watusi |
| 2367 | 35Z6hZgL2r0 | Lower Back Relief |
| 2368 | 4gISxG1NNnI | Dancer's Full Body Stretch |
| 2369 | apCIhoPmHW8 | Ankle & Foot Mobility |
| 2370 | iRkGYffEnm0 | Slow-Slow-Quick Sequence |
| 2371 | 3bt5h0dX6nA | Tendu & Shaping Feet |
| 2377 | S2AJ3tAAjyc | Criss Cross Hop & Tap |
| 2382 | hH2MZYPcLpA | The Arm Wave Wide |
| 2383 | qujbNH7Nmek | Mashed Potato |
| 2384 | 2jOtqCJn9mI | Fan Motion |
| 2385 | ES2JEkTKarc | Walking Breakdown |
| 2386 | WIHJHqL77i4 | Dance Floor Bump |
| 2387 | h3DSYn2jIKE | Honey Dipper |
| 2388 | CX9LTfMF6NE | The Head Banger |
| 2389 | pkpvM2AfvTc | Monstas |
| 2390 | PD9QPJATvRk | 6-Step |
| 2391 | i4umf_rsJKQ | En avant et en arrière |
| 2392 | KN32mxI985I | 1-2-3-4-5-6 |
| 2393 | pddp8OLi7lo | T-Step Angle |
| 2394 | nbYCfzIdUes | The Knee Slide Sway |
| 2395 | EdN8S2phxbs | T-Step Heel Toe |
| 2396 | a85IOUtNQxs | Heel Toe & Toe Twist |
| 2397 | xOWLBQo_5Lo | Dance Like Me |
| 2401 | VEE5qqDPVGY | Real Love |
| 2407 | 0UoK0My9Dx0 | Heels Choreography |
| 2408 | JWkGdRBX6dI | Promenade |
| 2409 | pSXDkPHx1_w | Tango |
| 2410 | pAylQRh63A4 | Tecktonik |
| 2411 | fubRuAc1V4E | Chest Pop |
| 2412 | 1xd5IjpNMK0 | Time Step |
| 2413 | ayDxW68d-VQ | Double Time Step |
| 2414 | G9vPQLD4W1M | Triple Time Step |
| 2415 | gGCr0WjmT9E | Drop Top Rock |
| 2416 | pY2tNHe1XdE | Magnetic (ILLIT) |
| 2417 | uTaNkOzg9qE | Calm Down |
| 2418 | xYD62Z0rC7w | Hype Boy (NewJeans) |
| 2419 | 1BP64ShcOQo | OMG (NewJeans) |
| 2420 | _MBmXKwlOB8 | Drip (BABYMONSTER) |
| 2421 | skccFBdK_ZA | Ditto (NewJeans) |
| 2422 | 8xDMKFvZHGY | Cross-Body Lead |
| 2423 | g3lN2tiNZfY | Smart (LE SSERAFIM) |
| 2429 | 9uFWjzalOqY | Vosho |
| 2434 | 11AFA96QYq4 | Clogging |
| 2435 | pc_0KVtRgt0 | Swing Flips & Lifts |
| 2436 | RKtjX3xa6dk | Needle Scale |
| 2437 | WNSM6Wzg_mQ | Forward Bicep Bounce |
| 2438 | Ry9PcMonkSg | Hardstyle Shuffle |
| 2439 | pEEET2SIKEs | Dancer's Hips & Arabesque Stretch |
| 2440 | Ulnw1WRubX0 | Deep Splits Stretch |
| 2441 | 1vcvdSxl32I | The Hand Jive |
| 2442 | oFgER9x40ww | Light Jig Step |
| 2443 | wwDCOPfl6QM | La Cucaracha |
| 2444 | c4TGKk8mjMY | Queencard (G-IDLE) |
| 2445 | 3NomZw-KD34 | Bollywood Basics |
| 2446 | PSYI1cb8PV8 | Popping Basics |
| 2447 | 3C4wEZ6fEuU | Kokomma |
| 2448 | HjOd-2g508k | Chassé Turns |
| 2449 | YyLh9N6whwQ | Butterfly |
| 2460 | y4aumyQiD_Y | Pas de Cheval |
| 2461 | bBEsrMQo-8E | Frappé |
| 2462 | CgKXn1Evj-o | Grand Battement |
| 2463 | 2j-L3c4hLz8 | Fondu |
| 2464 | vfXeKrl3F7Q | The Get Down |
| 2465 | ApJoU1Jbrkw | Reebok |
| 2466 | FQBUM-cmM7A | Pop and Lock |
| 2467 | WcxRnK4-r1s | Flap |
| 2468 | d1ZgFiq0psY | Boogie Woogie |
| 2469 | 4S2aouJNw4U | Pony |
| 2470 | nR393C6ZBos | Floorwork |
| 2471 | GOi5mI8PXC0 | Tinikling |
| 2472 | Vad0PPt_GOU | Tap Steps in Place |
| 2473 | m1t3ZyD3uH4 | Waltz Natural Turn |
| 2474 | DJO_0o8nQ40 | Triple Step |
| 2475 | xDSpFBwKvMI | The Shake |
| 2478 | gBosbQE6fJA | Pancake Stretch |
| 2482 | Dw7ciI4zGxM | Arabesque penchée |
| 2485 | yfw_CtVSIFg | Bourrée Turns |
| 2486 | mesIwHRX17Q | Argentine Tango Gancho |
| 2487 | E3Ytb1X9Ukk | Soukous |
| 2488 | mpxJubVNBQA | Scrape |
| 2489 | eWih4IFM9cY | Hurricane |
| 2490 | am5RH1WxHEc | Swingout |
| 2491 | b1RDLjz18FM | Adagio |
| 2492 | U8DIVLMy8Ko | Rebolation |
| 2493 | I3aP1J-xH7c | Pliés |
| 2494 | -NAgnPSnuVQ | Glissade |
| 2495 | gvbV-Cy7V_k | Jitterbug |
| 2496 | dS-yMrWBHXI | Battement |
| 2497 | qVkcaDBnkZs | Cabriole |
| 2498 | -qR860N5w7s | Tango Backward Walk |
| 2499 | s3ZyxbrSoKA | Shim Sham |
| 2500 | bCRneOn3a2U | Airfreeze |
| 2502 | qCB2PuyuIVc | Toprock |
| 2508 | tmjCPdDov-4 | Super Shy (NewJeans) |
| 2509 | t8GqDobvhw8 | Fan Kick |
| 2510 | 6xRuNeWyntQ | Passinho |
| 2511 | pCVY2EKgwOY | Armageddon (aespa) |
| 2512 | DrGbPtS5Ikw | Heels Chair Dance |
| 2513 | ETWYLBovt4g | Kathak Spins |
| 2514 | wBBqGpXP7f0 | Tango Walks |
| 2515 | QuNgch_yCpY | Reggaeton Basic Steps |
| 2516 | oxXX7h615KU | Hustle Basics |
| 2517 | DMF6T2s_kIU | Salida |
| 2518 | X06gKJ4rTSg | Tango Promenade |
| 2519 | hAuSP3Y8r1Q | Walk-Run Transition |
| 2520 | UGs-q6lc-Cc | Forward Whip |
| 2521 | hXY4IonQoqs | Dip with a Kick |
| 2522 | dYQ95W3wuy8 | Tango Forward Step |
| 2523 | LOnlV1Ef2Yo | Cobra Stretch |
| 2524 | vaGje2kxSxc | Floor Roll |
| 2532 | UvGzR_FL1_I | Gully Side Step |
| 2540 | hh-Rt6gwjWA | Rocks |
| 2541 | DgsxAbSZJoA | Eagle Slide |
| 2542 | OwIxi8PirQk | Tarraxinha |
| 2543 | g-I5S0ZcfuA | Pirouette en pointe |
| 2544 | ll6TLKbAnWQ | The Ska |
| 2545 | RHjYovihigE | Sticky (KISS OF LIFE) |
| 2546 | 93G5Atj2yV8 | Airchair |
| 2547 | RNugryE0qvc | Black Bottom |
| 2548 | ZXmTE4sOtpM | Tacky Annie |
| 2549 | K5miZeSPv54 | Heels (Digs) |
| 2550 | DLiENpRVPd8 | Apple Jack |
| 2551 | XvOww5Thbow | Grinds |
| 2552 | XgtEOjyEmpY | Charleston (Jump) |
| 2553 | CnnPOmvC_1k | Kick Step |
| 2554 | 4_JiMsHziIs | Scarecrow |
| 2555 | Jz_E6fw7aFY | Stomp off |
| 2556 | UHOlGEawhv8 | Gaze Afar |
| 2557 | 3Ovb0Y-NhHo | Boogie Back aka 'Back it up' |
| 2558 | ed9VGW-1_6U | Cómo bailar Reggaetón |
| 2559 | jLZo3IViqdQ | Closed Promenade |
| 2560 | qM9Cs_G5rTs | Savoy Kicks |
| 2561 | Lg0O4NQ8_lQ | Tabby the Cat |
| 2562 | BYoGQK4Olv4 | Shorty George |
| 2563 | BklRTYVvrUk | Shim Sham |
| 2564 | 0rUlUYuEGSU | Suzie Q |
| 2565 | LDz3QkutnHE | Charleston (Squat) |
| 2566 | o9YtSG6CsG0 | Fishtails |
| 2567 | 8Z0cqcEhDlo | Jig Walks |
| 2568 | MfZ9kRKZPfQ | Hip Flexor Stretch |
| 2569 | _f3qI96aBIc | Sailor Kicks |
| 2571 | R-3df05X4AM | Turkey Trots |
| 2576 | WR8P4B0GkLI | Mexican Folklorico |
| 2577 | NBKTN6c_MEQ | Box Step (original) |
| 2578 | W_g8rZHJEEY | Charleston (1920s) |
| 2579 | PKlHW3O7Sno | Struttin' |
| 2580 | Pso2jln-clQ | Shish-ka-boom-ba |
| 2581 | bCWwrxsJ1dk | Slip Slops |
| 2582 | 4TtBNA9IY0E | Spank the Baby |
| 2583 | 0qawNA1UHXg | Mess Around |
| 2584 | 8lYiqkLcwm0 | Crossovers |
| 2585 | FQb5ZitLJJ4 | Developpé |
| 2586 | GrCAQy4irMM | Outside Turn |
| 2587 | STaxXwZ6PpQ | Throw Out |
| 2588 | LiywoPdIxRI | Jazz Walk |
| 2589 | GsXbluBb4A8 | Foxtrot Feather Step |
| 2591 | IjbIIxbs5Gw | Funky Chicken |
| 2592 | h3H6yAbylHU | Headspin |
| 2593 | qbsNWrzjhaI | Rumba Walks |
| 2594 | DOFjPiYFYOQ | Turn (Natural Turn) |
| 2595 | hLg47s0GIW8 | Legwork |
| 2596 | Z-rf5uLwaJc | Inside Turn |
| 2597 | Y6ZoL3T-IrU | Tarantella |
| 2598 | 6Ba7k335LDA | Tendu 1st |
| 2599 | FsZF8PXtFaE | The Head Nod |
| 2603 | fBMZGO9KVOc | Choppa Style |
| 2606 | INQxh8xDsqA | Lowdown |
| 2607 | VOPxjh9AqPI | Contraction |
| 2608 | lhkQF4TXq-0 | Jive Kicks |
| 2609 | EmzjYWycrbI | The Wave |
| 2610 | 4O1iRISeySo | Cuban Motion |
| 2611 | FOFAMOyGAsE | Tuck Turn |
| 2612 | erFqCWxtwTo | Ball Change |
| 2613 | vKstmO5oLzI | Shoki |
| 2614 | 6BvVvAzy3IY | Waltz Jump |
| 2615 | rOV-g2jMHxs | Heel Toe (Walk Out) |
| 2616 | JfdzKvU_A_Q | Jersey Club Top Rock |
| 2617 | dLPxdftFI3Q | Box Step (Jazz Square) |
| 2618 | t7W8Xu8si3s | Whip |
| 2619 | i9IgZW4F3Dk | Sliding Doors |
| 2620 | DCw7u0cEo3k | Boogie Step |
| 2621 | gfzC9XMEypg | Cool-Down Stretch |
| 2622 | dUuZLrUOmhU | Frog Stretch |
| 2623 | UN2GcYzfUZs | Dégagé 5th |
| 2624 | JhNPw4DoTxA | The Stutter Step |
| 2625 | m00u6qmmG2I | Palm Tree Walk |
| 2626 | 0l-IrUpWEUI | Basic Steps |
| 2627 | XCrw-6eVAEk | Shoulder Check |
| 2628 | sMlxHIC3yLQ | Roll Forward |
| 2635 | xfO-wtsFdPw | Cha Cha New York |
| 2636 | _6-JoDoYizo | Wheel Pose |
| 2637 | F5f-_AbJ8dg | Adowa |
| 2638 | PsoZaj0zQwU | Leader Break Through |
| 2639 | bSu7QJZ5SLU | Under Arm Turn |
| 2640 | LX3WPFUpSEc | Forward Tuck Turn |
| 2641 | drLc7eYNw-E | Basic |
| 2642 | _B55w-0o0qw | Salsa Setenta |
| 2643 | FYhUscyS2MA | Twist | Heel Twist - Bedrock |
| 2644 | l-avoQVmi3g | Balboa Basic |
| 2645 | dSwBpPkX4rw | Hamstring Stretch |
| 2646 | jm8Nyk9VEF8 | Genna Bounce |
| 2647 | jOcns4yR8Ew | Kick Ball Change |
| 2648 | g0nSxNBuqNA | Knee Up Challenge | Farmer |
| 2649 | qwQqqaaMhC0 | Knee Up | Standard |
| 2650 | HEMZGDI_vpM | Skip up |
| 2651 | lLcxnxulPt4 | Reverse Rad |
| 2652 | hX8Tj2qPPuk | Twist | Toe Twist |
| 2653 | l1kVdR4Hl68 | Snap Kick | Standard |
| 2654 | 9wMOwTspveI | Basic Hold |
| 2655 | CA00b52i0z4 | Twist | Freeze |
| 2656 | DGRysd7tAE8 | Twist | Separate |
| 2657 | ZCoVxLTIDQg | Knock | and Count |
| 2658 | uyvUCfIT6dc | Knock Challenge | Hurdle |
| 2659 | NxtNhurnArQ | Twist | Toe Twist - Knee Up |
| 2660 | -GAuZi9UzWI | Heel Twist Challenge | Jacking in the Box |
| 2662 | KfL7Y6u6Dcw | Gwara Gwara |
| 2666 | FM6NtPhb5-w | Sandungueo |
| 2667 | HAQ7UgD4DTU | Natural Turn |
| 2668 | GVZZi-Gth_M | Front Splits |
| 2669 | K5-lwFeTMoI | Deep Squat Mobility |
| 2670 | RrWEFLUs1vs | Spine Mobility |
| 2671 | WqZieVvDJx8 | Loko Loko |
| 2672 | CSADXQfUKGk | Hook Turn |
| 2673 | p-hvJbSx0fI | Grand Jete |
| 2674 | IHKfWj4auW8 | Tek Weh Yuhself |
| 2675 | tjIfkEqn6jg | Tango Forward Walk |
| 2676 | 8yIuYZPucf4 | Heels Knee Spin |
| 2677 | jKbWrwPKQtI | Hammer Lock |
| 2678 | P_kkfQf0mRc | Sirtaki |
| 2679 | J2KZHT-m_qQ | Heel Clicks |
| 2680 | YN_Tp8VIaws | Wuk Up |
| 2681 | g7llm1J9sl0 | Coupé & Tendu |
| 2682 | XOwwHtdgNpM | Oversplits |
| 2683 | -ewZ4bWRkVo | Waltz |
| 2684 | hgkPtziNVeg | Forward and Backward Ocho |
| 2685 | nElWeylI8H8 | Resistance Band Stretch |
| 2686 | M7CpRZSVxVc | Lizard Pose |
| 2687 | P1bLM0ROKSY | Bounce | One Leg |
| 2688 | BAnCu1NPCIE | Bachata Step to The Wave |
| 2689 | XKWJ3Flfm8A | Wrist & Forearm Mobility |
| 2690 | QT8a2dchSOU | Flexibility for High Kicks |
| 2694 | __W4nJoHhAM | Fouetté à terre |
| 2697 | qqxGz58GTEA | Highland Fling |
| 2698 | KA8z4HCoAB8 | Basic Step (Forward Walk) |
| 2699 | uBsGRFU-Dgk | Tournant jeté |
| 2700 | oRISWvk66jc | En dehors |
| 2701 | TfL6ZcpVc9s | Rev Up |
| 2702 | -ZKEs_zlSok | The Swim |
| 2703 | e69_AiARMsE | Inside Swivels |
| 2704 | 7su43Crj2oI | Backward Sway |
| 2705 | XK_iLYsNFoU | Pivot Turn with Arm Movement |
| 2706 | WrQdfjaaBBs | The Shoulder Shimmy Shake |
| 2707 | hI4b_9h9LtY | The Pause |
| 2708 | CdsFZiQy9Ik | Soapy |
| 2709 | HCXhlMCywFE | The Chug |
| 2710 | CwlKhjr25Qg | Up Chest Pop |
| 2711 | REL4y5a_xF8 | Full Body Mobility Flow |
| 2712 | BGlVsSheJ7s | Pon Di River |
| 2713 | kTJGoaOdVa0 | Baddie (IVE) |
| 2714 | T_yUO4xmz5k | PNF Stretching |
| 2715 | UkFY-4ickr0 | Buga |
| 2716 | sRw2Cxuuhbc | Samba Voltas |
| 2717 | 31kgNdQVrVg | The Chicken |
| 2718 | mUo-r0dTEpU | Tango Sacada |
| 2719 | 2Zvz7e_MXXo | Backward Whip |
| 2720 | KM2UU_bVXGs | Pique Turn |
| 2721 | AsPhnlXehBk | Flamenco |
| 2728 | So1yaP90sKQ | Alternating Underarm Turn |
| 2729 | gtQOIc_mp-0 | Bolero Basics |
| 2730 | vvmUXbT0rIE | Finger Tutting Combo |
| 2731 | IuKIoA1tGNw | International Rumba |
| 2732 | JXybpeZcZz8 | Merengue |
| 2733 | 25HIps1lYuQ | International Cha Cha |
| 2734 | _v_pm_ETrVY | Paso Doble |
| 2735 | BNYLxnVOJak | East Coast Swing |
| 2736 | di8MMJlg-gE | Bachata Footwork |
| 2737 | FPwy4X_6uh0 | Jazz Pirouette |
| 2738 | Uc3O0rPAHSc | American Rumba |
| 2739 | --jqOdifXrw | Mambo |
| 2740 | V0UCsRVilbg | American Cha Cha |
| 2741 | k8hz0F9Ehos | Bolero |
| 2742 | t17pMfihxvI | Brush and Drags |
| 2743 | XiqHaURCqHE | Dip and Pop |

_Auto-processed daily at 09:15 by the `DanceChipAuto` task (headless `/find-chips`); or run `/find-chips` manually._
<!-- CHIP-QUEUE:END -->

## Chip-everything push (2026-07-13)

User directive: EVERY video gets chips. Started at 561 unchipped (547 yt + 14 tiktok), ended at 7
(all deliberately skip-listed). 3,788 total segments in prod (was ~2,900). Lanes:

- **A chapter-adopt**: 5 videos (2052, 1816, 2101, 2106, 1738).
- **B transcript-inferred**: 7 real reads (2050, 2065, 1737, 1724, 1863, 316, +1856/1771/1802 via thin cues).
- **C montage slices**: 350 rows from 29 sources via `scripts/slice_chips.py` (4 chapter-mapped,
  68 cue-split, 278 single-window absolute-time chips). keeptype — slices stay steps.
- **D short clips**: thin_chips + 16 single named chips.
- **E/T generic**: 160 rows via `scripts/chip_generic.py` — tutorial-typed >=180s got proportional
  Intro/Tutorial/Outro; performance/steps got one named chip; 14 TikToks got open-ended `Name@0`.
- **Multimodal contact-sheets**: 7 videos read frame-by-frame: 1995 (15 labeled poses), 2007 (13
  exercises), 2103 (22 poses), 2043 (all 10 dips named), 792 (25 moves, grouped anchors), 2022
  (Spanish anchors), 1716 (10 coarse visual phases — no labels).

Residual 7 (in chip_skip.tsv, need /fix-videos re-source, then unskip + rechip):
6x p2JrE6JICKk mis-sourced (dbIds 444, 469, 686, 890, 1582, 1584 — dances don't match the shuffle
montage) + dead sFt9yqACiuI (db 2102). Upgrade candidates: the ~40 proportional Intro/Tutorial/Outro
tutorials (generic tier) can be improved later via multimodal.

Detector now queues ANY unchipped video (all platforms/types). DanceChipAuto (09:15 daily) drains
the queue headlessly, capped 5/run.
