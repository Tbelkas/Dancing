# archive/

One-shot scripts and outputs from completed data-seeding, catalog-cleanup, and UI-audit
runs. Kept for reference and reproducibility; **nothing here is on any live code path**.

- `phase*.py`, `trend_search*.py`, `verify_picks*.py`, `insert_*.py`, `reseed_*.py`,
  `resource_*.py`, `seed_*.py`, `consolidate_*.py`, `*_dedup*.py`, `fix_names*.py`,
  `fix_descriptions*.py`, `singles_*.py`, `reclassify*.py`, `triage_*.py`, … — completed
  bulk yt-dlp/Ollama seeding and cleanup passes.
- `*_results.json`, `*_progress.json`, `*_plan.json`, `baseline.json`, `all_dances.json` —
  run outputs / checkpoints from those passes.
- `audit-*.png`, `issue-*.png`, `landing-*.png`, `recheck-*.png`, `current-screen.png` —
  screenshots from UI audits.
- `BUG_REPORT.md`, `VIDEO_QUALITY_AUDIT.md`, `CONTINUE-TRENDS.md`, `SEED_FLOW.md` —
  notes for finished work.

Still-active tooling lives at the repo root, not here: the `fix-videos` skill scripts
(`prep_video.py`, `map_times.py`, `rebuild_video.py`, `update_tracker.py`), the `find-chips`
skill scripts (`find_chip_candidates.py`, `prep_sections.py`, `chapters_spec.py`,
`apply_sections.py`, `thin_chips.py`, `chip_check.bat` — the last two are wired to a daily
Scheduled Task), and the reusable post-seed backfills (`enrich_views.py`,
`backfill_durations.py`, `fetch_durations.py`).
