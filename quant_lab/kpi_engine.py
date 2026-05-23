"""
KPI Engine — Compute win-rate, R:R, expectancy, Sharpe, Sortino, Kelly, DD
per strategy and per bundle from our actual JSON/SQLite data sources.

Adapted from Mercury/Inception Labs framework for our infrastructure.

Usage:
    python quant_lab/kpi_engine.py                    # Full snapshot
    python quant_lab/kpi_engine.py --strategy autocorrelation_exploiter  # Single strategy
    python quant_lab/kpi_engine.py --format json      # JSON output
"""
import json
import sys
import os
import math
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "alpha_engine" / "data"
SNAPSHOT_DIR = ROOT / "quant_lab" / "snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────
# Core metric functions (pure math, no pandas dependency)
# ─────────────────────────────────────────────────────────────────

def win_rate(pnls):
    """Fraction of trades with positive PnL."""
    if not pnls:
        return 0.0
    return sum(1 for p in pnls if p > 0) / len(pnls)


def avg_win(pnls):
    """Mean profit of winning trades."""
    wins = [p for p in pnls if p > 0]
    return sum(wins) / len(wins) if wins else 0.0


def avg_loss(pnls):
    """Mean loss of losing trades (returned as negative)."""
    losses = [p for p in pnls if p <= 0]
    return sum(losses) / len(losses) if losses else 0.0


def expectancy(pnls):
    """E = (WinRate × AvgWin) - (LossRate × |AvgLoss|)."""
    if not pnls:
        return 0.0
    wr = win_rate(pnls)
    aw = avg_win(pnls)
    al = abs(avg_loss(pnls))
    return wr * aw - (1 - wr) * al


def payoff_ratio(pnls):
    """|AvgWin| / |AvgLoss|. Returns 0 if no losses."""
    aw = avg_win(pnls)
    al = abs(avg_loss(pnls))
    if al == 0:
        return float('inf') if aw > 0 else 0.0
    return aw / al


def sharpe_ratio(pnls, rf_annual=0.05):
    """Sharpe ratio. rf_annual is annualized risk-free rate (GIC ~5%)."""
    if len(pnls) < 2:
        return 0.0
    mean_ret = sum(pnls) / len(pnls)
    rf_per_trade = rf_annual / 365.0  # approximate per-trade rf
    excess = [p - rf_per_trade for p in pnls]
    mean_excess = sum(excess) / len(excess)
    var = sum((x - mean_excess) ** 2 for x in excess) / len(excess)
    std = math.sqrt(var) if var > 0 else 0.0001
    return mean_excess / std


def sortino_ratio(pnls, rf_annual=0.05):
    """Sortino ratio — only downside volatility."""
    if len(pnls) < 2:
        return 0.0
    rf_per_trade = rf_annual / 365.0
    excess = [p - rf_per_trade for p in pnls]
    mean_excess = sum(excess) / len(excess)
    downside = [x for x in excess if x < 0]
    if not downside:
        return float('inf') if mean_excess > 0 else 0.0
    down_var = sum(x ** 2 for x in downside) / len(downside)
    down_std = math.sqrt(down_var) if down_var > 0 else 0.0001
    return mean_excess / down_std


def max_drawdown(pnls):
    """Maximum drawdown as fraction of peak equity. Input: list of PnL %."""
    if not pnls:
        return 0.0
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for p in pnls:
        equity *= (1 + p)
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def kelly_fraction(pnls):
    """Kelly criterion: K = W - (1-W)/R where W=win_rate, R=payoff_ratio."""
    if not pnls:
        return 0.0
    w = win_rate(pnls)
    r = payoff_ratio(pnls)
    if r == 0 or r == float('inf'):
        return 0.0
    k = w - (1 - w) / r
    return max(-1.0, min(1.0, k))  # clamp to [-1, 1]


def profit_factor(pnls):
    """Sum of wins / |Sum of losses|."""
    total_wins = sum(p for p in pnls if p > 0)
    total_losses = abs(sum(p for p in pnls if p <= 0))
    if total_losses == 0:
        return 99.99 if total_wins > 0 else 0.0
    return total_wins / total_losses


