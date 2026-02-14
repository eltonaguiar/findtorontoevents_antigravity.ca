# Setup Scheduled Task for Prediction Tracking
# Run this as Administrator to create automatic tracking every 2 hours

$taskName = "CryptoPredictionTracker"
$scriptPath = "$PSScriptRoot\alert_system.ps1"
$description = "Tracks crypto predictions every 2 hours with alerts"

Write-Host "Setting up scheduled task: $taskName" -ForegroundColor Cyan
Write-Host "Script path: $scriptPath" -ForegroundColor Gray

# Create action
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$scriptPath`""

# Create trigger - every 2 hours
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours 2)

# Create settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Check if task exists and remove
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Register task
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description $description -RunLevel Highest
    Write-Host "SUCCESS: Task '$taskName' created!" -ForegroundColor Green
    Write-Host ""
    Write-Host "The tracker will run every 2 hours and check:" -ForegroundColor White
    Write-Host "  - 50% milestone alerts (yellow)" -ForegroundColor Yellow
    Write-Host "  - 80% approaching target alerts (cyan)" -ForegroundColor Cyan
    Write-Host "  - WIN alerts when target hit (green)" -ForegroundColor Green
    Write-Host "  - LOSS alerts when stop loss hit (red)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check 'alerts_log.txt' for all alerts" -ForegroundColor Gray
} catch {
    Write-Host "ERROR: Failed to create task. Run as Administrator." -ForegroundColor Red
    Write-Host $_.Exception.Message
}
