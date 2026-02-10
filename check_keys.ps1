$names = @('FINNHUB','FINNHUB_API','FINNHUB_KEY','TWELVE_DATA','TWELVEDATA','FREECRYPTO','CRYPT','CURRENCY_LAYER_API','FTP_SERVER')
foreach ($n in $names) {
    $v = [Environment]::GetEnvironmentVariable($n,'User')
    if ($v) { Write-Host "$n`: len=$($v.Length)" }
}
