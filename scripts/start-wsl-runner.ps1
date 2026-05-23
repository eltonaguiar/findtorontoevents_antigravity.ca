# Start WSL GitHub Actions Runner
# Usage: .\scripts\start-wsl-runner.ps1

param(
    [switch]$Background,
    [switch]$Status
)

$WSL_DISTRO = "UbuntuRecovered"
$RUNNER_DIR = "/home/runner/actions-runner"
$RUNNER_USER = "runner"

function Get-RunnerStatus {
    $processes = wsl -d $WSL_DISTRO -- bash -c "ps aux | grep -v grep | grep run.sh" 2>$null
    if ($processes) {
        Write-Host "✅ WSL Runner is RUNNING" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ WSL Runner is NOT RUNNING" -ForegroundColor Red
        return $false
    }
}

function Start-Runner {
    Write-Host "Starting WSL GitHub Actions Runner..." -ForegroundColor Cyan
    Write-Host "Distribution: $WSL_DISTRO" -ForegroundColor Gray
    Write-Host "User: $RUNNER_USER" -ForegroundColor Gray
    Write-Host "Directory: $RUNNER_DIR" -ForegroundColor Gray
    Write-Host ""

    if ($Background) {
        # Start in background with nohup
        wsl -d $WSL_DISTRO -- bash -c "su - $RUNNER_USER -c 'cd $RUNNER_DIR && nohup ./run.sh > runner.log 2>&1 &'"
        Write-Host "✅ Runner started in background" -ForegroundColor Green
        Start-Sleep -Seconds 2
        Get-RunnerStatus
    } else {
        # Start in foreground (blocks until Ctrl+C)
        Write-Host "Starting in foreground mode (Ctrl+C to stop)..." -ForegroundColor Yellow
        wsl -d $WSL_DISTRO -- bash -c "su - $RUNNER_USER -c 'cd $RUNNER_DIR && ./run.sh'"
    }
}

function Stop-Runner {
    Write-Host "Stopping WSL Runner..." -ForegroundColor Yellow
    wsl -d $WSL_DISTRO -- bash -c "pkill -f 'run.sh'" 2>$null
    Start-Sleep -Seconds 2
    Get-RunnerStatus
}

# Main execution
if ($Status) {
    Get-RunnerStatus
    exit
}

# Check if already running
$isRunning = Get-RunnerStatus
if ($isRunning) {
    Write-Host ""
    $response = Read-Host "Runner is already running. Restart? (y/N)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Stop-Runner
        Start-Runner
    }
} else {
    Start-Runner
}
