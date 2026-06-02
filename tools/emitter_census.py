#!/usr/bin/env python3
"""Top emitters by volume and raw PF per asset class (EAGLE2 C1).

Reads alpha_engine/data/closed_picks.json (or policy-clean via build_pf_registry when available).
Writes reports/emitter_census_latest.json

Usage:
  python3 tools/emitter_census.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLOSED = ROOT / "alpha_engine" / "data" / "closed_picks.json"
OUT = ROOT / "reports" / "emitter_census_latest.json"

CLOSED_STATUSES = frozenset({"WON", "LOST", "CLOSED", "EXPIRED", "WIN", "LOSS"})


def _pf(wins_pnl: float, loss_pnl: float) -> float | None:
    if loss_pnl <= 0:
        return round(wins_pnl, 4) if wins_pnl > 0 else 0.0
    return round(wins_pnl / loss_pnl, 4)


def main() -> int:
    if not CLOSED.exists():
        print(f"No {CLOSED}", file=sys.stderr)
        return 1
    rows = json.loads(CLOSED.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        print("closed_picks.json not a list", file=sys.stderr)
        return 1

    by_class: dict[str, dict] = defaultdict(lambda: {
        "n": 0, "sources": Counter(), "strategies": Counter(),
        "win_pnl": 0.0, "loss_pnl": 0.0, "wins": 0,
    })

    for p in rows:
        st = str(p.get("status") or "").upper()
        if st not in CLOSED_STATUSES:
            continue
        ac = str(p.get("asset_class") or "UNKNOWN").upper()
        src = str(p.get("source_system") or "unknown")
        strat = str(p.get("strategy") or "unknown")
        pnl = float(p.get("pnl_pct") or 0)
        cell = by_class[ac]
        cell["n"] += 1
        cell["sources"][src] += 1
        cell["strategies"][strat] += 1
        if pnl > 0:
            cell["wins"] += 1
            cell["win_pnl"] += pnl
        else:
            cell["loss_pnl"] += abs(pnl)

    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(CLOSED),
        "note": "Raw closed_picks — not policy-clean; use money_ready_verdict for sizing.",
        "by_asset_class": {},
    }

    for ac, cell in sorted(by_class.items()):
        n = cell["n"]
        top_src, top_src_n = cell["sources"].most_common(1)[0] if cell["sources"] else ("", 0)
        top_st, top_st_n = cell["strategies"].most_common(1)[0] if cell["strategies"] else ("", 0)
        report["by_asset_class"][ac] = {
            "n": n,
            "wr_pct": round(100.0 * cell["wins"] / n, 1) if n else 0,
            "pf_raw": _pf(cell["win_pnl"], cell["loss_pnl"]),
            "top_source": top_src,
            "top_source_share": round(top_src_n / n, 4) if n else 0,
            "top_strategy": top_st,
            "top_strategy_share": round(top_st_n / n, 4) if n else 0,
            "top_sources": [
                {"source": s, "n": c, "share": round(c / n, 4)}
                for s, c in cell["sources"].most_common(8)
            ],
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    for ac, v in report["by_asset_class"].items():
        print(
            f"  {ac}: n={v['n']} pf={v['pf_raw']} "
            f"top_src={v['top_source']} ({v['top_source_share']*100:.0f}%)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())