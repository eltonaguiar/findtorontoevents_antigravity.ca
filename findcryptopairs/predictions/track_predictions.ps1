# Prediction Tracker - Automated Price Monitoring
# Run every 2-4 hours to check prediction status

$predictionsFile = "$PSScriptRoot\active_calls_v2.json"
$historyFile = "$PSScriptRoot\prediction_history.json"
$logFile = "$PSScriptRoot\tracking_log.txt"

function Write-Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$timestamp - $msg"
    Add-Content -Path $logFile -Value $line
    Write-Host $line
}

function Get-CryptoPrices {
    try {
        $url = "https://api.coingecko.com/api/v3/simple/price?ids=popcat,pudgy-penguins,dogecoin,bitcoin&vs_currencies=usd&include_24hr_change=true"
        $response = Invoke-RestMethod -Uri $url -TimeoutSec 15
        $prices = @{
            POPCAT = [decimal]$response.popcat.usd
            PENGU = [decimal]$response.'pudgy-penguins'.usd
            DOGE = [decimal]$response.dogecoin.usd
            BTC = [decimal]$response.bitcoin.usd
        }
        return $prices
    } catch {
        Write-Log "ERROR: Failed to fetch prices"
        return $null
    }
}

function Check-Prediction($pred, $currentPrice) {
    $target = [decimal]$pred.target_price
    $stopLoss = [decimal]$pred.stop_loss
    $entry = [decimal]$pred.current_price
    $prediction = $pred.prediction
    
    $pChange = (($currentPrice - $entry) / $entry) * 100
    $result = @{
        Status = "ACTIVE"
        CurrentPrice = $currentPrice
        PercentChange = [math]::Round($pChange, 2)
        Notes = ""
    }
    
    $now = Get-Date
    $expiry = [DateTime]::Parse($pred.expires_at)
    $isExpired = $now -gt $expiry
    
    if ($prediction -eq "BULLISH") {
        if ($currentPrice -ge $target) {
            $result.Status = "WIN"
            $result.Notes = "TARGET HIT"
        } elseif ($currentPrice -le $stopLoss) {
            $result.Status = "LOSS"
            $result.Notes = "STOP LOSS HIT"
        } elseif ($isExpired) {
            $result.Status = "EXPIRED"
            $result.Notes = "TIME EXPIRED"
        }
    } elseif ($prediction -eq "BEARISH") {
        if ($currentPrice -le $target) {
            $result.Status = "WIN"
            $result.Notes = "TARGET HIT"
        } elseif ($currentPrice -ge $stopLoss) {
            $result.Status = "LOSS"
            $result.Notes = "STOP LOSS HIT"
        } elseif ($isExpired) {
            $result.Status = "EXPIRED"
            $result.Notes = "TIME EXPIRED"
        }
    }
    
    return $result
}

# Main
Write-Log "=== Starting Prediction Track Run ==="

$prices = Get-CryptoPrices
if (-not $prices) {
    Write-Log "Failed to get prices, exiting"
    exit 1
}

$popcatPrice = $prices.POPCAT
$penguPrice = $prices.PENGU
$dogePrice = $prices.DOGE
$btcPrice = $prices.BTC

Write-Log "Prices - POPCAT: $popcatPrice PENGU: $penguPrice DOGE: $dogePrice BTC: $btcPrice"

# Load predictions
$jsonContent = Get-Content $predictionsFile -Raw
$predictions = $jsonContent | ConvertFrom-Json
$updatedPredictions = @()
$results = @()

foreach ($pred in $predictions.predictions) {
    $symbol = $pred.symbol
    $currentPrice = $prices[$symbol]
    
    if (-not $currentPrice) {
        Write-Log "Warning: No price data for $symbol"
        continue
    }
    
    $check = Check-Prediction $pred $currentPrice
    
    $resultObj = @{
        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        ID = $pred.id
        Symbol = $symbol
        Entry = $pred.current_price
        Target = $pred.target_price
        Current = $currentPrice
        ChangePct = $check.PercentChange
        Status = $check.Status
        Notes = $check.Notes
    }
    $results += $resultObj
    
    if ($check.Status -ne "ACTIVE") {
        $pred.status = $check.Status
        $pred.final_price = $currentPrice.ToString()
        $pred.percent_change = $check.PercentChange.ToString()
        $pred.result_notes = $check.Notes
        $pred.verified_at = Get-Date -Format "o"
        Write-Log "RESOLVED: $($pred.id) - $($check.Status) - $($check.Notes)"
    } else {
        $progressToTarget = ($currentPrice - $pred.current_price) / ($pred.target_price - $pred.current_price) * 100
        $progress = [math]::Round([math]::Abs($progressToTarget), 1)
        Write-Log "ACTIVE: $($pred.id) - Price: $currentPrice - Change: $($check.PercentChange)% - Progress: $progress%"
    }
    
    $updatedPredictions += $pred
}

# Save updated predictions
$predictions.predictions = $updatedPredictions
$newJson = $predictions | ConvertTo-Json -Depth 10
$newJson | Set-Content $predictionsFile

# Save history
$historyEntry = @{
    CheckTime = Get-Date -Format "o"
    Results = $results
}

$history = @()
if (Test-Path $historyFile) {
    $existingHistory = Get-Content $historyFile -Raw
    if ($existingHistory) {
        $history = $existingHistory | ConvertFrom-Json
    }
}
$history += $historyEntry
$historyJson = $history | ConvertTo-Json -Depth 10
$historyJson | Set-Content $historyFile

Write-Log "=== CURRENT STATUS ==="
foreach ($r in $results) {
    $statusLine = $r.Symbol + ": " + $r.Status + " | Current: " + $r.Current + " | Change: " + $r.ChangePct + "%"
    Write-Log $statusLine
}
Write-Log "=== Track Run Complete ==="
