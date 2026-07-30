@echo off
rem Commit, push, and roll the Pi over to the new HEAD.
rem
rem   deploy-dance.bat                    commit with no message
rem   deploy-dance.bat fix the tree       commit with "fix the tree"
rem   deploy-dance.bat "fix the tree"     same
rem
rem The Pi pulls from the remote, so a failed push must not reach the ssh step: it
rem would rebuild the previous commit and report a clean deploy.

setlocal

rem Every argument becomes the message, quoted or not. Stripping the quotes lets both
rem calling styles work without the nested-quote mess of handing %* straight to -m.
set "MSG=%*"
if defined MSG set "MSG=%MSG:"=%"

git pull
if errorlevel 1 goto :failed

git add .

rem Nothing staged is not a failure - re-running the deploy to rebuild the Pi from the
rem current HEAD is a legitimate thing to want, and `git commit` would abort the script.
git diff --cached --quiet
if errorlevel 1 (
  if defined MSG (
    git commit -m "%MSG%"
  ) else (
    rem What the script always meant to do. Plain `-m ""` is rejected outright, which is
    rem why every run of the old version stopped here and pushed nothing.
    git commit --allow-empty-message -m ""
  )
  if errorlevel 1 goto :failed
) else (
  echo No staged changes - deploying the current HEAD.
)

git push
if errorlevel 1 goto :failed

ssh pi@pi "./scripts/updateDance"
if errorlevel 1 goto :failed

endlocal
exit /b 0

:failed
echo.
echo Deploy aborted - see the error above. Nothing was sent to the Pi.
endlocal
exit /b 1
