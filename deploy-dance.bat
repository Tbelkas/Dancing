@echo off
rem Commit, push, and roll the Pi over to the new HEAD.
rem
rem   deploy-dance.bat                    commit with no message
rem   deploy-dance.bat fix the tree       commit with "fix the tree"
rem   deploy-dance.bat "fix the tree"     same
rem
rem The Pi pulls from the remote, so a failed push must not reach the ssh step: it
rem would rebuild the previous commit and report a clean deploy.
rem
rem Keep this file CRLF (.gitattributes pins it). cmd.exe mis-parses multi-line
rem parenthesised blocks in an LF-only batch file - it skips them and carries on, which
rem here meant deploying without committing. The flat goto flow below is deliberate for
rem the same reason: nothing depends on a block surviving the parser.

setlocal

rem Every argument becomes the message, quoted or not. Stripping the quotes lets both
rem calling styles work without the nested-quote mess of handing %* straight to -m.
set "MSG=%*"
if defined MSG set "MSG=%MSG:"=%"

git pull
if errorlevel 1 goto :failed

git add .

rem Exits 1 when something is staged. Nothing staged is not a failure - re-running the
rem deploy to rebuild the Pi from the current HEAD is a legitimate thing to want.
git diff --cached --quiet
if errorlevel 1 goto :commit
echo No staged changes - deploying the current HEAD.
goto :push

:commit
if defined MSG goto :commit_with_message
rem What the script always meant to do. A plain `-m ""` is rejected outright, which is
rem why every run of the old version stopped here and pushed nothing.
git commit --allow-empty-message -m ""
goto :commit_done

:commit_with_message
git commit -m "%MSG%"

:commit_done
if errorlevel 1 goto :failed

:push
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
