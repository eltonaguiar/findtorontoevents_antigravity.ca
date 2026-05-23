param(
    [string]$InputPath = "tmp/backtest_forward_drift_analysis.json",
    [string]$OutputPath = "tmp/backtest_forward_drift_analysis.validated.json",
    [string]$SnapshotDir = "audit_dashboard/data/drift_snapshots",
    [string]$SnapshotPattern = "*drift*.json",
    [string]$LogPath = "audit_dashboard/data/backtest_integrity.log",
    [switch]$StrictZeroBtWr,
    [switch]$FailOnError
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)
    $stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $line = "$stamp $Message"
    Write-Host $line
    Add-Content -Path $LogPath -Value $line
}

function Load-Json {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        throw "JSON file not found: $Path"
    }
    Get-Content -Path $Path -Raw | ConvertFrom-Json -Depth 100
}

function Extract-Rows {
    param($Doc)
    if ($Doc -is [System.Array]) { return ,$Doc }
    if ($null -ne $Doc.top_wr_drift) { return ,$Doc.top_wr_drift }
    if ($null -ne $Doc.strategies) { return ,$Doc.strategies }
    if ($null -ne $Doc.rows) { return ,$Doc.rows }
    return @()
}

function Get-JoinValue {
    param($Row, [string[]]$Candidates)
    foreach ($name in $Candidates) {
        $prop = $Row.PSObject.Properties[$name]
        if ($null -ne $prop -and $null -ne $prop.Value -and "" -ne "$($prop.Value)") {
            return "$($prop.Value)"
        }
    }
    return ""
}

function Test-BtRowHealthy {
    param($Row, [bool]$StrictZero)

    $btN = $null
    $btWr = $null

    if ($null -ne $Row.PSObject.Properties["bt_n"]) { $btN = [double]$Row.bt_n }
    if ($null -ne $Row.PSObject.Properties["bt_wr"]) { $btWr = [double]$Row.bt_wr }

    if ($null -eq $btN -or $btN -le 0) { return $false }
    if ($null -eq $btWr -or [double]::IsNaN($btWr)) { return $false }
    if ($StrictZero -and $btWr -eq 0) { return $false }

    return $true
}

function Snapshot-IsHealthy {
    param([string]$Path, [bool]$StrictZero)
    try {
        $doc = Load-Json -Path $Path
        $rows = Extract-Rows -Doc $doc
        if ($rows.Count -eq 0) { return $false }

        foreach ($r in $rows) {
            if (Test-BtRowHealthy -Row $r -StrictZero $StrictZero) {
                return $true
            }
        }
        return $false
    } catch {
        return $false
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogPath) | Out-Null

$doc = Load-Json -Path $InputPath

# Handle skip artifact from build_backtest_forward_drift.py
if ($doc.PSObject.Properties["skipped"] -and $doc.skipped) {
    Write-Log "INFO input is a skip artifact — reason: $($doc.reason)"
    $result = [ordered]@{
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        input_path = $InputPath
        output_path = $OutputPath
        strict_zero_bt_wr = $false
        rows_total = 0
        rows_valid = 0
        rows_invalid = 0
        used_fallback = $false
        fallback_path = ""
        missing_join_keys = @()
        skipped = $true
        skip_reason = $doc.reason
    }
    $result["data"] = $doc
    $result | ConvertTo-Json -Depth 100 | Set-Content -Path $OutputPath -Encoding UTF8
    Write-Log "INFO wrote validated skip artifact to $OutputPath"
    exit 0
}

$rows = Extract-Rows -Doc $doc

if ($rows.Count -eq 0) {
    Write-Log "ERROR no rows found in $InputPath"
    if ($FailOnError) { exit 2 }
    exit 0
}

$missing = @()
$validCount = 0
$strict = [bool]$StrictZeroBtWr

foreach ($row in $rows) {
    $healthy = Test-BtRowHealthy -Row $row -StrictZero $strict
    if ($healthy) {
        $validCount += 1
        continue
    }

    $missing += [pscustomobject]@{
        strategy_id = Get-JoinValue -Row $row -Candidates @("strategy_id", "strategy", "name")
        strategy_name = Get-JoinValue -Row $row -Candidates @("name", "strategy", "source_system")
        asset_class = Get-JoinValue -Row $row -Candidates @("asset_class", "asset_classes")
        source_system = Get-JoinValue -Row $row -Candidates @("source_system", "system")
        bt_n = if ($null -ne $row.PSObject.Properties["bt_n"]) { "$($row.bt_n)" } else { "" }
        bt_wr = if ($null -ne $row.PSObject.Properties["bt_wr"]) { "$($row.bt_wr)" } else { "" }
        reason = "missing_or_zero_backtest_fields"
    }
}

$usedFallback = $false
$fallbackPath = ""

if ($missing.Count -gt 0) {
    Write-Log "WARN integrity check failed for $($missing.Count)/$($rows.Count) rows; looking for fallback snapshot"

    if (Test-Path $SnapshotDir) {
        $candidate = Get-ChildItem -Path $SnapshotDir -Filter $SnapshotPattern -File |
            Sort-Object LastWriteTimeUtc -Descending |
            Where-Object { $_.FullName -ne (Resolve-Path $InputPath).Path } |
            Select-Object -First 25

        foreach ($file in $candidate) {
            if (Snapshot-IsHealthy -Path $file.FullName -StrictZero $strict) {
                $fallbackPath = $file.FullName
                $usedFallback = $true
                break
            }
        }
    }
}

$result = [ordered]@{
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    input_path = $InputPath
    output_path = $OutputPath
    strict_zero_bt_wr = $strict
    rows_total = $rows.Count
    rows_valid = $validCount
    rows_invalid = $missing.Count
    used_fallback = $usedFallback
    fallback_path = $fallbackPath
    missing_join_keys = $missing
}

if ($usedFallback) {
    Write-Log "INFO using fallback snapshot $fallbackPath"
    $fallbackDoc = Load-Json -Path $fallbackPath
    $result["data"] = $fallbackDoc
} else {
    $result["data"] = $doc
}

$result | ConvertTo-Json -Depth 100 | Set-Content -Path $OutputPath -Encoding UTF8

if ($missing.Count -gt 0 -and -not $usedFallback) {
    Write-Log "ERROR validation failed and no healthy fallback found"
    if ($FailOnError) { exit 2 }
}

if ($missing.Count -eq 0) {
    Write-Log "INFO integrity check passed for all rows"
} elseif ($usedFallback) {
    Write-Log "INFO integrity check recovered with fallback"
}
