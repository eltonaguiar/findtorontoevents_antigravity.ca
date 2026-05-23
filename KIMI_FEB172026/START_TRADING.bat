@echo off
chcp 65001 >nul
title KIMI_FEB172026 - Integrated Trading System
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════════════════╗
echo  ║                                                                      ║
echo  ║     KIMI_FEB172026 - Integrated Trading System v11.0                ║
echo  ║     Signal Generation + Validation + Optimization                    ║
echo  ║                                                                      ║
echo  ╚══════════════════════════════════════════════════════════════════════╝
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

echo [✓] Python found

REM Check dependencies
echo [i] Checking dependencies...
python -c "import numpy, pandas, sklearn, aiohttp" >nul 2>&1
if errorlevel 1 (
    echo [i] Installing dependencies...
    pip install -r KIMI_FEB172026\requirements.txt
)

echo [✓] Dependencies ready

REM Initialize if needed
if not exist "KIMI_FEB172026\data\kimi_trading.db" (
    echo [i] Initializing database...
    python -c "from KIMI_FEB172026.sqlite_store import SQLiteStore; SQLiteStore()"
)

echo.
echo [i] Starting Integrated Trading System...
echo [i] This includes:
echo    - Signal generation (every 5 minutes)
echo    - Live outcome validation (every 4 hours)
echo    - Performance tracking and optimization
echo    - Auto-tuning for crypto and forex (priority assets)
echo.
echo [i] Press Ctrl+C to stop
echo [i] View dashboard at: http://localhost:8000
echo.

python KIMI_FEB172026\integrated_system.py

if errorlevel 1 (
    echo.
    echo [ERROR] System encountered an error
    echo Check logs in KIMI_FEB172026\logs\
    pause
)

echo.
echo [i] Trading system stopped
timeout /t 3 >nul
