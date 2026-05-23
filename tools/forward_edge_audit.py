#!/usr/bin/env python3
"""
Forward-Only Edge Audit — B16

Produces a daily artifact answering the operator's question:
"If I put real money in there, would I have made a profit?"

Computes per-strategy:
  - Paper WR, PF, sum_pnl
  - After-cost net PnL (using tools/data/transaction_costs.json)
  - Wilson 95% lower bound on WR
  - Symbol concentration (top-3 share of n)
  - Capacity (picks/week based on closed_at timestamps)

NOTE: "Forward-only" filtering is approximate — no strategy_promotion_log.json
exists in the current repo. All closed picks from dashboard_data.json are
included with this caveat explicitly printed in the artifact header. A separate
action item should add promotion-date logging to the resolver pipeline.

OUTPUT:
  reports/forward_edge_audit_<date>.md  — human-readable Markdown artifact
  reports/forward_edge_audit_<date>.json — machine-readable artifact for B17

OPT-IN SIDECAR: This tool has no production caller yet. It is a read-only
analytics tool. Wiring plan: dashboard_generator.py will consume
reports/forward_edge_audit_<date>.json in a follow-up PR (B17).

Usage:
  python tools/forward_edge_audit.py [--date YYYY-MM-DD] [--output-dir reports/]
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
DASHBOARD_DATA = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
TRANSACTION_COSTS_FILE = REPO_ROOT / "tools" / "data" / "transaction_costs.json"
OUTPUT_DIR = REPO_ROOT / "reports"

WILSON_Z = 1.96  # 95% confidence
PF_CAP = 50.0    # cap reported PF; values above flagged with *


def load_transaction_costs() -> dict:
    with open(TRANSACTION_COSTS_FILE) as f:
        data = json.load(f)
    return {k: v["cost_pct"] for k, v in data["costs"].items()}


def wilson_lower_bound(wins: int, n: int, z: float = WILSON_Z) -> float:
    """Wilson score interval lower bound for a proportion."""
    if n == 0:
        return 0.0
    p = wins / n
    z2 = z * z
    denominator = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denominator
    spread = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denominator
    return max(0.0, centre - spread)


def picks_per_week(closed_dates: list) -> float:
    """Compute picks/week from a list of closed_at datetime strings."""
    if not closed_dates:
        return 0.0
    parsed = []
    for d in closed_dates:
        if not d:
            continue
        try:
            if d.endswith("Z"):
                d = d[:-1] + "+00:00"
            dt = datetime.fromisoformat(d)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            parsed.append(dt)
        except (ValueError, TypeError):
            continue
    if len(parsed) < 2:
        return float(len(parsed))
    parsed.sort()
    span_days = (parsed[-1] - parsed[0]).total_seconds() / 86400
    if span_days < 1:
        return float(len(parsed))
    return len(parsed) / (span_days / 7)


def safe_pf(gross_wins: float, gross_losses: float) -> tuple:
    """Return (pf, capped) where capped=True if PF was above PF_CAP."""
    if gross_losses == 0:
        return (PF_CAP, True) if gross_wins > 0 else (0.0, False)
    raw = gross_wins / gross_losses
    if raw > PF_CAP:
        return (PF_CAP, True)
    return (raw, False)


def compute_strategy_stats(picks: list, costs: dict) -> list:
    """
    Aggregate per-strategy statistics across all closed picks.
    Returns list of dicts, one per (strategy, asset_class) pocket.
    """
    buckets = defaultdict(list)
    for p in picks:
        if p.get("status") == "UNRESOLVED":
            continue
        strat = (p.get("strategy") or "unknown").strip()
        ac = (p.get("asset_class") or "UNKNOWN").upper()
        buckets[(strat, ac)].append(p)

    rows = []
    for (strat, ac), bucket in buckets.items():
        n = len(bucket)
        wins = sum(1 for p in bucket if p.get("status") == "WON")
        losses = n - wins
        pnls = [p["pnl_pct"] for p in bucket if p.get("pnl_pct") is not None]

        if not pnls:
            continue

        gross_wins_pct = sum(p for p in pnls if p > 0)
        gross_losses_pct = abs(sum(p for p in pnls if p < 0))
        sum_pnl = sum(pnls)
        mean_pnl = sum_pnl / len(pnls)

        wr = wins / n if n > 0 else 0.0
        wilson_lb = wilson_lower_bound(wins, n)
        pf_val, pf_capped = safe_pf(gross_wins_pct, gross_losses_pct)

        cost_pct = costs.get(ac, costs.get("UNKNOWN", 0.20))
        after_cost_mean_pnl = mean_pnl - cost_pct
        after_cost_sum_pnl = sum_pnl - (n * cost_pct)

        sym_counter = defaultdict(int)
        for p in bucket:
            sym = p.get("symbol") or "?"
            sym_counter[sym] += 1
        sorted_syms = sorted(sym_counter.items(), key=lambda x: -x[1])
        top3_n = sum(v for _, v in sorted_syms[:3])
        top3_share = top3_n / n if n > 0 else 0.0
        top3_symbols = [s for s, _ in sorted_syms[:3]]

        closed_dates = [p.get("closed_at") for p in bucket]
        ppw = picks_per_week(closed_dates)

        rows.append({
            "strategy": strat,
            "asset_class": ac,
            "n": n,
            "wins": wins,
            "losses": losses,
            "wr_pct": round(wr * 100, 1),
            "wilson_lb_wr_pct": round(wilson_lb * 100, 1),
            "pf": round(pf_val, 2),
            "pf_capped": pf_capped,
            "sum_pnl_pct": round(sum_pnl, 2),
            "mean_pnl_pct": round(mean_pnl, 3),
            "cost_bps": round(cost_pct * 100, 1),
            "after_cost_mean_pnl_pct": round(after_cost_mean_pnl, 3),
            "after_cost_sum_pnl_pct": round(after_cost_sum_pnl, 2),
            "top3_symbols": top3_symbols,
            "top3_share_pct": round(top3_share * 100, 0),
            "picks_per_week": round(ppw, 1),
            "survives_after_cost": after_cost_mean_pnl > 0,
            "survives_wilson_50pct": wilson_lb >= 0.50,
            "both_survive": after_cost_mean_pnl > 0 and wilson_lb >= 0.50,
            "small_sample_flag": n < 20,
        })

    return sorted(rows, key=lambda x: (-int(x["both_survive"]), -x["n"]))


def format_markdown_table(rows: list, min_n: int = 10) -> str:
    filtered = [r for r in rows if r["n"] >= min_n]
    if not filtered:
        return "_No strategies with n ≥ 10._\n"

    header = (
        "| Strategy | AC | n | WR% | Wilson lb% | PF | after-cost PnL/trade | "
        "after-cost sum | top-3 syms | conc% | picks/wk | pass |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    lines = [header]
    for r in filtered:
        pf_str = f"{r['pf']:.2f}{'*' if r['pf_capped'] else ''}"
        survivor = "✅" if r["both_survive"] else ("⚠" if r["survives_after_cost"] or r["survives_wilson_50pct"] else "❌")
        small_flag = " ⚑" if r["small_sample_flag"] else ""
        syms = ", ".join(r["top3_symbols"][:2]) if r["top3_symbols"] else "?"
        lines.append(
            f"| {r['strategy'][:35]} | {r['asset_class']} | {r['n']}{small_flag} | "
            f"{r['wr_pct']:.1f}% | {r['wilson_lb_wr_pct']:.1f}% | {pf_str} | "
            f"{r['after_cost_mean_pnl_pct']:+.3f}% | {r['after_cost_sum_pnl_pct']:+.1f}% | "
            f"{syms} | {r['top3_share_pct']:.0f}% | {r['picks_per_week']:.1f} | {survivor} |\n"
        )
    return "".join(lines)


def format_class_summary(rows: list) -> str:
    ac_buckets = defaultdict(list)
    for r in rows:
        if r["n"] >= 10:
            ac_buckets[r["asset_class"]].append(r)

    lines = ["| Asset Class | Total n | WR% (paper) | after-cost sum PnL | Survivors (both gates) |\n",
             "|---|---|---|---|---|\n"]
    for ac in sorted(ac_buckets.keys()):
        bucket = ac_buckets[ac]
        total_n = sum(r["n"] for r in bucket)
        all_pnls_sum = sum(r["sum_pnl_pct"] for r in bucket)
        all_ac_sum = sum(r["after_cost_sum_pnl_pct"] for r in bucket)
        wins = sum(r["wins"] for r in bucket)
        wr = wins / total_n * 100 if total_n > 0 else 0
        survivors = [r["strategy"] for r in bucket if r["both_survive"]]
        lines.append(
            f"| {ac} | {total_n} | {wr:.1f}% | {all_ac_sum:+.1f}% | "
            f"{', '.join(survivors[:3]) or 'none'} |\n"
        )
    return "".join(lines)


def generate_artifact(rows: list, date_str: str, output_dir: Path) -> tuple:
    md_path = output_dir / f"forward_edge_audit_{date_str}.md"
    json_path = output_dir / f"forward_edge_audit_{date_str}.json"

    survivors = [r for r in rows if r["both_survive"] and r["n"] >= 10]
    warning_strategies = [r for r in rows if r["n"] >= 10 and r["wr_pct"] == 0.0]

    md_content = f"""# Forward-Only Edge Audit — {date_str}
