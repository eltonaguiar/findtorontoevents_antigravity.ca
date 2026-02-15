# Pre-Deployment Checklist Script (Windows PowerShell)
# Usage: .\tools\pre-deploy-check.ps1
# Ensures all changes are tracked in GitHub before deployment

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "🚀 Pre-Deployment Checklist" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

$FAILED = $false

# Check 1: Git is initialized
Write-Host "📋 Check 1: Git repository..."
if (Test-Path ".git") {
    Write-Host "✓ Git repository found" -ForegroundColor Green
} else {
    Write-Host "✗ Not a git repository! Abort." -ForegroundColor Red
    exit 1
}
Write-Host ""

# Check 2: Remote origin is set
Write-Host "📋 Check 2: Remote origin..."
try {
    $REMOTE = git remote get-url origin 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Remote origin: $REMOTE" -ForegroundColor Green
    } else {
        throw
    }
} catch {
    Write-Host "✗ No remote origin set!" -ForegroundColor Red
    $FAILED = $true
}
Write-Host ""

# Check 3: Check for uncommitted changes
Write-Host "📋 Check 3: Uncommitted changes..."
$status = git status --porcelain
if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "✓ No uncommitted changes" -ForegroundColor Green
} else {
    Write-Host "✗ UNCOMMITTED CHANGES DETECTED:" -ForegroundColor Red
    Write-Host $status
    Write-Host ""
    Write-Host "⚠️  Commit these changes before deploying:" -ForegroundColor Yellow
    Write-Host "   git add <files>"
    Write-Host "   git commit -m 'type: description'"
    Write-Host "   git push origin main"
    $FAILED = $true
}
Write-Host ""

# Check 4: Check for untracked files
Write-Host "📋 Check 4: Untracked files..."
$UNTRACKED = git ls-files --others --exclude-standard
if ([string]::IsNullOrWhiteSpace($UNTRACKED)) {
    Write-Host "✓ No untracked files" -ForegroundColor Green
} else {
    Write-Host "⚠ Untracked files detected:" -ForegroundColor Yellow
    $UNTRACKED | Select-Object -First 10 | ForEach-Object { Write-Host "   $_" }
    if (($UNTRACKED | Measure-Object).Count -gt 10) {
        Write-Host "   ... and more"
    }
    Write-Host ""
    Write-Host "⚠️  If these should be deployed, add them:" -ForegroundColor Yellow
    Write-Host "   git add <files>"
    Write-Host "   git commit -m 'feat: Add new files'"
}
Write-Host ""

# Check 5: Latest commit info
Write-Host "📋 Check 5: Latest commit..."
Write-Host "Latest commits:" -ForegroundColor Green
(git log --oneline -3) | ForEach-Object { Write-Host "   $_" }
Write-Host ""

# Check 6: Check if local is ahead/behind remote
Write-Host "📋 Check 6: Sync with remote..."
git fetch origin main --quiet 2>$null
$LOCAL = git rev-parse @
$REMOTE = git rev-parse @{u} 2>$null
$BASE = git merge-base @ @{u} 2>$null

if ($REMOTE -eq $null) {
    Write-Host "⚠ Cannot check remote - no upstream branch" -ForegroundColor Yellow
} elseif ($LOCAL -eq $REMOTE) {
    Write-Host "✓ Local and remote are in sync" -ForegroundColor Green
} elseif ($LOCAL -eq $BASE) {
    Write-Host "✗ Local is BEHIND remote! Pull first:" -ForegroundColor Red
    Write-Host "   git pull origin main"
    $FAILED = $true
} elseif ($REMOTE -eq $BASE) {
    Write-Host "⚠ Local is AHEAD of remote. Need to push:" -ForegroundColor Yellow
    Write-Host "   git push origin main"
} else {
    Write-Host "✗ Local and remote have diverged!" -ForegroundColor Red
    $FAILED = $true
}
Write-Host ""

# Final result
Write-Host "===================================" -ForegroundColor Cyan
if (-not $FAILED) {
    Write-Host "✅ ALL CHECKS PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ready to deploy!"
    Write-Host ""
    Write-Host "Deployment options:"
    Write-Host "  1. GitHub Actions (if configured)"
    Write-Host "  2. Manual FTP deploy from local"
    Write-Host "  3. git push to trigger webhook"
} else {
    Write-Host "❌ CHECKS FAILED" -ForegroundColor Red
    Write-Host ""
    Write-Host "Fix the issues above before deploying."
    Write-Host "Remember: Commit to GitHub FIRST, then deploy."
}
Write-Host "===================================" -ForegroundColor Cyan
