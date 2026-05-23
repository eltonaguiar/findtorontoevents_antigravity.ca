#!/usr/bin/env python3
"""Background monitor for the 2-hour challenge. Checks every 15 minutes."""
import subprocess
import time
import sys
from datetime import datetime, timezone

TOTAL_CHECKS = 9  # Every 15 min for 2+ hours
INTERVAL = 15 * 60  # 15 minutes in seconds

print(f"CHALLENGE MONITOR STARTED at {datetime.now(timezone.utc).strftime('%H:%M UTC')}")
print(f"Will check every 15 minutes for {TOTAL_CHECKS} rounds")
print("=" * 60)

for i in range(TOTAL_CHECKS):
    if i > 0:
        wait = INTERVAL
        print(f"\n--- Sleeping {wait//60} minutes until next check (#{i+1}/{TOTAL_CHECKS})...")
        time.sleep(wait)

    print(f"\n{'='*60}")
    print(f"CHECK #{i+1} at {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")
    print(f"{'='*60}")

    result = subprocess.run(
        [sys.executable, "live_2hr_challenge.py", "check"],
        capture_output=False
    )

print("\n\nCHALLENGE COMPLETE! Final results above.")
