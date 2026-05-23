# Check for stale GitHub Actions workflows
# Identifies workflows that haven't run recently or have failing latest runs

param(
    [int]$DaysStale = 7,
    [switch]$Fix
)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GitHub Actions Stale Workflow Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get all workflow files
$workflowFiles = Get-ChildItem -Path ".github\workflows" -Filter "*.yml" | Select-Object -ExpandProperty Name
Write-Host "Found $($workflowFiles.Count) workflow files" -ForegroundColor Gray
Write-Host ""

# Try to get recent runs from gh CLI
try {
    $runsJson = gh run list --limit 500 --json workflowName,status,conclusion,createdAt,databaseId 2>$null
    $runs = $runsJson | ConvertFrom-Json
    
    Write-Host "Retrieved $($runs.Count) recent workflow runs from GitHub" -ForegroundColor Gray
    Write-Host ""
    
    # Group by workflow and get latest run
    $workflowStats = $runs | Group-Object workflowName | ForEach-Object {
        $latest = $_.Group | Sort-Object createdAt -Descending | Select-Object -First 1
        [PSCustomObject]@{
            Workflow = $_.Name
            LatestRun = $latest.createdAt
            Status = $latest.status
            Conclusion = $latest.conclusion
            RunId = $latest.databaseId
            TotalRuns = $_.Count
        }
    }
    
    # Find stale workflows (no runs in $DaysStale days)
    $staleThreshold = (Get-Date).AddDays(-$DaysStale)
    $staleWorkflows = $workflowStats | Where-Object { 
        [datetime]$_.LatestRun -lt $staleThreshold 
    } | Sort-Object LatestRun
    
    # Find failed workflows (latest run failed)
    $failedWorkflows = $workflowStats | Where-Object { 
        $_.Conclusion -eq "failure" -or $_.Conclusion -eq "timed_out" -or $_.Conclusion -eq "startup_failure"
    } | Sort-Object LatestRun
    
    # Find workflows with no runs at all
    $workflowNamesWithRuns = $workflowStats | Select-Object -ExpandProperty Workflow
    $unusedWorkflows = $workflowFiles | Where-Object { 
        $wfName = $_ -replace '\.yml$', ''
        $workflowNamesWithRuns -notcontains $wfName
    }
    
    # Display results
    Write-Host "STALE WORKFLOWS (no runs in last $DaysStale days):" -ForegroundColor Yellow
    Write-Host "------------------------------------------------" -ForegroundColor Yellow
    if ($staleWorkflows) {
        $staleWorkflows | Format-Table -AutoSize
        Write-Host "Count: $($staleWorkflows.Count)" -ForegroundColor Red
    } else {
        Write-Host "None found!" -ForegroundColor Green
    }
    Write-Host ""
    
    Write-Host "FAILED WORKFLOWS (latest run failed):" -ForegroundColor Red
    Write-Host "--------------------------------------" -ForegroundColor Red
    if ($failedWorkflows) {
        $failedWorkflows | Format-Table -AutoSize
        Write-Host "Count: $($failedWorkflows.Count)" -ForegroundColor Red
    } else {
        Write-Host "None found!" -ForegroundColor Green
    }
    Write-Host ""
    
    Write-Host "UNUSED WORKFLOWS (no recorded runs):" -ForegroundColor Magenta
    Write-Host "-------------------------------------" -ForegroundColor Magenta
    if ($unusedWorkflows) {
        $unusedWorkflows | ForEach-Object { Write-Host "  - $_" }
        Write-Host "Count: $($unusedWorkflows.Count)" -ForegroundColor Magenta
    } else {
        Write-Host "None found!" -ForegroundColor Green
    }
    Write-Host ""
    
    # Summary
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  SUMMARY" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Total workflow files:  $($workflowFiles.Count)" 
    Write-Host "Workflows with runs:   $($workflowStats.Count)"
    Write-Host "Stale workflows:       $($staleWorkflows.Count)" -ForegroundColor $(if($staleWorkflows.Count -gt 0){"Red"}else{"Green"})
    Write-Host "Failed workflows:      $($failedWorkflows.Count)" -ForegroundColor $(if($failedWorkflows.Count -gt 0){"Red"}else{"Green"})
    Write-Host "Unused workflows:      $($unusedWorkflows.Count)" -ForegroundColor $(if($unusedWorkflows.Count -gt 10){"Yellow"}else{"Green"})
    Write-Host ""
    
    # Offer to rerun failed workflows
    if ($failedWorkflows -and $Fix) {
        Write-Host "Attempting to rerun failed workflows..." -ForegroundColor Cyan
        foreach ($wf in $failedWorkflows) {
            Write-Host "Rerunning: $($wf.Workflow) (Run ID: $($wf.RunId))" -ForegroundColor Yellow
            gh run rerun --failed $wf.RunId 2>$null
            if ($?) {
                Write-Host "  Success - Rerun triggered" -ForegroundColor Green
            } else {
                Write-Host "  Failed to trigger rerun" -ForegroundColor Red
            }
        }
    }
    
} catch {
    Write-Host "ERROR: Failed to retrieve workflow runs" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure you have 'gh' CLI installed and authenticated:" -ForegroundColor Yellow
    Write-Host "  gh auth login" -ForegroundColor Gray
}

Write-Host ""
Write-Host 'Done!' -ForegroundColor Green
