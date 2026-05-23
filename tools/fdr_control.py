#!/usr/bin/env python3
"""
Benjamini-Hochberg FDR Control for Strategy Win Rates.

HEDGE_FUND_ENHANCEMENT_PLAN.md §1 quick win: **Benjamini–Hochberg FDR** on binomial
p-values (H0: per-strategy win rate = 50%).  Cross-references ``deflated_sharpe_results.json``
when present.

Tests each strategy's win rate with a two-sided binomial p-value, then applies the
BH procedure to control FDR at *alpha*.

Usage:
    python tools/fdr_control.py
    python tools/fdr_control.py --min-trades 15 --alpha 0.05 --redis-alert
    python tools/fdr_control.py --out tools/data/fdr_results.json
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DASHBOARD = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
DEFAULT_DSR = REPO / "tools" / "deflated_sharpe_results.json"
DEFAULT_OUT = REPO / "tools" / "data" / "fdr_results.json"

DEFAULT_MIN_TRADES = 10
DEFAULT_ALPHA = 0.05
DEFAULT_H0_WR = 0.50


def _log_binom_pmf(k: int, n: int, p: float) -> float:
    """Log of binomial PMF: C(n,k) * p^k * (1-p)^(n-k)."""
    return (
        math.lgamma(n + 1)
        - math.lgamma(k + 1)
        - math.lgamma(n - k + 1)
        + k * math.log(p)
        + (n - k) * math.log(1 - p)
    )


def binomial_pvalue_two_sided(wins: int, n: int, p0: float) -> float:
    """Two-sided binomial p-value: P(|X - np0| >= |wins - np0|)."""
    if n == 0:
        return 1.0
    observed_dev = abs(wins - n * p0)
    p_val = 0.0
    for k in range(n + 1):
        if abs(k - n * p0) >= observed_dev - 1e-9:
            p_val += math.exp(_log_binom_pmf(k, n, p0))
    return min(p_val, 1.0)


def benjamini_hochberg(
    pvalues_dict: Dict[str, float], alpha: float
) -> Dict[str, Dict[str, Any]]:
    """BH FDR. Returns strategy -> {p_value, rank, bh_threshold, significant}."""
    items = sorted(pvalues_dict.items(), key=lambda x: x[1])
    m = len(items)
    results: Dict[str, Dict[str, Any]] = {}
    max_significant_rank = 0
    for i, (_strategy, p) in enumerate(items, 1):
        threshold = (i / m) * alpha
        if p <= threshold:
            max_significant_rank = i

    for i, (strategy, p) in enumerate(items, 1):
        results[strategy] = {
            "p_value": round(p, 6),
            "rank": i,
            "bh_threshold": round((i / m) * alpha, 6),
            "significant": i <= max_significant_rank,
        }
    return results


def load_dsr_survivors(dsr_path: Path) -> Set[str]:
    if not dsr_path.is_file():
        return set()
    try:
        with open(dsr_path, "r", encoding="utf-8") as f:
            dsr_data = json.load(f)
    except (OSError, ValueError):
        return set()
    out: Set[str] = set()
    for s in dsr_data.get("all_strategies", []) or []:
        if isinstance(s, dict) and s.get("survives"):
            k = s.get("key")
            if k:
                out.add(str(k))
    return out


def run_fdr(
    dashboard_path: Path,
    dsr_path: Path,
    min_trades: int,
    alpha: float,
    h0_wr: float,
) -> Tuple[Dict[str, Any], int, int, int, int]:
    """Returns (output_dict, n_closed, n_eligible, sig_count, both_count)."""
    with open(dashboard_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    picks = (data.get("picks") or {}).get("recent_closed") or []
    n_closed = len(picks) if isinstance(picks, list) else 0

    by_strategy: Dict[str, Dict[str, int]] = defaultdict(lambda: {"wins": 0, "total": 0})
    for p in picks:
        if not isinstance(p, dict):
            continue
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        strat = str(p.get("strategy") or "unknown") or "unknown"
        by_strategy[strat]["total"] += 1
        try:
            if float(pnl) > 0:
                by_strategy[strat]["wins"] += 1
        except (TypeError, ValueError):
            continue

    eligible = {k: v for k, v in by_strategy.items() if v["total"] >= min_trades}
    n_eligible = len(eligible)

    pvalues: Dict[str, float] = {}
    strategy_stats: Dict[str, Dict[str, Any]] = {}
    for strat, stats in eligible.items():
        p_val = binomial_pvalue_two_sided(stats["wins"], stats["total"], h0_wr)
        pvalues[strat] = p_val
        wr = stats["wins"] / stats["total"] * 100
        strategy_stats[strat] = {
            "wins": stats["wins"],
            "total": stats["total"],
            "wr_pct": round(wr, 1),
        }

    bh_results = benjamini_hochberg(pvalues, alpha)
    dsr_survivors = load_dsr_survivors(dsr_path)

    rows: List[Dict[str, Any]] = []
    for strat in sorted(bh_results.keys(), key=lambda s: bh_results[s]["p_value"]):
        bh = bh_results[strat]
        st = strategy_stats[strat]
        survives_dsr = strat in dsr_survivors
        rows.append(
            {
                "strategy": strat,
                "trades": st["total"],
                "wins": st["wins"],
                "wr_pct": st["wr_pct"],
                "p_value": bh["p_value"],
                "bh_rank": bh["rank"],
                "bh_threshold": bh["bh_threshold"],
                "fdr_significant": bh["significant"],
                "dsr_survives": survives_dsr,
                "both_pass": bh["significant"] and survives_dsr,
            }
        )

    sig_count = sum(1 for r in rows if r["fdr_significant"])
    both_count = sum(1 for r in rows if r["both_pass"])

    output: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_dashboard": str(dashboard_path).replace("\\", "/"),
        "config": {
            "alpha": alpha,
            "h0_wr": h0_wr,
            "min_trades": min_trades,
        },
        "summary": {
            "closed_picks_loaded": n_closed,
            "strategies_tested": len(rows),
            "fdr_significant": sig_count,
            "dsr_survivors": len(dsr_survivors),
            "both_pass": both_count,
        },
        "strategies": rows,
    }
    return output, n_closed, n_eligible, sig_count, both_count


def redis_broadcast(msg: str) -> None:
    bus = Path(r"C:\Users\zerou\redis-bus\agent_bus.py")
    if not bus.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(bus), "broadcast", "cursor-composer", msg],
            check=False,
            timeout=15,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dashboard", type=str, default=str(DEFAULT_DASHBOARD))
    ap.add_argument("--dsr-json", type=str, default=str(DEFAULT_DSR))
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    ap.add_argument("--min-trades", type=int, default=DEFAULT_MIN_TRADES)
    ap.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    ap.add_argument("--h0-wr", type=float, default=DEFAULT_H0_WR)
    ap.add_argument("--redis-alert", action="store_true")
    args = ap.parse_args()

    dash = Path(args.dashboard)
    if not dash.is_file():
        print("ERROR: dashboard not found: %s" % dash, file=sys.stderr)
        return 1

    output, n_closed, n_eligible, sig_count, both_count = run_fdr(
        dash,
        Path(args.dsr_json),
        args.min_trades,
        args.alpha,
        args.h0_wr,
    )

    print("Loaded %s closed picks" % n_closed)
    print("Strategies with >= %s trades: %s" % (args.min_trades, n_eligible))
    dsr_n = output["summary"]["dsr_survivors"]
    if Path(args.dsr_json).is_file():
        print("DSR survivors loaded: %s" % dsr_n)

    rows = output["strategies"]
    print(f"\n{'='*85}")
    print(
        "BENJAMINI-HOCHBERG FDR CONTROL (alpha=%s, H0: WR=%s%%)"
        % (args.alpha, int(round(args.h0_wr * 100)))
    )
    print(f"{'='*85}")
    print(
        f"{'Strategy':<35} {'N':>5} {'WR%':>6} {'p-val':>8} {'BH-thr':>8} {'FDR':>4} {'DSR':>4} {'BOTH':>5}"
    )
    print("-" * 85)
    for r in rows[:30]:
        fdr = " YES" if r["fdr_significant"] else "  NO"
        dsr = " YES" if r["dsr_survives"] else "  NO"
        both = "  YES" if r["both_pass"] else "   NO"
        print(
            f"{r['strategy'][:34]:<35} {r['trades']:>5} {r['wr_pct']:>5.1f}% "
            f"{r['p_value']:>8.4f} {r['bh_threshold']:>8.4f} {fdr} {dsr} {both}"
        )

    print(f"\nFDR-significant: {sig_count}/{len(rows)}")
    print(f"DSR survivors:   {dsr_n}")
    print(f"Pass BOTH tests: {both_count} (highest confidence)")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nResults written to {out_path}")

    if args.redis_alert:
        redis_broadcast(
            "HEDGE_PLAN §1 BH-FDR: tools/fdr_control.py -> %s (tested=%s FDR_sig=%s both=%s)"
            % (
                str(out_path).replace("\\", "/"),
                len(rows),
                sig_count,
                both_count,
            )
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
