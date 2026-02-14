# Alert System for Prediction Tracking
# Enhanced tracker with alerts at 50% progress and WIN/LOSS triggers

$predictionsFile = "$PSScriptRoot\active_calls_v2.json"
$alertLogFile = "$PSScriptRoot\alerts_log.txt"
$sentAlertsFile = "$PSScriptRoot\sent_alerts.json"

# Load sent alerts tracking
$sentAlerts = @{}
if (Test-Path $sentAlertsFile) {
    $sentAlerts = Get-Content $sentAlertsFile -Raw | ConvertFrom-Json
}

function Send-Alert($type, $prediction, $message, $urgency) {
    $alertKey = "$($prediction.id)_$type"
    
    if ($sentAlerts[$alertKey]) {
        return
    }
    
    $alert = @{
        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Type = $type
        PredictionID = $prediction.id
        Symbol = $prediction.symbol
        Message = $message
        Urgency = $urgency
    }
    
    Add-Content -Path $alertLogFile -Value ($alert | ConvertTo-Json)
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor $urgency
    Write-Host "  *** ALERT: $type ***" -ForegroundColor $urgency
    Write-Host "========================================" -ForegroundColor $urgency
    Write-Host "  Symbol: $($prediction.symbol)" -ForegroundColor White
    Write-Host "  $message" -ForegroundColor White
    Write-Host "  Time: $($alert.Timestamp)" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor $urgency
    Write-Host ""
    
    $sentAlerts[$alertKey] = $true
    $sentAlerts | ConvertTo-Json | Set-Content $sentAlertsFile
}

function Write-Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$timestamp - $msg"
    Add-Content -Path "$PSScriptRoot\tracking_log.txt" -Value $line
    Write-Host $line
}

function Get-CryptoPrices {
    try {
        $url = "https://api.coingecko.com/api/v3/simple/price?ids=popcat,pudgy-penguins,dogecoin,bitcoin&vs_currencies=usd&include_24hr_change=true"
        $response = Invoke-RestMethod -Uri $url -TimeoutSec 15
        return @{
            POPCAT = [decimal]$response.popcat.usd
            PENGU = [decimal]$response.'pudgy-penguins'.usd
            DOGE = [decimal]$response.dogecoin.usd
            BTC = [decimal]$response.bitcoin.usd
        }
    } catch {
        Write-Log "ERROR: Failed to fetch prices"
        return $null
    }
}

function Check-PredictionWithAlerts($pred, $currentPrice) {
    $target = [decimal]$pred.target_price
    $stopLoss = [decimal]$pred.stop_loss
    $entry = [decimal]$pred.current_price
    $prediction = $pred.prediction
    
    $pChange = (($currentPrice - $entry) / $entry) * 100
    $progressToTarget = ($currentPrice - $entry) / ($target - $entry) * 100
    
    $result = @{
        Status = "ACTIVE"
        CurrentPrice = $currentPrice
        PercentChange = [math]::Round($pChange, 2)
        ProgressToTarget = [math]::Round($progressToTarget, 1)
        Notes = ""
    }
    
    $now = Get-Date
    $expiry = [DateTime]::Parse($pred.expires_at)
    $isExpired = $now -gt $expiry
    
    # 50% milestone alert
    if ($progressToTarget -ge 50 -and $progressToTarget -lt 100) {
        $msg = "HALFWAY TO TARGET! Price at $currentPrice (" + $result.PercentChange + " pct) - 50 pct to target of $target"
        Send-Alert "50_PERCENT_MILESTONE" $pred $msg "Yellow"
    }
    
    # 80% approaching target alert
    if ($progressToTarget -ge 80 -and $progressToTarget -lt 100) {
        $msg = "ALMOST AT TARGET! Price at $currentPrice (" + $result.PercentChange + " pct) - 80 pct to target"
        Send-Alert "80_PERCENT_APPROACHING" $pred $msg "Cyan"
    }
    
    if ($prediction -eq "BULLISH") {
        if ($currentPrice -ge $target) {
            $result.Status = "WIN"
            $result.Notes = "TARGET HIT"
            $msg = "WINNER! Target $target reached! Current: $currentPrice (" + $result.PercentChange + " pct)"
            Send-Alert "TARGET_HIT_WIN" $pred $msg "Green"
        } elseif ($currentPrice -le $stopLoss) {
            $result.Status = "LOSS"
            $result.Notes = "STOP LOSS HIT"
            $msg = "STOP LOSS HIT at $stopLoss! Current: $currentPrice (" + $result.PercentChange + " pct)"
            Send-Alert "STOP_LOSS_HIT" $pred $msg "Red"
        } elseif ($isExpired) {
            $result.Status = "EXPIRED"
            $result.Notes = "TIME EXPIRED"
            $msg = "Expired at $currentPrice (" + $result.PercentChange + " pct)"
            Send-Alert "PREDICTION_EXPIRED" $pred $msg "Gray"
        }
    } elseif ($prediction -eq "BEARISH") {
        if ($currentPrice -le $target) {
            $result.Status = "WIN"
            $result.Notes = "TARGET HIT"
            $msg = "WINNER (Short)! Target $target reached! Current: $currentPrice"
            Send-Alert "TARGET_HIT_WIN" $pred $msg "Green"
        } elseif ($currentPrice -ge $stopLoss) {
            $result.Status = "LOSS"
            $result.Notes = "STOP LOSS HIT"
            $msg = "STOP LOSS HIT at $stopLoss! Current: $currentPrice"
            Send-Alert "STOP_LOSS_HIT" $pred $msg "Red"
        } elseif ($isExpired) {
            $result.Status = "EXPIRED"
            $result.Notes = "TIME EXPIRED"
            $msg = "Expired at $currentPrice"
            Send-Alert "PREDICTION_EXPIRED" $pred $msg "Gray"
        }
    }
    
    return $result
}

# Main
Write-Log "=== ALERT SYSTEM TRACK RUN ==="

$prices = Get-CryptoPrices
if (-not $prices) {
    Write-Log "Failed to get prices, exiting"
    exit 1
}

Write-Log "Prices - POPCAT: $($prices.POPCAT) PENGU: $($prices.PENGU) DOGE: $($prices.DOGE) BTC: $($prices.BTC)"

$predictions = Get-Content $predictionsFile -Raw | ConvertFrom-Json
$updatedPredictions = @()
$results = @()

foreach ($pred in $predictions.predictions) {
    $symbol = $pred.symbol
    $currentPrice = $prices[$symbol]
    
    if (-not $currentPrice) {
        Write-Log "Warning: No price for $symbol"
        continue
    }
    
    $check = Check-PredictionWithAlerts $pred $currentPrice
    
    $resultObj = @{
        Symbol = $symbol
        Status = $check.Status
        Current = $currentPrice
        ChangePct = $check.PercentChange
        Progress = $check.ProgressToTarget
    }
    $results += $resultObj
    
    if ($check.Status -ne "ACTIVE") {
        $pred.status = $check.Status
        $pred.final_price = $currentPrice.ToString()
        $pred.percent_change = $check.PercentChange.ToString()
        $pred.result_notes = $check.Notes
        $pred.verified_at = Get-Date -Format "o"
    }
    
    $updatedPredictions += $pred
    
    Write-Log "$symbol | $($check.Status) | Price: $currentPrice | Change: $($check.PercentChange) pct | Progress: $($check.ProgressToTarget) pct"
}

$predictions.predictions = $updatedPredictions
$predictions | ConvertTo-Json -Depth 10 | Set-Content $predictionsFile

Write-Log "=== TRACK RUN COMPLETE ==="
