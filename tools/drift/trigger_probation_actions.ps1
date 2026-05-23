#!/posh
<#
.SYNOPSIS
    Trigger probation actions for strategies exceeding drift thresholds.

.DESCRIPTION
    Reads drift_scores_latest.json, filters strategies where:
    - probation=true AND consecutive_high_drift_hours >= threshold
    Writes probation state to tmp/strategy_probation_state.json for downstream action.
    Suitable for invocation by Alertmanager webhook or GitHub Actions workflow.

.PARAMETER DriftScorePath
    Path to drift_scores_latest.json (required)

.PARAMETER OutputPath
    Path to write strategy_probation_state.json

.PARAMETER ConsecutiveHoursThreshold
    Min consecutive high-drift hours to trigger probation (default: 2)

.PARAMETER LogPath
    Path to write action log

.EXAMPLE
    pwsh -File trigger_probation_actions.ps1 -DriftScorePath drift_scores_latest.json -OutputPath tmp/strategy_probation_state.json
#>

param(
    [string]$DriftScorePath = "tmp/drift_scores_latest.json",
    [string]$OutputPath = "tmp/strategy_probation_state.json",
    [int]$ConsecutiveHoursThreshold = 2,
    [string]$LogPath = "tmp/probation_actions.log"
)

$ErrorActionPreference = "Stop"

# Ensure output directory exists
$OutputDir = Split-Path $OutputPath -Parent
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$LogDir = Split-Path $LogPath -Parent
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message)
    $Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    "$Timestamp | $Message" | Tee-Object -FilePath $LogPath -Append
}

try {
    Write-Log "Starting probation action trigger..."
    
    # Validate input file
    if (-not (Test-Path $DriftScorePath)) {
        Write-Log "ERROR: Drift score file not found: $DriftScorePath"
        throw "Input file missing: $DriftScorePath"
    }
    
    # Load drift scores
    $DriftRaw = Get-Content $DriftScorePath -Raw | ConvertFrom-Json
    if (-not $DriftRaw) {
        Write-Log "ERROR: Failed to parse drift scores JSON"
        throw "Invalid JSON in drift scores file"
    }

    # Support both schemas:
    # 1) object with rows[] (current)
    # 2) top-level array (legacy)
    $DriftData = @()
    if ($DriftRaw -is [System.Array]) {
        $DriftData = $DriftRaw
    } elseif ($null -ne $DriftRaw.rows) {
        $DriftData = @($DriftRaw.rows)
    }
    if (-not $DriftData) {
        Write-Log "ERROR: No drift rows found in input schema"
        throw "Drift score payload has no rows"
    }
    
    Write-Log "Loaded drift_scores_latest.json with $($DriftData.Count) rows"
    
    # Filter for probation candidates:
    # - probation=true
    # - consecutive_high_drift_hours >= threshold
    $ProbationCandidates = $DriftData | Where-Object {
        $_.probation -eq $true -and $_.consecutive_high_drift_hours -ge $ConsecutiveHoursThreshold
    }
    
    Write-Log "Found $($ProbationCandidates.Count) strategies exceeding probation threshold"
    
    # Group by strategy when available; otherwise by asset class bucket.
    # This keeps the action artifact useful for both row schemas.
    $ProbationState = @()
    $StrategySet = @{}
    
    foreach ($Row in $ProbationCandidates) {
        $StrategyName = if ($null -ne $Row.strategy_name -and "$($Row.strategy_name)" -ne "") { "$($Row.strategy_name)" } else { "asset_class_policy" }
        $StrategyKey = "$($Row.asset_class):$StrategyName"
        
        if (-not $StrategySet.ContainsKey($StrategyKey)) {
            $StrategySet[$StrategyKey] = @{
                strategy_name = $StrategyName
                asset_class = $Row.asset_class
                max_consecutive_hours = $Row.consecutive_high_drift_hours
                max_drift_score = $Row.drift_score
                probation_triggered_at = $Row.event_ts
                action = "PROBATION"
            }
        } else {
            # Update if this row has higher consecutive hours
            if ($Row.consecutive_high_drift_hours -gt $StrategySet[$StrategyKey].max_consecutive_hours) {
                $StrategySet[$StrategyKey].max_consecutive_hours = $Row.consecutive_high_drift_hours
                $StrategySet[$StrategyKey].max_drift_score = $Row.drift_score
                $StrategySet[$StrategyKey].probation_triggered_at = $Row.event_ts
            }
        }
    }
    
    # Convert to sorted array
    $ProbationState = $StrategySet.Values | Sort-Object -Property @{Expression={$_.max_consecutive_hours}; Descending=$true}
    
    # Write probation state artifact
    $Output = @{
        timestamp = (Get-Date -Format "u")
        probation_threshold_hours = $ConsecutiveHoursThreshold
        strategies_on_probation = $ProbationState.Count
        probation_actions = $ProbationState
    }
    
    $Output | ConvertTo-Json -Depth 10 | Set-Content $OutputPath
    Write-Log "Wrote $($ProbationState.Count) probation actions to $OutputPath"
    
    # Log each probation action
    foreach ($Strategy in $ProbationState) {
        Write-Log "PROBATION: $($Strategy.strategy_name) [$($Strategy.asset_class)] - consecutive_hours=$($Strategy.max_consecutive_hours), drift_score=$($Strategy.max_drift_score)"
    }
    
    # Summary
    $Summary = @{
        status = "SUCCESS"
        strategies_processed = $DriftData.Count
        strategies_on_probation = $ProbationState.Count
        output_path = (Resolve-Path $OutputPath -Relative)
    }
    
    Write-Log "Probation action trigger completed. Status: $($Summary.status)"
    $Summary | ConvertTo-Json | Write-Output
    
    exit 0
}
catch {
    Write-Log "FATAL ERROR: $_"
    @{
        status = "FAILED"
        error = $_.Exception.Message
    } | ConvertTo-Json | Write-Output
    exit 1
}
