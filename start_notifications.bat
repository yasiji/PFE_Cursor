@echo off
REM ========================================
REM   Notification Background Job
REM   Runs notification generation every 15 minutes
REM ========================================

title Notification Background Job

echo.
echo ========================================
echo   Notification Background Job
echo   Generating notifications every 15 minutes
echo ========================================
echo.

cd /d %~dp0

:loop
echo [%date% %time%] Generating notifications for all stores...
python scripts\generate_notifications.py

if errorlevel 1 (
    echo [ERROR] Notification generation failed!
) else (
    echo [OK] Notifications generated successfully
)

echo.
echo Next run in 15 minutes...
echo Press Ctrl+C to stop
echo.

timeout /t 900 /nobreak >nul
goto loop

