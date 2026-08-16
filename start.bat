@echo off
title AI Image Bridge Launcher

:: Set current directory to script directory
cd /d "%~dp0"

:: -------------------------------------------------------------
:: Environment Setup
:: -------------------------------------------------------------

:: 1. Detect a working Python installation
::    IMPORTANT: Try 'py -3' FIRST. On Windows, bare 'python' in PATH can
::    resolve to an unrelated virtual environment (e.g. hermes-agent\venv)
::    that lacks this project's dependencies. The Windows Python Launcher
::    ('py') always finds the real system Python, ignoring venvs in PATH.
set "SYS_PYTHON="
set "_PYTMP=%TEMP%\_aibridgepy.tmp"

:: Try the Windows Python Launcher first (most reliable)
py -3 -c "import sys; print(sys.executable)" > "%_PYTMP%" 2>nul
if not errorlevel 1 (
    set /p SYS_PYTHON=<"%_PYTMP%"
    goto :python_found
)

:: Fall back to python in PATH
python -c "import sys; print(sys.executable)" > "%_PYTMP%" 2>nul
if not errorlevel 1 (
    set /p SYS_PYTHON=<"%_PYTMP%"
    goto :python_found
)

:: No Python found - show error and exit
del "%_PYTMP%" 2>nul
echo ============================================================
echo ERROR: Python is not installed or not in your system PATH.
echo ============================================================
echo.
echo Please download and install Python 3.10+ from:
echo https://www.python.org/downloads/
echo.
echo IMPORTANT: Make sure to check the box:
echo "[x] Add Python.exe to PATH" (or "Add Python to PATH")
echo during the installation setup.
echo.
pause
exit /b 1

:python_found
del "%_PYTMP%" 2>nul
echo [INFO] Found Python: %SYS_PYTHON%

:: 2. Setup/Detect Virtual Environment
set "PYTHON_EXE=.venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" goto :venv_ready

echo [SETUP] Creating Python Virtual Environment (.venv)...
"%SYS_PYTHON%" -m venv .venv
if not errorlevel 1 goto :venv_created_ok
echo [ERROR] Failed to create virtual environment.
pause
exit /b 1

:venv_created_ok
echo [SETUP] Virtual environment created successfully.

:venv_ready
:: 3. Verify/Install Requirements
"%PYTHON_EXE%" -c "import fastapi, uvicorn, playwright, dotenv, httpx" >nul 2>&1
if not errorlevel 1 goto :deps_ready

echo [SETUP] Installing required Python libraries...
"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install -r requirements.txt
if not errorlevel 1 goto :deps_installed_ok
echo [ERROR] Failed to install dependencies.
pause
exit /b 1

:deps_installed_ok
echo [SETUP] Dependencies installed successfully.

:deps_ready
:: 4. Verify Browser availability
> "%TEMP%\_browsercheck.py" echo import sys
>> "%TEMP%\_browsercheck.py" echo from bridge_utils import find_browser_executable
>> "%TEMP%\_browsercheck.py" echo sys.exit^(0 if find_browser_executable^(^) else 1^)
"%PYTHON_EXE%" "%TEMP%\_browsercheck.py" >nul 2>&1
set "_BROWSER_ERR=%errorlevel%"
del "%TEMP%\_browsercheck.py" 2>nul
if "%_BROWSER_ERR%"=="0" goto :browser_ready

echo [SETUP] No compatible local browser (Chrome/Edge) found.
echo [SETUP] Downloading Playwright Chromium binary...
"%PYTHON_EXE%" -m playwright install chromium
if not errorlevel 1 goto :browser_ready
echo [ERROR] Failed to install Playwright browser.
pause
exit /b 1

:browser_ready
:: -------------------------------------------------------------
:: Main Menu
:: -------------------------------------------------------------
:menu
cls
echo ========================================
echo       AI IMAGE BRIDGE LAUNCHER
echo ========================================
echo.
echo  [1] Start FreeGen Bridge (Port 8002) - FASTEST / UNLIMITED
echo  [2] Start EzMaker Bridge (Port 8004) - UNLIMITED & NO SIGN-UP
echo  [3] Start ZImage Bridge (Port 8001)
echo  [4] Start RedPanda Bridge (Port 8000)
echo  [5] Start Bing Bridge (Port 8003) - DALL-E 3 (Requires Login)
echo  [6] Exit
echo.
echo ========================================
echo  (Auto-choosing [1] in 5 seconds...)
echo.

:: Choice command: /C keys, /T seconds, /D default key
choice /C 123456 /T 5 /D 1 /M "Select an option (1-6): "

if errorlevel 6 goto end
if errorlevel 5 goto bing
if errorlevel 4 goto redpanda
if errorlevel 3 goto zimage
if errorlevel 2 goto ezmaker
if errorlevel 1 goto freegen
goto menu

:freegen
echo.
echo Starting FreeGen Bridge...
"%PYTHON_EXE%" freegen_bridge.py
pause
goto menu

:ezmaker
echo.
echo Starting EzMaker Bridge...
"%PYTHON_EXE%" ezmaker_bridge.py
pause
goto menu

:zimage
echo.
echo Starting ZImage Bridge...
"%PYTHON_EXE%" zimage_bridge.py
pause
goto menu

:redpanda
echo.
echo Starting RedPanda Bridge...
"%PYTHON_EXE%" main.py
pause
goto menu

:bing
echo.
echo Starting Bing Bridge...
"%PYTHON_EXE%" bing_bridge.py
pause
goto menu

:end
exit
