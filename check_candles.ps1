# Fetch BTC hourly candles from Binance
Write-Host "=== BTC/USD Hourly Candles (last 24h) ==="
try {
    $r = Invoke-RestMethod -Uri 'https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=24' -TimeoutSec 15
    $maxUp = 0; $maxDown = 0; $maxUpTime = ''; $maxDownTime = ''
    foreach ($k in $r) {
        $t = [DateTimeOffset]::FromUnixTimeMilliseconds($k[0]).ToOffset([TimeSpan]::FromHours(-5)).ToString('MM/dd HH:mm')
        $o = [double]$k[1]; $h = [double]$k[2]; $l = [double]$k[3]; $c = [double]$k[4]
        $ch = [math]::Round(($c - $o) / $o * 100, 3)
        $range = [math]::Round(($h - $l) / $l * 100, 3)
        Write-Host ('{0} EST  O={1,10:N2}  H={2,10:N2}  L={3,10:N2}  C={4,10:N2}  chg={5,6}%  range={6}%' -f $t, $o, $h, $l, $c, $ch, $range)
        if ($ch -gt $maxUp) { $maxUp = $ch; $maxUpTime = $t }
        if ($ch -lt $maxDown) { $maxDown = $ch; $maxDownTime = $t }
    }
    Write-Host "`nBTC Best hourly candle: +$maxUp% at $maxUpTime"
    Write-Host "BTC Worst hourly candle: $maxDown% at $maxDownTime"
} catch { Write-Host "Binance error: $($_.Exception.Message)" }

# ETH
Write-Host "`n=== ETH/USD Hourly Candles (last 24h) ==="
try {
    $r = Invoke-RestMethod -Uri 'https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=1h&limit=24' -TimeoutSec 15
    $maxUp = 0; $maxDown = 0; $maxUpTime = ''; $maxDownTime = ''
    foreach ($k in $r) {
        $t = [DateTimeOffset]::FromUnixTimeMilliseconds($k[0]).ToOffset([TimeSpan]::FromHours(-5)).ToString('MM/dd HH:mm')
        $o = [double]$k[1]; $h = [double]$k[2]; $l = [double]$k[3]; $c = [double]$k[4]
        $ch = [math]::Round(($c - $o) / $o * 100, 3)
        if ($ch -gt $maxUp) { $maxUp = $ch; $maxUpTime = $t }
        if ($ch -lt $maxDown) { $maxDown = $ch; $maxDownTime = $t }
    }
    Write-Host "ETH Best hourly candle: +$maxUp% at $maxUpTime"
    Write-Host "ETH Worst hourly candle: $maxDown% at $maxDownTime"
} catch { Write-Host "Error: $($_.Exception.Message)" }

# SOL
Write-Host "`n=== SOL/USD ==="
try {
    $r = Invoke-RestMethod -Uri 'https://api.binance.com/api/v3/klines?symbol=SOLUSDT&interval=1h&limit=24' -TimeoutSec 15
    $maxUp = 0; $maxDown = 0; $maxUpTime = ''; $maxDownTime = ''
    foreach ($k in $r) {
        $t = [DateTimeOffset]::FromUnixTimeMilliseconds($k[0]).ToOffset([TimeSpan]::FromHours(-5)).ToString('MM/dd HH:mm')
        $o = [double]$k[1]; $c = [double]$k[4]
        $ch = [math]::Round(($c - $o) / $o * 100, 3)
        if ($ch -gt $maxUp) { $maxUp = $ch; $maxUpTime = $t }
        if ($ch -lt $maxDown) { $maxDown = $ch; $maxDownTime = $t }
    }
    Write-Host "SOL Best hourly candle: +$maxUp% at $maxUpTime"
    Write-Host "SOL Worst hourly candle: $maxDown% at $maxDownTime"
} catch { Write-Host "Error: $($_.Exception.Message)" }

# XRP
Write-Host "`n=== XRP/USD ==="
try {
    $r = Invoke-RestMethod -Uri 'https://api.binance.com/api/v3/klines?symbol=XRPUSDT&interval=1h&limit=24' -TimeoutSec 15
    $maxUp = 0; $maxDown = 0; $maxUpTime = ''; $maxDownTime = ''
    foreach ($k in $r) {
        $t = [DateTimeOffset]::FromUnixTimeMilliseconds($k[0]).ToOffset([TimeSpan]::FromHours(-5)).ToString('MM/dd HH:mm')
        $o = [double]$k[1]; $c = [double]$k[4]
        $ch = [math]::Round(($c - $o) / $o * 100, 3)
        if ($ch -gt $maxUp) { $maxUp = $ch; $maxUpTime = $t }
        if ($ch -lt $maxDown) { $maxDown = $ch; $maxDownTime = $t }
    }
    Write-Host "XRP Best hourly candle: +$maxUp% at $maxUpTime"
    Write-Host "XRP Worst hourly candle: $maxDown% at $maxDownTime"
} catch { Write-Host "Error: $($_.Exception.Message)" }

# DOGE
Write-Host "`n=== DOGE/USD ==="
try {
    $r = Invoke-RestMethod -Uri 'https://api.binance.com/api/v3/klines?symbol=DOGEUSDT&interval=1h&limit=24' -TimeoutSec 15
    $maxUp = 0; $maxDown = 0; $maxUpTime = ''; $maxDownTime = ''
    foreach ($k in $r) {
        $t = [DateTimeOffset]::FromUnixTimeMilliseconds($k[0]).ToOffset([TimeSpan]::FromHours(-5)).ToString('MM/dd HH:mm')
        $o = [double]$k[1]; $c = [double]$k[4]
        $ch = [math]::Round(($c - $o) / $o * 100, 3)
        if ($ch -gt $maxUp) { $maxUp = $ch; $maxUpTime = $t }
        if ($ch -lt $maxDown) { $maxDown = $ch; $maxDownTime = $t }
    }
    Write-Host "DOGE Best hourly candle: +$maxUp% at $maxUpTime"
    Write-Host "DOGE Worst hourly candle: $maxDown% at $maxDownTime"
} catch { Write-Host "Error: $($_.Exception.Message)" }

# Forex - USDJPY via TwelveData
Write-Host "`n=== Forex Summary ==="
Write-Host "(Forex 24h ranges from cached data)"
Write-Host "USDJPY: range 155.716 - 156.229 = 0.33%"
Write-Host "EURUSD: range 1.19021 - 1.19214 = 0.16%"
Write-Host "GBPUSD: range 1.36786 - 1.37003 = 0.16%"
Write-Host "AUDUSD: change -0.17%"
Write-Host "USDCHF: change +0.16%"
