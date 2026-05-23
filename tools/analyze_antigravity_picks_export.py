#!/usr/bin/env python3
"""
Analyze antigravity CSV exports: closed performance by asset class / trust / grade;
active rows vs dashboard_hc_rules (HC v3 mirror).

Example:
  python tools/analyze_antigravity_picks_export.py ^
    --closed path/to/antigravity_closed_picks_*.csv ^
    --active path/to/antigravity_active_picks_*.csv ^
    --all-picks path/to/antigravity_all_picks_*.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "tools"))

try:
    from dashboard_hc_rules import passes_high_conviction_pick
except ImportError:
    passes_high_conviction_pick = None


def pct(x: str | None) -> float | None:
    if x is None:
        return None
    try:
        return float(str(x).replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def parse_fwd_wr(s: str | None) -> float:
    if not s:
        return 0.0
    m = re.search(r"([\d.]+)\s*%", str(s))
    if m:
        return float(m.group(1)) / 100.0
    try:
        v = float(s)
        return v / 100.0 if v > 1.5 else v
    except ValueError:
        return 0.0


def parse_fwd_n(s: str | None) -> int:
    if not s:
        return 0
    try:
        return int(float(str(s).replace(",", "").strip()))
    except ValueError:
        return 0


def row_to_pick_active(row: dict) -> dict:
    regime = (row.get("Market Regime") or row.get("Regime") or "").strip()
    consensus = row.get("Consensus System Reasons") or ""
    sources: list[str] = []
    if consensus:
        for part in re.findall(r"\[([^\]]+)\]", consensus):
            sources.append(part.strip().lower())
    return {
        "symbol": row.get("Symbol", ""),
        "direction": row.get("Direction", "LONG"),
        "asset_class": row.get("Asset Class", ""),
        "strategy": row.get("Strategy", ""),
        "trust_tier": row.get("Trust Tier", ""),
        "trust_score": row.get("Trust Score (0-10)", "") or row.get("Trust Score", ""),
        "score": row.get("Score", ""),
        "confidence": row.get("Confidence", ""),
        "strat_fwd_wr": parse_fwd_wr(row.get("Forward WR")),
        "strat_fwd_trades": parse_fwd_n(row.get("Forward Trades")),
        "forward_wr": parse_fwd_wr(row.get("Forward WR")),
        "forward_trades": parse_fwd_n(row.get("Forward Trades")),
        "regime": regime,
        "market_regime": regime,
        "source_systems": sources if sources else [],
        "wf_verdict": row.get("WF Verdict") or row.get("wf_verdict") or "",
    }


def summarize_closed(path: Path) -> None:
    by_ac: dict = defaultdict(lambda: {"n": 0, "wins": 0, "pnl_sum": 0.0})
    by_trust: dict = defaultdict(lambda: {"n": 0, "wins": 0, "pnl_sum": 0.0})
    by_grade: dict = defaultdict(lambda: {"n": 0, "wins": 0, "pnl_sum": 0.0})
    total = {"n": 0, "wins": 0, "pnl_sum": 0.0}

    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        for row in r:
            pnl = pct(row.get("PnL%"))
            if pnl is None:
                continue
            ac = (row.get("Asset Class") or "UNKNOWN").strip() or "UNKNOWN"
            tt = (row.get("Trust Tier") or "UNKNOWN").strip().upper()
            gr = (row.get("Grade") or "?").strip()
            total["n"] += 1
            total["pnl_sum"] += pnl
            if pnl > 0:
                total["wins"] += 1
            for d, k in ((by_ac, ac), (by_trust, tt), (by_grade, gr)):
                d[k]["n"] += 1
                d[k]["pnl_sum"] += pnl
                if pnl > 0:
                    d[k]["wins"] += 1

    def wr(d: dict) -> float:
        return 100.0 * d["wins"] / d["n"] if d["n"] else 0.0

    def avg(d: dict) -> float:
        return d["pnl_sum"] / d["n"] if d["n"] else 0.0

    print(f"=== CLOSED: {path.name} ===")
    print(
        f"Rows with PnL%: {total['n']} | Win rate: {wr(total):.1f}% | Avg PnL%: {avg(total):.3f}%"
    )
    print("\nBy Asset Class:")
    for ac in sorted(by_ac.keys(), key=lambda k: -by_ac[k]["n"]):
        d = by_ac[ac]
        print(f"  {ac:14} n={d['n']:5}  WR={wr(d):5.1f}%  avgPnL={avg(d):8.3f}%")
    print("\nBy Trust Tier:")
    for tt in sorted(by_trust.keys(), key=lambda k: -by_trust[tt]["n"]):
        d = by_trust[tt]
        print(f"  {tt:14} n={d['n']:5}  WR={wr(d):5.1f}%  avgPnL={avg(d):8.3f}%")
    print("\nBy Grade:")
    for gr in sorted(by_grade.keys(), key=lambda k: -by_grade[k]["n"]):
        d = by_grade[gr]
        print(f"  {gr:6} n={d['n']:5}  WR={wr(d):5.1f}%  avgPnL={avg(d):8.3f}%")


def hc_eligible_active(path: Path) -> None:
    if passes_high_conviction_pick is None:
        print("dashboard_hc_rules not available")
        return
    by_ac = defaultdict(lambda: {"n": 0, "hc": 0})
    by_tt = defaultdict(lambda: {"n": 0, "hc": 0})
    total = {"n": 0, "hc": 0}
    pnl_sum = 0.0
    pnl_n = 0
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        for row in r:
            p = row_to_pick_active(row)
            ok = passes_high_conviction_pick(p)
            ac = (row.get("Asset Class") or "UNKNOWN").strip() or "UNKNOWN"
            tt = (row.get("Trust Tier") or "UNKNOWN").strip().upper()
            total["n"] += 1
            if ok:
                total["hc"] += 1
            by_ac[ac]["n"] += 1
            if ok:
                by_ac[ac]["hc"] += 1
            by_tt[tt]["n"] += 1
            if ok:
                by_tt[tt]["hc"] += 1
            lp = pct(row.get("PnL%"))
            if lp is not None:
                pnl_sum += lp
                pnl_n += 1

    print(f"\n=== ACTIVE HC FILTER (dashboard_hc_rules) {path.name} ===")
    print(
        f"Total actives: {total['n']} | would pass HC: {total['hc']} ({100*total['hc']/max(total['n'],1):.1f}%)"
    )
    if pnl_n:
        print(f"Live PnL% avg (all with number): {pnl_sum/pnl_n:.3f}% (n={pnl_n})")
    print("\nHC pass rate by Asset Class:")
    for ac in sorted(by_ac.keys(), key=lambda k: -by_ac[k]["n"]):
        d = by_ac[ac]
        pct_hc = 100 * d["hc"] / d["n"] if d["n"] else 0
        print(f"  {ac:14} n={d['n']:4}  HC={d['hc']:4} ({pct_hc:5.1f}%)")
    print("\nHC pass rate by Trust Tier:")
    for tt in sorted(by_tt.keys(), key=lambda k: -by_tt[k]["n"]):
        d = by_tt[tt]
        pct_hc = 100 * d["hc"] / d["n"] if d["n"] else 0
        print(f"  {tt:14} n={d['n']:4}  HC={d['hc']:4} ({pct_hc:5.1f}%)")


def count_rows(path: Path) -> int:
    with path.open(encoding="utf-8", errors="replace") as f:
        return max(0, sum(1 for _ in f) - 1)


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze antigravity CSV exports.")
    ap.add_argument("--closed", type=Path, help="closed_picks CSV path")
    ap.add_argument("--active", type=Path, help="active_picks CSV path")
    ap.add_argument("--all-picks", type=Path, dest="all_picks", help="all_picks CSV path")
    args = ap.parse_args()
    if not args.closed and not args.active and not args.all_picks:
        ap.print_help()
        return 1
    if args.closed:
        if not args.closed.is_file():
            print("Missing --closed file:", args.closed, file=sys.stderr)
            return 1
        summarize_closed(args.closed)
    if args.active:
        if not args.active.is_file():
            print("Missing --active file:", args.active, file=sys.stderr)
            return 1
        hc_eligible_active(args.active)
    if args.all_picks:
        if not args.all_picks.is_file():
            print("Missing --all-picks file:", args.all_picks, file=sys.stderr)
            return 1
        print(f"\n=== ROW COUNT: {args.all_picks.name} ===")
        print(f"  rows: {count_rows(args.all_picks)}")
    if args.closed or args.active:
        print(
            "\nNote: HC simulation uses active columns (regime, consensus to source_systems, forward fields)."
        )
        print("Closed export lacks full consensus/regime; HC count on closed is not computed here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
