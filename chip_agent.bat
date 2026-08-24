@echo off
REM Chip Refinery - unattended continuation agent.
REM
REM Registered as Windows Scheduled Task "DanceChipAgent". Runs a headless Claude
REM Code session against scripts\agent_task.md, which carries the state of play,
REM the priority order, and the hard constraints (no deploys, no schema changes,
REM prod writes only through apply_chips.py's gate).
REM
REM Scheduled AFTER DanceChipOvernight so the sweep results exist to act on.
REM
REM COST: a long agentic session on the Claude Code subscription. That is the
REM point - Justas asked for the quota to be used.

cd /d "C:\Users\valot\Documents\Git\Projects\Dance"
set "LOG=_proto\agent.log"

echo. >> "%LOG%"
echo ======================================================== >> "%LOG%"
echo [%date% %time%] continuation agent starting >> "%LOG%"

python scripts\chip_paused.py
if not errorlevel 1 (
  echo [%date% %time%] paused from the dashboard - skipping >> "%LOG%"
  exit /b 0
)

REM Resolve the binary rather than hardcoding it - the literal path in this file's
REM sibling went stale for weeks and failed silently every night.
set "CLAUDE_BIN="
for /f "delims=" %%i in ('where claude 2^>nul') do if not defined CLAUDE_BIN set "CLAUDE_BIN=%%i"
if not defined CLAUDE_BIN if exist "%USERPROFILE%\.local\bin\claude.exe" set "CLAUDE_BIN=%USERPROFILE%\.local\bin\claude.exe"
if not defined CLAUDE_BIN (
  echo [%date% %time%] ERROR: claude binary not found >> "%LOG%"
  exit /b 1
)

call "%CLAUDE_BIN%" -p "Read scripts/agent_task.md and carry out the work it describes. Follow its hard constraints exactly. Finish by writing _proto/morning_report.md." --dangerously-skip-permissions >> "%LOG%" 2>&1

echo [%date% %time%] agent finished, exit code %errorlevel% >> "%LOG%"
