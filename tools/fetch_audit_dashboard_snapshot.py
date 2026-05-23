#!/usr/bin/env python3
"""Download live /audit/data/dashboard_data.json into tools/data/snapshots/.

Use for reproducible analysis aligned with findtorontoevents.ca/audit (plan: snapshot-json).
Default URL: https://findtorontoevents.ca/audit/data/dashboard_data.json
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parent.parent
SNAP_DIR = REPO / "tools" / "data" / "snapshots"
DEFAULT_URL = "https://findtorontoevents.ca/audit/data/dashboard_data.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch live audit dashboard_data.json snapshot")
    ap.add_argument("--url", default=DEFAULT_URL, help="JSON URL")
    ap.add_argument(
        "--out-dir",
        default=str(SNAP_DIR),
        help="Directory for dashboard_data_<UTC>.json",
    )
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / ("dashboard_data_%s.json" % ts)

    req = Request(args.url, headers={"User-Agent": "findtorontoevents-audit-snapshot/1.0"})
    try:
        with urlopen(req, timeout=120) as resp:
            body = resp.read()
    except Exception as e:
        print("fetch failed: %s" % e, file=sys.stderr)
        return 1

    out_path.write_bytes(body)
    print("wrote %s (%d bytes)" % (out_path, len(body)))
    print("analyze with: python tools/analyze_audit_active_book.py --dashboard %s" % out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
