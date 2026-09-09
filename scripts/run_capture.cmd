@echo off
REM C3: local redundant capture runner (Windows Task Scheduler).
REM Independent of GitHub Actions. Writes its own source-tagged file.
setlocal
set NOCTURNE_SOURCE=local
set GIT_TERMINAL_PROMPT=0
set GCM_INTERACTIVE=never
cd /d "%~dp0.."
py -3 scripts\capture.py >> logs\capture.log 2>&1

REM Stage ONLY live capture output. Bulk history (data/1h) is committed
REM separately - letting it into this commit made git slow enough that the
REM task hit its execution time limit and was killed mid-push.
if exist data\live git add -A data/live
if exist data\books git add -A data/books
if exist data\status.local.json git add data/status.local.json
if exist data\health.json git add data/health.json

git diff --cached --quiet && goto :end
git commit -q -m "capture local %DATE% %TIME%"
for /L %%i in (1,1,4) do (
  git pull --rebase --autostash -q origin master && git push -q && goto :end
  timeout /t 4 /nobreak >nul
)
echo PUSH FAILED %DATE% %TIME% >> logs\capture.log
:end
endlocal
