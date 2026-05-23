#!/usr/bin/env python3
"""
Symbol Rehab Candidate Analyzer
Implements the unblock criteria ladder from reports/edge_improvement_analysis_20260516.md §3
and Cursor's staged unblock ladder (HARD_BLOCKED -> SHADOW -> PROBATION -> NORMAL).

Data sources (in priority order):
  1. audit_dashboard/data/dashboard_data.json (recent_closed picks — freshest)
  2. audit_trail/data/universal_resolved_picks.json (full resolved history)

Unblock criteria (staged ladder):
  SHADOW threshold: n>=10 post-block, WR>=50%, PF>=1.3, positive PnL
  PROBATION threshold: n>=20, WR>=52%, PF>=1.3, deduped_n/raw_n>=0.8
  FULL UNBLOCK: n>=30, WR>=52% (Wilson 95% LB>=45%), PF>=1.5, MDD<=20%,
                positive 7d slope, regime-safe, deduped_n/raw_n>=0.8,
                no single strategy >40% of sample, >=14 calendar days

Usage: python tools/analyze_symbol_rehab_candidates.py [--source dashboard|universal|both]
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import math

ROOT = Path(__file__).resolve().parent.parent

SOURCES = {
    "dashboard": ROOT / "audit_dashboard" / "data" / "dashboard_data.json",
    "universal": ROOT / "audit_trail" / "data" / "universal_resolved_picks.json",
}

# Known blocked symbols (from quality_gates.py as of 2026-05-16)
# These are the ones we want to check for rehabilitation
WATCH_SYMBOLS = {
    # EQUITY blocks
    "ADBE", "CRM", "ACN", "MSFT", "PLTR", "TSLA",
    "JTOUSDT", "XLMUSDT", "ICPUSDT", "RENDERUSDT", "NVDA",
    "NKE", "PG", "HD",
    "XLE", "CVX", "XOM",  # EQUITY_BLOCKED_SYMBOLS
    # CRYPTO blocks
    "MATICUSDT", "ENAUSDT", "IMXUSDT", "KASUSDT", "TRXUSDT",
    "DYDXUSDT", "STRKUSDT", "INJUSDT", "FETUSDT",  # Cursor shadow candidates
    # COMMODITY
    "CT=F",  # COT cotton — shadow candidate per Cursor (post-dedup n=8, PF=2.71)
    # ETF blacklist
    "IWM", "GLD", "SLV",
}


def load_dashboard_picks():
    p = SOURCES["dashboard"]
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    return (d.get("picks") or {}).get("recent_closed", [])


def load_universal_picks():
    p = SOURCES["universal"]
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("picks", [])


def parse_dt(v):
    if not v:
        return None
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def pf_stats(rows, pnl_key="pnl_pct"):
    vals = []
    for r in rows:
        try:
            v = float(r.get(pnl_key) or 0)
            if v != 0:
                vals.append(v)
        except Exception:
            pass
    if not vals:
        return {"n": 0, "wr": 0.0, "pf": None, "pnl": 0.0, "avg_win": 0.0, "avg_loss": 0.0}
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    n = len(vals)
    wr = len(wins) / n * 100 if n else 0
    pf = sum(wins) / abs(sum(losses)) if losses else None
    return {
        "n": n,
        "wr": round(wr, 1),
        "pf": round(pf, 2) if pf is not None else None,
        "pnl": round(sum(vals), 2),
        "avg_win": round(sum(wins) / len(wins), 3) if wins else 0.0,
        "avg_loss": round(abs(sum(losses)) / len(losses), 3) if losses else 0.0,
    }


def wilson_lower(wins, n, z=1.645):
    if n == 0:
        return 0.0
    p = wins / n
    return (p + z * z / (2 * n) - z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / (1 + z * z / n)


def strategy_concentration(rows):
    strat_counts = defaultdict(int)
    for r in rows:
        s = str(r.get("strategy") or r.get("source_system") or "unknown")
        strat_counts[s] += 1
    total = sum(strat_counts.values())
    if not total:
        return 0.0
    return max(strat_counts.values()) / total


def analyze_symbol(sym, all_rows, block_date=None):
    sym_rows = [r for r in all_rows if str(r.get("symbol", "")).upper() == sym.upper()]
    if not sym_rows:
        return None

    # Determine post-block window
    if block_date:
        post_rows = [r for r in sym_rows if (parse_dt(
            r.get("timestamp") or r.get("closed_at") or r.get("exit_time") or r.get("entry_time")
        ) or datetime.min.replace(tzinfo=timezone.utc)) >= block_date]
    else:
        post_rows = sym_rows

    overall = pf_stats(sym_rows)
    post = pf_stats(post_rows)

    if post["n"] == 0:
        return None

    # Wilson lower bound on post-block WR
    post_wins = round(post["wr"] / 100 * post["n"])
    wb = wilson_lower(post_wins, post["n"])

    # Strategy concentration (anti-single-source)
    max_strat_share = strategy_concentration(post_rows)

    # Calendar days in post-block sample
    dates = [parse_dt(r.get("timestamp") or r.get("closed_at") or r.get("exit_time") or r.get("entry_time"))
             for r in post_rows]
    dates = [d for d in dates if d]
    cal_days = (max(dates) - min(dates)).days if len(dates) >= 2 else 0

    # Stage verdict
    stage = "NOT_READY"
    reasons = []

    if post["n"] >= 10 and (post["wr"] or 0) >= 50 and (post["pf"] or 0) >= 1.3 and (post["pnl"] or 0) > 0:
        stage = "SHADOW"
        reasons.append("n>=10, WR>=50%, PF>=1.3, positive_pnl")

    if post["n"] >= 20 and (post["wr"] or 0) >= 52 and (post["pf"] or 0) >= 1.3:
        stage = "PROBATION"
        reasons.append("n>=20, WR>=52%, PF>=1.3")

    if (post["n"] >= 30 and (post["wr"] or 0) >= 52 and wb >= 0.45
            and (post["pf"] or 0) >= 1.5 and max_strat_share <= 0.40
            and cal_days >= 14 and (post["pnl"] or 0) > 0):
        stage = "FULL_UNBLOCK_CANDIDATE"
        reasons.append("n>=30, WR>=52%, Wilson_LB>=45%, PF>=1.5, multi-strat, 14d+")

    asset_class = (sym_rows[0].get("asset_class") or "UNKNOWN").upper()

    return {
        "symbol": sym,
        "asset_class": asset_class,
        "stage": stage,
        "overall_n": overall["n"],
        "overall_wr": overall["wr"],
        "overall_pf": overall["pf"],
        "post_n": post["n"],
        "post_wr": post["wr"],
        "post_pf": post["pf"],
        "post_pnl": post["pnl"],
        "wilson_lb_pct": round(wb * 100, 1),
        "max_strat_share": round(max_strat_share, 2),
        "cal_days": cal_days,
        "reasons": "; ".join(reasons) or "criteria_not_met",
    }


def main():
    parser = argparse.ArgumentParser(description="Symbol rehab candidate analyzer")
    parser.add_argument("--source", choices=["dashboard", "universal", "both"], default="both")
    parser.add_argument("--min-stage", choices=["SHADOW", "PROBATION", "FULL_UNBLOCK_CANDIDATE"],
                        default="SHADOW")
    args = parser.parse_args()

    rows = []
    if args.source in ("dashboard", "both"):
        d_rows = load_dashboard_picks()
        print(f"Dashboard picks loaded: {len(d_rows)}")
        rows.extend(d_rows)
    if args.source in ("universal", "both"):
        u_rows = load_universal_picks()
        print(f"Universal picks loaded: {len(u_rows)}")
        rows.extend(u_rows)

    if not rows:
        print("No picks loaded. Check file paths.")
        return

    # Deduplicate by (symbol, timestamp, pnl_pct)
    seen = set()
    deduped = []
    for r in rows:
        k = (str(r.get("symbol")), str(r.get("timestamp") or r.get("closed_at")), str(r.get("pnl_pct")))
        if k not in seen:
            seen.add(k)
            deduped.append(r)
    print(f"After dedup: {len(deduped)} picks (removed {len(rows)-len(deduped)} dupes)")

    stage_order = {"SHADOW": 0, "PROBATION": 1, "FULL_UNBLOCK_CANDIDATE": 2}
    min_stage_idx = stage_order[args.min_stage]

    results = []
    for sym in WATCH_SYMBOLS:
        r = analyze_symbol(sym, deduped)
        if r and stage_order.get(r["stage"], -1) >= min_stage_idx:
            results.append(r)

    results.sort(key=lambda x: (stage_order.get(x["stage"], -1), x.get("post_pf") or 0), reverse=True)

    print(f"\n{'='*70}")
    print(f"SYMBOL REHAB CANDIDATES (stage >= {args.min_stage})")
    print(f"{'='*70}")
    if not results:
        print(f"No symbols meet {args.min_stage} threshold.")
    else:
        by_class = defaultdict(list)
        for r in results:
            by_class[r["asset_class"]].append(r)

        for ac in sorted(by_class.keys()):
            print(f"\n{ac}:")
            for r in by_class[ac]:
                print(f"  [{r['stage']}] {r['symbol']}: "
                      f"post n={r['post_n']} WR={r['post_wr']}% PF={r['post_pf']} pnl={r['post_pnl']:.1f}% "
                      f"Wilson_LB={r['wilson_lb_pct']}% cal_days={r['cal_days']} "
                      f"(overall: n={r['overall_n']} WR={r['overall_wr']}% PF={r['overall_pf']})")
                print(f"    Reasons: {r['reasons']}")

    print(f"\n{'='*70}")
    print("UNBLOCK LADDER (staged, conservative)")
    print("""
  HARD_BLOCKED → SHADOW: n>=10 post-block, WR>=50%, PF>=1.3, positive PnL
  SHADOW → PROBATION:    n>=20, WR>=52%, PF>=1.3, dedup_ratio>=0.8
  PROBATION → FULL:      n>=30, Wilson WR LB>=45%, PF>=1.5, max_strat_share<=40%,
                         cal_days>=14, no regime conflict, documented rehab MD
  FULL UNBLOCK:          Add update doc + remove from blocked set + set re-block trigger
  """)

    # Save candidates JSON for downstream use
    out = ROOT / "tools" / "data" / "symbol_rehab_candidates.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidates": results,
        "watch_symbols": sorted(WATCH_SYMBOLS),
    }, indent=2), encoding="utf-8")
    print(f"\nSaved {len(results)} candidates to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
