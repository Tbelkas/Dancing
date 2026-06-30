# Video Quality Audit — 2026-06-30

Scanned all **1,046 videos** (698 distinct YouTube ids + 15 TikToks). Read-only signals:
DB segment stats, per-dance `StartTime` (montage-slice vs standalone), yt-dlp durations,
oembed embeddability, user-data references. Scripts: `audit_videos.py`, `fetch_durations.py`,
`check_alive.py`.

## Health summary
- ✅ 0 bad segment timings; big vocabulary montages correctly per-move sliced (intentional).
- ✅ Embeddability clean — only known `xWiAh_EizqI` (jazz montage, 5 link-out dances) remains.

## Defects found

### 1. DEAD video — `h3DSYn2jIKE` (removed/private, won't play) — 4 dances, 0 user data
| Dance | Id | Style |
|---|---|---|
| Lift-Off | 366 | Breakdance |
| The Knee Slide | 446 | Breakdance |
| The Slide | 477 | House |
| Small Thing | 940 | Hip-hop |
→ Re-source each with a live tutorial, or detach+delete the dance.

### 2. Duplicate dances (same video + same move; newer round-10/11 dupes; 0 user data) → delete newer, keep older
| Keep | Delete (dupe) | Video |
|---|---|---|
| Hair Flip (d1781, 5 chips) | Heels Hair Flip (d1992, 0) | OSaHk-m6ouk |
| Floor Roll (d1734, 9) | Floor Rolls (d1991, 9) | Kh8FMlMs1sI |
| Spin and Dip (d1732, 8) | Vogue Spins and Dips (d2044, 8) | nCsIqNFfOZw |
| Wing (d1864, 6) | Tap Wings (d1970, 2) | 0BkFwdca9vU |
| Locking (d899, 10) | Locking Basics (d1873, 10) | nuo-6UKqBMI |

### 3. Duplicate video ROW on same dance → delete the extra row
- **Pas de Bourrée (d1725)**: `d5-TKHTOTdU` attached twice (v1757 + v2051). Delete v2051.

### 4. Mis-sourced (two different moves share one video — one is wrong) → re-source
| Dance | Video it wrongly shares | Fix |
|---|---|---|
| Spiral (d411, **House**) | Contemporary "Spiralling" clip (correct for Spiral d1735) | re-source House spiral |
| Backward Shuffle (d1639) | generic "Shuffling for Beginners" (shared w/ Cutting Shapes d1746) | re-source backward shuffle |
| Cross-Body Lead (d269, 0 chips) | shares hl-S_ovXl0c w/ Salsa Cross Body Lead (d1860, 6 chips) | same move — merge: copy chips to d269, delete d1860 |
| Chipping (d2045) | shares "5 Soca Moves" w/ Soca Footwork (d1863) | re-source dedicated chipping clip |
| Attitude (d672, **Krump**-tagged) | "Attitude Turn" clip (a ballet/contemp move) — mis-tagged | re-tag or merge w/ Attitude Turn (d1859, Contemporary) |
| Heels Dance Basics (d1687, **Jazz**-tagged) | generic heels-basics (shared w/ Heels Choreography d1980) | re-tag/merge under Heels |

## Enhancement buckets (not defects)
- **74 long (≥4 min) standalone videos with NO chips** — real chip candidates (En pointe 26m, Tendu 11m,
  Jazz Funk Basics 10m, Salsa Shines 10m, …). Run `/find-chips` workflow.
- **55 very short (<60 s) clips** — single-move demos (6 s Cabriole … 59 s). Mostly fine; a handful
  (≤15 s) are arguably too thin. `d1710 Tutting` has 4 videos (3 are <60 s) — could thin.
