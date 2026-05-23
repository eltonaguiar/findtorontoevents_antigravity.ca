#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Performance Benchmarks
=========================================
Three analytics modules in one file:

  1. BTC Buy-and-Hold Benchmark
     Compare system PnL vs passive BTC holding over the same period.
     Computes true alpha = system_return - btc_return.

  2. Slippage Estimator for Copy Trader Picks
     Estimates execution slippage per copy-trader pick based on
     15-min price movement after detection.

  3. Hold Time Analyzer
     Buckets closed picks by hold duration, winner/loser status,
     direction, asset class, and strategy.

Output: alpha_engine/data/performance_benchmarks.json
Stdlib only.  Binance 5-mirror failover.  Windows UTF-8 safe.

Usage:
    from performance_benchmarks import run
    results = run()
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

# ── Windows UTF-8 fix ─────────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Paths ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
AUDIT_PAYLOAD = BASE_DIR.parent / "audit_trail" / "data" / "dashboard_payload.json"
COPY_TRADER_PICKS = BASE_DIR.parent / "copy_trader_intel" / "data" / "active_picks.json"
OUTPUT_FILE = DATA_DIR / "performance_benchmarks.json"

# ── Binance 5-mirror failover ─────────────────────────────────────────
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com",
]


def _binance_get(path: str, params: str = "", timeout: int = 10) -> dict | list | None:
    """GET from Binance with 5-mirror failover.  Returns parsed JSON or None."""
    for mirror in BINANCE_MIRRORS:
        url = f"{mirror}{path}"
        if params:
            url += f"?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError, Exception):
            continue
    return None


def _btc_price_now() -> float | None:
    """Fetch current BTC/USDT price."""
    data = _binance_get("/api/v3/ticker/price", "symbol=BTCUSDT")
    if data and "price" in data:
        return float(data["price"])
    return None


def _btc_price_at(timestamp_ms: int) -> float | None:
    """Fetch BTC/USDT close price for the 1-minute candle covering *timestamp_ms*."""
    params = f"symbol=BTCUSDT&interval=1m&startTime={timestamp_ms}&limit=1"
    data = _binance_get("/api/v3/klines", params)
    if data and len(data) > 0:
        return float(data[0][4])  # close price
    return None


def _btc_rolling_return(days: int) -> float | None:
    """Return BTC % change over the last *days* days using daily klines."""
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - days * 86_400_000
    params = f"symbol=BTCUSDT&interval=1d&startTime={start_ms}&limit={days + 1}"
    data = _binance_get("/api/v3/klines", params)
    if data and len(data) >= 2:
        open_price = float(data[0][1])  # open of first candle
        close_price = float(data[-1][4])  # close of last candle
        if open_price > 0:
            return round((close_price - open_price) / open_price * 100, 4)
    return None


def _kline_close_after_minutes(symbol: str, start_ms: int, minutes: int = 15) -> float | None:
    """Fetch the close price *minutes* after *start_ms* using 1-min klines."""
    end_ms = start_ms + minutes * 60_000
    params = f"symbol={symbol}&interval=1m&startTime={end_ms}&limit=1"
    data = _binance_get("/api/v3/klines", params)
    if data and len(data) > 0:
        return float(data[0][4])
    return None


def _parse_ts(ts_str: str) -> datetime | None:
    """Parse various timestamp formats found in the data."""
    if not ts_str:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    # Handle +00:00 suffix manually
    try:
        cleaned = ts_str.replace("+00:00", "").replace("Z", "")
        dt = datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S.%f")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    return None


def _ts_to_ms(dt: datetime) -> int:
    """Convert datetime to epoch milliseconds."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _load_json(path: Path) -> dict | list | None:
    """Load a JSON file, return None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 1 — BTC Buy-and-Hold Benchmark
# ═══════════════════════════════════════════════════════════════════════

