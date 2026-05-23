"""Per-strategy realised-vs-declared transaction-cost realism check.

Why this exists
---------------
`tools/capacity_estimator.py` computes capacity assuming the per-asset-
class TC declared in `tools/data/transaction_costs.json`. If the
realised TC paid by a strategy is materially higher than declared, the
capacity column lies — the strategy will erode its edge faster than
the dashboard suggests.

This module flags strategies whose IMPLIED realised TC exceeds the
declared per-class TC by > 50%. It uses a back-of-envelope proxy:

    cost_free_proxy = (winners_mean - losers_mean) * win_rate
    realised        = mean(pnl_pct)
    implied_tc_pct  = max(0, cost_free_proxy - realised)

Interpretation: `cost_free_proxy` is the spread between average-win and
average-loss, weighted by win-rate — a "best-case if friction were zero"
expected return. If the strategy's actual mean falls materially below
this hypothetical, the gap is a proxy for friction (TC, slippage,
adverse selection on fills, etc.).

This is NOT an exact TC measurement (real TC requires fill-level data
the dashboard doesn't carry), but it surfaces the kind of strategies
where realised friction is suspiciously high — a leading indicator
for "the audit page's after-cost numbers are too rosy."

Output per strategy
-------------------
- n, asset_class
- mean_pnl_pct (realised), winners_mean, losers_mean, win_rate
- cost_free_proxy_pct, implied_tc_pct
- declared_tc_pct (from tools/data/transaction_costs.json)
- ratio_implied_to_declared
- flag_under_reported_friction (ratio > 1.5)

Wiring status: OPT-IN SIDECAR. Future PR adds a `friction realism`
column to `audit_dashboard/template.html` strategy table sourcing
`tools/data/slippage_realism_results.json`.

Caveats
-------
1. The cost_free_proxy is a hand-wavy upper bound, not a true gross-PnL
   estimate. Strategies with negative win_rate * losers_mean (e.g. all
   losers) will produce negative or zero cost_free_proxy and the
   implied TC will clamp to 0.
2. Doesn't account for asymmetric costs (taker fees on entry vs maker
   fees on exit). Pure round-trip estimate.
3. Like every closed-pick supplement, fits on labels from
   outcome_resolver.py.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
TC_PATH = REPO_ROOT / "tools" / "data" / "transaction_costs.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "slippage_realism_results.json"

DEFAULT_MIN_N = 20
DEFAULT_FLAG_RATIO = 1.5


def _safe_pnl(pick: dict) -> float | None:
    pnl = pick.get("pnl_pct")
    if pnl is None:
        return None
    try:
        v = float(pnl)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def load_declared_tc(tc_path: Path = TC_PATH) -> dict[str, float]:
    """Return {asset_class -> declared cost_pct}.

    Empty dict when file missing — analyse falls back to declared_tc=0,
    which means no flag (we can't evaluate without a baseline).
    """
    if not tc_path.exists():
        return {}
    try:
        with tc_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    costs = data.get("costs") if isinstance(data, dict) else None
    if not isinstance(costs, dict):
        return {}
    out: dict[str, float] = {}
    for klass, info in costs.items():
        if not isinstance(klass, str) or not isinstance(info, dict):
            continue
        cost_pct = info.get("cost_pct")
        if cost_pct is None:
            cost_bps = info.get("cost_bps")
            if isinstance(cost_bps, (int, float)):
                cost_pct = float(cost_bps) / 100.0
        if isinstance(cost_pct, (int, float)) and math.isfinite(cost_pct):
            out[klass.upper()] = float(cost_pct)
    return out


def analyze_strategy(picks: list[dict],
                      declared_tc: dict[str, float],
                      min_n: int = DEFAULT_MIN_N,
                      flag_ratio: float = DEFAULT_FLAG_RATIO) -> dict | None:
    pnls: list[float] = []
    klass = "UNKNOWN"
    for p in picks:
        pnl = _safe_pnl(p)
        if pnl is None:
            continue
        pnls.append(pnl)
        klass = (p.get("asset_class") or klass).upper()
    if len(pnls) < min_n:
        return None

    n = len(pnls)
    wins = [v for v in pnls if v > 0]
    losses = [v for v in pnls if v <= 0]
    win_rate = len(wins) / n
    mean_pnl = sum(pnls) / n
    winners_mean = (sum(wins) / len(wins)) if wins else 0.0
    losers_mean = (sum(losses) / len(losses)) if losses else 0.0

    cost_free_proxy = (winners_mean - losers_mean) * win_rate
    implied_tc = max(0.0, cost_free_proxy - mean_pnl)
    declared = declared_tc.get(klass)
    ratio = (implied_tc / declared) if (declared and declared > 0) else None

    return {
        "n": int(n),
        "asset_class": klass,
        "mean_pnl_pct": round(mean_pnl, 6),
        "winners_mean_pct": round(winners_mean, 6),
        "losers_mean_pct": round(losers_mean, 6),
        "win_rate": round(win_rate, 4),
        "cost_free_proxy_pct": round(cost_free_proxy, 6),
        "implied_tc_pct": round(implied_tc, 6),
        "declared_tc_pct": (round(declared, 6) if declared is not None else None),
        "ratio_implied_to_declared": (round(ratio, 4) if ratio is not None else None),
        "flag_under_reported_friction": bool(
            ratio is not None and ratio > flag_ratio
        ),
    }


def analyze_all(picks: list[dict],
                min_n: int = DEFAULT_MIN_N,
                flag_ratio: float = DEFAULT_FLAG_RATIO,
                tc_path: Path = TC_PATH) -> dict:
    declared = load_declared_tc(tc_path)
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_strategy[p.get("strategy") or "unknown"].append(p)

    out: list[dict] = []
    for strat, sub in by_strategy.items():
        r = analyze_strategy(sub, declared, min_n, flag_ratio)
        if r is None:
            continue
        r["strategy"] = strat
        out.append(r)
    out.sort(key=lambda r: -(r["ratio_implied_to_declared"] or 0))

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"min_n": min_n, "flag_ratio": flag_ratio,
                   "declared_tc_by_class": declared},
        "n_strategies": len(out),
        "n_under_reported_friction": sum(
            1 for r in out if r["flag_under_reported_friction"]),
        "strategies": out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--flag-ratio", type=float, default=DEFAULT_FLAG_RATIO)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.min_n, args.flag_ratio)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.quiet:
        print(f"strategies analysed: {summary['n_strategies']}")
        print(f"under-reported friction: {summary['n_under_reported_friction']}")
        for r in summary["strategies"][:10]:
            ratio = (f"{r['ratio_implied_to_declared']:.2f}"
                     if r['ratio_implied_to_declared'] is not None else "n/a")
            flag = "FLAG" if r["flag_under_reported_friction"] else " ok "
            print(f"  [{flag}] {r['strategy'][:30]:<30} {r['asset_class']:<10} "
                  f"implied={r['implied_tc_pct']:>+5.3f}% declared="
                  f"{r['declared_tc_pct']} ratio={ratio} n={r['n']}")
        print(f"JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
