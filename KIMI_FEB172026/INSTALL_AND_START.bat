@echo off
chcp 65001 >nul
title KIMI_FEB172026 - Installation
color 0B

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                                                              ║
echo  ║     KIMI_FEB172026 - Installation Wizard                    ║
echo  ║     This will set up the trading system to run              ║
echo  ║     automatically on your computer                          ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

REM Check admin privileges
net session >nul 2>&1
if errorlevel 1 (
    echo [i] Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [✓] Running with administrator privileges
echo.

REM Install Python if not present
python --version >nul 2>&1
if errorlevel 1 (
    echo [i] Python not found. Downloading and installing...
    
    REM Download Python installer
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    
    REM Install Python with PATH and pip
    echo [i] Installing Python (this may take a few minutes)...
    %TEMP%\python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
    
    REM Refresh environment
    call refreshenv.cmd 2>nul || set "PATH=%PATH%;C:\Python311;C:\Python311\Scripts"
)

echo [✓] Python ready

REM Install dependencies
echo [i] Installing required packages...
pip install --upgrade pip
pip install numpy pandas scikit-learn aiohttp fastapi uvicorn requests
if errorlevel 1 (
    echo [ERROR] Failed to install packages
    pause
    exit /b 1
)

echo [✓] All packages installed

REM Create necessary directories
echo [i] Creating directories...
if not exist "KIMI_FEB172026\data" mkdir "KIMI_FEB172026\data"
if not exist "KIMI_FEB172026\logs" mkdir "KIMI_FEB172026\logs"
if not exist "KIMI_FEB172026\config" mkdir "KIMI_FEB172026\config"

echo [✓] Directories created

REM Initialize database
echo [i] Initializing database...
python -c "
import sys
sys.path.insert(0, '.')
from KIMI_FEB172026.sqlite_store import SQLiteStore
store = SQLiteStore()
print('Database initialized')
"

echo [✓] Database ready

REM Create startup shortcut
echo [i] Setting up automatic startup...
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT=%STARTUP_FOLDER%\KIMI_Trader.lnk

powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%CD%\KIMI_FEB172026\START_TRADING.bat'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.IconLocation = '%SystemRoot%\System32\shell32.dll,21'; $Shortcut.Save()"

echo [✓] Auto-start configured

REM Create desktop shortcut
echo [i] Creating desktop shortcut...
set DESKTOP=%USERPROFILE%\Desktop
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\KIMI Trading System.lnk'); $Shortcut.TargetPath = '%CD%\KIMI_FEB172026\START_TRADING.bat'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.IconLocation = '%SystemRoot%\System32\shell32.dll,21'; $Shortcut.Save()"

echo [✓] Desktop shortcut created

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                                                              ║
echo  ║     Installation Complete!                                  ║
echo  ║                                                              ║
echo  ║     The trading system will now:                            ║
echo  ║     • Run automatically when Windows starts                  ║
echo  ║     • Scan markets every 5 minutes                           ║
echo  ║     • Generate BUY signals with TP/SL                        ║
echo  ║     • Self-monitor and validate performance                  ║
echo  ║                                                              ║
echo  ║     Dashboard: http://localhost:8000                        ║
echo  ║     Logs: KIMI_FEB172026\logs\                              ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

set /p START_NOW="Start trading system now? (Y/N): "
if /i "%START_NOW%"=="Y" (
    echo.
    echo Starting KIMI_FEB172026...
    start "" "KIMI_FEB172026\START_TRADING.bat"
)

echo.
echo [✓] Setup complete! The system will start automatically on next boot.
pause
