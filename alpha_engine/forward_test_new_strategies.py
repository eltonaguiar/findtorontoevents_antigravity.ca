#!/usr/bin/env python3
"""
Forward-Testing Portfolio Tracker for New Research-Backed Strategies
====================================================================
Tracks real-world performance of the 13 newest alpha engine strategies,
computing per-strategy metrics, symbol breakdowns, and high-score picks.

Run standalone:  python alpha_engine/forward_test_new_strategies.py
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TRACKED_STRATEGIES = [
    "beta_adjusted_residual_momentum",
    "stablecoin_flow_momentum",
    "disposition_effect_contrarian",
    "cross_sectional_reversal",
    "token_unlock_event_short",
    "btc_power_law_deviation",
    "nvm_metcalfe_valuation",
    "eth_gas_fee_reversal",
    "okx_top_trader_consensus",
    "binance_crowd_contrarian",
    "cme_cot_positioning",
    "weekly_oi_change_momentum",
    "miner_capitulation_recovery",
]

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
OUTPUT_PATH = DATA_DIR / "new_strategy_forward_results.json"

HIGH_SCORE_MIN_WR = 0.60
HIGH_SCORE_MIN_TRADES = 5

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> list:
    """Load a JSON file, returning [] if missing or invalid."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def safe_float(val, default=0.0):
    """Convert to float safely."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def compute_hold_days(entry_date_str, exit_date_str):
    """Compute hold days between two date strings."""
    if not entry_date_str or not exit_date_str:
        return None
    try:
        fmt = "%Y-%m-%d"
        entry = datetime.strptime(entry_date_str[:10], fmt)
        exit_ = datetime.strptime(exit_date_str[:10], fmt)
        return max((exit_ - entry).days, 0)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Core Analysis
# ---------------------------------------------------------------------------


def filter_picks(all_picks: list, strategies: list) -> list:
    """Filter picks belonging to tracked strategies."""
    strat_set = set(strategies)
    return [p for p in all_picks if p.get("strategy") in strat_set]


def compute_strategy_metrics(closed: list, open_: list) -> dict:
    """Compute performance metrics for a single strategy's picks."""
    total = len(closed) + len(open_)

    if total == 0:
        return {
            "total_trades": 0,
            "open_trades": 0,
            "closed_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "avg_pnl_pct": None,
            "profit_factor": None,
            "best_trade_pnl": None,
            "worst_trade_pnl": None,
            "avg_hold_days": None,
            "status": "Awaiting first trades...",
        }

    wins = [p for p in closed if p.get("status") == "WON"]
    losses = [p for p in closed if p.get("status") == "LOST"]
    n_closed = len(closed)
    n_wins = len(wins)
    n_losses = len(losses)

    pnls = [safe_float(p.get("pnl_pct")) for p in closed if p.get("pnl_pct") is not None]

    win_rate = round(n_wins / n_closed, 4) if n_closed > 0 else None
    avg_pnl = round(sum(pnls) / len(pnls), 6) if pnls else None

    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    profit_factor = round(gross_profit / gross_loss, 4) if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else None
    )

    best = round(max(pnls), 6) if pnls else None
    worst = round(min(pnls), 6) if pnls else None

    hold_days_list = []
    for p in closed:
        hd = p.get("hold_days")
        if hd is not None:
            hold_days_list.append(safe_float(hd))
        else:
            hd_calc = compute_hold_days(p.get("entry_date"), p.get("exit_date"))
            if hd_calc is not None:
                hold_days_list.append(hd_calc)

    avg_hold = round(sum(hold_days_list) / len(hold_days_list), 2) if hold_days_list else None

    return {
        "total_trades": total,
        "open_trades": len(open_),
        "closed_trades": n_closed,
        "wins": n_wins,
        "losses": n_losses,
        "win_rate": win_rate,
        "avg_pnl_pct": avg_pnl,
        "profit_factor": profit_factor if profit_factor != float("inf") else 999.99,
        "best_trade_pnl": best,
        "worst_trade_pnl": worst,
        "avg_hold_days": avg_hold,
        "status": "active",
    }


