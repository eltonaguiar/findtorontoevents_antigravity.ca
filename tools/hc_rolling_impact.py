"""
Rolling-window impact analysis for High-Conviction picks.

Sorts closed picks chronologically; for each asset class, takes last N (10, 20, 30).
Computes WR, mean pnl_pct, PF, Sortino.
Second slice: same windows restricted to passes_high_conviction_pick.
70/30 simulation: deterministic blend 0.7 * mean(HC) + 0.3 * mean(baseline).

Usage:
    python tools/hc_rolling_impact.py [--data PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DATA = REPO / "audit_dashboard" / "data" / "dashboard_data.json"

WINDOWS = [10, 20, 30]


def _load_data(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _ts_ms(p: dict) -> float:
    """Best-effort timestamp extraction for chronological sorting."""
    for key in ("closed_at", "close_time", "resolved_at", "updated_at", "created_at", "entry_time"):
        v = p.get(key)
        if v:
            try:
                # ISO string or numeric
                if isinstance(v, (int, float)):
                    return float(v)
                # Simple ISO parse fallback
                import datetime
                dt = datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
                return dt.timestamp() * 1000
            except Exception:
                continue
    return 0.0


def _normalize_asset_class(p: dict) -> str:
    ac = str(p.get("asset_class") or p.get("asset_class_type") or "").upper()
    if ac in ("STOCKS", "PENNY_STOCK", "EQUITIES"):
        ac = "EQUITY"
    if ac == "COMMODITIES":
        ac = "COMMODITY"
    if not ac:
        # Infer from symbol for crypto
        sym = str(p.get("symbol") or "").upper()
        if sym.endswith("USDT") or sym.endswith("USD") or sym.endswith("BTC") or sym.endswith("ETH"):
            ac = "CRYPTO"
        else:
            ac = "UNKNOWN"
    return ac


def _summarize(picks: list[dict]) -> dict[str, Any]:
    if not picks:
        return {"n": 0, "wr": None, "mean_pnl": None, "pf": None, "sortino": None}
    pnls = []
    wins = 0
    losses = 0
    for p in picks:
        pnl = p.get("pnl_pct")
        try:
            pnl = float(pnl) if pnl is not None else 0.0
        except (TypeError, ValueError):
            pnl = 0.0
        pnls.append(pnl)
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1
    resolved = wins + losses
    wr = (wins / resolved) if resolved > 0 else None

    mean_pnl = sum(pnls) / len(pnls)

    # PF
    gains = sum(x for x in pnls if x > 0)
    losses_sum = abs(sum(x for x in pnls if x < 0))
    pf = (gains / losses_sum) if losses_sum > 0 else (99.9 if gains > 0 else 0.0)

    # Sortino-like
    import math
    downs = [0.0 - x for x in pnls if x < 0.0]
    sortino = None
    if downs:
        dvar = sum(d * d for d in downs) / len(downs)
        dsd = math.sqrt(dvar) if dvar > 0 else None
        if dsd:
            sortino = mean_pnl / dsd

    return {
        "n": len(picks),
        "wr": round(wr, 4) if wr is not None else None,
        "mean_pnl": round(mean_pnl, 4),
        "pf": round(pf, 4),
        "sortino": round(sortino, 4) if sortino is not None else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rolling-window HC impact analysis")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Path to dashboard_data.json")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path")
    args = parser.parse_args()

    data = _load_data(args.data)
    picks = data.get("picks", {})
    closed = picks.get("recent_closed", picks.get("closed_picks", []))

    # Sort chronologically (most recent last)
    closed_sorted = sorted(closed, key=_ts_ms)

    # Load Python HC filter
    sys.path.insert(0, str(REPO))
    from tools.dashboard_hc_rules import passes_high_conviction_pick

    # Group by asset class
    by_ac: dict[str, list[dict]] = {}
    for p in closed_sorted:
        ac = _normalize_asset_class(p)
        by_ac.setdefault(ac, []).append(p)

    report: dict[str, Any] = {"source": str(args.data), "total_closed": len(closed), "windows": {}}

    for n in WINDOWS:
        report["windows"][f"last_{n}"] = {}
        for ac, ac_picks in sorted(by_ac.items()):
            slice_picks = ac_picks[-n:]
            if not slice_picks:
                continue
            baseline = _summarize(slice_picks)
            hc_picks = [p for p in slice_picks if passes_high_conviction_pick(p)]
            hc = _summarize(hc_picks)

            # 70/30 blend (deterministic, not Monte Carlo)
            blend_mean = None
            if baseline["mean_pnl"] is not None and hc["mean_pnl"] is not None:
                blend_mean = round(0.7 * hc["mean_pnl"] + 0.3 * baseline["mean_pnl"], 4)

            report["windows"][f"last_{n}"][ac] = {
                "baseline": baseline,
                "hc": hc,
                "blend_70_30_mean_pnl": blend_mean,
            }

    # Overall (all asset classes combined)
    for n in WINDOWS:
        slice_all = closed_sorted[-n:]
        baseline_all = _summarize(slice_all)
        hc_all = _summarize([p for p in slice_all if passes_high_conviction_pick(p)])
        blend_all = None
        if baseline_all["mean_pnl"] is not None and hc_all["mean_pnl"] is not None:
            blend_all = round(0.7 * hc_all["mean_pnl"] + 0.3 * baseline_all["mean_pnl"], 4)
        report["windows"][f"last_{n}"]["ALL"] = {
            "baseline": baseline_all,
            "hc": hc_all,
            "blend_70_30_mean_pnl": blend_all,
        }

    print(json.dumps(report, indent=2))

    if args.out:
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport written to {args.out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
