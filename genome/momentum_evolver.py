#!/usr/bin/env python3
"""
DARWIN ENGINE - VORTEX: Momentum Scanner DNA Evolution
======================================================
Scans 20+ crypto symbols for momentum setups, then evolves GP strategies
specifically on the highest-momentum assets. Adapts symbol selection each run.

Unlike GENESIS which evolves on a fixed set of 5 symbols, VORTEX first
identifies WHERE the action is, then evolves strategies for those specific markets.

Pipeline:
1. Scan 20 symbols for momentum (price change, volume surge, volatility expansion)
2. Rank and select top 8 momentum candidates
3. Evolve GP strategies specifically tuned to high-momentum environments
4. Output: genome/data/momentum_active_picks.json
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
OUTPUT_PATH = GENOME_DIR / "data" / "momentum_active_picks.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("MomentumEvolver")

# Import GP engine
_gp_path = str(GENOME_DIR / "genetic_programmer.py")
_spec = importlib.util.spec_from_file_location("genetic_programmer", _gp_path)
_gp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gp)

# Expanded symbol universe
SYMBOL_UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOGEUSDT",
    "ADAUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT", "XRPUSDT",
    "BNBUSDT", "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT",
    "SUIUSDT", "SEIUSDT", "TIAUSDT", "INJUSDT", "FETUSDT",
]


def scan_momentum(symbols: List[str], limit: int = 200) -> List[Dict]:
    """Scan symbols for momentum signals and rank them."""
    logger.info(f"Scanning {len(symbols)} symbols for momentum...")
    rankings = []

    try:
        market_data = _gp.fetch_market_data(symbols, limit=limit)
    except Exception as e:
        logger.warning(f"Fetch failed: {e}")
        return []

    for sym, data in market_data.items():
        close = np.array(data.close)
        volume = np.array(data.volume)
        high = np.array(data.high)
        low = np.array(data.low)

        if len(close) < 50:
            continue

        # Momentum metrics
        ret_24h = (close[-1] / close[-24] - 1) * 100 if len(close) >= 24 else 0
        ret_72h = (close[-1] / close[-72] - 1) * 100 if len(close) >= 72 else 0
        ret_168h = (close[-1] / close[-168] - 1) * 100 if len(close) >= 168 else 0

        # Volume surge (current vs 20-period average)
        vol_avg = np.mean(volume[-20:])
        vol_recent = np.mean(volume[-3:])
        vol_surge = vol_recent / (vol_avg + 1e-8)

        # Volatility expansion (ATR ratio)
        tr = np.maximum(high[1:] - low[1:], np.maximum(
            np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
        atr_recent = np.mean(tr[-5:])
        atr_avg = np.mean(tr[-20:])
        vol_expansion = atr_recent / (atr_avg + 1e-8)

        # Trend strength (price above EMA)
        ema20 = close[-1]
        alpha = 2 / 21
        for c in close[-20:]:
            ema20 = alpha * c + (1 - alpha) * ema20
        trend_strength = (close[-1] / ema20 - 1) * 100

        # Combined momentum score
        score = (
            abs(ret_24h) * 0.25 +
            abs(ret_72h) * 0.20 +
            vol_surge * 10 * 0.20 +
            vol_expansion * 10 * 0.15 +
            abs(trend_strength) * 0.20
        )

        direction = "LONG" if ret_24h > 0 and ret_72h > 0 else "SHORT" if ret_24h < 0 and ret_72h < 0 else "NEUTRAL"

        rankings.append({
            "symbol": sym,
            "score": round(score, 2),
            "ret_24h": round(ret_24h, 2),
            "ret_72h": round(ret_72h, 2),
            "ret_168h": round(ret_168h, 2),
            "vol_surge": round(vol_surge, 2),
            "vol_expansion": round(vol_expansion, 2),
            "trend_strength": round(trend_strength, 2),
            "direction": direction,
            "current_price": float(close[-1]),
        })

    rankings.sort(key=lambda x: x["score"], reverse=True)
    return rankings


def evolve_on_momentum(top_symbols: List[str], pop: int = 40, gens: int = 12) -> List[Dict]:
    """Run GP evolution specifically on high-momentum symbols."""
    logger.info(f"Evolving on momentum symbols: {top_symbols}")

    try:
        market_data = _gp.fetch_market_data(top_symbols, limit=750)
    except Exception as e:
        logger.warning(f"Fetch failed: {e}")
        return []

    if not market_data:
        return []

    # Initialize population
    population = []
    for i in range(pop):
        strategy = _gp.random_strategy(generation=0, name_prefix="Vortex")
        # Bias toward momentum-friendly parameters
        strategy.tp_pct = np.random.uniform(3.0, 8.0)  # Wider TP for momentum
        strategy.sl_pct = np.random.uniform(1.5, 4.0)
        strategy.max_hold_bars = np.random.randint(5, 30)
        population.append(strategy)

    best_ever = None
    best_fitness = -999

    for gen in range(gens):
        # Evaluate
        fitnesses = []
        for strategy in population:
            results = []
            for sym, data in market_data.items():
                try:
                    result = _gp.backtest_strategy(strategy, data)
                    results.append(result)
                except:
                    results.append({"overall_fitness": -1})

            avg_fitness = np.mean([r.get("overall_fitness", -1) for r in results])
            fitnesses.append(avg_fitness)

            if avg_fitness > best_fitness:
                best_fitness = avg_fitness
                best_ever = (strategy, results)

        # Selection + crossover + mutation
        sorted_idx = np.argsort(fitnesses)[::-1]
        elite_count = max(2, pop // 10)
        new_pop = [population[i] for i in sorted_idx[:elite_count]]

        while len(new_pop) < pop:
            # Tournament selection
            candidates = np.random.choice(len(population), size=5, replace=False)
            parent1 = population[candidates[np.argmax([fitnesses[c] for c in candidates])]]
            candidates = np.random.choice(len(population), size=5, replace=False)
            parent2 = population[candidates[np.argmax([fitnesses[c] for c in candidates])]]

            if np.random.random() < 0.7:
                child = _gp.crossover_strategies(parent1, parent2, gen + 1)
            else:
                child = _gp.mutate_strategy(parent1, gen + 1)

            new_pop.append(child)

        population = new_pop
        avg = np.mean(fitnesses)
        logger.info(f"Gen {gen:2d} | Best: {best_fitness:.4f} | Avg: {avg:.4f}")

    return _generate_picks(best_ever, market_data) if best_ever else []


def _generate_picks(best, market_data) -> List[Dict]:
    """Generate picks from the best evolved strategy."""
    strategy, results = best
    picks = []
    now = datetime.now(timezone.utc).isoformat()

    for (sym, data), result in zip(market_data.items(), results):
        if result.get("overall_fitness", 0) < 0.2:
            continue

        trades = result.get("trades", [])
        if not trades:
            continue

        last_trade = trades[-1]
        direction = last_trade.get("direction", "LONG")

        picks.append({
            "symbol": sym,
            "direction": direction,
            "entry_price": float(data.close[-1]),
            "confidence": min(result.get("overall_fitness", 0.5), 0.95),
            "strategy": strategy.name if hasattr(strategy, 'name') else "Vortex",
            "source_system": "momentum_evolver",
            "win_rate": result.get("win_rate", 0),
            "sharpe_ratio": result.get("sharpe_ratio", 0),
            "profit_factor": result.get("profit_factor", 0),
            "performance_score": result.get("overall_fitness", 0),
            "total_trades": result.get("total_trades", 0),
            "timestamp": now,
        })

    return picks


def run_momentum_evolution():
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("VORTEX: Momentum Scanner DNA Evolution")
    logger.info("=" * 70)

    # Step 1: Scan for momentum
    rankings = scan_momentum(SYMBOL_UNIVERSE)
    if not rankings:
        logger.warning("No momentum data available")
        return {"picks": [], "momentum_scan": []}

    logger.info(f"\nMomentum Rankings (top 10):")
    for r in rankings[:10]:
        logger.info(f"  {r['symbol']:10s} Score={r['score']:6.1f} | 24h={r['ret_24h']:+6.2f}% | "
                     f"72h={r['ret_72h']:+6.2f}% | Vol={r['vol_surge']:.1f}x | Dir={r['direction']}")

    # Step 2: Select top 8 momentum symbols
    top_symbols = [r["symbol"] for r in rankings[:8]]

    # Step 3: Evolve on momentum symbols
    picks = evolve_on_momentum(top_symbols, pop=40, gens=12)

    # Step 4: Also add momentum-based directional picks (non-GP)
    for r in rankings[:5]:
        if r["direction"] != "NEUTRAL" and abs(r["ret_24h"]) > 1.0:
            picks.append({
                "symbol": r["symbol"],
                "direction": r["direction"],
                "entry_price": r["current_price"],
                "confidence": min(r["score"] / 50, 0.90),
                "strategy": "VortexMomentumScan",
                "source_system": "momentum_evolver",
                "win_rate": 0,
                "sharpe_ratio": 0,
                "performance_score": r["score"] / 50,
                "momentum_score": r["score"],
                "ret_24h": r["ret_24h"],
                "vol_surge": r["vol_surge"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": "momentum_evolver",
        "codename": "VORTEX",
        "symbols_scanned": len(SYMBOL_UNIVERSE),
        "momentum_rankings": rankings[:10],
        "top_momentum_symbols": top_symbols,
        "total_picks": len(picks),
        "picks": picks,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2))
    logger.info(f"\nSaved {len(picks)} momentum-evolved picks to {OUTPUT_PATH}")

    print(f"\n{'=' * 70}")
    print("VORTEX — Momentum Scanner DNA Evolution Results")
    print(f"{'=' * 70}")
    print(f"  Symbols scanned: {len(SYMBOL_UNIVERSE)}")
    print(f"  Top momentum: {', '.join(top_symbols[:5])}")
    print(f"  Picks generated: {len(picks)}")
    for p in picks[:5]:
        print(f"    {p['direction']:5s} {p['symbol']:10s} | Score={p.get('performance_score',0):.3f} | "
              f"WR={p.get('win_rate',0):.0%} | Conf={p['confidence']:.3f}")

    return result


if __name__ == "__main__":
    run_momentum_evolution()
