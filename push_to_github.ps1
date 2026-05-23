#!/usr/bin/env powershell
# Push to GitHub and Enable Actions

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PUSH TO GITHUB & ENABLE ACTIONS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in a git repo
if (-not (Test-Path .git)) {
    Write-Host "[ERROR] Not a git repository!" -ForegroundColor Red
    exit 1
}

# Check git status
Write-Host "[1] Checking Git Status..." -ForegroundColor Yellow
$status = git status --porcelain
if ($status) {
    Write-Host "    Uncommitted changes found:" -ForegroundColor White
    git status --short
} else {
    Write-Host "    No changes to commit" -ForegroundColor Green
}

Write-Host ""

# Add all files
Write-Host "[2] Adding Files..." -ForegroundColor Yellow
git add .
Write-Host "    Added all files" -ForegroundColor Green

Write-Host ""

# Commit
Write-Host "[3] Committing..." -ForegroundColor Yellow
$commitMsg = "Production deployment: Williams+Connors bundle with CI/CD tracking"
git commit -m "$commitMsg"
if ($LASTEXITCODE -eq 0) {
    Write-Host "    Committed: $commitMsg" -ForegroundColor Green
} else {
    Write-Host "    Nothing to commit or error occurred" -ForegroundColor Yellow
}

Write-Host ""

# Push
Write-Host "[4] Pushing to GitHub..." -ForegroundColor Yellow
git push origin main
if ($LASTEXITCODE -eq 0) {
    Write-Host "    Successfully pushed to GitHub!" -ForegroundColor Green
} else {
    Write-Host "    [ERROR] Push failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SUCCESSFULLY PUSHED TO GITHUB!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Show next steps
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "-----------" -ForegroundColor White
Write-Host ""
Write-Host "1. Enable GitHub Actions:" -ForegroundColor Yellow
Write-Host "   - Go to: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/settings/actions" -ForegroundColor White
Write-Host "   - Select: 'Allow all actions and reusable workflows'" -ForegroundColor White
Write-Host "   - Click: Save" -ForegroundColor White
Write-Host ""
Write-Host "2. Enable GitHub Pages:" -ForegroundColor Yellow
Write-Host "   - Go to: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/settings/pages" -ForegroundColor White
Write-Host "   - Source: Deploy from a branch" -ForegroundColor White
Write-Host "   - Branch: gh-pages / (root)" -ForegroundColor White
Write-Host "   - Click: Save" -ForegroundColor White
Write-Host ""
Write-Host "3. Deploy to Paper Trading:" -ForegroundColor Yellow
Write-Host "   - Go to: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions" -ForegroundColor White
Write-Host "   - Click: 'Deploy Strategy Bundle'" -ForegroundColor White
Write-Host "   - Click: 'Run workflow'" -ForegroundColor White
Write-Host "   - Enter: bundle=williams_connors, mode=paper" -ForegroundColor White
Write-Host "   - Click: Run workflow" -ForegroundColor White
Write-Host ""
Write-Host "4. View Dashboard:" -ForegroundColor Yellow
Write-Host "   https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/" -ForegroundColor White
Write-Host ""