def btc_benchmark() -> dict:
    """
    Compare system total PnL% vs passive BTC buy-and-hold over the same
    period.  Returns dict with alpha_generated and rolling context.
    """
    result: dict = {
        "system_return_pct": None,
        "btc_return_pct": None,
        "alpha_generated_pct": None,
        "btc_start_price": None,
        "btc_current_price": None,
        "portfolio_start_date": None,
        "rolling_7d_btc_return": None,
        "rolling_30d_btc_return": None,
        "rolling_90d_btc_return": None,
        "error": None,
    }

    payload = _load_json(AUDIT_PAYLOAD)
    if not payload:
        result["error"] = "Could not load dashboard_payload.json"
        return result

    summary = payload.get("summary", {})
    system_return = summary.get("total_pnl_pct")
    if system_return is None:
        result["error"] = "total_pnl_pct not found in summary"
        return result
    result["system_return_pct"] = system_return

    # Find earliest pick timestamp for portfolio start date
    closed_picks = payload.get("picks", {}).get("recent_closed", [])
    active_picks = payload.get("picks", {}).get("active", [])
    all_timestamps = []
    for p in closed_picks + active_picks:
        ts = _parse_ts(p.get("timestamp", ""))
        if ts:
            all_timestamps.append(ts)

    if not all_timestamps:
        result["error"] = "No pick timestamps found"
        return result

    start_dt = min(all_timestamps)
    result["portfolio_start_date"] = start_dt.isoformat()

    # Fetch BTC price at start and now
    start_ms = _ts_to_ms(start_dt)
    btc_start = _btc_price_at(start_ms)
    btc_now = _btc_price_now()

    if btc_start and btc_now and btc_start > 0:
        result["btc_start_price"] = btc_start
        result["btc_current_price"] = btc_now
        btc_return = round((btc_now - btc_start) / btc_start * 100, 4)
        result["btc_return_pct"] = btc_return
        result["alpha_generated_pct"] = round(system_return - btc_return, 4)
    else:
        result["error"] = "Could not fetch BTC prices from Binance mirrors"

    # Rolling BTC returns for context
    result["rolling_7d_btc_return"] = _btc_rolling_return(7)
    result["rolling_30d_btc_return"] = _btc_rolling_return(30)
    result["rolling_90d_btc_return"] = _btc_rolling_return(90)

    return result


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 2 — Slippage Estimator for Copy Trader Picks
# ═══════════════════════════════════════════════════════════════════════

def slippage_estimator() -> dict:
    """
    For each copy-trader pick, estimate slippage as the absolute %
    price change in the 15 minutes after detection.
    """
    result: dict = {
        "total_picks_analyzed": 0,
        "picks_with_slippage_data": 0,
        "avg_slippage_pct": None,
        "median_slippage_pct": None,
        "worst_slippage_pct": None,
        "worst_slippage_pick": None,
        "by_trader": {},
        "all_slippages": [],
        "error": None,
    }

    picks = _load_json(COPY_TRADER_PICKS)
    if not picks:
        result["error"] = "Could not load copy trader active_picks.json"
        return result

    if isinstance(picks, dict):
        picks = picks.get("picks", picks.get("active", []))
    if not isinstance(picks, list):
        result["error"] = "Unexpected format in active_picks.json"
        return result

    result["total_picks_analyzed"] = len(picks)
    slippages: list[float] = []
    trader_slippages: dict[str, list[float]] = {}
    worst_slip = 0.0
    worst_pick_id = ""

    for pick in picks:
        symbol = pick.get("symbol", "")
        entry_price = pick.get("entry_price") or pick.get("original_trader_entry")
        detected_str = pick.get("detected_at") or pick.get("timestamp", "")

        if not symbol or not entry_price or not detected_str:
            continue

        detected_dt = _parse_ts(detected_str)
        if not detected_dt:
            continue

        detected_ms = _ts_to_ms(detected_dt)

        # Fetch price 15 minutes after detection
        price_after = _kline_close_after_minutes(symbol, detected_ms, minutes=15)
        if price_after is None or entry_price == 0:
            continue

        slip_pct = round(abs(price_after - entry_price) / entry_price * 100, 4)
        slippages.append(slip_pct)

        # Track by trader
        trader = pick.get("trader_label") or pick.get("strategy", "unknown")
        if trader not in trader_slippages:
            trader_slippages[trader] = []
        trader_slippages[trader].append(slip_pct)

        if slip_pct > worst_slip:
            worst_slip = slip_pct
            worst_pick_id = pick.get("id", f"{symbol}_{detected_str}")

    result["picks_with_slippage_data"] = len(slippages)

    if slippages:
        result["avg_slippage_pct"] = round(mean(slippages), 4)
        result["median_slippage_pct"] = round(median(slippages), 4)
        result["worst_slippage_pct"] = round(worst_slip, 4)
        result["worst_slippage_pick"] = worst_pick_id
        result["all_slippages"] = [round(s, 4) for s in sorted(slippages, reverse=True)[:50]]

        # Aggregate by trader
        by_trader = {}
        for trader, slips in trader_slippages.items():
            by_trader[trader] = {
                "count": len(slips),
                "avg_slippage_pct": round(mean(slips), 4),
                "median_slippage_pct": round(median(slips), 4),
                "worst_slippage_pct": round(max(slips), 4),
            }
        # Sort by worst avg slippage
        result["by_trader"] = dict(
            sorted(by_trader.items(), key=lambda x: x[1]["avg_slippage_pct"], reverse=True)
        )
    else:
        result["error"] = result.get("error") or "No slippage data could be computed (picks may be too recent)"

    return result


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 3 — Hold Time Analyzer
# ═══════════════════════════════════════════════════════════════════════

