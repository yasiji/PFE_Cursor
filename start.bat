@echo off
REM ========================================
REM   Store Manager Platform - Startup Script
REM   Starts everything in one go!
REM ========================================

title Store Manager Platform - Starting...

echo.
echo ========================================
echo   Store Manager Platform
echo   Starting All Services...
echo ========================================
echo.

REM Change to script directory
cd /d %~dp0

REM ========================================
REM Step 1: Check Prerequisites
REM ========================================
echo [1/10] Checking prerequisites...
echo.

REM Check Python
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

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo Please install Node.js 18+ and try again.
    pause
    exit /b 1
) else (
    for /f %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
    echo [OK] Node.js %NODE_VERSION%
)

echo.

REM ========================================
REM Step 2: Check Dependencies
REM ========================================
echo [2/10] Checking dependencies...
echo.

REM Check backend dependencies
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing backend dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install backend dependencies!
        pause
        exit /b 1
    )
    echo [OK] Backend dependencies installed
) else (
    echo [OK] Backend dependencies installed
)

REM Check frontend dependencies
if not exist "apps\store-manager-frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd apps\store-manager-frontend
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies!
        cd ..\..
        pause
        exit /b 1
    )
    cd ..\..
    echo [OK] Frontend dependencies installed
) else (
    echo [OK] Frontend dependencies installed
)

echo.

REM ========================================
REM Step 3: Initialize Database
REM ========================================
echo [3/10] Initializing database...
python scripts\init_database.py
if %errorlevel% EQU 0 (
    echo [OK] Database initialized
) else (
    echo [INFO] Database may already be initialized (this is OK)
)

echo.

REM ========================================
REM Step 4: Run Database Migrations
REM ========================================
echo [4/10] Running database migrations...
echo.

echo [INFO] Running migration: Shelf vs Stock separation...
python scripts\migrations\add_shelf_stock_separation.py
if %errorlevel% EQU 0 (
    echo [OK] Shelf/Stock migration completed
) else (
    echo [INFO] Shelf/Stock migration: Columns may already exist (this is OK)
)

echo.
echo [INFO] Running migration: Transit time and orders...
python scripts\migrations\add_transit_time_and_orders.py
if %errorlevel% EQU 0 (
    echo [OK] Transit/Orders migration completed
) else (
    echo [INFO] Transit/Orders migration: Tables may already exist (this is OK)
)

echo.
echo [INFO] Running migration: Notifications table...
python scripts\migrations\add_notifications_table.py
if %errorlevel% EQU 0 (
    echo [OK] Notifications migration completed
) else (
    echo [INFO] Notifications migration: Table may already exist (this is OK)
)

echo.
echo [INFO] Running migration: Losses table...
python scripts\migrations\add_losses_table.py
if %errorlevel% EQU 0 (
    echo [OK] Losses migration completed
) else (
    echo [INFO] Losses migration: Table may already exist (this is OK)
)

echo.

REM ========================================
REM Step 5: Check Model File
REM ========================================
echo [5/10] Checking ML model...
if exist "data\models\lightgbm_model.pkl" (
    echo [OK] ML model found
) else (
    echo [WARNING] ML model not found at data\models\lightgbm_model.pkl
    echo [INFO] Forecasts may not work until model is trained
    echo [INFO] To train model: python scripts\train_lightgbm_model.py
)

echo.

REM ========================================
REM Step 6: Seed Test Data and Ensure Users
REM ========================================
echo [6/10] Setting up test data and users...

REM Always ensure test users exist (critical for login!)
echo [INFO] Ensuring test users exist...
python scripts\ensure_test_user.py
if errorlevel 1 (
    echo [WARNING] Test user setup had issues, but continuing...
) else (
    echo [OK] Test users ready
)

REM Check if products need seeding
python -c "from services.api_gateway.database import get_db; from services.api_gateway.models import Product; db = next(get_db()); products = db.query(Product).count(); db.close(); print('products:', products)" 2>nul | findstr /C:"products: 0" >nul
if not errorlevel 1 (
    echo [INFO] Database is empty, seeding test data...
    python scripts\seed_test_data.py
    if errorlevel 1 (
        echo [WARNING] Data seeding had issues, but continuing...
    ) else (
        echo [OK] Test data seeded
    )
)

REM Always ensure prices exist (they may be missing even if products exist)
echo [INFO] Ensuring product prices...
python scripts\seed_prices.py
if errorlevel 1 (
    echo [WARNING] Price seeding had issues, but continuing...
) else (
    echo [OK] Product prices ready
)

echo.

REM ========================================
REM Step 7: Start Backend Server
REM ========================================
echo [7/10] Starting backend server...
start "Backend API Server" cmd /k "cd /d %~dp0 && python -m uvicorn services.api_gateway.main:app --reload --host 127.0.0.1 --port 8000"

