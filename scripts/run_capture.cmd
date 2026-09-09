@echo off
REM C3: local redundant capture runner (Windows Task Scheduler).
REM Independent of GitHub Actions. Writes its own source-tagged file.
setlocal
set NOCTURNE_SOURCE=local
cd /d "%~dp0.."
py -3 scripts\capture.py >> logs\capture.log 2>&1
git add -A data/ >nul 2>&1
git diff --cached --quiet && goto :end
git commit -q -m "capture local %DATE% %TIME%" >nul 2>&1
for /L %%i in (1,1,4) do (
  git pull --rebase --autostash -q origin master >nul 2>&1 && git push -q >nul 2>&1 && goto :end
  timeout /t 5 /nobreak >nul
)
:end
endlocal