def avg_hold_days(trades):
    """Average holding period in days."""
    holds = [t.get("hold_days", 0) for t in trades if "hold_days" in t]
    return sum(holds) / len(holds) if holds else 0.0


def avg_mfe(trades):
    """Average Maximum Favorable Excursion."""
    mfes = [t.get("mfe", 0) for t in trades if "mfe" in t]
    return sum(mfes) / len(mfes) if mfes else 0.0


def avg_mae(trades):
    """Average Maximum Adverse Excursion."""
    maes = [t.get("mae", 0) for t in trades if "mae" in t]
    return sum(maes) / len(maes) if maes else 0.0


# ─────────────────────────────────────────────────────────────────
# Data loading — reads our actual JSON files
# ─────────────────────────────────────────────────────────────────

def load_closed_picks():
    """Load all closed trades from alpha_engine/data/closed_picks.json."""
    path = DATA_DIR / "closed_picks.json"
    if not path.exists():
        print(f"ERROR: {path} not found")
        return []
    with open(path, "r") as f:
        return json.load(f)


def load_strategy_performance():
    """Load pre-computed strategy performance from strategy_performance.json."""
    path = DATA_DIR / "strategy_performance.json"
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return json.load(f)


ACTIVE_PICKS_PATH = ROOT / "paper_trading" / "data" / "active_picks.json"


def load_active_picks():
    """Load all currently-open picks from paper_trading/data/active_picks.json."""
    if not ACTIVE_PICKS_PATH.exists():
        return []
    try:
        with open(ACTIVE_PICKS_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def get_active_counts_by_strategy(active_picks=None):
    """Return {strategy_name: [pick, ...]} for open picks."""
    if active_picks is None:
        active_picks = load_active_picks()
    by_strat = defaultdict(list)
    for p in active_picks:
        strat = p.get("strategy", "unknown")
        by_strat[strat].append(p)
    return dict(by_strat)


def get_latest_closed_per_strategy(closed=None):
    """Return {strategy: latest_closed_pick_dict} by exit_date or entry_date."""
    if closed is None:
        closed = load_closed_picks()
    latest = {}
    for trade in closed:
        strat = trade.get("strategy", "unknown")
        ts = trade.get("exit_date") or trade.get("entry_date") or ""
        if not ts:
            continue
        prev_ts = latest.get(strat, {}).get("_sort_ts", "")
        if ts > prev_ts:
            latest[strat] = {**trade, "_sort_ts": ts}
    # Strip temporary sort key
    return {k: {kk: vv for kk, vv in v.items() if kk != "_sort_ts"}
            for k, v in latest.items()}


def load_bundle_registry():
    """Load bundle definitions from BABY_BUNDLE_REGISTRY.md (parse YAML blocks)."""
    # We'll use the battleground DB data instead for actual metrics
    bundles = {}
    try:
        import sqlite3
        db_path = ROOT / "battleground" / "data" / "bundle_babies.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM bundle_babies").fetchall()
            for row in rows:
                bundles[row["bundle_id"]] = dict(row)
            conn.close()
    except Exception as e:
        print(f"Warning: Could not load bundle DB: {e}")
    return bundles


# ─────────────────────────────────────────────────────────────────
# Main KPI computation
# ─────────────────────────────────────────────────────────────────