def compute_symbol_breakdown(closed: list) -> dict:
    """Break down closed picks by symbol."""
    by_sym = defaultdict(list)
    for p in closed:
        by_sym[p.get("symbol", "UNKNOWN")].append(p)

    result = {}
    for sym, picks in sorted(by_sym.items()):
        n = len(picks)
        wins = sum(1 for p in picks if p.get("status") == "WON")
        pnls = [safe_float(p.get("pnl_pct")) for p in picks if p.get("pnl_pct") is not None]
        gp = sum(x for x in pnls if x > 0)
        gl = abs(sum(x for x in pnls if x < 0))
        pf = round(gp / gl, 4) if gl > 0 else (999.99 if gp > 0 else None)

        result[sym] = {
            "trades": n,
            "wr": round(wins / n, 4) if n > 0 else None,
            "pf": pf,
            "avg_pnl": round(sum(pnls) / len(pnls), 6) if pnls else None,
        }
    return result


def build_full_report(active_picks: list, closed_picks: list) -> dict:
    """Build the full forward-test report for all tracked strategies."""
    active_filtered = filter_picks(active_picks, TRACKED_STRATEGIES)
    closed_filtered = filter_picks(closed_picks, TRACKED_STRATEGIES)

    # Group by strategy
    active_by_strat = defaultdict(list)
    closed_by_strat = defaultdict(list)
    for p in active_filtered:
        active_by_strat[p["strategy"]].append(p)
    for p in closed_filtered:
        closed_by_strat[p["strategy"]].append(p)

    report = {}
    high_score_picks = []

    for strat in TRACKED_STRATEGIES:
        strat_closed = closed_by_strat.get(strat, [])
        strat_open = active_by_strat.get(strat, [])

        overall = compute_strategy_metrics(strat_closed, strat_open)
        by_symbol = compute_symbol_breakdown(strat_closed)

        # Recommended / avoid symbols
        recommended = []
        avoid = []
        for sym, stats in by_symbol.items():
            if stats["trades"] >= 3 and stats["wr"] is not None:
                if stats["wr"] >= 0.60:
                    recommended.append(sym)
                elif stats["wr"] < 0.40:
                    avoid.append(sym)

        report[strat] = {
            "overall": overall,
            "by_symbol": by_symbol,
            "recommended_symbols": sorted(recommended),
            "avoid_symbols": sorted(avoid),
        }

        # High-score picks: strategy+symbol combos with WR > 60% and 5+ trades
        for sym, stats in by_symbol.items():
            if (
                stats["trades"] >= HIGH_SCORE_MIN_TRADES
                and stats["wr"] is not None
                and stats["wr"] >= HIGH_SCORE_MIN_WR
            ):
                high_score_picks.append({
                    "strategy": strat,
                    "symbol": sym,
                    "trades": stats["trades"],
                    "win_rate": stats["wr"],
                    "profit_factor": stats["pf"],
                    "avg_pnl_pct": stats["avg_pnl"],
                })

    # Sort high-score by WR desc, then trades desc
    high_score_picks.sort(key=lambda x: (-x["win_rate"], -x["trades"]))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tracked_strategies": TRACKED_STRATEGIES,
        "strategy_count": len(TRACKED_STRATEGIES),
        "total_active_picks": len(active_filtered),
        "total_closed_picks": len(closed_filtered),
        "strategies": report,
        "high_score_picks": high_score_picks,
    }


# ---------------------------------------------------------------------------
# Human-Readable Report
# ---------------------------------------------------------------------------


