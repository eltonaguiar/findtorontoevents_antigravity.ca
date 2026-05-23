#!/usr/bin/env python3
"""Build strategy_symbol_edge_registry.json from audit_dashboard recent_closed (real rows only)."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_DASH = _REPO / "audit_dashboard" / "data" / "dashboard_data.json"
_OUT = _REPO / "alpha_engine" / "data" / "strategy_symbol_edge_registry.json"


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pairs: dict[str, dict] = {}
    if not _DASH.is_file():
        doc = {
            "version": 1,
            "generated_at": ts,
            "note": "dashboard_data.json missing — pairs empty",
            "pairs": {},
        }
        _OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        print("Wrote empty registry (no dashboard)")
        return 0

    data = json.loads(_DASH.read_text(encoding="utf-8", errors="replace"))
    closed = (data.get("picks") or {}).get("recent_closed") or data.get("recent_closed") or []
    if not isinstance(closed, list):
        closed = []

    # (strategy, symbol) -> wins, losses, pnl sum
    agg: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])

    for row in closed:
        if not isinstance(row, dict):
            continue
        strat = str(row.get("strategy") or "").strip()
        sym = str(row.get("symbol") or "").strip().upper().replace("-", "").replace("/", "")
        if not strat or not sym:
            continue
        won = row.get("won")
        if won is None:
            res = str(row.get("result") or row.get("outcome") or "").lower()
            er = str(row.get("exit_reason") or "").upper()
            if res in ("win", "tp", "take_profit", "1", "true"):
                won = True
            elif res in ("loss", "sl", "stop", "0", "false"):
                won = False
            elif "TP" in er or "TAKE" in er:
                won = True
            elif "SL" in er or "STOP" in er:
                won = False
            else:
                try:
                    won = float(row.get("pnl_pct") or 0) > 0
                except (TypeError, ValueError):
                    won = None
        if won is None:
            continue
        try:
            pnl = float(row.get("pnl_pct") or row.get("realized_pnl_pct") or 0)
        except (TypeError, ValueError):
            pnl = 0.0
        key = (strat, sym)
        if won:
            agg[key][0] += 1
        else:
            agg[key][1] += 1
        agg[key][2] += pnl

    for (strat, sym), (w, l, pnl_sum) in agg.items():
        n = int(w + l)
        if n < 5:
            continue
        wr = w / n if n else 0.0
        key_json = "%s|%s" % (strat, sym)
        pairs[key_json] = {
            "n": n,
            "wins": int(w),
            "losses": int(l),
            "wr": round(wr, 4),
            "avg_pnl_pct": round(pnl_sum / n, 4) if n else 0.0,
        }

    doc = {
        "version": 1,
        "generated_at": ts,
        "source_dashboard": str(_DASH),
        "pair_count": len(pairs),
        "pairs": dict(sorted(pairs.items())),
    }
    _OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print("Wrote %d pairs to %s" % (len(pairs), _OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
