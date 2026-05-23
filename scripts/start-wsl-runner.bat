@echo off
:: Start WSL GitHub Actions Runner
:: Usage: scripts\start-wsl-runner.bat [background]

echo ============================================
echo   WSL GitHub Actions Runner Manager
echo ============================================
echo.

:: Check if WSL is available
wsl -l -v >nul 2>&1
if errorlevel 1 (
    echo ERROR: WSL is not installed or not available
    echo Please install WSL first: wsl --install
    exit /b 1
)

:: Check if UbuntuRecovered distribution exists
wsl -l -v | findstr "UbuntuRecovered" >nul
if errorlevel 1 (
    echo ERROR: UbuntuRecovered distribution not found
    echo Available distributions:
    wsl -l -v
    exit /b 1
)

echo Distribution: UbuntuRecovered
echo Runner User: runner
echo Runner Dir: /home/runner/actions-runner
echo.

:: Check if runner is already running
echo Checking runner status...
wsl -d UbuntuRecovered -- bash -c "ps aux | grep -v grep | grep run.sh" >nul 2>&1
if not errorlevel 1 (
    echo.
    echo [INFO] Runner is already RUNNING
    echo.
    choice /C YN /M "Do you want to restart it"
    if errorlevel 2 goto :eof
    if errorlevel 1 (
        echo Stopping runner...
        wsl -d UbuntuRecovered -- bash -c "pkill -f 'run.sh'" 2>nul
        timeout /t 2 >nul
    )
)

:: Start the runner
echo.
echo Starting WSL runner...
echo.

if "%~1"=="background" (
    echo [Mode] Background (detached)
    wsl -d UbuntuRecovered -- bash -c "su - runner -c 'cd /home/runner/actions-runner && nohup ./run.sh > runner.log 2>&1 &'"
    timeout /t 2 >nul
    
    :: Verify it started
    wsl -d UbuntuRecovered -- bash -c "ps aux | grep -v grep | grep run.sh" >nul 2>&1
    if not errorlevel 1 (
        echo.
        echo [SUCCESS] Runner started in background
        echo To view logs: wsl -d UbuntuRecovered -- tail -f /home/runner/actions-runner/runner.log
    ) else (
        echo [ERROR] Failed to start runner
    )
) else (
    echo [Mode] Foreground (Ctrl+C to stop)
    echo.
    wsl -d UbuntuRecovered -- bash -c "su - runner -c 'cd /home/runner/actions-runner && ./run.sh'"
)

echo.
pause
