@echo off
title LineBackupToDiscord
cd /d %~dp0

REM Check if uv is installed
where uv >nul 2>nul
if %errorlevel% equ 0 (
    echo Running with uv...
    uv run main.py
) else (
    echo Running with traditional venv...
    call .venv\Scripts\activate
    python main.py
)

pause