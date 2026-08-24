@echo off
REM Chip Refinery — one full pass over the eval set, stages 01 to 03, then score.
REM
REM Registered as Windows Scheduled Task "DanceChipPipeline". Runs locally because
REM the prod DB is on the LAN and the signal cache is on this disk; a cloud agent
REM can reach neither.
REM
REM COST: only step 4 spends anything. It is one headless `claude -p` call per gold
REM video on the Claude Code subscription (~60 with the default gold set). Steps 1-3
REM are local GPU/CPU and free. Pause from the dashboard stops it between videos.
REM
REM Keep this file CRLF, same reason as deploy-dance.bat.

cd /d "C:\Users\valot\Documents\Git\Projects\Dance"
set "LOG=_proto\pipeline.log"

echo. >> "%LOG%"
echo ======================================================== >> "%LOG%"
echo [%date% %time%] pipeline run starting >> "%LOG%"

REM Honour the dashboard's Pause/Stop button before spending anything.
python scripts\chip_paused.py
if not errorlevel 1 (
  echo [%date% %time%] paused from the dashboard - skipping this run >> "%LOG%"
  exit /b 0
)

echo [%date% %time%] 1/5 rebuilding gold set from creator chapters >> "%LOG%"
python scripts\chip_gold.py auto >> "%LOG%" 2>&1

echo [%date% %time%] 2/5 extracting signals (GPU, free) >> "%LOG%"
python scripts\signals.py --gold >> "%LOG%" 2>&1

echo [%date% %time%] 3/5 building candidate boundaries + recall >> "%LOG%"
python scripts\candidates.py --gold --eval --force >> "%LOG%" 2>&1

echo [%date% %time%] 4/5 proposing sections (claude -p, uses the subscription) >> "%LOG%"
python scripts\propose.py --gold --samples 1 >> "%LOG%" 2>&1

echo [%date% %time%] 5/5 scoring >> "%LOG%"
echo --- baseline: today's prod chips --- >> "%LOG%"
python scripts\chip_gold.py baseline >> "%LOG%" 2>&1
echo --- proposed: stage 03 output --- >> "%LOG%"
python scripts\propose.py --eval >> "%LOG%" 2>&1

echo [%date% %time%] pipeline run finished, exit code %errorlevel% >> "%LOG%"
