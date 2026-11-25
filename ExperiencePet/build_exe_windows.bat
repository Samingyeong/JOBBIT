@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Please run install_windows.bat first.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if %ERRORLEVEL% neq 0 exit /b 1
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if %ERRORLEVEL% neq 0 exit /b 1
".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm --onefile --windowed --name ExperiencePet --icon "app\assets\shinchan_icon.ico" --add-data "app\assets;assets" --hidden-import pystray._win32 "app\main.py"
if %ERRORLEVEL% neq 0 (
 echo EXE build failed.
 pause
 exit /b 1
)
echo.
echo BUILD DONE: dist\ExperiencePet.exe
echo Move ExperiencePet.exe to its final location BEFORE enabling startup.
pause
