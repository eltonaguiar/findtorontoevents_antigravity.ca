@echo off
echo ==========================================
echo   PREDICTION TRACKER WITH ALERTS
echo ==========================================
echo.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "alert_system.ps1"
echo.
echo ==========================================
echo   Press any key to close
echo ==========================================
pause >nul
