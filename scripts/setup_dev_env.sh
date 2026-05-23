#!/bin/bash
# scripts/setup_dev_env.sh
# Reliable dev environment setup for the FindTorontoEvents multi-app codebase.
#
# Usage:  ./scripts/setup_dev_env.sh
#         ./scripts/setup_dev_env.sh --skip-browsers   # skip Playwright download
#
# Apps served locally:
#   /         → Main events site (index.html)
#   /fc/      → FavCreators (Vite-built SPA, pre-built in favcreators/docs/)
#   /audit/   → Audit Dashboard (trading strategy audit)
#   /MENTALHEALTHRESOURCES/ → Mental Health Resources

set -e

SKIP_BROWSERS=false
for arg in "$@"; do
  case "$arg" in
    --skip-browsers) SKIP_BROWSERS=true ;;
  esac
done

echo "=== Development Environment Setup ==="

# --- Prerequisite check ---
MISSING=()
for cmd in git node npm python3 pip; do
  if ! command -v "$cmd" &>/dev/null; then
    MISSING+=("$cmd")
  fi
done
if [ ${#MISSING[@]} -ne 0 ]; then
  echo "ERROR: Missing required tools: ${MISSING[*]}"
  echo "  Install them before running this script."
  exit 1
fi

echo "  node $(node --version), npm $(npm --version), python $(python3 --version 2>&1 | awk '{print $2}')"

# --- Node.js dependencies ---
echo ""
echo "--- Installing Node.js dependencies ---"
npm install

# --- Python dependencies ---
echo ""
echo "--- Installing Python dependencies ---"
pip install -r requirements.txt 2>/dev/null || pip install --user -r requirements.txt

# --- Playwright browsers ---
if [ "$SKIP_BROWSERS" = false ]; then
  echo ""
  echo "--- Installing Playwright Chromium browser ---"
  npx playwright install chromium
else
  echo ""
  echo "--- Skipping Playwright browser install (--skip-browsers) ---"
fi

# --- Validate critical files ---
echo ""
echo "--- Validating critical Python scripts ---"
python3 -c "import py_compile; py_compile.compile('tools/serve_local.py', doraise=True)" \
  && echo "  tools/serve_local.py: OK" \
  || echo "  tools/serve_local.py: SYNTAX ERROR"

# --- Verify FavCreators build output exists ---
if [ -f "favcreators/docs/index.html" ]; then
  echo "  favcreators/docs/index.html: OK (pre-built)"
else
  echo "  WARNING: favcreators/docs/index.html missing (FavCreators will not load locally)"
fi

# --- Verify audit dashboard exists ---
if [ -f "audit_dashboard/index.html" ]; then
  echo "  audit_dashboard/index.html: OK"
else
  echo "  WARNING: audit_dashboard/index.html missing"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Start the local dev server:"
echo "  python3 tools/serve_local.py"
echo ""
echo "Then visit:"
echo "  Main site:           http://127.0.0.1:5173/"
echo "  FavCreators:         http://127.0.0.1:5173/fc/"
echo "  Audit Dashboard:     http://127.0.0.1:5173/audit/"
echo "  Mental Health:       http://127.0.0.1:5173/MENTALHEALTHRESOURCES/"
echo ""
echo "Run Playwright tests:"
echo "  npx playwright test tests/mental-health-resources.spec.ts --project='Desktop Chrome'"
