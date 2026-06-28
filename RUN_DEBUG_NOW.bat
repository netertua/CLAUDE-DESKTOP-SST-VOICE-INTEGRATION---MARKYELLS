@echo off
title MARKYELLS DEBUG
cd /d "%~dp0"
echo MARKYELLS DEBUG RUN > DEBUG_LAST_RESULT.txt
echo Started: %date% %time% >> DEBUG_LAST_RESULT.txt
echo. >> DEBUG_LAST_RESULT.txt
python -u debug_full.py >> DEBUG_LAST_RESULT.txt 2>&1
echo. >> DEBUG_LAST_RESULT.txt
echo EXIT_CODE=%ERRORLEVEL% >> DEBUG_LAST_RESULT.txt
echo. >> DEBUG_LAST_RESULT.txt
echo === GUI LAUNCH PROBE === >> DEBUG_LAST_RESULT.txt
python -u _debug_gui_probe.py >> DEBUG_LAST_RESULT.txt 2>&1
echo GUI_PROBE_EXIT=%ERRORLEVEL% >> DEBUG_LAST_RESULT.txt
notepad DEBUG_LAST_RESULT.txt