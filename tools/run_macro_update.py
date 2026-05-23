#!/usr/bin/env python3
"""
Runner for the macro data engine.
Called from cron / GitHub Actions to refresh macro_factors_snapshot.json.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Ensure alpha_engine is importable when running from tools/
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from alpha_engine.macro_data_pipeline import run_macro_pipeline

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run_macro_pipeline()
    print(json.dumps(result, indent=2, default=str))
