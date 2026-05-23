#!/usr/bin/env python3
"""
Performance Monitor — Per-System Sharpe, Win Rate & Demotion Triggers
======================================================================
Reads closed trade data from picks/results JSON files across subsystems.
Computes:
  - Per-system 7-day rolling Sharpe ratio
  - Per-system 20-trade rolling win rate
  - Per-system max drawdown
Checks demotion triggers (from TESTING_PROTOCOL.MD & BACKTEST_4MONTH_ANALYSIS.md):
  - 7-day Sharpe < 0 => alert
  - Rolling 20-trade expectancy < 0 => flag
  - Rolling 30-day WR drops > 10pp below baseline => flag
  - Strategy-level DD exceeds 15% => flag
  - Win rate < 30% on 20+ recent trades => flag
  - Sharpe < 0 for 2 consecutive weeks => demote trust tier

Outputs: strategy_health/data/performance_report.json

Run:  python -m strategy_health.performance_monitor [--verbose]
"""

import argparse
import datetime as dt
import json
import math
import os
import pathlib
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / "strategy_health" / "data" / "performance_report.json"
HISTORY_DIR = REPO_ROOT / "strategy_health" / "data"

# ---------------------------------------------------------------------------
# Thresholds (from BACKTEST_4MONTH_ANALYSIS Appendix B & TESTING_PROTOCOL)
# ---------------------------------------------------------------------------
SHARPE_ALERT_THRESHOLD = 0.0           # 7-day Sharpe < 0 => alert
SHARPE_DEMOTE_CONSECUTIVE_WEEKS = 2    # < 0 for 2 consecutive weeks => demote
WIN_RATE_FLOOR = 0.30                  # WR < 30% on 20+ trades => flag
WIN_RATE_DROP_PP = 0.10                # WR drops > 10pp below baseline => flag
MAX_DD_THRESHOLD = 0.15                # Strategy DD > 15% => flag
MAX_DD_48H_THRESHOLD = 0.05           # DD > 5% in 48h => auto-pause alert
EXPECTANCY_FLOOR = 0.0                 # 20-trade rolling expectancy < 0 => flag
MIN_TRADES_FOR_EVAL = 5                # Minimum trades to evaluate

# ---------------------------------------------------------------------------
# Data sources: directories containing closed_picks.json
# ---------------------------------------------------------------------------
CLOSED_PICKS_SOURCES = [
    "alpha_engine/data/closed_picks.json",
    "alpha_engine/data/closed_picks_fast.json",
    "battleground/data/closed_picks.json",
    "crypto_signal_engine/data/closed_picks.json",
    "genome/data/closed_picks.json",
    "KIMI_RISEOFTHECLAW/data/closed_picks.json",
    "mercury2/data/closed_picks.json",
    "ml_battleground/ensemble_data/closed_picks.json",
    "paper_trading/data/closed_picks.json",
    "rapid_fire_data/closed_picks.json",
]

GOLDMINE_TRADES = "data/goldmine/closed_trades.json"
COPY_TRADER_TRADES = "copy_trader_intel/data/closed_trades.json"


