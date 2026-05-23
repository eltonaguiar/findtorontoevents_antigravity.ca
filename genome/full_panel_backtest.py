#!/usr/bin/env python3
"""
DARWIN ENGINE — Full Panel Backtester
=====================================
Loads picks from ALL evolution engines and backtests them extensively
against individual symbols and symbol sets. Produces a comparison report.
"""

import importlib.util
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENOME_DIR = Path(__file__).resolve().parent
DATA_DIR = GENOME_DIR / "data"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("PanelBacktest")

# Import GP engine for backtesting
_gp_path = str(GENOME_DIR / "genetic_programmer.py")
_spec = importlib.util.spec_from_file_location("genetic_programmer", _gp_path)
_gp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gp)

# All engine picks files
ENGINE_PICKS = {
    "GENESIS": "gp_active_picks.json",
    "ATLAS": "mape_active_picks.json",
    "NEXUS": "ae_active_picks.json",
    "LEGION": "ensemble_active_picks.json",
    "PHOENIX": "failure_evolved_picks.json",
    "VORTEX": "momentum_active_picks.json",
    "HORIZON": "multitf_active_picks.json",
    "REBEL": "contrarian_active_picks.json",
    "CONSENSUS": "universal_picks.json",
}

TEST_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOGEUSDT"]
TEST_TIMEFRAMES = ["1h"]


def load_all_picks() -> Dict[str, List[Dict]]:
    """Load picks from all evolution engines."""
    all_picks = {}
    for engine, filename in ENGINE_PICKS.items():
        path = DATA_DIR / filename
        try:
            if path.exists():
                data = json.loads(path.read_text())
                picks = data.get("consensus_picks", data.get("picks", []))
                all_picks[engine] = picks
                logger.info(f"  {engine}: {len(picks)} picks loaded")
            else:
                all_picks[engine] = []
                logger.info(f"  {engine}: no picks file found")
        except Exception as e:
            all_picks[engine] = []
            logger.warning(f"  {engine}: error loading - {e}")
    return all_picks


def backtest_pick_on_symbol(pick: Dict, market_data, symbol: str) -> Dict:
    """Simulate a single pick's performance on a symbol's data."""
    if symbol not in market_data:
        return {"symbol": symbol, "result": "NO_DATA"}

    data = market_data[symbol]
    close = data.close
    direction = pick.get("direction", "LONG")
    entry_price = float(close[-50]) if len(close) >= 50 else float(close[0])

    # Simulate forward from entry point
    tp_pct = 5.0  # Default 5% TP
    sl_pct = 2.5  # Default 2.5% SL

    best_pnl = 0
    worst_pnl = 0
    exit_pnl = 0
    exit_reason = "MAX_HOLD"
    hold_bars = 0

    for i in range(-49, 0) if len(close) >= 50 else range(1, len(close)):
        idx = i if i >= 0 else len(close) + i
        if idx >= len(close):
            break
        price = close[idx]
        hold_bars += 1

        if direction == "LONG":
            pnl = (price - entry_price) / entry_price * 100
        else:
            pnl = (entry_price - price) / entry_price * 100

        best_pnl = max(best_pnl, pnl)
        worst_pnl = min(worst_pnl, pnl)

        if pnl >= tp_pct:
            exit_pnl = pnl
            exit_reason = "TP_HIT"
            break
        elif pnl <= -sl_pct:
            exit_pnl = pnl
            exit_reason = "SL_HIT"
            break
        exit_pnl = pnl

    return {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "exit_pnl_pct": round(exit_pnl, 2),
        "best_pnl_pct": round(best_pnl, 2),
        "worst_pnl_pct": round(worst_pnl, 2),
        "exit_reason": exit_reason,
        "hold_bars": hold_bars,
        "won": exit_pnl > 0,
    }