def hold_time_analyzer() -> dict:
    """
    Analyze hold durations from closed picks.  Bucket by winner/loser,
    direction, asset class, and strategy.  Output optimal hold time
    recommendations and time-stop suggestions.
    """
    result: dict = {
        "total_closed_analyzed": 0,
        "avg_hold_hours": None,
        "median_hold_hours": None,
        "by_outcome": {},
        "by_direction": {},
        "by_asset_class": {},
        "by_strategy_top20": {},
        "optimal_hold_recommendations": {},
        "time_stop_recommendations": [],
        "research_comparison": {
            "expected_winner_avg_hours": 33,
            "expected_loser_avg_hours": 51,
            "note": "Research finding: winners close in ~33h avg, losers drag to ~51h",
        },
        "error": None,
    }

    payload = _load_json(AUDIT_PAYLOAD)
    if not payload:
        result["error"] = "Could not load dashboard_payload.json"
        return result

    closed = payload.get("picks", {}).get("recent_closed", [])
    if not closed:
        result["error"] = "No recent_closed picks found"
        return result

    # Collect hold times with metadata
    records: list[dict] = []
    for p in closed:
        age_h = p.get("age_hours")
        if age_h is None or age_h <= 0:
            # Try to compute from timestamps
            ts_open = _parse_ts(p.get("timestamp", ""))
            ts_close = _parse_ts(p.get("closed_at", ""))
            if ts_open and ts_close:
                delta = (ts_close - ts_open).total_seconds() / 3600
                if delta > 0:
                    age_h = round(delta, 2)
            if age_h is None or age_h <= 0:
                continue

        status = p.get("status", "").upper()
        is_winner = status in ("WON", "WIN", "TP_HIT")
        is_loser = status in ("LOST", "LOSS", "SL_HIT", "STOPPED")
        if not is_winner and not is_loser:
            # Infer from pnl_pct
            pnl = p.get("pnl_pct")
            if pnl is not None:
                is_winner = pnl > 0
                is_loser = pnl <= 0
            else:
                continue

        records.append({
            "hold_hours": age_h,
            "outcome": "winner" if is_winner else "loser",
            "direction": (p.get("direction") or "UNKNOWN").upper(),
            "asset_class": (p.get("asset_class") or "UNKNOWN").upper(),
            "strategy": p.get("strategy") or "unknown",
            "pnl_pct": p.get("pnl_pct", 0),
        })

    result["total_closed_analyzed"] = len(records)
    if not records:
        result["error"] = "No closed picks with valid hold time data"
        return result

    all_hours = [r["hold_hours"] for r in records]
    result["avg_hold_hours"] = round(mean(all_hours), 2)
    result["median_hold_hours"] = round(median(all_hours), 2)

    # ── By outcome (winner vs loser) ──
    for outcome in ("winner", "loser"):
        subset = [r["hold_hours"] for r in records if r["outcome"] == outcome]
        if subset:
            result["by_outcome"][outcome] = {
                "count": len(subset),
                "avg_hours": round(mean(subset), 2),
                "median_hours": round(median(subset), 2),
                "min_hours": round(min(subset), 2),
                "max_hours": round(max(subset), 2),
            }

    # ── By direction ──
    directions = set(r["direction"] for r in records)
    for d in sorted(directions):
        subset = [r for r in records if r["direction"] == d]
        hours = [r["hold_hours"] for r in subset]
        winners_h = [r["hold_hours"] for r in subset if r["outcome"] == "winner"]
        losers_h = [r["hold_hours"] for r in subset if r["outcome"] == "loser"]
        result["by_direction"][d] = {
            "count": len(hours),
            "avg_hours": round(mean(hours), 2),
            "winner_avg_hours": round(mean(winners_h), 2) if winners_h else None,
            "loser_avg_hours": round(mean(losers_h), 2) if losers_h else None,
        }

    # ── By asset class ──
    asset_classes = set(r["asset_class"] for r in records)
    for ac in sorted(asset_classes):
        subset = [r for r in records if r["asset_class"] == ac]
        hours = [r["hold_hours"] for r in subset]
        winners_h = [r["hold_hours"] for r in subset if r["outcome"] == "winner"]
        losers_h = [r["hold_hours"] for r in subset if r["outcome"] == "loser"]
        result["by_asset_class"][ac] = {
            "count": len(hours),
            "avg_hours": round(mean(hours), 2),
            "winner_avg_hours": round(mean(winners_h), 2) if winners_h else None,
            "loser_avg_hours": round(mean(losers_h), 2) if losers_h else None,
        }

    # ── By strategy (top 20 by volume) ──
    strategy_groups: dict[str, list[dict]] = {}
    for r in records:
        strat = r["strategy"]
        if strat not in strategy_groups:
            strategy_groups[strat] = []
        strategy_groups[strat].append(r)

    top_strats = sorted(strategy_groups.items(), key=lambda x: len(x[1]), reverse=True)[:20]
    for strat, recs in top_strats:
        hours = [r["hold_hours"] for r in recs]
        winners_h = [r["hold_hours"] for r in recs if r["outcome"] == "winner"]
        losers_h = [r["hold_hours"] for r in recs if r["outcome"] == "loser"]
        win_count = len(winners_h)
        loss_count = len(losers_h)
        result["by_strategy_top20"][strat] = {
            "count": len(hours),
            "wins": win_count,
            "losses": loss_count,
            "win_rate_pct": round(win_count / len(hours) * 100, 1) if hours else 0,
            "avg_hours": round(mean(hours), 2),
            "winner_avg_hours": round(mean(winners_h), 2) if winners_h else None,
            "loser_avg_hours": round(mean(losers_h), 2) if losers_h else None,
        }

    # ── Optimal hold recommendations ──
    winner_data = result["by_outcome"].get("winner", {})
    loser_data = result["by_outcome"].get("loser", {})
    winner_avg = winner_data.get("avg_hours")
    loser_avg = loser_data.get("avg_hours")

    recommendations: dict = {}
    if winner_avg and loser_avg:
        recommendations["overall"] = {
            "observed_winner_avg_hours": winner_avg,
            "observed_loser_avg_hours": loser_avg,
            "research_winner_benchmark_hours": 33,
            "research_loser_benchmark_hours": 51,
            "suggested_time_stop_hours": round(winner_avg * 1.5, 1),
            "rationale": (
                f"Winners close in {winner_avg}h avg. "
                f"Losers drag to {loser_avg}h. "
                f"Time-stop at {round(winner_avg * 1.5, 1)}h would cut losers "
                f"that exceed 1.5x winner hold time."
            ),
        }

    for ac, ac_data in result["by_asset_class"].items():
        w_avg = ac_data.get("winner_avg_hours")
        l_avg = ac_data.get("loser_avg_hours")
        if w_avg:
            recommendations[ac] = {
                "suggested_time_stop_hours": round(w_avg * 1.5, 1),
                "winner_avg_hours": w_avg,
                "loser_avg_hours": l_avg,
            }

    result["optimal_hold_recommendations"] = recommendations

    # ── Time-stop recommendations ──
    time_stops: list[dict] = []
    if winner_avg:
        time_stops.append({
            "rule": "AGGRESSIVE",
            "time_stop_hours": round(winner_avg * 1.2, 1),
            "description": f"Close any pick not at TP after {round(winner_avg * 1.2, 1)}h (1.2x winner avg)",
        })
        time_stops.append({
            "rule": "MODERATE",
            "time_stop_hours": round(winner_avg * 1.5, 1),
            "description": f"Close any pick not at TP after {round(winner_avg * 1.5, 1)}h (1.5x winner avg)",
        })
        time_stops.append({
            "rule": "CONSERVATIVE",
            "time_stop_hours": round(winner_avg * 2.0, 1),
            "description": f"Close any pick not at TP after {round(winner_avg * 2.0, 1)}h (2x winner avg)",
        })
    result["time_stop_recommendations"] = time_stops

    return result


