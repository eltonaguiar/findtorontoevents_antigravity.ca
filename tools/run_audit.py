#!/usr/bin/env python3
"""
run_audit.py — Reproducible per-asset-class performance audit

Usage:
  python run_audit.py [--dashboard PATH] [--output PATH] [--window DAYS]

Produces:
  - Console summary table
  - JSON audit file with full per-asset, per-strategy, per-window metrics
  - Strategy health alerts (strategies below threshold)

Data source: audit_dashboard/data/dashboard_data.json (or arg override)
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import statistics

# === CONFIG ===
# Thresholds for win/loss/flat classification
# pnl_pct field is in PERCENTAGE POINTS (1.05 = +1.05%)
FLAT_THRESHOLD_BP = 1.0  # 1 basis point = 0.01%
FLAT_PNL = FLAT_THRESHOLD_BP / 100.0  # 0.01

THRESH_BY_ASSET = {
    "CRYPTO": FLAT_PNL,
    "EQUITY": FLAT_PNL,
    "FOREX": FLAT_PNL,
    "COMMODITY": FLAT_PNL,
    "ETF": FLAT_PNL,
    "BOND": FLAT_PNL,
    "UNKNOWN": FLAT_PNL,
}

# Tier definitions
TIERS = {
    "Tier-1": {"pf": 2.0, "wr": 55, "mdd": 10},
    "Tier-2": {"pf": 1.5, "wr": 50, "mdd": 20},
    "Tier-3": {"pf": 1.2, "wr": 48, "mdd": 30},
}

# Strategy volume concentration limit
MAX_STRATEGY_VOLUME_PCT = 15


def parse_dt(s):
    if not s:
        return None
    try:
        s = str(s).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s[:32])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def calc_metrics(pnls, thresh):
    """Compute PF, WR, MDD, and counts from a list of PnL values."""
    if not pnls:
        return None
    wins = [p for p in pnls if p > thresh]
    losses = [p for p in pnls if p < -thresh]
    flats = [p for p in pnls if -thresh <= p <= thresh]

    gross_wins = sum(wins) if wins else 0.0
    gross_losses = abs(sum(losses)) if losses else 0.0

    if gross_losses > 0:
        pf = gross_wins / gross_losses
    elif gross_wins > 0:
        pf = float("inf")
    else:
        pf = 0.0

    wr = len(wins) / len(pnls) * 100 if pnls else 0
    avg = statistics.mean(pnls) if pnls else 0.0

    # MDD approximation (naive running sum)
    running = 0
    peak = 0
    mdd = 0
    for p in pnls:
        running += p
        if running > peak:
            peak = running
        dd = peak - running
        if dd > mdd:
            mdd = dd

    return {
        "n": len(pnls),
        "pf": pf,
        "wr": wr,
        "avg_pnl": avg,
        "mdd": mdd,
        "wins": len(wins),
        "losses": len(losses),
        "flats": len(flats),
        "gross_wins": gross_wins,
        "gross_losses": gross_losses,
    }


def tier_status(m):
    """Assign tier label from metrics dict."""
    if not m:
        return "No Data"
    if m["pf"] >= TIERS["Tier-1"]["pf"] and m["wr"] >= TIERS["Tier-1"]["wr"] and m["mdd"] <= TIERS["Tier-1"]["mdd"]:
        return "Tier-1"
    if m["pf"] >= TIERS["Tier-2"]["pf"] and m["wr"] >= TIERS["Tier-2"]["wr"] and m["mdd"] <= TIERS["Tier-2"]["mdd"]:
        return "Tier-2"
    if m["pf"] >= TIERS["Tier-3"]["pf"] and m["wr"] >= TIERS["Tier-3"]["wr"] and m["mdd"] <= TIERS["Tier-3"]["mdd"]:
        return "Tier-3"
    return "Below"


def run_audit(dashboard_path, output_path, max_window_days=30):
    with open(dashboard_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    recent_closed = data.get("picks", {}).get("recent_closed", [])
    active = data.get("picks", {}).get("active", [])
    now = datetime.now(timezone.utc)

    windows = {
        "24h": timedelta(hours=24),
        "72h": timedelta(hours=72),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    # Build per-asset, per-window dataset
    asset_data = defaultdict(lambda: defaultdict(list))
    strategy_data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for pick in recent_closed:
        closed_at = parse_dt(pick.get("closed_at") or pick.get("exit_date"))
        if not closed_at:
            continue
        age = now - closed_at
        pnl = pick.get("pnl_pct")
        if pnl is None:
            continue

        asset = (pick.get("asset_class") or "UNKNOWN").upper()
        strategy = pick.get("strategy", "UNKNOWN")

        for win_name, win_delta in windows.items():
            if age <= win_delta:
                record = {
                    "pnl": pnl,
                    "symbol": pick.get("symbol", ""),
                    "direction": (pick.get("direction") or "").upper(),
                    "strategy": strategy,
                    "status": pick.get("status", ""),
                    "exit_reason": pick.get("exit_reason", ""),
                }
                asset_data[asset][win_name].append(record)
                strategy_data[asset][strategy][win_name].append(record)

    # Compute metrics
    report = {
        "generated_at": now.isoformat(),
        "dashboard_at": data.get("generated_at", "unknown"),
        "total_closed": len(recent_closed),
        "total_active": len(active),
        "threshold_bp": FLAT_THRESHOLD_BP,
        "assets": {},
        "alerts": [],
    }

    print("=" * 80)
    print("PER-ASSET PERFORMANCE AUDIT")
    print(f"Dashboard: {report['dashboard_at']}")
    print(f"Audit run: {report['generated_at']}")
    print(f"Threshold: {FLAT_THRESHOLD_BP}bp = {FLAT_PNL}%")
    print("=" * 80)
    print(f"{'Asset':<10} {'Window':<5} {'n':>5} {'PF':>6} {'WR%':>6} {'MDD%':>7} {'Tier':>8}")
    print("-" * 60)

    for asset in ["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND"]:
        report["assets"][asset] = {}
        for win_name in ["24h", "72h", "7d", "30d"]:
            picks = asset_data[asset][win_name]
            thresh = THRESH_BY_ASSET.get(asset, FLAT_PNL)
            m = calc_metrics([p["pnl"] for p in picks], thresh)
            report["assets"][asset][win_name] = m

            if m:
                pf_str = f"{m['pf']:.2f}" if m["pf"] != float("inf") else "inf"
                tier = tier_status(m)
                print(f"{asset:<10} {win_name:<5} {m['n']:>5} {pf_str:>6} {m['wr']:>5.1f} {m['mdd']:>6.1f} {tier:>8}")

                # Alert if below Tier-3
                if tier == "Below" and m["n"] >= 10:
                    report["alerts"].append({
                        "severity": "HIGH",
                        "asset": asset,
                        "window": win_name,
                        "message": f"{asset} {win_name} below Tier-3: PF={pf_str} WR={m['wr']:.1f}% MDD={m['mdd']:.1f}%",
                    })
            else:
                print(f"{asset:<10} {win_name:<5} {'—':>5} {'—':>6} {'—':>5} {'—':>6} {'—':>8}")

    # Strategy-level concentration analysis (7d window)
    print("\n" + "=" * 80)
    print("STRATEGY VOLUME CONCENTRATION (7d window)")
    print("=" * 80)
    print(f"{'Asset':<10} {'Strategy':<40} {'n':>4} {'Pct%':>6} {'PF':>6} {'WR%':>6} {'Alert':>10}")
    print("-" * 90)

    for asset in ["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF"]:
        total_7d = len(asset_data[asset]["7d"])
        if total_7d == 0:
            continue

        for strategy, win_picks in sorted(
            strategy_data[asset].items(),
            key=lambda x: -len(x[1].get("7d", []))
        ):
            picks = win_picks.get("7d", [])
            if not picks:
                continue
            n = len(picks)
            pct = n / total_7d * 100
            thresh = THRESH_BY_ASSET.get(asset, FLAT_PNL)
            m = calc_metrics([p["pnl"] for p in picks], thresh)
            pf_str = f"{m['pf']:.2f}" if m["pf"] != float("inf") else "inf" if m else "—"
            alert = ""
            if pct > MAX_STRATEGY_VOLUME_PCT:
                alert = "VOLUME"
            if m and m["pf"] < 1.0:
                alert += "+DRAG" if alert else "DRAG"

            if pct > 5:  # Only show significant strategies
                print(f"{asset:<10} {strategy[:40]:<40} {n:>4} {pct:>5.1f} {pf_str:>6} {m['wr']:>5.1f} {alert:>10}")

    # Active pick gate health
    print("\n" + "=" * 80)
    print("ACTIVE PICK GATE HEALTH")
    print("=" * 80)

    blocked_strategies = {"forex_carry_momentum", "goldmine_6x_consensus"}
    jpy_crosses = {"CADJPY", "EURJPY", "NZDJPY", "GBPJPY", "AUDJPY", "CHFJPY"}

    issues = []
    for p in active:
        strategy = p.get("strategy", "")
        sym = (p.get("symbol") or "").replace("=X", "").upper()
        direction = (p.get("direction") or "").upper()

        if strategy in blocked_strategies:
            issues.append(f"Blocked strategy in active: {strategy} {sym}")

        is_jpy = len(sym) == 6 and sym[3:] == "JPY" and sym != "USDJPY"
        if is_jpy and direction in ("LONG", "BUY", "BULLISH"):
            issues.append(f"JPY LONG in active: {sym} {direction}")

        if strategy == "quan_engine" and "HYPE" in sym:
            issues.append(f"HYPE quan_engine in active: {sym}")

    if issues:
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        print(f"  ✅ All gates clean. {len(active)} active picks pass all checks.")

    # Write JSON output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n✅ Full audit written to: {output_path}")
    print(f"   Alerts: {len(report['alerts'])}")
    return report


def main():
    parser = argparse.ArgumentParser(description="Reproducible per-asset performance audit")
    parser.add_argument("--dashboard", default="audit_dashboard/data/dashboard_data.json",
                        help="Path to dashboard_data.json")
    parser.add_argument("--output", default="/tmp/audit_output.json",
                        help="Path for JSON output")
    parser.add_argument("--window", type=int, default=30,
                        help="Max lookback window in days")
    args = parser.parse_args()

    try:
        run_audit(args.dashboard, args.output, args.window)
    except FileNotFoundError:
        print(f"❌ Dashboard file not found: {args.dashboard}")
        print("   Fetch from: https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/audit_dashboard/data/dashboard_data.json")
        sys.exit(1)


if __name__ == "__main__":
    main()
