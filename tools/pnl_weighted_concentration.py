"""PnL-weighted Herfindahl concentration — closes the count-only caveat.

Why this exists
---------------
`tools/symbol_concentration_index.py` computes a count-based HHI per
strategy and explicitly documents this as a caveat: a strategy that
emits 50/50 BTC/ETH but earns 99% of its PnL on BTC has evenly-
distributed counts but concentrated PnL.

This module computes the COMPLEMENT: HHI weighted by per-symbol
|sum(pnl)| share. Combined with the count-based HHI, it surfaces the
dispositive "hidden concentration" pattern: a strategy whose count-HHI
is moderate but whose PnL-HHI is severe is making its money on one
symbol despite trading across many.

Dispositive flag: `pnl_hhi - count_hhi > 2000` fires when the PnL is
materially more concentrated than the trading activity. That gap is
the actionable signal.

Reuses `tools/symbol_concentration_index.py:compute_concentration` via
importlib — just feeds it a dict of `symbol -> summed |pnl_pct|`
instead of a Counter.

Output per strategy
-------------------
- Per-symbol PnL HHI fields:
    pnl_hhi, pnl_effective_n_symbols, pnl_top1_share_pct,
    pnl_top3_share_pct
- Count HHI for comparison: count_hhi
- Concentration GAP: pnl_minus_count_hhi
- Flag: flag_hidden_concentration when GAP > 2000

Wiring status: OPT-IN SIDECAR. Future PR adds a "PnL-conc gap" badge
to `audit_dashboard/template.html` strategy table sourcing
`tools/data/pnl_weighted_concentration_results.json`.

Caveats
-------
1. Uses |pnl_pct| (absolute value) so a strategy that has +99 wins on
   BTC and -1 losses on BTC still attributes 100% to BTC. This is the
   correct interpretation for "where is the trading exposure" but
   would misrepresent "where is the net edge". A signed-net version
   is a future enhancement if needed.
2. Requires both `symbol` and `pnl_pct` on each pick; picks missing
   either are skipped (matches symbol_concentration_index.py).
3. Like every closed-pick supplement, fits on labels from
   outcome_resolver.py — Theme B contamination on FOREX/COMMODITY
   pending the cloud agent's resolver fix.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
OUT_JSON = REPO_ROOT / "tools" / "data" / "pnl_weighted_concentration_results.json"

DEFAULT_MIN_N = 20
DEFAULT_GAP_FLAG = 2000.0  # PnL-HHI - count-HHI threshold for flag


def _load_compute_concentration():
    spec = importlib.util.spec_from_file_location(
        "symbol_concentration_index",
        REPO_ROOT / "tools" / "symbol_concentration_index.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.compute_concentration


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


def _abs_pnl_by_symbol_counter(picks: list[dict]) -> Counter:
    """Build a Counter where the 'count' is integer scaled |pnl_pct|.

    The underlying compute_concentration uses Counter values as raw
    weights: HHI = sum( (count/total)^2 ) * 10000. Counter requires
    integer values, so we scale |pnl_pct| by 1e4 (1bp resolution) and
    round. Resolution is more than enough — HHI computation is
    invariant to common-factor scaling.
    """
    weights: Counter = Counter()
    for p in picks:
        sym = p.get("symbol")
        if not isinstance(sym, str) or not sym:
            continue
        pnl = _safe_pnl(p)
        if pnl is None:
            continue
        scaled = int(round(abs(pnl) * 10000))  # |pnl_pct| in tenths of bp
        if scaled <= 0:
            scaled = 1  # ensure breakeven picks still register the symbol
        weights[sym] += scaled
    return weights


def _count_by_symbol_counter(picks: list[dict]) -> Counter:
    counts: Counter = Counter()
    for p in picks:
        sym = p.get("symbol")
        if not isinstance(sym, str) or not sym:
            continue
        if _safe_pnl(p) is None:
            continue
        counts[sym] += 1
    return counts


def analyze_strategy(picks: list[dict],
                     min_n: int = DEFAULT_MIN_N,
                     gap_threshold: float = DEFAULT_GAP_FLAG,
                     compute_concentration=None) -> dict | None:
    """Per-strategy PnL-weighted HHI vs count-HHI gap analysis."""
    if compute_concentration is None:
        compute_concentration = _load_compute_concentration()

    pnl_weights = _abs_pnl_by_symbol_counter(picks)
    count_weights = _count_by_symbol_counter(picks)
    n_usable = sum(count_weights.values())
    if n_usable < min_n:
        return None

    pnl_conc = compute_concentration(pnl_weights)
    count_conc = compute_concentration(count_weights)
    gap = pnl_conc["hhi"] - count_conc["hhi"]
    flag = gap > gap_threshold

    return {
        "n_picks": int(n_usable),
        "n_unique_symbols": int(len(count_weights)),
        "count_hhi": round(count_conc["hhi"], 4),
        "pnl_hhi": round(pnl_conc["hhi"], 4),
        "pnl_minus_count_hhi": round(gap, 4),
        "pnl_effective_n_symbols": round(pnl_conc["effective_n_symbols"], 4),
        "pnl_top1_share_pct": round(pnl_conc["top1_share_pct"], 4),
        "pnl_top3_share_pct": round(pnl_conc["top3_share_pct"], 4),
        "flag_hidden_concentration": flag,
    }


def analyze_all(picks: list[dict],
                min_n: int = DEFAULT_MIN_N,
                gap_threshold: float = DEFAULT_GAP_FLAG) -> dict:
    compute_concentration = _load_compute_concentration()
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        by_strategy[p.get("strategy") or "unknown"].append(p)

    out: list[dict] = []
    for strat, sub in by_strategy.items():
        r = analyze_strategy(sub, min_n, gap_threshold,
                             compute_concentration=compute_concentration)
        if r is None:
            continue
        r["strategy"] = strat
        out.append(r)
    out.sort(key=lambda r: -r["pnl_minus_count_hhi"])

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "config": {"min_n": min_n,
                   "gap_threshold_hhi": gap_threshold},
        "n_strategies": len(out),
        "n_hidden_concentration": sum(
            1 for r in out if r["flag_hidden_concentration"]),
        "strategies": out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    ap.add_argument("--gap-flag", type=float, default=DEFAULT_GAP_FLAG)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    picks = data.get("picks", {}).get("recent_closed", [])

    summary = analyze_all(picks, args.min_n, args.gap_flag)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    if not args.quiet:
        print(f"strategies analysed: {summary['n_strategies']}")
        print(f"hidden-concentration (gap > {args.gap_flag:.0f}): "
              f"{summary['n_hidden_concentration']}")
        print("top 10 by pnl_minus_count_hhi (positive gap = PnL more concentrated):")
        for r in summary["strategies"][:10]:
            flag = "HID " if r["flag_hidden_concentration"] else " ok "
            print(f"  [{flag}] {r['strategy'][:30]:<30} "
                  f"count_hhi={r['count_hhi']:>5.0f} pnl_hhi={r['pnl_hhi']:>5.0f} "
                  f"gap={r['pnl_minus_count_hhi']:>+5.0f} n={r['n_picks']}")
        print(f"JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
