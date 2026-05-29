#!/usr/bin/env python3
"""Ensure audit_dashboard/data/claudes_test_state.json exists for CI/deploy.

The live state file is gitignored (2MB+). Fresh checkouts and GHA runners need
a minimal seed so generate_hourly_update.py and deploy-competition FTP steps
do not fail on FileNotFoundError.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "audit_dashboard" / "data" / "claudes_test_state.json"
SEED_FILE = ROOT / "audit_dashboard" / "data" / "seeds" / "claudes_test_state_min.json"
DASHBOARD_FILE = ROOT / "audit_dashboard" / "data" / "claudes_test_dashboard.json"
DASHBOARD_SEED = ROOT / "audit_dashboard" / "data" / "seeds" / "claudes_test_dashboard_min.json"


def _copy_seed(seed: Path, dest: Path, label: str) -> bool:
    if dest.is_file():
        return False
    if not seed.is_file():
        print(f"ERROR: missing seed {seed}", file=sys.stderr)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(seed, dest)
    print(f"bootstrap: created {label} from {seed.name}")
    return True


def main() -> int:
    created = False
    created |= _copy_seed(SEED_FILE, STATE_FILE, "claudes_test_state.json")
    if DASHBOARD_SEED.is_file():
        created |= _copy_seed(DASHBOARD_SEED, DASHBOARD_FILE, "claudes_test_dashboard.json")
    elif not DASHBOARD_FILE.is_file():
        DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
        DASHBOARD_FILE.write_text(
            json.dumps({"portfolios": [], "generated_at": None}, indent=2) + "\n",
            encoding="utf-8",
        )
        print("bootstrap: created minimal claudes_test_dashboard.json")
        created = True
    if not created:
        print("bootstrap: state files already present — no-op")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
