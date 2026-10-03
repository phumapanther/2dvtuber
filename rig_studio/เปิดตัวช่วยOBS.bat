@echo off
title PhumaPanther Helper
rem Python จาก Microsoft Store เปิดไมค์ไม่ได้ (ไม่มีสิทธิ์ไมค์) — มี Python แบบ embeddable ในเครื่องก็ใช้ตัวนั้นก่อน
set PY=python
if exist "%USERPROFILE%\hacker\pyembed\python.exe" set PY="%USERPROFILE%\hacker\pyembed\python.exe"
%PY% -c "import numpy, websockets, sounddevice" 2>nul
if errorlevel 1 (
  echo กำลังติดตั้งไลบรารีที่จำเป็น ครั้งแรกครั้งเดียว รอสักครู่...
  %PY% -m pip install numpy websockets sounddevice
)
%PY% "%~dp0helper.py"
pause
