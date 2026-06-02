@echo off
title IP Validator Automation
cls

echo =======================================================
echo     Checking Dependencies ^& Running Automation
echo =======================================================
echo.

:: Change directory to the folder where this batch file is located
cd /d "%~dp0"

:: Automatically install or verify requirements silently
echo [*] Verifying Python dependencies...
python -m pip install -q -r requirements.txt

echo [*] Launching validator...
echo.
python validator.py

echo.
echo =======================================================
echo     Process Finished.
echo =======================================================
echo.
pause