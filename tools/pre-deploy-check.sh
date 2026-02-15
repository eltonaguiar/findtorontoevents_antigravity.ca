#!/bin/bash

# Pre-Deployment Checklist Script
# Usage: ./tools/pre-deploy-check.sh
# Ensures all changes are tracked in GitHub before deployment

echo "==================================="
echo "🚀 Pre-Deployment Checklist"
echo "==================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0

# Check 1: Git is initialized
echo "📋 Check 1: Git repository..."
if [ -d ".git" ]; then
    echo -e "${GREEN}✓${NC} Git repository found"
else
    echo -e "${RED}✗${NC} Not a git repository! Abort."
    exit 1
fi
echo ""

# Check 2: Remote origin is set
echo "📋 Check 2: Remote origin..."
REMOTE=$(git remote get-url origin 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Remote origin: $REMOTE"
else
    echo -e "${RED}✗${NC} No remote origin set!"
    FAILED=1
fi
echo ""

# Check 3: Check for uncommitted changes
echo "📋 Check 3: Uncommitted changes..."
if git diff-index --quiet HEAD --; then
    echo -e "${GREEN}✓${NC} No uncommitted changes"
else
    echo -e "${RED}✗${NC} UNCOMMITTED CHANGES DETECTED:"
    git status --short
    echo ""
    echo -e "${YELLOW}⚠️  Commit these changes before deploying:${NC}"
    echo "   git add <files>"
    echo "   git commit -m 'type: description'"
    echo "   git push origin main"
    FAILED=1
fi
echo ""

# Check 4: Check for untracked files
echo "📋 Check 4: Untracked files..."
UNTRACKED=$(git ls-files --others --exclude-standard)
if [ -z "$UNTRACKED" ]; then
    echo -e "${GREEN}✓${NC} No untracked files"
else
    echo -e "${YELLOW}⚠${NC} Untracked files detected:"
    echo "$UNTRACKED" | head -10
    if [ $(echo "$UNTRACKED" | wc -l) -gt 10 ]; then
        echo "   ... and more"
    fi
    echo ""
    echo -e "${YELLOW}⚠️  If these should be deployed, add them:${NC}"
    echo "   git add <files>"
    echo "   git commit -m 'feat: Add new files'"
fi
echo ""

# Check 5: Latest commit info
echo "📋 Check 5: Latest commit..."
echo -e "${GREEN}Latest commits:${NC}"
git log --oneline -3
echo ""

# Check 6: Check if local is ahead/behind remote
echo "📋 Check 6: Sync with remote..."
git fetch origin main --quiet 2>/dev/null
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "none")
BASE=$(git merge-base @ @{u} 2>/dev/null || echo "none")

if [ "$REMOTE" = "none" ]; then
    echo -e "${YELLOW}⚠${NC} Cannot check remote - no upstream branch"
elif [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${GREEN}✓${NC} Local and remote are in sync"
elif [ "$LOCAL" = "$BASE" ]; then
    echo -e "${RED}✗${NC} Local is BEHIND remote! Pull first:"
    echo "   git pull origin main"
    FAILED=1
elif [ "$REMOTE" = "$BASE" ]; then
    echo -e "${YELLOW}⚠${NC} Local is AHEAD of remote. Need to push:"
    echo "   git push origin main"
else
    echo -e "${RED}✗${NC} Local and remote have diverged!"
    FAILED=1
fi
echo ""

# Check 7: Sensitive files check
echo "📋 Check 7: Sensitive files..."
SENSITIVE_PATTERNS="password secret key token .env config"
SENSITIVE_FILES=$(git diff --cached --name-only | grep -iE "(password|secret|key|token|\.env|config)" || true)
if [ -n "$SENSITIVE_FILES" ]; then
    echo -e "${YELLOW}⚠${NC} Potentially sensitive files in commit:"
    echo "$SENSITIVE_FILES"
    echo ""
    echo -e "${YELLOW}⚠️  Review these files for secrets before pushing!${NC}"
fi
echo ""

# Final result
echo "==================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED${NC}"
    echo ""
    echo "Ready to deploy!"
    echo ""
    echo "Deployment options:"
    echo "  1. GitHub Actions (if configured)"
    echo "  2. Manual FTP deploy from local"
    echo "  3. git push to trigger webhook"
else
    echo -e "${RED}❌ CHECKS FAILED${NC}"
    echo ""
    echo "Fix the issues above before deploying."
    echo "Remember: Commit to GitHub FIRST, then deploy."
    exit 1
fi
echo "==================================="
