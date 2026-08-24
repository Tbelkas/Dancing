# Chip Refinery — unattended continuation task

You are continuing the Chip Refinery work on DancePlatform, unattended, while
Justas sleeps. Read this whole file before doing anything.

Orient first: `CLAUDE.md`, then the memory files `chip-refinery-flow`,
`stage03-oversegments`, `intake-gate-2026-08`, `no-paid-apis-dance`.

## Where things stand

The pipeline runs end to end but **stage 03 currently loses to the chips already
on the site**: boundary F1 0.261 against a prod baseline of **0.449** on the
informative subset (the videos where prod did not simply copy the creator's
chapters). Cause is over-segmentation — median 12 sections proposed against 6 in
gold. Candidate recall is 0.817, so the boundaries are reachable; the model picks
too many of them.

A prompt sweep ran at 06:00 (`DanceChipOvernight`): five variants over ~59 eval
videos. Results in `_proto/sweep_results.json`, log in `_proto/overnight.log`.

## Hard constraints — do not violate these

1. **Never deploy.** Do not run `deploy-dance.bat`. The Pi is not to be touched.
2. **Never change the database schema.** No migrations, no `ALTER TABLE`.
3. **The ONLY way you may write chips to prod is `scripts/apply_chips.py`**, and
   only if a variant genuinely beat the 0.449 baseline. It has the gate, the
   overwrite rule and a tagged undo. Never write `VideoSegments` by hand.
4. **Never touch the intake gate** (`ReviewState`, the query filter, `video_gate.py`).
5. **No paid APIs.** Local tooling plus `claude -p` on the existing subscription.
6. **Stop if `python scripts/chip_paused.py` exits 0** — that means Justas hit
   Pause in the dashboard. Respect it immediately.
7. **Commit as you go** with real messages saying what you did and why. Do not
   push anything that fails `python -c "import ast; ast.parse(...)"`.
8. Budget roughly **2 hours**, then write your report and stop.

## What to do, in priority order

### 1. Read the sweep results
If `_proto/sweep_results.json` is missing or empty, the 06:00 run failed. Read
`_proto/overnight.log`, diagnose, fix, and re-run `python scripts/sweep.py
--videos 40`. That becomes your main task if so.

### 2. Judge the variants honestly
A variant wins only if **F1 > 0.449 AND `size_ratio` is near 1.0** (0.8–1.3).
A high F1 with a ratio of 2 is luck, not a result. Beware: the metric measures
agreement with the creator, not quality — a proposal can be genuinely better and
score badly. Before declaring a winner, open two or three of its proposals in
`_proto/sweep/<variant>/` and read the labels. If they are good but score badly,
say so in your report rather than chasing the number.

### 3a. If a variant won
- Make its settings the default in `scripts/propose.py` (the `suggested_sections`
  divisor and any extra rules). Keep the old value in a comment with the number
  it scored, so the change is auditable.
- Re-run `python scripts/propose.py --gold --samples 1 --force` and
  `python scripts/propose.py --eval` to confirm on the full eval set.
- Only if it still beats 0.449: apply to a **small** batch first —
  `python scripts/apply_chips.py --limit 20 apply`. Record the run id it prints
  in your report. Verify with a spot check against the live API
  (`https://dance-api.takelord.com/api/videos/dance/<danceId>`).
- Do not apply more than 20 videos unattended, however good it looks.

### 3b. If nothing won
This is the likely case and it is not a failure. Design a second round of
variants informed by what the first showed — if everything over-segmented, go
coarser still; if labels scored badly, work on the labelling instructions rather
than the count. Add them to `VARIANTS` in `scripts/sweep.py` and run another
sweep. Keep the earlier variants in place so rounds stay comparable.

### 4. If you have time left
Pick from these, in this order:
- **Stage 04, visual grounding.** 5 gold videos have 0–2 ASR segments and
  recall 0.40 — nothing to hear. `ffmpeg` contact sheets at candidate times with
  timecodes burned in, read by `claude -p`. This is the only route for silent
  videos. Design it, build it, measure it on those 5.
- **Wire `--source`/`--confidence` into `scripts/apply_sections.py`** so the
  older chipping path records provenance like `apply_chips.py` does.
- **Liveness sweep**: `yt-dlp --simulate` across the catalogue, flag dead videos
  as `rejected` via the intake gate. 0 of 60 sampled were dead, so expect few.

## Report

Write `_proto/morning_report.md` — plain markdown, for a person reading it with
coffee. Include:
- what the sweep found, with the numbers, and whether anything beat 0.449
- what you changed and committed (with hashes)
- anything you applied to prod, with the undo command
- what you tried that did not work, and why
- what you would do next and what you need from Justas

Be honest about negative results. A sweep where nothing won is a real finding and
saying so is more useful than a hedge. Do not overstate a marginal improvement.
