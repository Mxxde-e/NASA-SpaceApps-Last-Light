@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run Setup-Last-Light.ps1 once before starting the app.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m backend.launch
pause
