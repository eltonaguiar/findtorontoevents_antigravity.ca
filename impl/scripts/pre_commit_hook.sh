#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMPL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "[pre-commit] Running impl CI checks..."
"${IMPL_ROOT}/scripts/ci_local.sh"
echo "[pre-commit] Passed."
