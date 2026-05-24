#!/usr/bin/env bash
# ⚠ DEPRECATED 2026-05-24 — DO NOT RUN THIS SCRIPT.
# Starts a SECOND gateway on the Linux/WSL host, which fragments the bus
# (peers on the canonical 192.168.2.32:8788 never see this one's traffic).
# See tools/GATEWAY_SERVICE_SETUP.md "Part 0" for the silent-failure trap.
# To make this a no-op while preserving git history, the body below now
# exits early before doing anything.
echo "DEPRECATED: do not start a second gateway on Linux. See tools/GATEWAY_SERVICE_SETUP.md Part 0." >&2
exit 1

# chatbible-gateway-start.sh — start or restart the CHATBIBLE gateway
# Usage: bash tools/chatbible-gateway-start.sh
#
# Tries systemd first (preferred — auto-restarts on crash),
# falls back to background process if systemd unavailable.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== CHATBIBLE Gateway Startup ==="

# Check if already running
if curl -sf --max-time 3 http://127.0.0.1:8788/health >/dev/null 2>&1; then
    echo "✓ Gateway already running on :8788"
    curl -s --max-time 3 http://127.0.0.1:8788/health | python3 -c "
import sys, json
d = json.load(sys.stdin)
peers = list(d.get('peer_registry', {}).keys())
print(f'  peers: {len(peers)} — {peers[:5]}')
"
    exit 0
fi

# Try systemd (user service)
if command -v systemctl >/dev/null 2>&1 && systemctl --user is-active chatbible-gateway >/dev/null 2>&1 2>/dev/null; then
    echo "→ Restarting via systemd user service..."
    systemctl --user restart chatbible-gateway
    sleep 2
    if curl -sf --max-time 3 http://127.0.0.1:8788/health >/dev/null 2>&1; then
        echo "✓ Gateway started via systemd"
        exit 0
    fi
fi

# Try to enable and start systemd service
if [ -f "$HOME/.config/systemd/user/chatbible-gateway.service" ]; then
    echo "→ Enabling systemd user service..."
    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user enable chatbible-gateway 2>/dev/null || true
    systemctl --user start chatbible-gateway 2>/dev/null || true
    sleep 3
    if curl -sf --max-time 3 http://127.0.0.1:8788/health >/dev/null 2>&1; then
        echo "✓ Gateway started via systemd (first time)"
        exit 0
    fi
    echo "  systemd start failed, falling back to background process..."
fi

# Fallback: direct background process
echo "→ Starting gateway as background process..."
mkdir -p logs/cross_pc_protocol
nohup /usr/bin/python3 tools/protocol_gateway.py \
    --host 0.0.0.0 --ws-port 8787 --http-port 8788 --peer-id gateway-fallback \
    >> /tmp/chatbible-gateway.log 2>&1 &
GATEWAY_PID=$!
echo "  PID: $GATEWAY_PID (log: /tmp/chatbible-gateway.log)"

# Wait for startup
for i in $(seq 1 10); do
    sleep 1
    if curl -sf --max-time 2 http://127.0.0.1:8788/health >/dev/null 2>&1; then
        echo "✓ Gateway started (background, PID=$GATEWAY_PID)"
        exit 0
    fi
done

echo "✗ Gateway failed to start after 10s. Check /tmp/chatbible-gateway.log"
exit 1
