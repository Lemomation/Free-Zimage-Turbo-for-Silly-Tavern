@echo off
title Lemon Image API
cd /d "%~dp0"

echo.
echo                 .-''''-.
echo               .'  .--.  '.
echo              /   /    \   \
echo             ^|   ^|  ()  ^|   ^|
echo              \   \    /   /
echo               '.  '--'  .'
echo                 '-.____.-'
echo.
echo              LEMON IMAGE API
echo       All providers at http://127.0.0.1:8000
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Please run start_lemon_api.bat once to create the environment.
    pause
    exit /b 1
)

.venv\Scripts\python.exe lemon_image_api.py
pause