def compute_all_kpis(min_trades=1):
    """Compute KPIs for every strategy from closed_picks.json."""
    closed = load_closed_picks()
    if not closed:
        print("No closed picks found.")
        return []

    # Group trades by strategy
    by_strategy = defaultdict(list)
    for trade in closed:
        strat = trade.get("strategy", "unknown")
        by_strategy[strat].append(trade)

    results = []
    for strat_name, trades in sorted(by_strategy.items()):
        if len(trades) < min_trades:
            continue

        pnls = [t.get("pnl_pct", 0) for t in trades]
        pnl_dollars = [t.get("pnl_dollar", 0) for t in trades]

        # Compute all KPIs
        wr = win_rate(pnls)
        aw = avg_win(pnls)
        al = avg_loss(pnls)
        exp = expectancy(pnls)
        pr = payoff_ratio(pnls)
        kf = kelly_fraction(pnls)
        sr = sharpe_ratio(pnls)
        sort = sortino_ratio(pnls)
        mdd = max_drawdown(pnls)
        pf = profit_factor(pnls)
        mfe = avg_mfe(trades)
        mae = avg_mae(trades)
        hold = avg_hold_days(trades)

        # TP efficiency: how much of the favorable move we capture
        tp_efficiency = (sum(pnls) / len(pnls)) / mfe if mfe > 0 else 0

        # Symbol breakdown
        by_symbol = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0})
        for t in trades:
            sym = t.get("symbol", "UNKNOWN")
            if t.get("pnl_pct", 0) > 0:
                by_symbol[sym]["wins"] += 1
            else:
                by_symbol[sym]["losses"] += 1
            by_symbol[sym]["pnl"] += t.get("pnl_pct", 0)

        # Direction breakdown
        long_pnls = [t["pnl_pct"] for t in trades if t.get("signal_type") == "BUY"]
        short_pnls = [t["pnl_pct"] for t in trades if t.get("signal_type") == "SELL"]

        # Confidence breakdown
        high_conf = [t["pnl_pct"] for t in trades if t.get("confidence", 0) >= 0.65]
        low_conf = [t["pnl_pct"] for t in trades if t.get("confidence", 0) < 0.65]

        # Exit reason breakdown
        exit_reasons = defaultdict(int)
        for t in trades:
            exit_reasons[t.get("exit_reason", "UNKNOWN")] += 1

        results.append({
            "entity_type": "strategy",
            "entity_id": strat_name,
            "trade_count": len(trades),
            "wins": sum(1 for p in pnls if p > 0),
            "losses": sum(1 for p in pnls if p <= 0),
            "win_rate": round(wr, 4),
            "avg_win_pct": round(aw, 6),
            "avg_loss_pct": round(al, 6),
            "expectancy_pct": round(exp, 6),
            "payoff_ratio": round(pr, 4) if pr != float('inf') else 99.99,
            "kelly_fraction": round(kf, 4),
            "sharpe": round(sr, 4),
            "sortino": round(sort, 4) if sort != float('inf') else 99.99,
            "max_drawdown": round(mdd, 4),
            "profit_factor": round(pf, 4),
            "total_pnl_pct": round(sum(pnls), 6),
            "total_pnl_dollar": round(sum(pnl_dollars), 2),
            "avg_hold_days": round(hold, 1),
            "avg_mfe": round(mfe, 6),
            "avg_mae": round(mae, 6),
            "tp_efficiency": round(tp_efficiency, 4),
            "exit_reasons": dict(exit_reasons),
            "symbols_traded": len(by_symbol),
            "by_symbol": dict(by_symbol),
            "long_expectancy": round(expectancy(long_pnls), 6) if long_pnls else None,
            "short_expectancy": round(expectancy(short_pnls), 6) if short_pnls else None,
            "high_conf_expectancy": round(expectancy(high_conf), 6) if high_conf else None,
            "low_conf_expectancy": round(expectancy(low_conf), 6) if low_conf else None,
            "high_conf_wr": round(win_rate(high_conf), 4) if high_conf else None,
            "low_conf_wr": round(win_rate(low_conf), 4) if low_conf else None,
        })

    return results


def compute_edge_verdict(kpi):
    """Classify a strategy: EDGE, MARGINAL, TRAP, ASYMMETRIC, DEAD."""
    exp = kpi["expectancy_pct"]
    wr = kpi["win_rate"]
    kf = kpi["kelly_fraction"]
    pf = kpi["profit_factor"]
    trades = kpi["trade_count"]

    if exp <= 0 and wr > 0.7:
        return "TRAP"  # High WR masking negative expectancy
    if exp <= -0.02:
        return "DEAD"
    if exp <= 0:
        return "NO_EDGE"
    if wr < 0.35 and pf > 2.0:
        return "ASYMMETRIC"  # Low WR but big wins
    if trades < 5:
        return "EDGE_UNCONFIRMED"
    if kf > 0.1 and exp > 0.02:
        return "EDGE"
    if exp > 0:
        return "MARGINAL"
    return "UNKNOWN"


