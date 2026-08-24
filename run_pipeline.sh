#!/usr/bin/env bash
# Chip Refinery — one full pass over the eval set, stages 01-03, then score.
#
# The shell-runnable twin of chip_pipeline.bat (which exists for the Windows
# Scheduled Task). Running the .bat via `cmd /c` from a POSIX shell opens an
# interactive prompt instead of executing it, which looks like a silent success:
# exit 0, no output, nothing done. Use this from a terminal; the .bat from the
# scheduler.
#
# COST: only step 4 spends anything - one `claude -p` per gold video on the
# Claude Code subscription. Steps 1-3 are local GPU/CPU and free.
set -euo pipefail
cd "$(dirname "$0")"

if python scripts/chip_paused.py; then
  echo "paused from the dashboard - not running"
  exit 0
fi

echo "=== 1/5 gold set from creator chapters ==="
python scripts/chip_gold.py auto
echo "=== 2/5 signals (local GPU, free) ==="
python scripts/signals.py --gold
echo "=== 3/5 candidate boundaries + recall ==="
python scripts/candidates.py --gold --eval --force
echo "=== 4/5 propose sections (claude -p, uses the subscription) ==="
python scripts/propose.py --gold --samples "${SAMPLES:-1}"
echo "=== 5/5 scores ==="
echo "--- baseline: today's prod chips ---"
python scripts/chip_gold.py baseline
echo "--- proposed: stage 03 output ---"
python scripts/propose.py --eval
