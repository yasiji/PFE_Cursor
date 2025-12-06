@echo off
REM ========================================
REM   Store Manager Platform - VENV Starter
REM   Creates/uses venv "PFE" and starts app
REM ========================================

title Store Manager Platform - VENV Setup

echo.
echo ========================================
echo   Store Manager Platform (VENV)
echo   Creating/Using venv "PFE" and starting
echo ========================================
echo.

REM Change to script directory (project root)
cd /d %~dp0

REM ----------------------------------------
REM Step 1: Check Python
REM ----------------------------------------
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] Python %PYTHON_VERSION%
)

echo.

REM ----------------------------------------
REM Step 2: Create venv "PFE" if needed
REM ----------------------------------------
echo [2/4] Ensuring virtual environment "PFE" exists...
if exist "PFE\Scripts\activate.bat" (
    echo [OK] Existing venv found at .\PFE
) else (
    echo [INFO] Creating new virtual environment "PFE"...
    python -m venv PFE
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment "PFE".
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

echo.

REM ----------------------------------------
REM Step 3: Activate venv and install deps
REM ----------------------------------------
echo [3/4] Activating venv and installing dependencies...

call ".\PFE\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Upgrade pip quietly (optional but helpful)
python -m pip install --upgrade pip >nul 2>&1

echo [INFO] Installing Python dependencies from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    echo Make sure you have internet access and try again.
    pause
    exit /b 1
)
echo [OK] Python dependencies installed.

echo.

REM ----------------------------------------
REM Step 4: Delegate to main startup script
REM ----------------------------------------
echo [4/4] Starting platform using start.bat inside venv...
call start.bat

echo.
echo NOTE: You are currently inside the \"PFE\" virtual environment in this window.
echo       When you are done, you can close all opened CMD windows to stop services.
echo.

pause







