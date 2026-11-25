@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo Python launcher not found. Install Python 3.11+ first from python.org.
  pause
  exit /b 1
)
py -3 -m venv .venv
if %ERRORLEVEL% neq 0 (
  echo Failed to create virtual environment.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
  echo Dependency installation failed.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if %ERRORLEVEL% neq 0 (
  echo Tests failed. Please fix before running.
  pause
  exit /b 1
)
call run_windows.bat
