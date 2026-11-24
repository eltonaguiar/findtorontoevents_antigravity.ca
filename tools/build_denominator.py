"""Write audit_dashboard/data/denominator.json -- the shared population sidecar.

Reads the publisher's canonical view plus the audit3 ledger coverage block and
emits one artifact every surface can print, so a rate can never be quoted without
its population. Exits 2 only when neither input is readable at all; a missing
canonical count is written as null + note (visible), not as a crash.

Usage:
    python3 tools/build_denominator.py
    python3 tools/build_denominator.py --out /tmp/denominator.json --json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
for _p in (str(REPO), str(REPO / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from alpha_engine.denominator import SCHEMA, build  # noqa: E402

DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
LEDGER = REPO / "audit_dashboard" / "data" / "audit3_ledger.json"
OUT = REPO / "audit_dashboard" / "data" / "denominator.json"


def _load(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dashboard", default=str(DASHBOARD))
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--json", action="store_true", help="print the payload")
    args = ap.parse_args(argv)

    dashboard = _load(Path(args.dashboard))
    ledger = _load(Path(args.ledger))
    if dashboard is None and ledger is None:
        print("ERROR: neither dashboard_data.json nor audit3_ledger.json is readable",
              file=sys.stderr)
        return 2

    payload = build(dashboard, ledger,
                    generated_at=datetime.now(timezone.utc).isoformat())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}: {SCHEMA} -- {payload['population_label']}")
    for note in payload["notes"]:
        print(f"::warning::denominator: {note}")
    if args.json:
        print(json.dumps(payload, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