def load_closed_picks(verbose: bool = False) -> List[Dict]:
    """Load all closed trade records from known JSON sources."""
    all_trades: List[Dict] = []

    for rel_path in CLOSED_PICKS_SOURCES:
        fpath = REPO_ROOT / rel_path
        if not fpath.exists():
            if verbose:
                print(f"  [SKIP] {rel_path} — not found")
            continue
        try:
            raw = json.loads(fpath.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                trades = raw
            elif isinstance(raw, dict) and "trades" in raw:
                trades = raw["trades"]
            elif isinstance(raw, dict) and "tracked_picks" in raw:
                trades = raw["tracked_picks"]
            else:
                trades = []

            source_label = rel_path.split("/")[0]
            for t in trades:
                # Normalize fields
                trade = _normalize_trade(t, source_label)
                if trade:
                    all_trades.append(trade)

            if verbose:
                print(f"  [OK]   {rel_path} — {len(trades)} records")
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            if verbose:
                print(f"  [ERR]  {rel_path} — {e}")

    # Goldmine trades (different format)
    goldmine_path = REPO_ROOT / GOLDMINE_TRADES
    if goldmine_path.exists():
        try:
            raw = json.loads(goldmine_path.read_text(encoding="utf-8"))
            trades_list = raw.get("trades", []) if isinstance(raw, dict) else raw
            for t in trades_list:
                trade = _normalize_goldmine_trade(t)
                if trade:
                    all_trades.append(trade)
            if verbose:
                print(f"  [OK]   {GOLDMINE_TRADES} — {len(trades_list)} records")
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            if verbose:
                print(f"  [ERR]  {GOLDMINE_TRADES} — {e}")

    # Copy trader trades
    copy_path = REPO_ROOT / COPY_TRADER_TRADES
    if copy_path.exists():
        try:
            raw = json.loads(copy_path.read_text(encoding="utf-8"))
            trades_list = raw.get("trades", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
            for t in trades_list:
                trade = _normalize_trade(t, "copy_trader")
                if trade:
                    all_trades.append(trade)
            if verbose:
                print(f"  [OK]   {COPY_TRADER_TRADES} — {len(trades_list)} records")
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            if verbose:
                print(f"  [ERR]  {COPY_TRADER_TRADES} — {e}")

    return all_trades


def _normalize_trade(t: Dict, source_label: str) -> Optional[Dict]:
    """Normalize a closed_picks.json trade record to common format."""
    status = str(t.get("status", "")).upper()
    if status not in ("CLOSED", "TP_HIT", "SL_HIT", "WIN", "LOSS"):
        # Also check outcome field
        outcome = str(t.get("outcome", "")).upper()
        if outcome not in ("WIN", "LOSS", "TP_HIT", "SL_HIT"):
            return None

    pnl = t.get("pnl_pct") or t.get("final_return_pct") or t.get("unrealized_pnl_pct")
    if pnl is None:
        return None
    try:
        pnl = float(pnl)
    except (ValueError, TypeError):
        return None

    # Determine outcome
    outcome = str(t.get("outcome", "")).upper()
    if outcome in ("WIN", "TP_HIT"):
        is_win = True
    elif outcome in ("LOSS", "SL_HIT"):
        is_win = False
    else:
        is_win = pnl > 0

    # Parse close time
    closed_at = t.get("closed_at") or t.get("exit_time") or t.get("exit_date") or t.get("resolved_at")
    close_dt = _parse_datetime(closed_at)

    # Strategy name
    strategy = t.get("strategy") or t.get("source_system") or t.get("source") or source_label
    source = t.get("source_system") or t.get("source") or source_label

    return {
        "strategy": str(strategy),
        "source": str(source),
        "symbol": t.get("symbol") or t.get("ticker") or "UNKNOWN",
        "pnl_pct": pnl,
        "is_win": is_win,
        "closed_at": close_dt,
    }


def _normalize_goldmine_trade(t: Dict) -> Optional[Dict]:
    """Normalize goldmine/closed_trades.json format."""
    outcome = str(t.get("outcome", "")).upper()
    if outcome not in ("WIN", "LOSS"):
        return None

    pnl = t.get("final_return_pct", 0)
    try:
        pnl = float(pnl)
    except (ValueError, TypeError):
        return None

    close_dt = _parse_datetime(t.get("exit_date"))

    return {
        "strategy": "goldmine",
        "source": "goldmine",
        "symbol": t.get("ticker") or "UNKNOWN",
        "pnl_pct": pnl,
        "is_win": outcome == "WIN",
        "closed_at": close_dt,
    }


def _parse_datetime(val) -> Optional[dt.datetime]:
    """Best-effort datetime parsing from various string formats."""
    if val is None:
        return None
    if isinstance(val, dt.datetime):
        return val
    s = str(val).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            parsed = dt.datetime.strptime(s[:26].replace("+00:00", "").rstrip("Z"), fmt.replace("%z", ""))
            return parsed
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

def compute_sharpe(returns: List[float], annualize_factor: float = 365.0) -> Optional[float]:
    """Compute Sharpe ratio from a list of pnl_pct values.
    Returns None if insufficient data."""
    if len(returns) < 2:
        return None
    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    std_r = math.sqrt(variance) if variance > 0 else 0
    if std_r == 0:
        return None
    # Annualized Sharpe (assuming daily returns)
    sharpe = (mean_r / std_r) * math.sqrt(annualize_factor)
    return round(sharpe, 4)


def compute_rolling_win_rate(trades: List[Dict], window: int = 20) -> Optional[float]:
    """Compute win rate over the last N trades."""
    if len(trades) < window:
        return None
    recent = trades[-window:]
    wins = sum(1 for t in recent if t["is_win"])
    return round(wins / window, 4)


def compute_expectancy(trades: List[Dict], window: int = 20) -> Optional[float]:
    """Compute expectancy over the last N trades."""
    if len(trades) < window:
        return None
    recent = trades[-window:]
    wins = [t["pnl_pct"] for t in recent if t["is_win"]]
    losses = [abs(t["pnl_pct"]) for t in recent if not t["is_win"]]
    total = len(recent)
    if total == 0:
        return None
    wr = len(wins) / total
    avg_win = (sum(wins) / len(wins)) if wins else 0
    avg_loss = (sum(losses) / len(losses)) if losses else 0
    return round((wr * avg_win) - ((1 - wr) * avg_loss), 4)


def compute_max_drawdown(trades: List[Dict]) -> float:
    """Compute max drawdown from cumulative PnL curve."""
    if not trades:
        return 0.0
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        cumulative += t["pnl_pct"]
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 4)


def compute_48h_drawdown(trades: List[Dict]) -> float:
    """Compute drawdown from trades in the last 48 hours."""
    now = dt.datetime.utcnow()
    cutoff = now - dt.timedelta(hours=48)
    recent = [t for t in trades if t.get("closed_at") and t["closed_at"] >= cutoff]
    if not recent:
        return 0.0
    return compute_max_drawdown(recent)


def compute_7day_sharpe(trades: List[Dict]) -> Optional[float]:
    """Compute Sharpe from trades closed in the last 7 days."""
    now = dt.datetime.utcnow()
    cutoff = now - dt.timedelta(days=7)
    recent = [t for t in trades if t.get("closed_at") and t["closed_at"] >= cutoff]
    if len(recent) < 2:
        return None
    returns = [t["pnl_pct"] for t in recent]
    return compute_sharpe(returns, annualize_factor=365.0 / 7.0)


def compute_weekly_sharpes(trades: List[Dict], weeks: int = 4) -> List[Optional[float]]:
    """Compute Sharpe for each of the last N weeks (most recent last)."""
    now = dt.datetime.utcnow()
    result = []
    for w in range(weeks, 0, -1):
        end = now - dt.timedelta(weeks=w - 1)
        start = now - dt.timedelta(weeks=w)
        week_trades = [
            t for t in trades
            if t.get("closed_at") and start <= t["closed_at"] < end
        ]
        returns = [t["pnl_pct"] for t in week_trades]
        if len(returns) >= 2:
            result.append(compute_sharpe(returns, annualize_factor=52.0))
        else:
            result.append(None)
    return result


def compute_baseline_wr(trades: List[Dict]) -> Optional[float]:
    """Compute all-time win rate as baseline."""
    if not trades:
        return None
    wins = sum(1 for t in trades if t["is_win"])
    return round(wins / len(trades), 4)


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze_strategies(all_trades: List[Dict], verbose: bool = False) -> Dict[str, Any]:
    """Group trades by strategy, compute metrics, check thresholds."""
    # Group by strategy
    by_strategy: Dict[str, List[Dict]] = {}
    for t in all_trades:
        key = t["strategy"]
        by_strategy.setdefault(key, []).append(t)

    # Sort each strategy's trades by close time
    for key in by_strategy:
        by_strategy[key].sort(
            key=lambda x: x.get("closed_at") or dt.datetime.min
        )

    report = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "total_strategies": len(by_strategy),
        "total_trades": len(all_trades),
        "strategies": {},
        "warnings": [],
        "demotion_candidates": [],
        "auto_pause_candidates": [],
    }

    for strategy, trades in sorted(by_strategy.items()):
        n_trades = len(trades)
        if n_trades < MIN_TRADES_FOR_EVAL:
            continue

        # Core metrics
        sharpe_7d = compute_7day_sharpe(trades)
        weekly_sharpes = compute_weekly_sharpes(trades, weeks=4)
        rolling_wr_20 = compute_rolling_win_rate(trades, window=20)
        rolling_expect_20 = compute_expectancy(trades, window=20)
        baseline_wr = compute_baseline_wr(trades)
        max_dd = compute_max_drawdown(trades)
        dd_48h = compute_48h_drawdown(trades)

        # All-time stats
        total_wins = sum(1 for t in trades if t["is_win"])
        total_pnl = sum(t["pnl_pct"] for t in trades)

        entry = {
            "total_trades": n_trades,
            "total_wins": total_wins,
            "total_pnl_pct": round(total_pnl, 4),
            "baseline_wr": baseline_wr,
            "sharpe_7d": sharpe_7d,
            "weekly_sharpes_last_4w": weekly_sharpes,
            "rolling_20_trade_wr": rolling_wr_20,
            "rolling_20_trade_expectancy": rolling_expect_20,
            "max_drawdown_pct": max_dd,
            "drawdown_48h_pct": dd_48h,
            "flags": [],
        }

        # --- Demotion trigger checks ---

        # 1) 7-day Sharpe < 0
        if sharpe_7d is not None and sharpe_7d < SHARPE_ALERT_THRESHOLD:
            msg = f"[SHARPE] {strategy}: 7-day Sharpe = {sharpe_7d:.4f} (< 0)"
            entry["flags"].append("sharpe_7d_negative")
            report["warnings"].append(msg)

        # 2) Sharpe < 0 for 2 consecutive weeks => demote
        if len(weekly_sharpes) >= 2:
            last_two = weekly_sharpes[-2:]
            if (last_two[0] is not None and last_two[0] < 0 and
                    last_two[1] is not None and last_two[1] < 0):
                msg = (f"[DEMOTE] {strategy}: Sharpe < 0 for 2 consecutive weeks "
                       f"({last_two[0]:.4f}, {last_two[1]:.4f})")
                entry["flags"].append("sharpe_consecutive_negative")
                report["demotion_candidates"].append({
                    "strategy": strategy,
                    "reason": msg,
                    "weekly_sharpes": last_two,
                })
                report["warnings"].append(msg)

        # 3) Rolling 20-trade expectancy < 0
        if rolling_expect_20 is not None and rolling_expect_20 < EXPECTANCY_FLOOR:
            msg = (f"[EXPECTANCY] {strategy}: 20-trade rolling expectancy = "
                   f"{rolling_expect_20:.4f}% (< 0)")
            entry["flags"].append("expectancy_negative")
            report["warnings"].append(msg)

        # 4) Win rate < 30% on 20+ recent trades
        if rolling_wr_20 is not None and rolling_wr_20 < WIN_RATE_FLOOR:
            msg = (f"[WIN_RATE] {strategy}: 20-trade rolling WR = "
                   f"{rolling_wr_20 * 100:.1f}% (< 30%)")
            entry["flags"].append("win_rate_below_floor")
            report["warnings"].append(msg)

        # 5) WR drops > 10pp below baseline
        if (rolling_wr_20 is not None and baseline_wr is not None
                and n_trades >= 20):
            drop = baseline_wr - rolling_wr_20
            if drop > WIN_RATE_DROP_PP:
                msg = (f"[WR_DECAY] {strategy}: WR dropped {drop * 100:.1f}pp "
                       f"(baseline {baseline_wr * 100:.1f}% -> "
                       f"recent {rolling_wr_20 * 100:.1f}%)")
                entry["flags"].append("win_rate_decay")
                report["warnings"].append(msg)

        # 6) Strategy-level DD exceeds 15%
        if max_dd > MAX_DD_THRESHOLD * 100:  # max_dd is in pct points
            msg = (f"[DRAWDOWN] {strategy}: max DD = {max_dd:.2f}% "
                   f"(> {MAX_DD_THRESHOLD * 100:.0f}%)")
            entry["flags"].append("max_dd_exceeded")
            report["warnings"].append(msg)

        # 7) DD > 5% in 48h => auto-pause alert
        if dd_48h > MAX_DD_48H_THRESHOLD * 100:
            msg = (f"[AUTO-PAUSE] {strategy}: 48h DD = {dd_48h:.2f}% "
                   f"(> {MAX_DD_48H_THRESHOLD * 100:.0f}%)")
            entry["flags"].append("auto_pause_48h_dd")
            report["auto_pause_candidates"].append({
                "strategy": strategy,
                "reason": msg,
                "dd_48h": dd_48h,
            })
            report["warnings"].append(msg)

        report["strategies"][strategy] = entry

    # Summary
    report["summary"] = {
        "strategies_evaluated": len(report["strategies"]),
        "strategies_with_warnings": sum(
            1 for s in report["strategies"].values() if s["flags"]
        ),
        "demotion_candidates_count": len(report["demotion_candidates"]),
        "auto_pause_candidates_count": len(report["auto_pause_candidates"]),
        "total_warnings": len(report["warnings"]),
    }

    return report


