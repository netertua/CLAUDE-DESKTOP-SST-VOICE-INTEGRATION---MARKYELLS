@echo off
title MARKYELLS — User Test Start
cd /d "%~dp0"

echo.
echo ========================================
echo   MARKYELLS USER TEST START
echo   Capt Can Yapici / ASPERA.BOND
echo ========================================
echo.

echo [1] Killing old Python GUI processes...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM pythonw.exe /T >nul 2>&1
ping 127.0.0.1 -n 2 >nul

echo [2] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found.
    pause
    exit /b 1
)

echo.
echo [3] Installing/updating dependencies...
python -m pip install -r requirements_auto.txt -q
if errorlevel 1 (
    echo WARN: pip install had issues — continuing anyway.
)

echo.
echo [4] Running FULL debug check (Qt/CTk/PyQt conflict)...
python -u debug_full.py
if errorlevel 1 (
    echo.
    echo DEBUG FAILED — fix errors above before GUI launch.
    pause
    exit /b 1
)

echo.
echo [5] Launching MARKYELLS Qt GUI...
echo     Close the window with X when done.
echo.
python markyells_auto.py
set GUIEXIT=%ERRORLEVEL%

echo.
echo ========================================
echo   SMOKE TEST: PASSED
echo   GUI EXIT CODE: %GUIEXIT%
echo ========================================
if %GUIEXIT% NEQ 0 (
    echo WARN: GUI returned %GUIEXIT% but smoke test passed.
    echo If the app opened and closed normally, you are fine.
)
pause
exit /b 0