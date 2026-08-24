@echo off
REM Chip Refinery - overnight prompt sweep.
REM
REM Registered as Windows Scheduled Task "DanceChipOvernight".
REM
REM WHY: the first full stage-03 run scored F1 0.302 against a prod baseline of
REM 0.449 - worse than what is already on the site. Diagnosis was over-segmentation
REM (median 12 sections proposed vs 6 in gold). Each variant is a different answer
REM to "how coarse is a section"; the sweep scores them all on the same videos so
REM the next prompt is picked from evidence.
REM
REM WRITES NOTHING TO THE DATABASE. Proposals land in _proto/sweep/ and the scores
REM in _proto/sweep_results.json. Applying anything stays a separate decision that
REM a human makes after reading the numbers.
REM
REM COST: 5 variants x ~59 videos = ~295 headless `claude -p` calls on the Claude
REM Code subscription, roughly an hour. Pause in the dashboard stops it between
REM videos.

cd /d "C:\Users\valot\Documents\Git\Projects\Dance"
set "LOG=_proto\overnight.log"

echo. >> "%LOG%"
echo ======================================================== >> "%LOG%"
echo [%date% %time%] overnight sweep starting >> "%LOG%"

python scripts\chip_paused.py
if not errorlevel 1 (
  echo [%date% %time%] paused from the dashboard - skipping >> "%LOG%"
  exit /b 0
)

python scripts\sweep.py --videos 59 >> "%LOG%" 2>&1
echo [%date% %time%] sweep finished, exit code %errorlevel% >> "%LOG%"

REM Re-score the original run alongside, so the morning summary has both.
echo --- prod baseline --- >> "%LOG%"
python scripts\chip_gold.py baseline >> "%LOG%" 2>&1

echo [%date% %time%] overnight run complete >> "%LOG%"
