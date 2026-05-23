#!/usr/bin/env python3
"""
DARWIN ENGINE - HORIZON: Multi-Timeframe DNA Evolution
======================================================
Evolves strategies across multiple timeframes (1h, 4h, 1d) to find swing
trades that the 1h-only engines miss. Uses higher-timeframe confirmation
to filter entries and wider TP/SL for multi-day holds.

Pipeline:
1. Fetch 1h, 4h, and 1d candles for each symbol
2. Compute features on each timeframe independently
3. Evolve GP strategies that combine signals across timeframes
4. Require higher-TF trend alignment before entry
5. Output: genome/data/multitf_active_picks.json
"""

import copy
import importlib.util
import json
import logging
import hashlib
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENOME_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = GENOME_DIR / "data" / "multitf_active_picks.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("MultiTFEvolver")

# Import GP engine
_gp_path = str(GENOME_DIR / "genetic_programmer.py")
_spec = importlib.util.spec_from_file_location("genetic_programmer", _gp_path)
_gp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gp)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOGEUSDT"]
TIMEFRAMES = {"1h": 750, "4h": 500, "1d": 365}


def fetch_multitf_data(symbols: List[str]) -> Dict[str, Dict[str, object]]:
    """Fetch market data across multiple timeframes."""
    logger.info(f"Fetching multi-timeframe data for {len(symbols)} symbols...")
    all_data = {}

    for tf, limit in TIMEFRAMES.items():
        try:
            data = _gp.fetch_market_data(symbols, timeframe=tf, limit=limit)
            for sym, ohlcv in data.items():
                if sym not in all_data:
                    all_data[sym] = {}
                all_data[sym][tf] = ohlcv
                logger.info(f"  {sym} {tf}: {len(ohlcv)} bars")
        except Exception as e:
            logger.warning(f"Failed to fetch {tf} data: {e}")

    return all_data


def compute_htf_bias(data_4h, data_1d) -> Dict[str, float]:
    """Compute higher-timeframe directional bias."""
    bias = {}

    for label, d in [("4h", data_4h), ("1d", data_1d)]:
        if d is None or len(d) < 50:
            continue
        close = d.close

        # EMA trend
        ema20 = close[-1]
        alpha = 2 / 21
        for c in close[-20:]:
            ema20 = alpha * c + (1 - alpha) * ema20
        ema50 = close[-1]
        alpha50 = 2 / 51
        for c in close[-50:]:
            ema50 = alpha50 * c + (1 - alpha50) * ema50

        # Trend score: +1 bullish, -1 bearish, 0 neutral
        trend = 0
        if close[-1] > ema20 and ema20 > ema50:
            trend = 1.0
        elif close[-1] < ema20 and ema20 < ema50:
            trend = -1.0
        else:
            trend = 0.5 * np.sign(close[-1] - ema20)

        # Momentum (% change over lookback)
        lookback = min(20, len(close) - 1)
        momentum = (close[-1] / close[-lookback - 1] - 1) * 100

        bias[f"{label}_trend"] = trend
        bias[f"{label}_momentum"] = momentum

    return bias


