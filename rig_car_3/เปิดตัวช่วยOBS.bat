@echo off
title PhumaPanther Helper
python -c "import numpy, websockets, sounddevice" 2>nul
if errorlevel 1 (
  echo กำลังติดตั้งไลบรารีที่จำเป็น ครั้งแรกครั้งเดียว รอสักครู่...
  python -m pip install numpy websockets sounddevice
)
python "%~dp0helper.py"
pause
