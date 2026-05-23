#!/bin/bash
set -e
echo "=== Linting configs ==="
python -c "import json; json.load(open('config/hf_conviction_tiers.json'))"
echo "=== Running tests ==="
python -m pytest tests/ -v --tb=short
echo "=== All checks passed ==="
