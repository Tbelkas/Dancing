@echo off
rem Commit, push, build here, and roll .196 over to the new HEAD.
rem
rem   deploy-dance.bat                    commit with no message
rem   deploy-dance.bat fix the tree       commit with "fix the tree"
rem   deploy-dance.bat "fix the tree"     same
rem
rem The build is made from this working tree, so a failed push must not reach the build
rem step: .196 would run code the remote does not have. .196 has only the .NET runtime;
rem ~/deploy-dance there swaps the API, UI and scripts in and rolls the API back if it
rem does not come up.
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
rem deploy to rebuild .196 from the current HEAD is a legitimate thing to want.
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

set "OUT=%TEMP%\dance-deploy"
if exist "%OUT%" rmdir /s /q "%OUT%"

dotnet publish "%~dp0DancePlatform.API" -c Release -o "%OUT%\api" --nologo -v q
if errorlevel 1 goto :failed

pushd "%~dp0dance-platform-ui"
call npm install --no-audit --no-fund
if errorlevel 1 goto :failed_ui
call npm run build -- --configuration production
if errorlevel 1 goto :failed_ui
popd
robocopy "%~dp0dance-platform-ui\dist\dance-platform-ui\browser" "%OUT%\ui" /e /nfl /ndl /njh /njs /np >nul
if errorlevel 8 goto :failed
robocopy "%~dp0scripts" "%OUT%\scripts" /e /xd __pycache__ /nfl /ndl /njh /njs /np >nul
if errorlevel 8 goto :failed

tar -czf - -C "%OUT%" api ui scripts | ssh hp@192.168.0.196 "~/deploy-dance"
if errorlevel 1 goto :failed

endlocal
exit /b 0

:failed_ui
popd
:failed
echo.
echo Deploy aborted - see the error above.
endlocal
exit /b 1