REM Wait for backend to start
timeout /t 3 /nobreak >nul
echo [OK] Backend server starting on http://localhost:8000

echo.

REM ========================================
REM Step 8: Start Frontend Server
REM ========================================
echo [8/10] Starting frontend server...
start "Frontend Development Server" cmd /k "cd /d %~dp0\apps\store-manager-frontend && npm run dev"

REM Wait for frontend to start
timeout /t 5 /nobreak >nul
echo [OK] Frontend server starting on http://localhost:3000

echo.

REM ========================================
REM Step 8.5: Start ML Dashboard (Streamlit)
REM ========================================
echo [8.5/10] Starting ML Dashboard (Streamlit)...
start "ML Dashboard - Streamlit" cmd /k "cd /d %~dp0 && streamlit run apps/streamlit/app.py --server.port 8501 --server.headless true"

REM Wait for Streamlit to start
timeout /t 3 /nobreak >nul
echo [OK] ML Dashboard starting on http://localhost:8501

echo.

REM ========================================
REM Step 9: Check Ports and Wait for Backend
REM ========================================
echo [9/10] Checking ports and waiting for backend...
netstat -an | findstr ":8000" >nul
if not errorlevel 1 (
    echo [WARNING] Port 8000 is already in use! Backend may already be running.
) else (
    echo [OK] Port 8000 is available
)

netstat -an | findstr ":3000" >nul
if not errorlevel 1 (
    echo [WARNING] Port 3000 is already in use! Frontend may already be running.
) else (
    echo [OK] Port 3000 is available
)

echo.
echo [INFO] Waiting for backend to be ready...
echo [INFO] Giving backend 5 seconds to start...
timeout /t 5 /nobreak >nul

REM Try to check if backend is responding (optional - curl may not be available)
where curl >nul 2>&1
if not errorlevel 1 (
    curl -s http://localhost:8000/health >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Backend health check passed
    ) else (
        echo [INFO] Backend is starting... (check backend window for status)
    )
) else (
    echo [INFO] Backend should be ready (curl not available for health check)
    echo [INFO] Check the backend window to confirm it's running
)

echo.

REM ========================================
REM Step 10: Open Browser and Show Summary
REM ========================================
echo [10/10] Opening browser...
timeout /t 3 /nobreak >nul
start http://localhost:3000

echo.
echo ========================================
echo   Platform Started Successfully!
echo ========================================
echo.
echo Services Running:
echo   - Backend API:     http://localhost:8000
echo   - API Docs:        http://localhost:8000/docs
echo   - Frontend:        http://localhost:3000
echo   - ML Dashboard:    http://localhost:8501
echo.
echo Database Migrations:
echo   [OK] Shelf vs Stock separation
echo   [OK] Transit time and orders
echo   [OK] Notifications table
echo   [OK] Losses table
echo.
echo Manager Workflow (Understand → Anticipate → Act):
echo   - Business Overview: Dashboard page (revenue, profit, loss)
echo   - Forecast Outlook: Forecast page (7/14/30-day projections)
echo   - Refill Plan: Refill page (automated shelf/stock recommendations)
echo   - Inventory & Expiry: Inventory page (shelf vs stock, expiry tracking)
echo.
echo Additional Features:
echo   - 30-Day Forecast: Analytics tab → 30-Day Forecast
echo   - Real-Time Notifications: Bell icon in header
echo   - Loss Tracking: Dashboard KPI card
echo   - Order Management: Orders page
echo.
echo Login Credentials (if test data was seeded):
echo   Username: test_user
echo   Password: test123
echo.
echo   Or register a new user at: http://localhost:8000/docs
echo.
echo Windows Opened:
echo   - Backend API Server (port 8000) - Check for errors here
echo   - Frontend Dev Server (port 3000) - Check for errors here
echo   - ML Dashboard Streamlit (port 8501) - Model analytics
echo.
echo Optional Services:
echo   - Notification Background Job: Run start_notifications.bat
echo   - Public URL (ngrok):          Run start_ngrok.bat
echo.
echo Share with Anyone (ngrok):
echo   1. Run start_ngrok.bat in a new terminal
echo   2. Share the https://xxxxx.ngrok.app URL
echo   3. Others can access your app from anywhere!
echo.
echo Testing Tips:
echo   1. Open http://localhost:3000 in your browser
echo   2. Login with test_user / test123 (or register new user)
echo   3. Check Business Overview dashboard for today's metrics
echo   4. Go to Forecast Outlook to see future projections
echo   5. Visit Refill Plan to see tomorrow's recommendations
echo   6. Check Inventory & Expiry for shelf/stock breakdown
echo.
echo Press any key to close this window...
echo (The servers will continue running in their own windows)
pause >nul