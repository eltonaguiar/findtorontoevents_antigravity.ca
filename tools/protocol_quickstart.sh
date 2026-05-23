#!/usr/bin/env bash
# tools/protocol_quickstart.sh
# Bootstrap a cross-pc/v1 sender on Linux, WSL, or Git Bash in one command.
# Usage:
#   bash tools/protocol_quickstart.sh                    # defaults: ws://127.0.0.1:8787
#   bash tools/protocol_quickstart.sh cursor-2           # custom peer ID
#   bash tools/protocol_quickstart.sh cursor-2 ws://192.168.1.50:8787 http://192.168.1.50:8788

set -e

SCRIPT_DIR=$(cd -- $(dirname -- $0) && pwd)
REPO_ROOT=$(cd -- $SCRIPT_DIR/.. && pwd)

# Resolve peer ID
if [ -n ${AGENT_ID:-} ]; then
    PEER_ID=$AGENT_ID
elif [ -n ${1:-} ]; then
    PEER_ID=$1
else
    read -p 'Enter peer ID (e.g. cursor-main): ' PEER_ID
fi

WS_URL=${2:-ws://127.0.0.1:8787}
HTTP_BASE=${3:-http://127.0.0.1:8788}

ADAPTER=${ADAPTER:-python}
case $(uname -s) in
    Linux|*-WSL|CYGWIN*|MINGW*|MSYS*) ;;
    *) ADAPTER=python ;;
esac

echo '=== Cross-PC Protocol v1 Quickstart (bash) ==='
echo 'Peer ID  :' $PEER_ID
echo 'WS URL   :' $WS_URL
echo 'HTTP Base:' $HTTP_BASE
echo ''

GREETING=$(date -u '+%H:%M UTC')

echo "[1] Sending test dispatch..."
RESULT=$($ADAPTER $REPO_ROOT/tools/adapters/freebuff_adapter.py --peer-id $PEER_ID --ws-url $WS_URL --http-base $HTTP_BASE dispatch \
    --command "Hello from Cross-PC Protocol v1! Quickstart bootstrap successful. Sent via bash at $GREETING." \
    --workspace $REPO_ROOT --priority 1 2>&1) || true
echo "$RESULT"

echo ''
echo '[2] Sending heartbeat...'
HB_RESULT=$($ADAPTER $REPO_ROOT/tools/adapters/freebuff_adapter.py --peer-id $PEER_ID --ws-url $WS_URL --http-base $HTTP_BASE heartbeat --status ready 2>&1) || true
echo $HB_RESULT

echo ''
echo '[3] Polling for queued messages...'
POLL_RESULT=$($ADAPTER $REPO_ROOT/tools/adapters/freebuff_adapter.py --peer-id $PEER_ID --ws-url $WS_URL --http-base $HTTP_BASE poll --limit 5 2>&1) || true
echo $POLL_RESULT

echo ''
echo '=== Done ==='
echo 'To send a custom message:'
echo '  python tools/adapters/freebuff_adapter.py --peer-id <id> dispatch --command <msg>'
echo ''
echo 'Quickstart complete.'