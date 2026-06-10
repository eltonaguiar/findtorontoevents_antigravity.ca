#!/usr/bin/env bash
# Apply Copilot model-picker fix on gx10 + push to Windows via cross-PC gateway.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CODE_CLI="$(ls -1 "$HOME"/.vscode-server/cli/servers/Stable-*/server/bin/remote-cli/code 2>/dev/null | sort -V | tail -1)"

echo "[1/3] Install DeepSeek V4 for Copilot extension (remote)"
"$CODE_CLI" --install-extension Vizards.deepseek-v4-for-copilot --force

echo "[2/3] Write BYOK config from ~/dbpasses.txt (all providers)"
python3 "$REPO_ROOT/tools/fix_windows_copilot_lm.py"

echo "[3/3] Done."