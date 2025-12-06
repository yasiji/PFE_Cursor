@echo off
REM ========================================
REM   Ngrok Public URL Creator
REM   Share your app with anyone!
REM ========================================

title Ngrok - Public URL

echo.
echo ========================================
echo   Ngrok Public URL Creator
echo   Share your app with anyone!
echo ========================================
echo.

REM Change to script directory
cd /d %~dp0

REM ----------------------------------------
REM Check if ngrok is installed
REM ----------------------------------------
echo [1/3] Checking ngrok installation...
ngrok version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] ngrok is not installed!
    echo.
    echo To install ngrok:
    echo   1. Go to https://ngrok.com/download
    echo   2. Download ngrok for Windows
    echo   3. Extract ngrok.exe to a folder
    echo   4. Add that folder to your PATH
    echo      OR copy ngrok.exe to this project folder
    echo.
    echo   5. Sign up at https://ngrok.com ^(free^)
    echo   6. Run: ngrok config add-authtoken YOUR_TOKEN
    echo.
    pause
    exit /b 1
)
echo [OK] ngrok found

echo.

REM ----------------------------------------
REM Check if services are running
REM ----------------------------------------
echo [2/3] Checking if services are running...

netstat -an | findstr ":3000.*LISTEN" >nul
if errorlevel 1 (
    echo [ERROR] Frontend is not running on port 3000!
    echo [INFO] Please run start_venv.bat first to start all services.
    pause
    exit /b 1
)
echo [OK] Frontend running on port 3000

netstat -an | findstr ":8000.*LISTEN" >nul
if errorlevel 1 (
    echo [WARNING] Backend may not be running on port 8000
) else (
    echo [OK] Backend running on port 8000
)

echo.

REM ----------------------------------------
REM Start ngrok tunnel
REM ----------------------------------------
echo [3/3] Starting ngrok tunnel...
echo.
echo ========================================
echo   IMPORTANT: Keep this window open!
echo   The public URL will appear below.
echo ========================================
echo.
echo Starting tunnel to http://localhost:3000...
echo.

REM Start ngrok and keep the window open
ngrok http 3000

echo.
echo Ngrok tunnel closed.
pause