def evolve_multitf(multitf_data: Dict, pop: int = 50, gens: int = 15) -> List[Dict]:
    """Evolve strategies with multi-timeframe awareness."""
    logger.info(f"Evolving multi-timeframe strategies: pop={pop}, gens={gens}")

    # Use 1h data for backtesting, HTF for bias filtering
    hourly_data = {}
    htf_biases = {}

    for sym, tf_data in multitf_data.items():
        if "1h" in tf_data:
            hourly_data[sym] = tf_data["1h"]
        # Compute HTF bias
        data_4h = tf_data.get("4h")
        data_1d = tf_data.get("1d")
        htf_biases[sym] = compute_htf_bias(data_4h, data_1d)

    if not hourly_data:
        logger.warning("No hourly data available")
        return []

    # Initialize population with swing-trade parameters
    population = []
    for i in range(pop):
        strategy = _gp.random_strategy(generation=0, name_prefix="Horizon")
        # Swing trade parameters: wider TP/SL, longer holds
        strategy.tp_pct = round(random.uniform(0.04, 0.12), 4)  # 4-12% TP
        strategy.sl_pct = round(random.uniform(0.02, 0.06), 4)  # 2-6% SL
        strategy.max_hold_bars = random.choice([24, 48, 72, 96, 120, 168])  # 1-7 days
        population.append(strategy)

    best_ever = None
    best_fitness = -999

    for gen in range(gens):
        fitnesses = []
        results_map = {}

        for strategy in population:
            sym_results = []
            for sym, data in hourly_data.items():
                try:
                    result = _gp.backtest_strategy(strategy, data)

                    # HTF alignment bonus: reward strategies that agree with higher TF
                    bias = htf_biases.get(sym, {})
                    htf_trend_4h = bias.get("4h_trend", 0)
                    htf_trend_1d = bias.get("1d_trend", 0)

                    trades = result.get("trades", [])
                    if trades:
                        # Check if strategy's dominant direction aligns with HTF
                        long_count = sum(1 for t in trades if t.get("direction") == "LONG")
                        short_count = len(trades) - long_count
                        dominant_dir = 1 if long_count > short_count else -1

                        alignment = 0
                        if htf_trend_4h != 0:
                            alignment += 0.5 if np.sign(dominant_dir) == np.sign(htf_trend_4h) else -0.3
                        if htf_trend_1d != 0:
                            alignment += 0.5 if np.sign(dominant_dir) == np.sign(htf_trend_1d) else -0.3

                        # Boost fitness for HTF-aligned strategies
                        adjusted_fitness = result.get("overall_fitness", -1) + alignment * 0.1
                        result["overall_fitness"] = adjusted_fitness

                    sym_results.append(result)
                except Exception:
                    sym_results.append({"overall_fitness": -1})

            avg_fitness = np.mean([r.get("overall_fitness", -1) for r in sym_results])
            fitnesses.append(avg_fitness)
            results_map[id(strategy)] = sym_results

            if avg_fitness > best_fitness:
                best_fitness = avg_fitness
                best_ever = (strategy, sym_results, hourly_data)

        # Selection + crossover + mutation
        sorted_idx = np.argsort(fitnesses)[::-1]
        elite_count = max(3, pop // 8)
        new_pop = [population[i] for i in sorted_idx[:elite_count]]

        while len(new_pop) < pop:
            candidates = np.random.choice(len(population), size=5, replace=False)
            parent1 = population[candidates[np.argmax([fitnesses[c] for c in candidates])]]
            candidates = np.random.choice(len(population), size=5, replace=False)
            parent2 = population[candidates[np.argmax([fitnesses[c] for c in candidates])]]

            if random.random() < 0.65:
                child = _gp.crossover_strategies(parent1, parent2, gen + 1)
                # Maintain swing-trade parameters
                child.tp_pct = round(np.clip(child.tp_pct, 0.04, 0.12), 4)
                child.sl_pct = round(np.clip(child.sl_pct, 0.02, 0.06), 4)
                child.max_hold_bars = random.choice([24, 48, 72, 96, 120, 168])
            else:
                child = _gp.mutate_strategy(parent1, gen + 1)
                child.tp_pct = round(np.clip(child.tp_pct, 0.04, 0.12), 4)
                child.sl_pct = round(np.clip(child.sl_pct, 0.02, 0.06), 4)

            new_pop.append(child)

        population = new_pop
        avg = np.mean(fitnesses)
        best_gen = max(fitnesses)
        logger.info(f"Gen {gen:2d} | Best Ever: {best_fitness:.4f} | Gen Best: {best_gen:.4f} | Avg: {avg:.4f}")

    return _generate_picks(best_ever, htf_biases) if best_ever else []


def _generate_picks(best, htf_biases: Dict) -> List[Dict]:
    """Generate picks from the best evolved strategy with HTF context."""
    strategy, results, hourly_data = best
    picks = []
    now = datetime.now(timezone.utc).isoformat()

    for (sym, data), result in zip(hourly_data.items(), results):
        if result.get("overall_fitness", 0) < 0.15:
            continue

        trades = result.get("trades", [])
        if not trades:
            continue

        last_trade = trades[-1]
        direction = last_trade.get("direction", "LONG")

        # Check HTF alignment
        bias = htf_biases.get(sym, {})
        htf_4h = bias.get("4h_trend", 0)
        htf_1d = bias.get("1d_trend", 0)

        # Only take trades aligned with at least one HTF
        dir_sign = 1 if direction == "LONG" else -1
        htf_aligned = (np.sign(dir_sign) == np.sign(htf_4h)) or (np.sign(dir_sign) == np.sign(htf_1d))

        if not htf_aligned and abs(htf_4h) > 0.5:
            continue  # Skip counter-trend entries when HTF trend is strong

        confidence = min(result.get("overall_fitness", 0.5), 0.95)
        # Boost confidence for HTF-aligned trades
        if htf_aligned:
            confidence = min(confidence * 1.15, 0.95)

        picks.append({
            "symbol": sym,
            "direction": direction,
            "entry_price": float(data.close[-1]),
            "confidence": round(confidence, 3),
            "strategy": strategy.name if hasattr(strategy, "name") else "Horizon",
            "source_system": "multitf_evolver",
            "win_rate": result.get("win_rate", 0),
            "sharpe_ratio": result.get("sharpe_ratio", 0),
            "profit_factor": result.get("profit_factor", 0),
            "performance_score": result.get("overall_fitness", 0),
            "total_trades": result.get("total_trades", 0),
            "htf_bias_4h": round(htf_4h, 2),
            "htf_bias_1d": round(htf_1d, 2),
            "htf_aligned": bool(htf_aligned),
            "trade_type": "swing",
            "expected_hold": "1-7 days",
            "timestamp": now,
        })

    return picks


def run_multitf_evolution():
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("HORIZON: Multi-Timeframe DNA Evolution")
    logger.info("=" * 70)

    # Step 1: Fetch multi-timeframe data
    multitf_data = fetch_multitf_data(SYMBOLS)
    if not multitf_data:
        logger.warning("No multi-timeframe data available")
        return {"picks": []}

    # Log HTF biases
    for sym, tf_data in multitf_data.items():
        bias = compute_htf_bias(tf_data.get("4h"), tf_data.get("1d"))
        logger.info(f"  {sym}: 4h_trend={bias.get('4h_trend', 'N/A'):.1f} | "
                     f"1d_trend={bias.get('1d_trend', 'N/A'):.1f} | "
                     f"4h_mom={bias.get('4h_momentum', 0):.1f}% | "
                     f"1d_mom={bias.get('1d_momentum', 0):.1f}%")

    # Step 2: Evolve with HTF awareness
    picks = evolve_multitf(multitf_data, pop=50, gens=15)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": "multitf_evolver",
        "codename": "HORIZON",
        "timeframes": list(TIMEFRAMES.keys()),
        "symbols": SYMBOLS,
        "total_picks": len(picks),
        "picks": picks,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2))
    logger.info(f"\nSaved {len(picks)} multi-TF picks to {OUTPUT_PATH}")

    print(f"\n{'=' * 70}")
    print("HORIZON — Multi-Timeframe DNA Evolution Results")
    print(f"{'=' * 70}")
    print(f"  Symbols: {', '.join(SYMBOLS)}")
    print(f"  Timeframes: {', '.join(TIMEFRAMES.keys())}")
    print(f"  Picks generated: {len(picks)}")
    for p in picks[:5]:
        htf_label = "HTF-ALIGNED" if p.get("htf_aligned") else "counter-trend"
        print(f"    {p['direction']:5s} {p['symbol']:10s} | Score={p.get('performance_score',0):.3f} | "
              f"WR={p.get('win_rate',0):.0%} | {htf_label} | Hold={p.get('expected_hold')}")

    return result


if __name__ == "__main__":
    run_multitf_evolution()
