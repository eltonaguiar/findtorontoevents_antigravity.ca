@echo off
chcp 65001 >nul
title KIMI_FEB172026 - Test and Validation
color 0E

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                                                              ║
echo  ║     KIMI_FEB172026 - System Test and Validation             ║
echo  ║     This will verify all components are working             ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

set PASSED=0
set FAILED=0

REM Test 1: Python version
echo [TEST 1] Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Python not found
    set /a FAILED+=1
) else (
    for /f "tokens=*" %%a in ('python --version') do echo   [PASS] %%a
    set /a PASSED+=1
)
echo.

REM Test 2: Dependencies
echo [TEST 2] Checking dependencies...
python -c "import numpy, pandas, sklearn" >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Missing dependencies
    set /a FAILED+=1
) else (
    echo   [PASS] All core dependencies installed
    set /a PASSED+=1
)
echo.

REM Test 3: Module imports
echo [TEST 3] Testing module imports...
python -c "
import sys
sys.path.insert(0, '.')
try:
    from KIMI_FEB172026.crypto_acceleration_engine import CryptoAccelerationEngine
    from KIMI_FEB172026.ml_signal_ranker import MLSignalRanker
    from KIMI_FEB172026.sqlite_store import SQLiteStore
    from KIMI_FEB172026.elimination_engine import EliminationEngine
    print('  [PASS] All modules imported successfully')
    exit(0)
except Exception as e:
    print(f'  [FAIL] Import error: {e}')
    exit(1)
" >nul 2>&1
if errorlevel 1 (
    set /a FAILED+=1
) else (
    set /a PASSED+=1
)
echo.

REM Test 4: Database initialization
echo [TEST 4] Testing database...
python -c "
import sys
sys.path.insert(0, '.')
from KIMI_FEB172026.sqlite_store import SQLiteStore
store = SQLiteStore()
print('  [PASS] Database initialized')
" >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Database error
    set /a FAILED+=1
) else (
    set /a PASSED+=1
)
echo.

REM Test 5: Signal generation
echo [TEST 5] Testing signal generation...
python -c "
import sys
import asyncio
sys.path.insert(0, '.')
from KIMI_FEB172026.crypto_acceleration_engine import CryptoAccelerationEngine

async def test():
    engine = CryptoAccelerationEngine()
    print(f'  [INFO] Monitoring {len(engine.symbols)} symbols')
    print('  [PASS] Signal engine ready')

asyncio.run(test())
" >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Signal engine error
    set /a FAILED+=1
) else (
    set /a PASSED+=1
)
echo.

REM Test 6: ML Ranker
echo [TEST 6] Testing ML ranker...
python -c "
import sys
sys.path.insert(0, '.')
from KIMI_FEB172026.ml_signal_ranker import MLSignalRanker
ranker = MLSignalRanker()
print(f'  [INFO] ML Model trained: {ranker.is_trained}')
print('  [PASS] ML ranker ready')
" >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] ML ranker error
    set /a FAILED+=1
) else (
    set /a PASSED+=1
)
echo.

REM Test 7: Elimination Engine
echo [TEST 7] Testing elimination engine...
python -c "
import sys
sys.path.insert(0, '.')
from KIMI_FEB172026.elimination_engine import EliminationEngine, CHALLENGER_POOL
engine = EliminationEngine()
print(f'  [INFO] Challenger pool: {len(CHALLENGER_POOL)} algorithms')
print('  [PASS] Elimination engine ready')
" >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Elimination engine error
    set /a FAILED+=1
) else (
    set /a PASSED+=1
)
echo.

REM Summary
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║  TEST SUMMARY                                                ║
echo  ╠══════════════════════════════════════════════════════════════╣
echo  ║  PASSED: %PASSED%                                              ║
echo  ║  FAILED: %FAILED%                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

if %FAILED% GTR 0 (
    echo [WARNING] Some tests failed. System may not work correctly.
    echo.
    echo Run INSTALL_AND_START.bat to fix issues.
) else (
    echo [SUCCESS] All tests passed! System is ready.
    echo.
    echo You can now:
    echo   1. Run START_TRADING.bat to start trading
    echo   2. Run monitor_dashboard.py for web dashboard
)

echo.
pause
