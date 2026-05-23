#!/usr/bin/env python3
"""
Backtest passes_high_conviction_pick on closed_picks.json (same heuristics as hc_filter.js).

  python tools/hc_filter_backtest.py [path/to/closed_picks.json]

Python's json decoder accepts NaN/Infinity; use this when Node JSON.parse rejects exports.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "tools") not in sys.path:
    sys.path.insert(0, str(_REPO / "tools"))

from dashboard_hc_rules import passes_high_conviction_pick  # noqa: E402


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else _REPO / "alpha_engine" / "data" / "closed_picks.json"
    if not path.is_file():
        print("Missing %s" % path, file=sys.stderr)
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("Expected JSON array", file=sys.stderr)
        return 1

    n_hc = 0
    wins = 0
    pnl_sum = 0.0
    for p in data:
        if not isinstance(p, dict):
            continue
        if not passes_high_conviction_pick(p):
            continue
        n_hc += 1
        try:
            pnl = float(p.get("pnl_pct") or 0)
        except (TypeError, ValueError):
            pnl = 0.0
        pnl_sum += pnl
        if pnl > 0:
            wins += 1

    wr = (wins / n_hc) if n_hc else None
    exp = (pnl_sum / n_hc) if n_hc else None
    out = {
        "closed_path": str(path),
        "n_total": len(data),
        "n_high_conviction": n_hc,
        "win_rate": round(wr, 4) if wr is not None else None,
        "mean_pnl_pct": round(exp, 6) if exp is not None else None,
        "sum_pnl_pct": round(pnl_sum, 6),
    }
    if n_hc == 0:
        out["warning"] = (
            "No rows passed — common causes: strat_fwd_trades/forward_trades < 5, "
            "elite_score < 50, trust_score < 6."
        )
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