def print_report(report: Dict, verbose: bool = False):
    """Print human-readable report to stdout."""
    print("=" * 72)
    print("  PERFORMANCE MONITOR REPORT")
    print(f"  Generated: {report['generated_at']}")
    print("=" * 72)

    summary = report["summary"]
    print(f"\n  Strategies evaluated:    {summary['strategies_evaluated']}")
    print(f"  Total trades analyzed:   {report['total_trades']}")
    print(f"  Strategies with flags:   {summary['strategies_with_warnings']}")
    print(f"  Demotion candidates:     {summary['demotion_candidates_count']}")
    print(f"  Auto-pause candidates:   {summary['auto_pause_candidates_count']}")

    if report["warnings"]:
        print(f"\n{'=' * 72}")
        print("  WARNINGS ({} total)".format(len(report["warnings"])))
        print("=" * 72)
        for w in report["warnings"]:
            print(f"  {w}")

    if report["demotion_candidates"]:
        print(f"\n{'=' * 72}")
        print("  DEMOTION CANDIDATES")
        print("=" * 72)
        for d in report["demotion_candidates"]:
            print(f"  >> {d['strategy']}")
            print(f"     {d['reason']}")

    if report["auto_pause_candidates"]:
        print(f"\n{'=' * 72}")
        print("  AUTO-PAUSE CANDIDATES (48h DD > 5%)")
        print("=" * 72)
        for a in report["auto_pause_candidates"]:
            print(f"  >> {a['strategy']}")
            print(f"     {a['reason']}")

    if verbose and report["strategies"]:
        print(f"\n{'=' * 72}")
        print("  PER-STRATEGY DETAIL")
        print("=" * 72)
        for name, s in sorted(report["strategies"].items()):
            flags_str = ", ".join(s["flags"]) if s["flags"] else "OK"
            print(f"\n  [{flags_str}] {name}")
            print(f"    Trades: {s['total_trades']}  |  "
                  f"WR: {(s['baseline_wr'] or 0) * 100:.1f}%  |  "
                  f"PnL: {s['total_pnl_pct']:.2f}%")
            print(f"    Sharpe 7d: {s['sharpe_7d']}  |  "
                  f"Rolling 20 WR: {s['rolling_20_trade_wr']}  |  "
                  f"Expect: {s['rolling_20_trade_expectancy']}")
            print(f"    MaxDD: {s['max_drawdown_pct']:.2f}%  |  "
                  f"48h DD: {s['drawdown_48h_pct']:.2f}%")
            print(f"    Weekly Sharpes (last 4w): {s['weekly_sharpes_last_4w']}")

    if not report["warnings"]:
        print("\n  All systems within thresholds. No action required.")

    print(f"\n{'=' * 72}")
    print(f"  Report saved to: {REPORT_PATH}")
    print("=" * 72)