*Generated by `tools/forward_edge_audit.py` (B16)*

> **CAVEAT — forward-only filtering is approximate.** No `strategy_promotion_log.json`
> exists in the repo. All closed picks from `picks.recent_closed` are included.
> The "forward-only" label means picks emitted after strategy stabilization, but we
> cannot strictly filter to post-promotion trades without a promotion log. A separate
> action item will add promotion-date logging to the resolver pipeline.
>
> **Transaction costs** are round-trip estimates from `tools/data/transaction_costs.json`.
> After-cost analysis deducts one round-trip cost from every trade's mean PnL.
>
> **Symbols:** ⑦ = small sample (n < 20); PF* = capped at {PF_CAP}× (raw value higher).
> **Gates for "pass" (✅):** after_cost_mean_pnl > 0 AND wilson_lb_wr ≥ 50%.

## 1. After-Cost Survivors (both gates pass, n ≥ 10)

{f"**{len(survivors)} strateg{'y' if len(survivors)==1 else 'ies'} pass both after-cost and Wilson 50% gates:**" if survivors else "_No strategies pass both gates at n ≥ 10._"}

{chr(10).join(f"- **{r['strategy']}** ({r['asset_class']}) — WR {r['wr_pct']}% / Wilson lb {r['wilson_lb_wr_pct']}% / after-cost PnL/trade {r['after_cost_mean_pnl_pct']:+.3f}% / {r['picks_per_week']:.1f}/wk" for r in survivors)}

