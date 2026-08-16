@echo off
title Unified Local Image Generation API
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Failed to create .venv. Install Python 3.10+ first.
        pause
        exit /b 1
    )
)

.venv\Scripts\python.exe -c "import fastapi, uvicorn, playwright, httpx" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo Starting unified API on http://127.0.0.1:8000
.venv\Scripts\python.exe api_server.py
pause
