#!/usr/bin/env bash
# Workflow Health Check — failures + chronic cancellation scan (see Python).
# Requires: gh, python3
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR"
exec python3 "$(dirname "$0")/workflow_health_check.py" "$@"
