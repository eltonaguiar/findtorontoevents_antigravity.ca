param(
    [string]$DriftScorePath = "audit_dashboard/data/drift_scores_latest.json",
    [string]$IntegrityPath = "tmp/backtest_forward_drift_analysis.validated.json",
    [string]$OutputPromPath = "audit_dashboard/data/drift_metrics.prom",
    [string]$PushgatewayUrl = "",
    [string]$JobName = "drift_monitor"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Load-JsonOrNull {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    return (Get-Content -Path $Path -Raw | ConvertFrom-Json -Depth 100)
}

$drift = Load-JsonOrNull -Path $DriftScorePath
if ($null -eq $drift -or $null -eq $drift.rows) {
    throw "Drift score file is missing or malformed: $DriftScorePath"
}

$integrity = Load-JsonOrNull -Path $IntegrityPath
$integrityFailures = 0
if ($null -ne $integrity -and $null -ne $integrity.rows_invalid) {
    $integrityFailures = [int]$integrity.rows_invalid
}

$lines = @()
$lines += "# HELP drift_score Drift score per asset class hour"
$lines += "# TYPE drift_score gauge"
$lines += "# HELP drift_high Flag for high drift"
$lines += "# TYPE drift_high gauge"
$lines += "# HELP drift_consecutive_high_hours Consecutive high-drift hours"
$lines += "# TYPE drift_consecutive_high_hours gauge"
$lines += "# HELP drift_probation Flag for probation state"
$lines += "# TYPE drift_probation gauge"
$lines += "# HELP backtest_integrity_failures Count of rows with invalid backtest baseline fields"
$lines += "# TYPE backtest_integrity_failures gauge"

foreach ($row in $drift.rows) {
    $ac = "$($row.asset_class)"
    $hour = "$($row.hour_utc)"
    $score = [double]$row.drift_score
    $high = if ($row.high_drift) { 1 } else { 0 }
    $consecutive = [int]$row.consecutive_high_drift_hours
    $probation = if ($row.probation) { 1 } else { 0 }

    $labels = "asset_class=`"$ac`",hour_utc=`"$hour`""
    $lines += "drift_score{$labels} $score"
    $lines += "drift_high{$labels} $high"
    $lines += "drift_consecutive_high_hours{$labels} $consecutive"
    $lines += "drift_probation{$labels} $probation"
}

$lines += "backtest_integrity_failures $integrityFailures"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPromPath) | Out-Null
Set-Content -Path $OutputPromPath -Value ($lines -join "`n") -Encoding UTF8
Write-Host "Wrote Prometheus metrics to $OutputPromPath"

if ($PushgatewayUrl -ne "") {
    $url = "$PushgatewayUrl/metrics/job/$JobName"
    Invoke-WebRequest -Method Put -Uri $url -InFile $OutputPromPath -ContentType "text/plain"
    Write-Host "Pushed metrics to $url"
}
