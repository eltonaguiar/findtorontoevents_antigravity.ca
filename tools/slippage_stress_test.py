#!/usr/bin/env python3
"""B14: Liquidity / slippage stress test.

Simulates 1×, 2×, 3×, and 5× volume-spike slippage scenarios on closed picks
to answer: "which strategies survive realistic transaction costs at scale?"

Uses a linear market impact model (conservative / worst-case):
  - 1× base:    round-trip cost from tools/data/transaction_costs.json
  - 2× volume:  2 × base cost (doubling position size doubles slippage)
  - 3× volume:  3 × base cost
  - 5× volume:  5 × base cost (extreme liquidity stress)

OPT-IN SIDECAR: read-only analytics tool. No production caller yet.
Wiring plan: dashboard_generator.py → new payload section picks.slippage_stress
in a follow-up "B14-dashboard-panel" PR (target: 2026-05-16, after operator
validates output).

Usage:
    python tools/slippage_stress_test.py [--asset-class CRYPTO] [--min-n 5]
                                          [--out reports/slippage_stress_<date>.json]
                                          [--report reports/slippage_stress_<date>.md]

Outputs:
    reports/slippage_stress_<date>.json  -- machine-readable index per strategy
    reports/slippage_stress_<date>.md    -- human-readable Markdown artifact
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
DASHBOARD_DATA = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
TRANSACTION_COSTS_FILE = REPO_ROOT / "tools" / "data" / "transaction_costs.json"
REPORTS_DIR = REPO_ROOT / "reports"

# Multipliers for volume-spike stress scenarios
STRESS_MULTIPLIERS: dict[str, float] = {
    "1x_base": 1.0,
    "2x_volume": 2.0,
    "3x_volume": 3.0,
    "5x_volume": 5.0,
}

MIN_N_DEFAULT = 5


def _load_transaction_costs() -> dict[str, float]:
    """Return per-asset-class base round-trip cost as a percentage."""
    try:
        raw = json.loads(TRANSACTION_COSTS_FILE.read_text())
        return {
            cls: info["cost_pct"]
            for cls, info in raw.get("costs", {}).items()
        }
    except Exception:
        # Fallback conservative defaults
        return {
            "CRYPTO": 0.30,
            "EQUITY": 0.10,
            "FOREX": 0.08,
            "COMMODITY": 0.15,
            "ETF": 0.10,
            "BOND": 0.04,
            "FUTURES": 0.10,
        }


def _load_closed_picks(asset_class_filter: str | None = None) -> list[dict]:
    """Load closed picks from dashboard_data.json."""
    raw = json.loads(DASHBOARD_DATA.read_text())
    picks_section = raw.get("picks", {})

    # Support both 'closed' and 'recent_closed' keys
    picks: list[dict] = (
        picks_section.get("closed")
        or picks_section.get("recent_closed")
        or []
    )

    if asset_class_filter:
        picks = [
            p for p in picks
            if (p.get("asset_class") or "").upper() == asset_class_filter.upper()
        ]
    return picks


def _safe_pnl(pick: dict) -> float | None:
    """Return pnl_pct as float, or None if missing / non-numeric."""
    raw = pick.get("pnl_pct")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _profit_factor(wins: list[float], losses: list[float]) -> float | None:
    """Compute Profit Factor = sum(wins) / |sum(losses)|."""
    gross_win = sum(w for w in wins if w > 0)
    gross_loss = abs(sum(l for l in losses if l < 0))
    if gross_loss == 0:
        return math.inf if gross_win > 0 else None
    return gross_win / gross_loss


def _bucket_stats(
    pnls: list[float],
    cost_pct: float,
    multiplier: float,
) -> dict:
    """Compute WR, PF, sum_pnl for a list of paper PnL values after slippage."""
    net = [p - cost_pct * multiplier for p in pnls]
    n = len(net)
    if n == 0:
        return {"n": 0, "wr_pct": None, "pf": None, "sum_pnl_pct": None}

    wins = [v for v in net if v > 0]
    losses = [v for v in net if v <= 0]
    wr = len(wins) / n * 100.0
    pf = _profit_factor(wins, losses)
    s = sum(net)
    return {
        "n": n,
        "wr_pct": round(wr, 2),
        "pf": round(pf, 4) if pf is not None and not math.isinf(pf) else (
            "inf" if pf == math.inf else None
        ),
        "sum_pnl_pct": round(s, 4),
    }


def _breakeven_multiplier(
    paper_sum_pnl: float,
    base_cost_pct: float,
    n: int,
) -> float | None:
    """
    Return the cost multiplier at which the strategy's net sum_pnl hits zero.

    breakeven_mult = paper_sum_pnl / (base_cost_pct * n)

    Returns None for ALREADY_LOSING (paper_sum_pnl <= 0) and None if
    base_cost_pct or n is zero.
    """
    if paper_sum_pnl <= 0 or base_cost_pct <= 0 or n <= 0:
        return None
    return round(paper_sum_pnl / (base_cost_pct * n), 2)


def _label(paper_sum_pnl: float, net_2x_sum: float) -> str:
    """Danger-level label for a strategy under stress."""
    if paper_sum_pnl <= 0:
        return "ALREADY_LOSING"
    if net_2x_sum <= 0:
        return "FAILS_2X"  # profitable at 1× but not at 2×
    if net_2x_sum > 0:
        return "SURVIVES_2X"
    return "BORDERLINE"


def run_stress_test(
    asset_class_filter: str | None = None,
    min_n: int = MIN_N_DEFAULT,
) -> dict:
    """Core computation. Returns the full stress test result dict."""
    costs = _load_transaction_costs()
    picks = _load_closed_picks(asset_class_filter)

    # Group paper PnLs by (strategy, asset_class)
    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
    for pick in picks:
        pnl = _safe_pnl(pick)
        if pnl is None:
            continue
        strategy = pick.get("strategy") or "unknown"
        ac = (pick.get("asset_class") or "UNKNOWN").upper()
        buckets[(strategy, ac)].append(pnl)

    results: list[dict] = []
    for (strategy, ac), pnls in sorted(buckets.items()):
        n = len(pnls)
        base_cost = costs.get(ac, 0.10)

        if n < min_n:
            results.append({
                "strategy": strategy,
                "asset_class": ac,
                "n": n,
                "status": "INSUFFICIENT_DATA",
                "note": f"n={n} < min_n={min_n}",
            })
            continue

        # Paper (0× slippage — not realistic, baseline reference)
        paper_wins = [v for v in pnls if v > 0]
        paper_losses = [v for v in pnls if v <= 0]
        paper_wr = len(paper_wins) / n * 100.0
        paper_pf_val = _profit_factor(paper_wins, paper_losses)
        paper_sum = sum(pnls)

        scenario_stats: dict[str, dict] = {}
        for label, mult in STRESS_MULTIPLIERS.items():
            scenario_stats[label] = _bucket_stats(pnls, base_cost, mult)

        bkeven = _breakeven_multiplier(paper_sum, base_cost, n)
        net_2x = scenario_stats["2x_volume"]["sum_pnl_pct"]
        status = _label(paper_sum, net_2x if net_2x is not None else -1.0)

        results.append({
            "strategy": strategy,
            "asset_class": ac,
            "n": n,
            "base_cost_pct": base_cost,
            "paper": {
                "wr_pct": round(paper_wr, 2),
                "pf": (
                    round(paper_pf_val, 4)
                    if paper_pf_val is not None and not math.isinf(paper_pf_val)
                    else ("inf" if paper_pf_val == math.inf else None)
                ),
                "sum_pnl_pct": round(paper_sum, 4),
            },
            "scenarios": scenario_stats,
            "breakeven_multiplier": bkeven,
            "status": status,
        })

    # Sort: SURVIVES_2X first, then FAILS_2X, ALREADY_LOSING, INSUFFICIENT_DATA
    _order = {"SURVIVES_2X": 0, "FAILS_2X": 1, "ALREADY_LOSING": 2, "INSUFFICIENT_DATA": 3}
    results.sort(key=lambda r: (_order.get(r.get("status", ""), 9), -(r.get("n") or 0)))

    total_picks = len(picks)
    strategies_tested = sum(1 for r in results if r.get("status") != "INSUFFICIENT_DATA")
    survives_2x = sum(1 for r in results if r.get("status") == "SURVIVES_2X")
    fails_2x = sum(1 for r in results if r.get("status") == "FAILS_2X")
    already_losing = sum(1 for r in results if r.get("status") == "ALREADY_LOSING")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asset_class_filter": asset_class_filter or "ALL",
        "min_n": min_n,
        "total_closed_picks_loaded": total_picks,
        "strategy_buckets_total": len(results),
        "strategy_buckets_tested": strategies_tested,
        "summary": {
            "survives_2x": survives_2x,
            "fails_2x": fails_2x,
            "already_losing": already_losing,
            "insufficient_data": len(results) - strategies_tested,
        },
        "note_model": (
            "Linear market impact model (conservative/worst-case). "
            "2× volume = 2× round-trip cost. "
            "Square-root model (Almgren-Chriss) would give ~1.41× at 2× volume."
        ),
        "note_wiring": (
            "OPT-IN SIDECAR. Wiring plan: dashboard_generator.py → "
            "picks.slippage_stress payload section in B14-dashboard-panel PR "
            "(target: 2026-05-16)."
        ),
        "strategies": results,
    }


def _render_markdown(data: dict) -> str:
    """Render the stress test result as a human-readable Markdown report."""
    ts = data["generated_at"][:10]
    ac = data["asset_class_filter"]
    s = data["summary"]
    lines = [
        f"# Slippage Stress Test — {ts} ({ac})",
        "",
        "## Summary",
        "",
        f"- **Closed picks loaded:** {data['total_closed_picks_loaded']}",
        f"- **Strategy buckets tested (n≥{data['min_n']}):** {data['strategy_buckets_tested']}",
        f"- **Survives 2× volume:** {s['survives_2x']} strategies ✅",
        f"- **Fails at 2× volume:** {s['fails_2x']} strategies ⚠️",
        f"- **Already losing (paper):** {s['already_losing']} strategies ❌",
        f"- **Insufficient data (<n={data['min_n']}):** {s['insufficient_data']} strategies 🔍",
        "",
        f"> Model: {data['note_model']}",
        "",
        "## Strategies that survive 2× volume-spike slippage",
        "",
        "| Strategy | Class | n | Paper WR | Paper PF | Paper ΣPnL | 1× Net ΣPnL | 2× Net ΣPnL | Breakeven Mult |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for r in data["strategies"]:
        if r.get("status") != "SURVIVES_2X":
            continue
        p = r["paper"]
        s1 = r["scenarios"]["1x_base"]
        s2 = r["scenarios"]["2x_volume"]
        bk = r.get("breakeven_multiplier")
        lines.append(
            f"| {r['strategy']} | {r['asset_class']} | {r['n']} "
            f"| {p['wr_pct']}% | {p['pf']} | {p['sum_pnl_pct']:.2f}% "
            f"| {s1['sum_pnl_pct']:.2f}% | {s2['sum_pnl_pct']:.2f}% "
            f"| {bk if bk else '—'} |"
        )

    lines += [
        "",
        "## Strategies that fail at 2× volume-spike (but profitable on paper)",
        "",
        "| Strategy | Class | n | Paper ΣPnL | 2× Net ΣPnL | Breakeven Mult |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in data["strategies"]:
        if r.get("status") != "FAILS_2X":
            continue
        p = r["paper"]
        s2 = r["scenarios"]["2x_volume"]
        bk = r.get("breakeven_multiplier")
        lines.append(
            f"| {r['strategy']} | {r['asset_class']} | {r['n']} "
            f"| {p['sum_pnl_pct']:.2f}% | {s2['sum_pnl_pct']:.2f}% "
            f"| {bk if bk else '—'} |"
        )

    lines += [
        "",
        "## Already-losing strategies (paper PnL ≤ 0)",
        "",
        "| Strategy | Class | n | Paper ΣPnL |",
        "|---|---|---:|---:|",
    ]
    for r in data["strategies"]:
        if r.get("status") != "ALREADY_LOSING":
            continue
        p = r["paper"]
        lines.append(
            f"| {r['strategy']} | {r['asset_class']} | {r['n']} "
            f"| {p['sum_pnl_pct']:.2f}% |"
        )

    lines += [
        "",
        "---",
        f"*Generated by `tools/slippage_stress_test.py` — {data['generated_at']}*",
        "",
        f"> {data['note_wiring']}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Slippage stress test for closed picks."
    )
    parser.add_argument(
        "--asset-class",
        default=None,
        help="Filter by asset class (e.g. CRYPTO, EQUITY). Default: ALL.",
    )
    parser.add_argument(
        "--min-n",
        type=int,
        default=MIN_N_DEFAULT,
        help=f"Minimum picks per strategy bucket (default: {MIN_N_DEFAULT}).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Path for JSON output (default: reports/slippage_stress_<date>.json).",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Path for Markdown report (default: reports/slippage_stress_<date>.md).",
    )
    args = parser.parse_args(argv)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    out_json = Path(args.out) if args.out else REPORTS_DIR / f"slippage_stress_{today}.json"
    out_md = Path(args.report) if args.report else REPORTS_DIR / f"slippage_stress_{today}.md"

    print(f"Loading picks from {DASHBOARD_DATA} …", file=sys.stderr)
    data = run_stress_test(
        asset_class_filter=args.asset_class,
        min_n=args.min_n,
    )

    out_json.write_text(json.dumps(data, indent=2))
    out_md.write_text(_render_markdown(data))

    s = data["summary"]
    print(
        f"Done. {data['total_closed_picks_loaded']} picks, "
        f"{data['strategy_buckets_tested']} strategies tested.\n"
        f"  SURVIVES_2X: {s['survives_2x']}\n"
        f"  FAILS_2X:    {s['fails_2x']}\n"
        f"  ALREADY_LOSING: {s['already_losing']}\n"
        f"  INSUFFICIENT_DATA: {s['insufficient_data']}\n"
        f"JSON  → {out_json}\n"
        f"Report→ {out_md}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
