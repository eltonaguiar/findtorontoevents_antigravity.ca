#!/bin/bash
# scripts/verify_dev_env.sh
# Verify the development environment is correctly set up and ready to use.
#
# Exit code 0 = all checks pass. Non-zero = something is wrong.
# Use after setup_dev_env.sh or as a CI health check.

PASS=0
WARN=0
FAIL=0

check() {
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "  PASS  $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $label"
    FAIL=$((FAIL + 1))
  fi
}

warn_check() {
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "  PASS  $label"
    PASS=$((PASS + 1))
  else
    echo "  WARN  $label"
    WARN=$((WARN + 1))
  fi
}

echo "=== Development Environment Verification ==="
echo ""

# ── Required binaries ──
echo "--- Required Tools ---"
check "node installed" command -v node
check "npm installed" command -v npm
check "python3 installed" command -v python3
check "pip installed" command -v pip
check "git installed" command -v git

# ── Node.js dependencies ──
echo ""
echo "--- Node.js Dependencies ---"
check "node_modules exists" test -d node_modules
check "@playwright/test installed" test -d node_modules/@playwright
check "acorn installed" test -d node_modules/acorn

# ── Python dependencies ──
echo ""
echo "--- Python Dependencies ---"
check "pandas importable" python3 -c "import pandas"
check "numpy importable" python3 -c "import numpy"
check "requests importable" python3 -c "import requests"

# ── Critical files ──
echo ""
echo "--- Critical Files ---"
check "tools/serve_local.py exists" test -f tools/serve_local.py
check "tools/serve_local.py valid syntax" python3 -c "import py_compile; py_compile.compile('tools/serve_local.py', doraise=True)"
check "favcreators/docs/index.html exists" test -f favcreators/docs/index.html
check "audit_dashboard/index.html exists" test -f audit_dashboard/index.html
check "audit_dashboard/template.html exists" test -f audit_dashboard/template.html
check "playwright.config.ts exists" test -f playwright.config.ts

# ── Dashboard data ──
echo ""
echo "--- Dashboard Data ---"
check "dashboard_data.json exists" test -f audit_dashboard/data/dashboard_data.json
warn_check "context_rankings.json exists" test -f data/context_rankings.json

# ── Playwright browser ──
echo ""
echo "--- Playwright Browser ---"
warn_check "Chromium installed" npx playwright install --dry-run chromium

# ── Port availability ──
echo ""
echo "--- Port Availability ---"
if command -v ss >/dev/null 2>&1; then
  if ss -tlnp 2>/dev/null | grep -q ":5173 "; then
    echo "  WARN  Port 5173 already in use (dev server may be running)"
    WARN=$((WARN + 1))
  else
    echo "  PASS  Port 5173 is free"
    PASS=$((PASS + 1))
  fi
elif command -v lsof >/dev/null 2>&1; then
  if lsof -iTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "  WARN  Port 5173 already in use"
    WARN=$((WARN + 1))
  else
    echo "  PASS  Port 5173 is free"
    PASS=$((PASS + 1))
  fi
else
  echo "  WARN  Cannot check port (no ss or lsof)"
  WARN=$((WARN + 1))
fi

# ── Analysis tools ──
echo ""
echo "--- Analysis Tools ---"
warn_check "analysis/score_calibration.py valid" python3 -c "import py_compile; py_compile.compile('analysis/score_calibration.py', doraise=True)"
warn_check "analysis/walkforward_optimizer.py valid" python3 -c "import py_compile; py_compile.compile('analysis/walkforward_optimizer.py', doraise=True)"
warn_check "engine/context_ranking.py valid" python3 -c "import py_compile; py_compile.compile('engine/context_ranking.py', doraise=True)"
warn_check "engine/dynamic_threshold.py valid" python3 -c "import py_compile; py_compile.compile('engine/dynamic_threshold.py', doraise=True)"

# ── Summary ──
echo ""
echo "=== Results ==="
echo "  PASS: $PASS"
echo "  WARN: $WARN"
echo "  FAIL: $FAIL"
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo "RESULT: FAILED — $FAIL checks failed. Run scripts/setup_dev_env.sh to fix."
  exit 1
elif [ "$WARN" -gt 0 ]; then
  echo "RESULT: OK with warnings — environment is usable but not fully optimal."
  exit 0
else
  echo "RESULT: ALL CHECKS PASSED"
  exit 0
fi
