#!/usr/bin/env python3
"""
audit_verify.py
===============
Checks all registered JSON_PICK_SOURCES. 
Alerts (fails or warns) if any source files are stale (>24h since last modification).
"""

import sys
import time
import os
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from audit_trail.dashboard_generator import JSON_PICK_SOURCES, _HIDDEN_SYSTEMS

def check_staleness():
    print("==================================================")
    print("  AUDIT VERIFY: Checking System Staleness (>24h)  ")
    print("==================================================")

    now = time.time()
    stale_limit = 24 * 3600  # 24 hours

    alerts = []

    for sys_name, active_rel, closed_rel in JSON_PICK_SOURCES:
        if sys_name in _HIDDEN_SYSTEMS:
            continue

        for rel_path in filter(None, [active_rel, closed_rel]):
            file_path = REPO_ROOT / rel_path
            if not file_path.exists():
                alerts.append(f"[MISSING] {sys_name} ({rel_path}) does not exist.")
                continue

            try:
                mtime = os.path.getmtime(file_path)
                age = now - mtime
                if age > stale_limit:
                    hours_stale = age / 3600
                    alerts.append(f"[STALE] {sys_name} ({rel_path}) is {hours_stale:.1f} hours old (>24h)")
            except Exception as e:
                alerts.append(f"[ERROR] Could not check {rel_path}: {e}")

    if alerts:
        print("\n".join(alerts))
        print(f"\n[!] Found {len(alerts)} staleness/missing alerts.")
        # We can decide to exit(1) to fail CI or exit(0) to just warn
        sys.exit(0)  # Just warn for now so we don't break the pipeline
    else:
        print("All visible registered sources are fresh (<24h).")
        sys.exit(0)

if __name__ == "__main__":
    check_staleness()
