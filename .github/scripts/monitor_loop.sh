#!/usr/bin/env bash
# 8-hour monitoring loop — checks workflows every hour
# Usage: bash .github/scripts/monitor_loop.sh

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR"

HOURS=8
INTERVAL=3600  # 1 hour in seconds
CHECKS=$((HOURS))

echo "Starting $HOURS-hour workflow monitoring (checking every hour)..."
echo "Start time: $(date -u '+%Y-%m-%d %H:%M UTC')"
echo ""

for i in $(seq 1 $CHECKS); do
    echo ""
    echo "=== Check $i/$CHECKS ==="
    python .github/scripts/workflow_health_check.py 2>/dev/null
    EXIT=$?

    if [ $EXIT -eq 0 ]; then
        echo "ALL WORKFLOWS HEALTHY - monitoring complete!"
        exit 0
    fi

    if [ $i -lt $CHECKS ]; then
        echo "Next check in 1 hour..."
        sleep $INTERVAL
    fi
done

echo ""
echo "8-hour monitoring complete. Final status above."
