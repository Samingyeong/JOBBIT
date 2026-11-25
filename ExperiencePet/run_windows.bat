@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo [Experience Pet] Python environment not ready. Run install_windows.bat first.
  pause
  exit /b 1
)
start "ExperiencePet" ".venv\Scripts\pythonw.exe" "app\main.py" --open-notes