def run_panel_backtest():
    """Run comprehensive backtest of all engine picks."""
    logger.info("=" * 70)
    logger.info("DARWIN ENGINE — Full Panel Backtester")
    logger.info("=" * 70)

    # Load picks
    all_picks = load_all_picks()

    # Fetch market data
    logger.info(f"\nFetching market data for {len(TEST_SYMBOLS)} symbols...")
    try:
        market_data = _gp.fetch_market_data(TEST_SYMBOLS, limit=750)
    except Exception as e:
        logger.error(f"Failed to fetch market data: {e}")
        return

    if not market_data:
        logger.error("No market data available")
        return

    # Current prices
    current_prices = {sym: float(data.close[-1]) for sym, data in market_data.items()}
    logger.info(f"Current prices: {current_prices}")

    # === Panel Comparison ===
    print(f"\n{'=' * 90}")
    print("DARWIN ENGINE — Full Panel Evolution Comparison")
    print(f"{'=' * 90}")

    engine_stats = {}

    for engine, picks in all_picks.items():
        if not picks:
            engine_stats[engine] = {
                "total_picks": 0, "long": 0, "short": 0, "neutral": 0,
                "avg_confidence": 0, "avg_win_rate": 0, "avg_perf_score": 0,
                "symbols": [],
            }
            continue

        long_count = sum(1 for p in picks if p.get("direction") == "LONG")
        short_count = sum(1 for p in picks if p.get("direction") == "SHORT")
        neutral = len(picks) - long_count - short_count

        confidences = [float(p.get("confidence", 0)) for p in picks]
        avg_conf = np.mean(confidences) if confidences else 0

        win_rates = [float(p.get("win_rate", 0)) for p in picks if p.get("win_rate")]
        avg_wr = np.mean(win_rates) if win_rates else 0

        perf_scores = [float(p.get("performance_score", p.get("overall_fitness", 0))) for p in picks]
        avg_perf = np.mean(perf_scores) if perf_scores else 0

        symbols = list(set(p.get("symbol", "") for p in picks))

        engine_stats[engine] = {
            "total_picks": len(picks),
            "long": long_count,
            "short": short_count,
            "neutral": neutral,
            "avg_confidence": round(avg_conf, 3),
            "avg_win_rate": round(avg_wr, 3),
            "avg_perf_score": round(avg_perf, 3),
            "symbols": symbols,
        }

    # Print comparison table
    print(f"\n{'Engine':<12} {'Picks':>5} {'LONG':>5} {'SHORT':>6} {'Conf':>6} {'WR':>6} {'Score':>6} {'Symbols'}")
    print("-" * 90)
    for engine, stats in sorted(engine_stats.items(), key=lambda x: x[1]["total_picks"], reverse=True):
        syms = ", ".join(stats["symbols"][:3])
        if len(stats["symbols"]) > 3:
            syms += f" +{len(stats['symbols']) - 3}"
        print(f"{engine:<12} {stats['total_picks']:>5} {stats['long']:>5} {stats['short']:>6} "
              f"{stats['avg_confidence']:>6.3f} {stats['avg_win_rate']:>5.0%} {stats['avg_perf_score']:>6.3f} {syms}")

    # === Per-Symbol Backtest ===
    print(f"\n\n{'=' * 90}")
    print("Per-Symbol Backtest Results (simulated forward test, last 50 bars)")
    print(f"{'=' * 90}")

    for symbol in TEST_SYMBOLS:
        if symbol not in market_data:
            continue

        print(f"\n  {symbol} (current: ${current_prices.get(symbol, 0):,.2f})")
        print(f"  {'Engine':<12} {'Dir':>5} {'P/L':>7} {'Best':>7} {'Worst':>7} {'Exit':>10} {'Bars':>5}")
        print(f"  {'-' * 65}")

        for engine, picks in all_picks.items():
            sym_picks = [p for p in picks if p.get("symbol") == symbol]
            if not sym_picks:
                continue

            for pick in sym_picks[:2]:  # Max 2 per engine per symbol
                result = backtest_pick_on_symbol(pick, market_data, symbol)
                won = "W" if result.get("won") else "L"
                print(f"  {engine:<12} {result['direction']:>5} {result['exit_pnl_pct']:>+6.2f}% "
                      f"{result['best_pnl_pct']:>+6.2f}% {result['worst_pnl_pct']:>+6.2f}% "
                      f"{result['exit_reason']:>10} {result['hold_bars']:>5} {won}")

    # === Direction Bias Analysis ===
    print(f"\n\n{'=' * 90}")
    print("Direction Bias Analysis")
    print(f"{'=' * 90}")
    total_long = sum(s["long"] for s in engine_stats.values())
    total_short = sum(s["short"] for s in engine_stats.values())
    total_all = total_long + total_short
    if total_all > 0:
        print(f"  Total LONG:  {total_long:>4} ({total_long/total_all*100:.1f}%)")
        print(f"  Total SHORT: {total_short:>4} ({total_short/total_all*100:.1f}%)")
        if total_short > total_long * 2:
            print(f"  WARNING: HEAVY SHORT BIAS detected - REBEL engine should help balance this")
        elif total_long > total_short * 2:
            print(f"  WARNING: HEAVY LONG BIAS detected")
        else:
            print(f"  OK: Direction balance looks healthy")

    # === Save results ===
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": "full_panel_backtest",
        "symbols_tested": TEST_SYMBOLS,
        "current_prices": current_prices,
        "engine_stats": engine_stats,
        "total_engines_with_picks": sum(1 for s in engine_stats.values() if s["total_picks"] > 0),
        "total_picks_across_engines": sum(s["total_picks"] for s in engine_stats.values()),
    }

    output_path = DATA_DIR / "panel_backtest_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2))
    logger.info(f"\nPanel backtest results saved to {output_path}")

    return output


if __name__ == "__main__":
    run_panel_backtest()
