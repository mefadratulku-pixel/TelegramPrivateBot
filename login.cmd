@echo off
chcp 65001 >nul
title Connect Telegram Account - RestrictedContentDL
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" login.py
) else (
    python login.py
)
echo.
pause
