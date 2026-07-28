@echo off
REM Auto-chip runner: drains the CHIP-QUEUE via a headless Claude Code run of /find-chips.
REM Registered as Windows Scheduled Task "DanceChipAuto" (daily 09:15, after DanceChipCheck
REM refreshes the queue at 09:00). Skips the Claude run entirely when the queue is empty.
cd /d "C:\Users\valot\Documents\Git\Projects\Dance"
findstr /C:"awaiting section chips" SECTIONS_FIXUP.md >nul 2>&1
if errorlevel 1 (
  echo [%date% %time%] queue empty - nothing to do >> "_proto\chip_auto.log"
  exit /b 0
)
echo [%date% %time%] queue has pending videos - starting headless /find-chips run >> "_proto\chip_auto.log"
call "C:\nvm4w\nodejs\claude.cmd" -p "/find-chips Process the auto-detected chip queue in SECTIONS_FIXUP.md. Limit this run to at most 5 videos (leave the rest for tomorrow's run). Apply the skill's skip rules — add unchippable videos to _proto/chip_skip.tsv instead of forcing bad chips." --dangerously-skip-permissions >> "_proto\chip_auto.log" 2>&1
echo [%date% %time%] run finished, exit code %errorlevel% >> "_proto\chip_auto.log"
