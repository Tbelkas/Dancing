@echo off
REM Daily detection of tutorial videos that still need section chips.
REM Registered as Windows Scheduled Task "DanceChipCheck". Detection only — no DB writes.
cd /d "C:\Users\valot\Documents\Git\Projects\Dance"
python find_chip_candidates.py >> "_proto\chip_check.log" 2>&1
