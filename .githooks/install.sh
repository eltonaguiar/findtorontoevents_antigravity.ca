#!/usr/bin/env bash
# Install Redis-bus git hooks for this clone.
#
# Usage: bash .githooks/install.sh
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$REPO_ROOT" ]; then
    echo "ERROR: not inside a git repository"
    exit 1
fi

cd "$REPO_ROOT"

# Point git at our hooks directory
git config core.hooksPath .githooks
echo "[install] core.hooksPath = .githooks"

# Make hooks executable
chmod +x .githooks/pre-push 2>/dev/null || true
echo "[install] pre-push hook is executable"

# Suggest AGENT_ID
if [ -z "${AGENT_ID:-}" ]; then
    echo ""
    echo "[install] RECOMMENDED: set AGENT_ID in your shell profile so your"
    echo "          own locks don't block your own pushes."
    echo ""
    echo "          Add to ~/.bashrc or ~/.zshrc:"
    echo "              export AGENT_ID=\"your-agent-id\""
    echo ""
    echo "          Example names: claude-opus-scoring, antigrav-dash, cursor-audit"
fi

# Test Redis connectivity
REDIS_CLI="${REDIS_CLI:-C:/Users/zerou/redis-bus/redis-cli.exe}"
if command -v "$REDIS_CLI" >/dev/null 2>&1 || [ -x "$REDIS_CLI" ]; then
    PING=$("$REDIS_CLI" -p 6379 PING 2>/dev/null || echo "FAIL")
    if [ "$PING" = "PONG" ]; then
        echo "[install] Redis bus reachable — lock checks will run on push"
    else
        echo "[install] WARNING: Redis bus not reachable (hook will skip silently)"
    fi
else
    echo "[install] WARNING: redis-cli not found at $REDIS_CLI (hook will skip silently)"
fi

echo ""
echo "[install] DONE. Pre-push hook is active for this clone."
echo "          Bypass with: BUS_HOOK_SKIP=1 git push"