def print_report(data: dict):
    """Print a formatted performance report."""
    print("=" * 90)
    print("  FORWARD-TEST TRACKER  |  New Research-Backed Strategies")
    print(f"  Generated: {data['generated_at']}")
    print(f"  Strategies tracked: {data['strategy_count']}")
    print(f"  Active picks: {data['total_active_picks']}  |  Closed picks: {data['total_closed_picks']}")
    print("=" * 90)

    # Ranking table
    rows = []
    for strat in TRACKED_STRATEGIES:
        info = data["strategies"][strat]["overall"]
        if info["status"] == "Awaiting first trades...":
            rows.append((strat, 0, None, None, None, None, "awaiting"))
        else:
            rows.append((
                strat,
                info["total_trades"],
                info["win_rate"],
                info["profit_factor"],
                info["avg_pnl_pct"],
                info["avg_hold_days"],
                "active",
            ))

    # Sort: active strategies first (by WR desc), then awaiting
    rows.sort(key=lambda r: (
        0 if r[6] == "active" else 1,
        -(r[2] or 0),
        -(r[1] or 0),
    ))

    print()
    print(f"  {'#':<3} {'Strategy':<40} {'Trades':>7} {'WR':>8} {'PF':>8} {'Avg PnL':>10} {'Hold(d)':>8}")
    print("  " + "-" * 86)

    rank = 1
    for strat, trades, wr, pf, avg_pnl, hold, status in rows:
        name = strat[:38]
        if status == "awaiting":
            print(f"  {'-':<3} {name:<40} {'--':>7} {'--':>8} {'--':>8} {'--':>10} {'--':>8}  Awaiting first trades...")
        else:
            wr_str = f"{wr*100:.1f}%" if wr is not None else "--"
            pf_str = f"{pf:.2f}" if pf is not None and pf < 900 else ("INF" if pf and pf >= 900 else "--")
            pnl_str = f"{avg_pnl*100:.2f}%" if avg_pnl is not None else "--"
            hold_str = f"{hold:.1f}" if hold is not None else "--"
            print(f"  {rank:<3} {name:<40} {trades:>7} {wr_str:>8} {pf_str:>8} {pnl_str:>10} {hold_str:>8}")
            rank += 1

    # Symbol breakdown for strategies with data
    print()
    print("=" * 90)
    print("  SYMBOL BREAKDOWN (strategies with closed trades)")
    print("=" * 90)

    for strat in TRACKED_STRATEGIES:
        sdata = data["strategies"][strat]
        if not sdata["by_symbol"]:
            continue
        print(f"\n  >> {strat}")
        print(f"     {'Symbol':<15} {'Trades':>7} {'WR':>8} {'PF':>8} {'Avg PnL':>10}")
        print("     " + "-" * 50)
        for sym, stats in sorted(sdata["by_symbol"].items(), key=lambda x: -(x[1].get("wr") or 0)):
            wr_s = f"{stats['wr']*100:.1f}%" if stats["wr"] is not None else "--"
            pf_s = f"{stats['pf']:.2f}" if stats["pf"] is not None and stats["pf"] < 900 else ("INF" if stats["pf"] and stats["pf"] >= 900 else "--")
            pnl_s = f"{stats['avg_pnl']*100:.2f}%" if stats["avg_pnl"] is not None else "--"
            print(f"     {sym:<15} {stats['trades']:>7} {wr_s:>8} {pf_s:>8} {pnl_s:>10}")

        if sdata["recommended_symbols"]:
            print(f"     Recommended: {', '.join(sdata['recommended_symbols'])}")
        if sdata["avoid_symbols"]:
            print(f"     Avoid:       {', '.join(sdata['avoid_symbols'])}")

    # High-score picks
    print()
    print("=" * 90)
    print("  HIGH-SCORE PICKS  (WR >= 60% with 5+ closed trades)")
    print("=" * 90)

    if not data["high_score_picks"]:
        print("  No qualifying combos yet. Need more closed trades to identify high-score picks.")
    else:
        print(f"\n  {'Strategy':<40} {'Symbol':<12} {'Trades':>7} {'WR':>8} {'PF':>8} {'Avg PnL':>10}")
        print("  " + "-" * 86)
        for pick in data["high_score_picks"]:
            wr_s = f"{pick['win_rate']*100:.1f}%"
            pf_s = f"{pick['profit_factor']:.2f}" if pick["profit_factor"] and pick["profit_factor"] < 900 else "INF"
            pnl_s = f"{pick['avg_pnl_pct']*100:.2f}%" if pick["avg_pnl_pct"] is not None else "--"
            print(f"  {pick['strategy']:<40} {pick['symbol']:<12} {pick['trades']:>7} {wr_s:>8} {pf_s:>8} {pnl_s:>10}")

    print()
    print(f"  Results saved to: {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print("=" * 90)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print(f"[forward_test] Loading picks from {DATA_DIR} ...")

    active_picks = load_json(ACTIVE_PICKS_PATH)
    closed_picks = load_json(CLOSED_PICKS_PATH)

    print(f"[forward_test] Loaded {len(active_picks)} active, {len(closed_picks)} closed picks total")

    report = build_full_report(active_picks, closed_picks)

    # Save results
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print_report(report)

    # Summary exit
    active_strats = sum(
        1 for s in TRACKED_STRATEGIES
        if report["strategies"][s]["overall"]["status"] == "active"
    )
    print(f"\n[forward_test] Done. {active_strats}/{len(TRACKED_STRATEGIES)} strategies have trade data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