## 2. Asset-Class Summary

{format_class_summary(rows)}

## 3. Full Strategy Table (n ≥ 10)

{format_markdown_table(rows, min_n=10)}

### Notes
- ⑦ = small sample flag (n < 20); interpret with caution
- PF* = Profit Factor capped at {PF_CAP}×; raw value above cap
- ✅ = passes both after-cost-net > 0 AND Wilson 95% lb ≥ 50%
- ⚠ = passes one of the two gates
- ❌ = fails both gates
- conc% = top-3 symbol share of total trades (high = single-stock risk)
- Wilson 50% gate: the lower bound of the 95% CI on WR must be ≥ 50%

## 4. Zero-WR Strategies (0% win rate, n ≥ 10)

{chr(10).join(f"- **{r['strategy']}** ({r['asset_class']}) — n={r['n']}, sum_pnl={r['sum_pnl_pct']:+.1f}%" for r in warning_strategies) or "_None detected._"}

*Zero-WR strategies are candidates for kill-list review per `TESTING_PROTOCOL.MD` §7.*

## 5. Operator Summary

- **Total closed picks analysed:** {sum(r['n'] for r in rows if r['n'] >= 10)}
- **Strategies with n ≥ 10:** {len([r for r in rows if r['n'] >= 10])}
- **Strategies passing both gates:** {len(survivors)}
- **Strategies with 0% WR (kill candidates):** {len(warning_strategies)}
- **Artifact version:** 1.0 (B16)
- **Wiring status:** OPT-IN SIDECAR — no production caller yet. Wiring plan: B17 will add `picks.forward_edge_audit` payload section to `dashboard_generator.py`.
"""

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    json_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": date_str,
        "caveat": "forward-only filtering is approximate; no strategy_promotion_log.json",
        "wiring_status": "opt-in sidecar; wiring plan in B17",
        "version": "1.0",
        "survivors": [r["strategy"] for r in survivors],
        "strategies": rows,
        "summary": {
            "total_n": sum(r["n"] for r in rows if r["n"] >= 10),
            "strategies_n10": len([r for r in rows if r["n"] >= 10]),
            "survivors_count": len(survivors),
            "zero_wr_count": len(warning_strategies),
        },
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2)

    return md_path, json_path


def main():
    parser = argparse.ArgumentParser(description="Forward-only edge audit (B16)")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="Date string for artifact filenames (default: today)")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR),
                        help="Directory to write artifact files")
    parser.add_argument("--min-n", type=int, default=10,
                        help="Minimum closed trades to include a strategy (default: 10)")
    parser.add_argument("--data-file", default=str(DASHBOARD_DATA),
                        help="Path to dashboard_data.json")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    costs = load_transaction_costs()

    data_file = Path(args.data_file)
    if not data_file.exists():
        print(f"ERROR: dashboard_data.json not found at {data_file}", file=sys.stderr)
        sys.exit(1)

    with open(data_file) as f:
        dashboard = json.load(f)

    picks = dashboard.get("picks", {}).get("recent_closed", [])
    if not picks:
        print("WARNING: No recent_closed picks found in dashboard_data.json", file=sys.stderr)
        picks = []

    print(f"Loaded {len(picks)} closed picks from {data_file}")

    rows = compute_strategy_stats(picks, costs)
    rows_filtered = [r for r in rows if r["n"] >= args.min_n]
    print(f"Strategies with n >= {args.min_n}: {len(rows_filtered)}")

    md_path, json_path = generate_artifact(rows, args.date, output_dir)
    print(f"Artifact written: {md_path}")
    print(f"JSON written:     {json_path}")

    survivors = [r for r in rows if r["both_survive"] and r["n"] >= args.min_n]
    print(f"\nSurvivors (after-cost AND Wilson lb >= 50%, n >= {args.min_n}): {len(survivors)}")
    for r in survivors:
        print(f"  {r['strategy'][:40]} ({r['asset_class']}) "
              f"WR={r['wr_pct']}% lb={r['wilson_lb_wr_pct']}% "
              f"after-cost={r['after_cost_mean_pnl_pct']:+.3f}%/trade "
              f"{r['picks_per_week']:.1f}/wk")

    return 0


if __name__ == "__main__":
    sys.exit(main())
