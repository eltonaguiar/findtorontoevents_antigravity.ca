"""Per-strategy Herfindahl-Hirschman symbol-concentration index.

Why this exists
---------------
The forward-edge audit already shows a `top-3 conc%` column per strategy
— useful but blunt. A strategy with top-3 = 100% might be evenly spread
across three symbols (effectively 3-symbol diversified) OR concentrated
90% on one symbol with two tiny tails (effectively 1-symbol). The HHI
distinguishes these cases; top-N share doesn't.

This module computes the formal economic-concentration metric:

    HHI = sum( share_i^2 ) * 10000        (range: 10000/n_symbols .. 10000)
    effective_n = 1 / sum( share_i^2 )    (interpretable "feels like trading N")

where `share_i` is the fraction of the strategy's closed picks that
went to symbol i.

A strategy with HHI > 5000 is "single-symbol dominated" — that's the
DOJ/FTC market-concentration threshold for highly concentrated, applied
analogously here. Surfaced via `flag_single_symbol_dominated`.

Output per strategy
-------------------
- `n_picks`          total usable picks
- `n_unique_symbols` count of distinct symbols
- `hhi`              0–10000
- `effective_n_symbols`  reciprocal of sum-of-squares
- `top1_share_pct`   share of the most-traded symbol
- `top3_share_pct`   share of the top-3 symbols combined
- `flag_single_symbol_dominated`  True iff hhi > 5000

Wiring status: OPT-IN SIDECAR. Future PR adds a `concentration` column
to `audit_dashboard/template.html` strategy table sourcing
`tools/data/symbol_concentration_results.json`.

Caveats
-------
1. Pure count-based HHI: ignores PnL contribution per symbol. A strategy
   that emits 50/50 BTC/ETH but earns 99% of its PnL on BTC has
   evenly-distributed counts but concentrated PnL. PnL-weighted HHI is
   a future enhancement.
2. Like every closed-pick supplement, fits on labels from
   outcome_resolver.py — no contamination here, just count-based math.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "symbol_concentration_results.json"

DEFAULT_MIN_N = 20
DEFAULT_HHI_FLAG = 5000.0  # DOJ/FTC analog: highly concentrated above this


def compute_concentration(symbol_counts: Counter,
                          flag_threshold: float = DEFAULT_HHI_FLAG) -> dict[str, Any]:
    """Pure function: Counter of symbol -> {hhi, effective_n, etc.}."""
    n_picks = sum(symbol_counts.values())
    if n_picks == 0:
        return {
            "n_picks": 0, "n_unique_symbols": 0,
            "hhi": 0.0, "effective_n_symbols": 0.0,
            "top1_share_pct": 0.0, "top3_share_pct": 0.0,
            "flag_single_symbol_dominated": False,
        }
    shares = [c / n_picks for c in symbol_counts.values()]
    sum_sq = sum(s * s for s in shares)
    hhi = sum_sq * 10000.0
    effective_n = (1.0 / sum_sq) if sum_sq > 1e-12 else 0.0
    top_shares_desc = sorted(shares, reverse=True)
    top1 = top_shares_desc[0] * 100.0 if top_shares_desc else 0.0
    top3 = sum(top_shares_desc[:3]) * 100.0
    return {
        "n_picks": int(n_picks),
        "n_unique_symbols": int(len(symbol_counts)),
        "hhi": round(hhi, 4),
        "effective_n_symbols": round(effective_n, 4),
        "top1_share_pct": round(top1, 4),
        "top3_share_pct": round(top3, 4),
        "flag_single_symbol_dominated": hhi > flag_threshold,
    }


def analyze_strategy(picks: list[dict],
                     min_n: int = DEFAULT_MIN_N,
                     flag_threshold: float = DEFAULT_HHI_FLAG) -> dict | None:
    """Per-strategy concentration. Returns None when n < min_n.

    Picks with missing or non-string symbol field are skipped.
    """
    counts: Counter = Counter()
    for p in picks:
        sym = p.get("symbol")
        if not isinstance(sym, str) or not sym:
            continue
        counts[sym] += 1
    if sum(counts.values()) < min_n:
        return None
    return compute_concentration(counts, flag_threshold)


def analyze_all(picks: list[dict],
                min_n: int = DEFAULT_MIN_N,
                flag_threshold: float = DEFAULT_HHI_FLAG) -> dict:
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_strategy[p.get("strategy") or "unknown"].append(p)

    out: list[dict] = []
    for strat, sub in by_strategy.items():
        r = analyze_strategy(sub, min_n, flag_threshold)
        if r is None:
            continue
        r["strategy"] = strat
        out.append(r)
    out.sort(key=lambda r: -r["hhi"])

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"min_n": min_n, "flag_threshold_hhi": flag_threshold},
        "n_strategies": len(out),
        "n_single_symbol_dominated": sum(
            1 for r in out if r["flag_single_symbol_dominated"]),
        "strategies": out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--flag-hhi", type=float, default=DEFAULT_HHI_FLAG)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.min_n, args.flag_hhi)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.quiet:
        print(f"strategies analysed: {summary['n_strategies']}")
        print(f"single-symbol-dominated (hhi > {args.flag_hhi:.0f}): "
              f"{summary['n_single_symbol_dominated']}")
        print("top 10 by HHI:")
        for r in summary["strategies"][:10]:
            flag = "DOM " if r["flag_single_symbol_dominated"] else " ok "
            print(f"  [{flag}] {r['strategy'][:30]:<30} "
                  f"hhi={r['hhi']:>7.0f} eff_N={r['effective_n_symbols']:>5.2f} "
                  f"top1={r['top1_share_pct']:>5.1f}% n={r['n_picks']}")
        print(f"JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
