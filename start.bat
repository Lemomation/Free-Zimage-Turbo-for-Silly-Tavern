@echo off
title AI Image Bridge Launcher
:menu
cls
echo ========================================
echo       AI IMAGE BRIDGE LAUNCHER
echo ========================================
echo.
echo  [1] Start ZImage Bridge (Port 8001) - Faster/Recommended
echo  [2] Start RedPanda Bridge (Port 8000)
echo  [3] Exit
echo.
echo ========================================
echo  (Auto-choosing [1] in 5 seconds...)
echo.

:: Choice command: /C keys, /T seconds, /D default key
choice /C 123 /T 5 /D 1 /M "Select an option (1-3): "

if errorlevel 3 goto end
if errorlevel 2 goto redpanda
if errorlevel 1 goto zimage
goto menu

:zimage
echo.
echo Starting ZImage Bridge...
python zimage_bridge.py
pause
goto menu

:redpanda
echo.
echo Starting RedPanda Bridge...
python main.py
pause
goto menu

:end
exit
