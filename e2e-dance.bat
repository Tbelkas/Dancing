@echo off
REM Periodic production smoke check for dance.takelord.com.
REM
REM Runs the @smoke subset against the live site and writes a timestamped log to e2e\runs\.
REM Exits non-zero when something is broken, so Task Scheduler shows it as a failed run.
REM
REM Schedule hourly:
REM   schtasks /create /tn "DancePlatform e2e smoke" /tr "%~f0" /sc hourly
REM Remove:
REM   schtasks /delete /tn "DancePlatform e2e smoke"

setlocal
cd /d "%~dp0e2e" || exit /b 1

if not exist "runs" mkdir "runs"

REM Timestamp via PowerShell: wmic is no longer present on current Windows 11 builds.
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm"`) do set "STAMP=%%I"

REM Never run with an unset stamp — the redirect below would fail and the script would
REM report success without having tested anything.
if not defined STAMP (
  echo FAIL  could not determine a timestamp; aborting without running tests.
  exit /b 1
)

set "LOG=runs\smoke_%STAMP%.log"

echo Running production smoke check at %STAMP%> "%LOG%"
if not exist "%LOG%" (
  echo FAIL  could not write %LOG%; aborting without running tests.
  exit /b 1
)

call npm run test:smoke >> "%LOG%" 2>&1
set "RESULT=%ERRORLEVEL%"

if "%RESULT%"=="0" (
  echo PASS  %STAMP%  --  see e2e\%LOG%
) else (
  echo FAIL  %STAMP%  --  see e2e\%LOG%
  echo.
  echo ---- tail of log ----
  powershell -NoProfile -Command "Get-Content '%LOG%' -Tail 30"
)

REM Keep the last 50 logs; a scheduled job would otherwise fill the folder forever.
for /f "usebackq skip=50 delims=" %%F in (`dir /b /o-d "runs\smoke_*.log" 2^>nul`) do del "runs\%%F"

exit /b %RESULT%
