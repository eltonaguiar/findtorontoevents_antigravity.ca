# Rapid Strategy Validation Engine - Deployment Script
# Run this in PowerShell to set up RSVE

Write-Host "🚀 Rapid Strategy Validation Engine Deployment" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running from correct directory
if (-not (Test-Path "api/rapid_signal_engine.php")) {
    Write-Host "❌ Error: Please run this script from the rapid-validator directory" -ForegroundColor Red
    exit 1
}

# Create data directory if not exists
$dataDir = "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    Write-Host "✅ Created data directory" -ForegroundColor Green
}

# Initialize data files
Write-Host "📁 Initializing data files..." -ForegroundColor Yellow

data_files = @{
    "active_signals.json" = '{"signals":[]}'
    "signal_outcomes.json" = '{"outcomes":[]}'
    "evaluation_state.json" = '{}'
    "elimination_log.json" = '[]'
    "promotion_log.json" = '[]'
    "generation_log.txt" = ""
}

foreach ($file in $data_files.GetEnumerator()) {
    $path = Join-Path $dataDir $file.Key
    if (-not (Test-Path $path)) {
        $file.Value | Out-File -FilePath $path -Encoding UTF8
        Write-Host "  Created: $($file.Key)" -ForegroundColor Gray
    }
}

Write-Host "✅ Data files initialized" -ForegroundColor Green
Write-Host ""

# Test API endpoints
Write-Host "🧪 Testing API endpoints..." -ForegroundColor Yellow

$endpoints = @(
    "api/rapid_signal_engine.php?action=stats",
    "api/auto_eliminator.php?action=evaluate"
)

foreach ($endpoint in $endpoints) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost/rapid-validator/$endpoint" -Method GET -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✅ $endpoint" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  $endpoint (Status: $($response.StatusCode))" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ❌ $endpoint (Error: $($_.Exception.Message))" -ForegroundColor Red
    }
}

Write-Host ""

# Display next steps
Write-Host "🎯 Next Steps:" -ForegroundColor Cyan
Write-Host "==============" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Access the dashboard:" -ForegroundColor White
Write-Host "   Open: frontend/rapid_dashboard.html" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Set up cron jobs (automated scheduling):" -ForegroundColor White
Write-Host "   Option A - Windows Task Scheduler:" -ForegroundColor Gray
Write-Host "     - Create task to run every 5 minutes" -ForegroundColor Gray
Write-Host "     - Action: curl http://yourdomain/api/rapid_signal_engine.php?action=generate" -ForegroundColor Gray
Write-Host ""
Write-Host "   Option B - GitHub Actions (if using GitHub Pages):" -ForegroundColor Gray
Write-Host "     - See .github/workflows/rsve-automation.yml example" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Monitor first 24 hours:" -ForegroundColor White
Write-Host "   - Expect 100-200 signals generated" -ForegroundColor Gray
Write-Host "   - First eliminations after ~20 trades per strategy" -ForegroundColor Gray
Write-Host "   - First promotions after ~30 trades per strategy" -ForegroundColor Gray
Write-Host ""
Write-Host "4. After 72 hours:" -ForegroundColor White
Write-Host "   - Check Championship Round for top strategies" -ForegroundColor Gray
Write-Host "   - Integrate winners into your live picks page" -ForegroundColor Gray
Write-Host ""

Write-Host "📖 Documentation: RSVE_COMPLETE_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 RSVE is ready! Start compressing months into days." -ForegroundColor Green
