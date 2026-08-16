@echo off
setlocal
title Lemon Image API Launcher
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

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
set "LEMON_URL=http://127.0.0.1:8000"

if exist "%PYTHON_EXE%" goto dependencies
echo [SETUP] Creating the Python virtual environment...
py -3 -m venv .venv
if errorlevel 1 goto no_python

:dependencies
"%PYTHON_EXE%" -c "import fastapi, uvicorn, playwright, httpx" >nul 2>&1
if not errorlevel 1 goto health_check
echo [SETUP] Installing required Python packages...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 goto dependency_error

:health_check
powershell.exe -NoProfile -Command "try { Invoke-RestMethod '%LEMON_URL%/health' -TimeoutSec 1; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto ready

echo [START] Launching Lemon Image API...
powershell.exe -NoProfile -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'lemon_image_api_freegen_fixed.py' -WorkingDirectory '%CD%' -WindowStyle Minimized"
if errorlevel 1 goto startup_error

echo [WAIT] Waiting for the server to become ready...
set /a ATTEMPTS=0

:wait_loop
set /a ATTEMPTS+=1
powershell.exe -NoProfile -Command "try { Invoke-RestMethod '%LEMON_URL%/health' -TimeoutSec 1; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto ready
if %ATTEMPTS% GEQ 30 goto startup_error
ping 127.0.0.1 -n 2 >nul
goto wait_loop

:ready
echo [READY] Lemon Image API is running.
echo [OPEN] Opening %LEMON_URL% in your default browser...
start "" "%LEMON_URL%"
exit /b 0

:no_python
echo [ERROR] Python 3 was not found. Install Python 3.10 or newer.
pause
exit /b 1

:dependency_error
echo [ERROR] Could not install the required Python packages.
pause
exit /b 1

:startup_error
echo [ERROR] Lemon Image API did not start within 30 seconds.
pause
exit /b 1
