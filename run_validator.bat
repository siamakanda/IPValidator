@echo off
title IP Validator Automation
cls

echo =======================================================
echo     Running Dialer IP Whitelisting Automation
echo =======================================================
echo.

:: Change directory to the folder where this batch file is located
cd /d "%~dp0"

:: Execute the script using your Python path and a relative script path
python validator.py

echo.
echo =======================================================
echo     Process Finished.
echo =======================================================
echo.
pause