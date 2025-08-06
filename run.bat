@echo off
title LineBackupToDiscord
cd /d %~dp0

REM Check if the virtual environment exists
if not exist .venv (
    echo Virtual environment not found. Starting setup...

    REM Check if uv is installed
    where uv >nul 2>nul
    if %errorlevel% equ 0 (
        echo Found uv! Using uv for setup...
        uv sync
        if errorlevel 1 (
            echo Failed to sync with uv
            pause
            exit /b 1
        )
    ) else (
        echo uv not found, falling back to traditional setup...
        echo Creating virtual environment...
        python -m venv .venv
        if errorlevel 1 (
            echo Failed to create virtual environment
            pause
            exit /b 1
        )
        echo Activating virtual environment...
        call .venv\Scripts\activate
        if errorlevel 1 (
            echo Failed to activate virtual environment
            pause
            exit /b 1
        )
        echo Installing requirements...
        pip install -r requirements.txt
        if errorlevel 1 (
            echo Failed to install requirements
            pause
            exit /b 1
        )
    )
    echo Setup completed successfully!
)

REM Run the application
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