def save_report(report: Dict):
    """Save report JSON to data directory."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Also archive with timestamp for history tracking
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    history_path = HISTORY_DIR / f"perf_report_{timestamp}.json"

    report_json = json.dumps(report, indent=2, default=str) + "\n"
    REPORT_PATH.write_text(report_json, encoding="utf-8")

    # Keep last 30 days of history (clean old files)
    try:
        existing = sorted(HISTORY_DIR.glob("perf_report_*.json"))
        if len(existing) > 30:
            for old_file in existing[:-30]:
                old_file.unlink()
    except OSError:
        pass

    history_path.write_text(report_json, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Performance Monitor — Per-system Sharpe & demotion triggers"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-strategy detail")
    args = parser.parse_args()

    print(f"Loading trade data from {REPO_ROOT}...")
    all_trades = load_closed_picks(verbose=args.verbose)
    print(f"Loaded {len(all_trades)} closed trades\n")

    if not all_trades:
        print("No closed trades found. Nothing to analyze.")
        # Still write an empty report
        report = {
            "generated_at": dt.datetime.utcnow().isoformat() + "Z",
            "total_strategies": 0,
            "total_trades": 0,
            "strategies": {},
            "warnings": [],
            "demotion_candidates": [],
            "auto_pause_candidates": [],
            "summary": {
                "strategies_evaluated": 0,
                "strategies_with_warnings": 0,
                "demotion_candidates_count": 0,
                "auto_pause_candidates_count": 0,
                "total_warnings": 0,
            },
        }
        save_report(report)
        return

    report = analyze_strategies(all_trades, verbose=args.verbose)
    save_report(report)
    print_report(report, verbose=args.verbose)


if __name__ == "__main__":
    main()
