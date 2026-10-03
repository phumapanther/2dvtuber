@echo off
title Vowel Setup - PhumaPanther
rem ร้อง อา เอ อี โอ อู ให้ตัวช่วยจำเสียงสระของเราเอง → vowels.json (ตัวช่วยที่เปิดอยู่ใช้ค่าใหม่ทันที)
set PY=python
if exist "%USERPROFILE%\hacker\pyembed\python.exe" set PY="%USERPROFILE%\hacker\pyembed\python.exe"
%PY% "%~dp0helper.py" --calibrate
pause