def save_snapshot(results):
    """Save KPI snapshot as JSON."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    path = SNAPSHOT_DIR / f"kpi_snapshot_{ts}.json"
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_strategies": len(results),
        "strategies": results,
    }
    with open(path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"Snapshot saved: {path}")
    return path


def print_report(results, top_n=20):
    """Print formatted KPI report to console."""
    # Sort by expectancy descending
    ranked = sorted(results, key=lambda x: x["expectancy_pct"], reverse=True)

    print("\n" + "=" * 120)
    print("QUANT RESEARCH LAB — KPI ENGINE REPORT")
    print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Total strategies analyzed: {len(results)}")
    print("=" * 120)

    # Summary stats
    positive_edge = [r for r in results if r["expectancy_pct"] > 0]
    negative_edge = [r for r in results if r["expectancy_pct"] <= 0]
    total_pnl = sum(r["total_pnl_dollar"] for r in results)
    pos_pnl = sum(r["total_pnl_dollar"] for r in positive_edge)
    neg_pnl = sum(r["total_pnl_dollar"] for r in negative_edge)

    print(f"\nEdge Summary: {len(positive_edge)} positive / {len(negative_edge)} negative")
    print(f"Total PnL: ${total_pnl:,.2f}  (Winners: ${pos_pnl:,.2f} | Losers: ${neg_pnl:,.2f})")

    # Table header
    print(f"\n{'Strategy':<35} {'Trades':>6} {'WR%':>6} {'Expect':>8} {'Sharpe':>7} "
          f"{'Kelly':>6} {'PF':>6} {'MaxDD':>7} {'PnL$':>9} {'Verdict':<15}")
    print("-" * 120)

    for r in ranked[:top_n]:
        verdict = compute_edge_verdict(r)
        print(f"{r['entity_id']:<35} {r['trade_count']:>6} "
              f"{r['win_rate']*100:>5.1f}% {r['expectancy_pct']:>+7.4f} "
              f"{r['sharpe']:>7.2f} {r['kelly_fraction']:>+5.2f} "
              f"{r['profit_factor']:>6.2f} {r['max_drawdown']:>6.2%} "
              f"${r['total_pnl_dollar']:>+8.2f} {verdict:<15}")

    # TP Efficiency analysis
    print(f"\n{'─'*60}")
    print("TP EFFICIENCY ANALYSIS (are we leaving money on the table?)")
    print(f"{'─'*60}")
    for r in ranked[:10]:
        if r["avg_mfe"] > 0 and r["expectancy_pct"] > 0:
            captured = r["tp_efficiency"]
            left = 1 - captured if captured < 1 else 0
            print(f"  {r['entity_id']:<35} MFE: {r['avg_mfe']:>+.4f} | "
                  f"Captured: {captured:>5.1%} | Left on table: {left:>5.1%}")

    # Confidence analysis
    print(f"\n{'─'*60}")
    print("CONFIDENCE THRESHOLD ANALYSIS")
    print(f"{'─'*60}")
    for r in ranked[:10]:
        if r["high_conf_expectancy"] is not None and r["low_conf_expectancy"] is not None:
            print(f"  {r['entity_id']:<35} "
                  f"High(≥0.65): E={r['high_conf_expectancy']:>+.4f} WR={r['high_conf_wr']:.0%} | "
                  f"Low(<0.65): E={r['low_conf_expectancy']:>+.4f} WR={r['low_conf_wr']:.0%}")


# ─────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Quant Lab KPI Engine")
    parser.add_argument("--strategy", type=str, help="Analyze single strategy")
    parser.add_argument("--min-trades", type=int, default=1, help="Min trades to include")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--save", action="store_true", help="Save snapshot")
    args = parser.parse_args()

    results = compute_all_kpis(min_trades=args.min_trades)

    if args.strategy:
        results = [r for r in results if r["entity_id"] == args.strategy]

    if args.format == "json":
        print(json.dumps(results, indent=2, default=str))
    else:
        print_report(results)

    if args.save:
        save_snapshot(results)
