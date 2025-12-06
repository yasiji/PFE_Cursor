# Quick Start Guide

## 🚀 One-Command Startup

Simply run:
```bash
start.bat
```

This will automatically:
1. ✅ Check prerequisites (Python, Node.js)
2. ✅ Install dependencies if needed
3. ✅ Initialize database
4. ✅ Run all migrations (safe to run multiple times)
5. ✅ Seed test data if needed
6. ✅ Start backend server (port 8000)
7. ✅ Start frontend server (port 3000)
8. ✅ Open browser

## 📋 What You'll See

The script will show progress for each step. If you see:
- `[OK]` - Step completed successfully
- `[INFO]` - Informational message (usually means "already done")
- `[WARNING]` - Non-critical issue (script continues)

## 🔧 Troubleshooting

### Migrations Show Warnings

If migrations show warnings like "may already be applied", this is **normal and safe**. The migrations are idempotent (safe to run multiple times). They check if columns/tables exist before creating them.

### Database Already Initialized

If you see "Database may already be initialized", that's fine! The script checks if the database exists and only creates it if needed.

### Ports Already in Use

If ports 8000 or 3000 are already in use:
- **Backend (8000)**: Close any other FastAPI/uvicorn processes
- **Frontend (3000)**: Close any other React/Vite dev servers

## 🌐 Access Points

Once started, access:
- **Frontend App**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔐 Default Login

- **Username**: `test_user`
- **Password**: `test123`

## 📝 Optional: Notification Background Job

To enable automatic notification generation, run in a separate terminal:
```bash
start_notifications.bat
```

Or set up a Windows scheduled task to run:
```bash
python scripts\generate_notifications.py
```
every 15 minutes.

## ✨ New Features Available

After startup, you'll have access to:
- **Refill Dashboard** (`/refill`) - See what to refill for tomorrow
- **30-Day Forecast** (Analytics tab) - Financial projections
- **Real-Time Notifications** (Bell icon) - Critical alerts
- **Loss Tracking** (Dashboard) - Waste and expiry monitoring
- **Order Management** (Orders page) - Complete workflow

## 🛑 Stopping Services

To stop the services:
1. Close the backend server window (Ctrl+C)
2. Close the frontend server window (Ctrl+C)
3. Or close both windows manually

---

**That's it!** The platform should now be running. 🎉

