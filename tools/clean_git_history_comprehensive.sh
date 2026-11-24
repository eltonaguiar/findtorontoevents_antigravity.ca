#!/usr/bin/env bash
#
# tools/clean_git_history_comprehensive.sh
#
# Purpose: Remove ALL large data files (>10MB) that were accidentally committed
#          across the entire repository history.
#
# Usage:
#   cd /home/eaguiar2015/repo-clean
#   bash tools/clean_git_history_comprehensive.sh
#

set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")

# Comprehensive list of large data file patterns to remove from ALL history
# Based on analysis: these files appear hundreds/thousands of times at ~10MB each
LARGE_PATTERNS=(
    # Main offenders (50-75 GB combined)
    "ml_crypto_predictor/enhanced_models/live_picks/all_picks_log.json"
    "signal_recorder/data/signal_log.db"
    "meta_strategy/data/meta_strategy.db"
    "data/live_picks.db"
    "coinglass_strategies/data/coinglass.db"
    
    # Secondary offenders (10-20 GB combined)
    "alpha_engine/data/wrong_guesses_log.json"
    "KIMI_RISEOFTHECLAW/data/kimi_trading.db"
    "genome/strategy_registry.db"
    "alpha_engine/data/closed_picks.json"
    "alpha_engine/data/closed_picks.archive.jsonl"
    
    # Original targets (already removed, but keep for safety)
    "audit_dashboard/data/dashboard_data.json"
    "audit_trail/data/dashboard_payload.json"
    
    # SQL chunks and other large artifacts
    "sql_chunks/"
    
    # ML models (should be in Git LFS or ignored)
    "ml_crypto_predictor/production_models/"
    "ml_crypto_predictor/enhanced_models/"
    "ml_crypto_predictor/data/"
    
    # Any other live data directories
    "data/live_picks.db"
    "data/arena_picks_"
    "logs/"
    "reports/transcript_scan_"
)

echo "=== Comprehensive Git History Cleanup ==="
echo "Repository: $REPO_ROOT"
echo ""
echo "Target patterns (${{#LARGE_PATTERNS[@]}} total):"
for p in "${LARGE_PATTERNS[@]}"; do
    count=$(git log --all --oneline -- "$p" 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$count" -gt 0 ]]; then
        echo "  [${count} commits] $p"
    fi
done
echo ""

# Check disk space
AVAIL_GB=$(df -BG "$REPO_ROOT" | tail -1 | awk '{print $4}' | tr -d 'G')
echo "Available disk space: ${AVAIL_GB} GB"
if [[ "$AVAIL_GB" -lt 50 ]]; then
    echo "WARNING: Low disk space. Recommend at least 50GB free for rewrite."
    read -rp "Continue anyway? (y/N) " ans
    [[ "$ans" =~ ^[Yy]$ ]] || exit 1
fi

# Install git-filter-repo if needed
if ! python3 -c "import git_filter_repo" 2>/dev/null; then
    echo "Installing git-filter-repo..."
    pip install --user git-filter-repo
fi

# Create backup reminder
echo ""
echo "!!! IMPORTANT !!!"
echo "Ensure you have a mirror backup before proceeding:"
echo "  git clone --mirror git@github.com:eltonaguiar/findtorontoevents_antigravity.ca.git backup-$(date +%Y%m%d).git"
echo ""

read -rp "Type 'COMPREHENSIVE CLEAN' to proceed: " ans
[[ "$ans" == "COMPREHENSIVE CLEAN" ]] || exit 1

# Build filter-repo command with all paths
FILTER_ARGS=(--force --invert-paths)
for p in "${LARGE_PATTERNS[@]}"; do
    FILTER_ARGS+=(--path "$p")
done

echo ""
echo "Starting git-filter-repo (this may take 30-60 minutes)..."
echo "Log: /tmp/comprehensive-cleanup-$(date +%Y%m%d-%H%M%S).log"
echo ""

START_TIME=$(date +%s)
git filter-repo "${FILTER_ARGS[@]}" 2>&1 | tee /tmp/comprehensive-cleanup-$(date +%Y%m%d-%H%M%S).log
END_TIME=$(date +%s)

ELAPSED=$((END_TIME - START_TIME))
echo ""
echo "=== Cleanup Complete (${ELAPSED} seconds) ==="

# Verification
echo ""
echo "=== Post-cleanup verification ==="
NEW_SIZE=$(du -sh .git 2>/dev/null | cut -f1)
echo "New .git size: $NEW_SIZE"

echo ""
echo "Checking remaining large blobs (>1MB):"
git rev-list --objects --all | \
    git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
    awk '$1 == "blob" && $3 > 1048576 {print $3, $4}' | \
    sort -rn | \
    head -10 | \
    while read size path; do
        mb=$((size / 1048576))
        echo "  ${mb}MB: $path"
    done

echo ""
echo "Remaining object count:"
git count-objects -vH

echo ""
echo "=== Ready to push ==="
echo "Run these commands when ready:"
echo ""
echo "  git push --force --all origin"
echo "  git push --force --tags origin"
