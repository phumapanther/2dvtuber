@echo off
where python >nul 2>nul
if %errorlevel%==0 (
  start "" http://localhost:8931/
  python -m http.server 8931 --directory "%~dp0."
) else (
  start "" "%~dp0index.html"
)
