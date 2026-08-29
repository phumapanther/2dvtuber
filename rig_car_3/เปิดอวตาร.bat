@echo off
rem เคลียร์เซิร์ฟเวอร์เก่าที่ค้างบนพอร์ตนี้ก่อน (กันเปิดแล้วได้โมเดลผิดตัว)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr "LISTENING" ^| findstr ":8933 "') do taskkill /f /pid %%a >nul 2>nul
where python >nul 2>nul
if %errorlevel%==0 (
  start "" "http://localhost:8933/index.html?nocache=%RANDOM%"
  python -m http.server 8933 --directory "%~dp0."
) else (
  start "" "%~dp0index.html"
)
