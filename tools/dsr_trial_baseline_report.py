"""Report the per-class trial-count baseline the DSR gate deflates by.

``alpha_engine.money_ready_verdict.NB_TRIALS_BY_CLASS`` holds the number of
independent trials each asset class was searched over. Deflating by 1 applies no
multiple-testing correction, so a baseline must be >= 2 and must not exceed the
number of strategy cells the class was actually tested on (over-counting is as
dishonest as under-counting).

Method: count distinct strategy cells per class in the canonical registry view
``by_asset_class_strategy_policy_clean_net`` (the same book the verdict reads).
``cells_ge_20`` is the count of cells with n >= MIN_N_STRATEGY, the old
source-system-style floor.

Usage:
    python3 tools/dsr_trial_baseline_report.py
    python3 tools/dsr_trial_baseline_report.py --json --strict
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
for _p in (str(REPO), str(REPO / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from alpha_engine.money_ready_verdict import (  # noqa: E402
    CANONICAL_ASSET_CLASSES, NB_TRIALS_BY_CLASS,
)

REGISTRY = REPO / "audit_dashboard" / "data" / "pf_registry.json"
KEY = "by_asset_class_strategy_policy_clean_net"
MIN_N = 20


def measure(registry: dict) -> dict[str, dict]:
    """class -> {cells, cells_ge_20}. Every tested cell is a trial."""
    out: dict[str, dict] = {}
    for row in registry.get(KEY) or []:
        if not isinstance(row, dict):
            continue
        cls = str(row.get("asset_class") or "").upper()
        if not cls:
            continue
        bucket = out.setdefault(cls, {"cells": 0, "cells_ge_20": 0})
        bucket["cells"] += 1
        try:
            n = int(row.get("n") or 0)
        except (TypeError, ValueError):
            n = 0
        if n >= MIN_N:
            bucket["cells_ge_20"] += 1
    return out


def audit(measured: dict[str, dict]) -> list[dict]:
    rows: list[dict] = []
    for cls in sorted(set(CANONICAL_ASSET_CLASSES) | set(measured)
                      | set(NB_TRIALS_BY_CLASS)):
        cells = int(measured.get(cls, {}).get("cells", 0))
        mapped = NB_TRIALS_BY_CLASS.get(cls)
        problems: list[str] = []
        if cells < 2 and mapped is None:
            problems = []          # nothing was tested: skipping DSR is correct
            state = "unmeasured (nothing to deflate)"
        elif mapped is None:
            problems.append("class has tested cells but no baseline -- DSR skips it")
            state = "MISSING"
        elif mapped < 2:
            problems.append(f"baseline {mapped} applies no correction")
            state = "UNDER"
        elif mapped > cells:
            problems.append(f"baseline {mapped} exceeds {cells} tested cells")
            state = "OVER"
        else:
            state = "ok"
        rows.append({"class": cls, "mapped": mapped, "cells": cells,
                     "cells_ge_20": int(measured.get(cls, {}).get("cells_ge_20", 0)),
                     "state": state, "problems": problems})
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", default=str(REGISTRY))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when any class is MISSING/UNDER/OVER")
    args = ap.parse_args(argv)
    try:
        with open(args.registry, encoding="utf-8") as f:
            registry = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"ERROR: cannot read {args.registry}: {exc}", file=sys.stderr)
        return 2
    rows = audit(measure(registry))
    if args.json:
        print(json.dumps(rows, indent=1))
    else:
        print(f"{'class':<14}{'mapped':>7}{'cells':>7}{'>=20':>6}  state")
        for r in rows:
            print(f"{r['class']:<14}{str(r['mapped']):>7}{r['cells']:>7}"
                  f"{r['cells_ge_20']:>6}  {r['state']}"
                  + (f" -- {'; '.join(r['problems'])}" if r["problems"] else ""))
    bad = [r for r in rows if r["state"] in ("MISSING", "UNDER", "OVER")]
    if args.strict and bad:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
