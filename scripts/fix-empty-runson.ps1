# Fix Empty runs-on Expressions in GitHub Actions Workflows
# 
# Many workflows have empty runs-on: lines which cause failures.
# This script adds 'ubuntu-latest' as the default runner.

param(
    [switch]$WhatIf,
    [string]$WorkflowDir = ".github/workflows"
)

$fixedCount = 0
$alreadyOK = 0

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fix Empty runs-on Expressions" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$workflows = Get-ChildItem "$WorkflowDir/*.yml" -ErrorAction Stop

foreach ($wf in $workflows) {
    $content = Get-Content $wf.FullName -Raw
    $originalContent = $content
    
    # Pattern: runs-on: followed by only whitespace/end of line
    # Replace with: runs-on: ubuntu-latest
    $fixedContent = $content -replace '(?m)^(\s+)runs-on:\s*$', '$1runs-on: ubuntu-latest'
    
    if ($content -ne $fixedContent) {
        $fixedCount++
        if ($WhatIf) {
            Write-Host "[WOULD FIX] $($wf.Name)" -ForegroundColor Yellow
        } else {
            Set-Content $wf.FullName $fixedContent -NoNewline
            Write-Host "[FIXED] $($wf.Name)" -ForegroundColor Green
        }
    } else {
        $alreadyOK++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total workflows: $($workflows.Count)"
Write-Host "Already OK: $alreadyOK" -ForegroundColor Green
if ($WhatIf) {
    Write-Host "Would fix: $fixedCount" -ForegroundColor Yellow
} else {
    Write-Host "Fixed: $fixedCount" -ForegroundColor Green
}
Write-Host ""

if ($fixedCount -gt 0 -and -not $WhatIf) {
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Review changes with: git diff --stat"
    Write-Host "  2. Commit with: git add .github/workflows && git commit -m 'Fix empty runs-on expressions'"
    Write-Host "  3. Push: git push origin main"
}
