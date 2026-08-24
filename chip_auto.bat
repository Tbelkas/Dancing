@echo off
REM Auto-chip runner: drains the CHIP-QUEUE via a headless Claude Code run of /find-chips.
REM Registered as Windows Scheduled Task "DanceChipAuto" (daily 09:15, after DanceChipCheck
REM refreshes the queue at 09:00). Skips the Claude run entirely when the queue is empty.
cd /d "C:\Users\valot\Documents\Git\Projects\Dance"
REM Honour the dashboard's Pause/Stop button (scripts/chip_ui.py -> _proto\chip_control.json).
python scripts\chip_paused.py
if not errorlevel 1 (
  echo [%date% %time%] paused from the dashboard - skipping this run >> "_proto\chip_auto.log"
  exit /b 0
)
findstr /C:"awaiting section chips" SECTIONS_FIXUP.md >nul 2>&1
if errorlevel 1 (
  echo [%date% %time%] queue empty - nothing to do >> "_proto\chip_auto.log"
  exit /b 0
)
echo [%date% %time%] queue has pending videos - starting headless /find-chips run >> "_proto\chip_auto.log"
REM Resolve the Claude binary rather than hardcoding it. The previous literal
REM stopped existing when the install moved, and this task then failed silently
REM every night - the chip queue grew from 7 to 130 before anyone noticed.
set "CLAUDE_BIN="
for /f "delims=" %%i in ('where claude 2^>nul') do if not defined CLAUDE_BIN set "CLAUDE_BIN=%%i"
if not defined CLAUDE_BIN if exist "%USERPROFILE%\.local\bin\claude.exe" set "CLAUDE_BIN=%USERPROFILE%\.local\bin\claude.exe"
if not defined CLAUDE_BIN (
  echo [%date% %time%] ERROR: claude binary not found >> "_proto\chip_auto.log"
  exit /b 1
)
call "%CLAUDE_BIN%" -p "/find-chips Process the auto-detected chip queue in SECTIONS_FIXUP.md. Limit this run to at most 5 videos (leave the rest for tomorrow's run). Apply the skill's skip rules — add unchippable videos to _proto/chip_skip.tsv instead of forcing bad chips." --dangerously-skip-permissions >> "_proto\chip_auto.log" 2>&1
echo [%date% %time%] run finished, exit code %errorlevel% >> "_proto\chip_auto.log"