# ═══════════════════════════════════════════════════════════════════════
#  OUTPUT & ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

def _print_summary(results: dict) -> None:
    """Print a formatted summary table to stdout."""
    print("\n" + "=" * 70)
    print("  ALPHA ENGINE — PERFORMANCE BENCHMARKS")
    print("=" * 70)

    # Section 1 — BTC Benchmark
    btc = results.get("btc_benchmark", {})
    print("\n--- BTC Buy-and-Hold Benchmark ---")
    if btc.get("error"):
        print(f"  ERROR: {btc['error']}")
    else:
        print(f"  System Return:        {btc.get('system_return_pct', 'N/A')}%")
        print(f"  BTC Return (same period): {btc.get('btc_return_pct', 'N/A')}%")
        print(f"  Alpha Generated:      {btc.get('alpha_generated_pct', 'N/A')}%")
        print(f"  BTC Start Price:      ${btc.get('btc_start_price', 'N/A')}")
        print(f"  BTC Current Price:    ${btc.get('btc_current_price', 'N/A')}")
        print(f"  Portfolio Start:      {btc.get('portfolio_start_date', 'N/A')}")
        print(f"  Rolling 7d BTC:       {btc.get('rolling_7d_btc_return', 'N/A')}%")
        print(f"  Rolling 30d BTC:      {btc.get('rolling_30d_btc_return', 'N/A')}%")
        print(f"  Rolling 90d BTC:      {btc.get('rolling_90d_btc_return', 'N/A')}%")

    # Section 2 — Slippage
    slip = results.get("slippage_estimator", {})
    print("\n--- Copy Trader Slippage Estimator ---")
    if slip.get("error"):
        print(f"  ERROR: {slip['error']}")
    print(f"  Picks Analyzed:       {slip.get('total_picks_analyzed', 0)}")
    print(f"  With Slippage Data:   {slip.get('picks_with_slippage_data', 0)}")
    if slip.get("avg_slippage_pct") is not None:
        print(f"  Avg Slippage:         {slip['avg_slippage_pct']}%")
        print(f"  Median Slippage:      {slip['median_slippage_pct']}%")
        print(f"  Worst Slippage:       {slip['worst_slippage_pct']}%")
        print(f"  Worst Pick:           {slip.get('worst_slippage_pick', 'N/A')}")
    if slip.get("by_trader"):
        print("  Top 5 Worst Traders by Avg Slippage:")
        for i, (trader, data) in enumerate(list(slip["by_trader"].items())[:5]):
            print(f"    {i+1}. {trader}: avg={data['avg_slippage_pct']}% ({data['count']} picks)")

    # Section 3 — Hold Time
    hold = results.get("hold_time_analyzer", {})
    print("\n--- Hold Time Analyzer ---")
    if hold.get("error"):
        print(f"  ERROR: {hold['error']}")
    else:
        print(f"  Closed Picks Analyzed: {hold.get('total_closed_analyzed', 0)}")
        print(f"  Avg Hold Time:        {hold.get('avg_hold_hours', 'N/A')}h")
        print(f"  Median Hold Time:     {hold.get('median_hold_hours', 'N/A')}h")
        for outcome, data in hold.get("by_outcome", {}).items():
            print(f"  {outcome.capitalize():8s} avg: {data['avg_hours']}h  (n={data['count']})")
        recs = hold.get("optimal_hold_recommendations", {}).get("overall", {})
        if recs:
            print(f"  Suggested Time-Stop:  {recs.get('suggested_time_stop_hours', 'N/A')}h")
        # Asset class breakdown
        for ac, data in hold.get("by_asset_class", {}).items():
            w = data.get("winner_avg_hours", "N/A")
            l = data.get("loser_avg_hours", "N/A")
            print(f"  {ac:12s} winner={w}h  loser={l}h  (n={data['count']})")

    print("\n" + "=" * 70)
    print(f"  Results saved to: {OUTPUT_FILE}")
    print("=" * 70 + "\n")


def run() -> dict:
    """Execute all three benchmark modules and save results."""
    print("[performance_benchmarks] Running BTC benchmark...")
    btc = btc_benchmark()

    print("[performance_benchmarks] Running slippage estimator...")
    slip = slippage_estimator()

    print("[performance_benchmarks] Running hold time analyzer...")
    hold = hold_time_analyzer()

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "btc_benchmark": btc,
        "slippage_estimator": slip,
        "hold_time_analyzer": hold,
    }

    # Save output
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    _print_summary(results)
    return results


if __name__ == "__main__":
    run()
