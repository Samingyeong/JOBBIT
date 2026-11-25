@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3 install_chatgpt_plugin_windows.py
pause
