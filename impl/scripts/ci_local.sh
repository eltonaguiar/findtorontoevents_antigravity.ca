#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMPL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${IMPL_ROOT}"

echo "[ci_local] Running syntax checks..."
python -m py_compile alpha_engine/stat_tests.py alpha_engine/policy_eval.py

echo "[ci_local] Running unit tests..."
pytest -q tests/test_stat_tests.py

echo "[ci_local] OK"
