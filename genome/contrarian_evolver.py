#!/usr/bin/env python3
"""
DARWIN ENGINE - REBEL: Contrarian DNA Evolution
=================================================
Evolves strategies that bet AGAINST the consensus. While most engines have
an 84% SHORT bias, REBEL specifically evolves contrarian strategies that:
1. Detect oversold/overbought extremes
2. Find mean-reversion setups after panic moves
3. Fade the crowd when sentiment is extreme
4. Buy dips in uptrends, sell rips in downtrends

Addresses the SHORT bias problem by explicitly rewarding LONG trades
in oversold conditions and penalizing herd-following behavior.

Pipeline:
1. Analyze current consensus direction from all other engines
2. Evolve strategies that perform well going AGAINST consensus
3. Reward mean-reversion behavior and penalize trend-following
4. Require contrarian confirmation (RSI extreme, BB touch, volume spike)
5. Output: genome/data/contrarian_active_picks.json
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
from typing import Dict, List, Tuple
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENOME_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = GENOME_DIR / "data" / "contrarian_active_picks.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
logger = logging.getLogger("ContrarianEvolver")

# Import GP engine
_gp_path = str(GENOME_DIR / "genetic_programmer.py")
_spec = importlib.util.spec_from_file_location("genetic_programmer", _gp_path)
_gp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gp)

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOGEUSDT"]

# Consensus picks files from other engines
CONSENSUS_SOURCES = [
    "genome/data/gp_active_picks.json",
    "genome/data/mape_active_picks.json",
    "genome/data/ae_active_picks.json",
    "genome/data/ensemble_active_picks.json",
    "genome/data/momentum_active_picks.json",
    "genome/data/multitf_active_picks.json",
]


def load_consensus_direction() -> Dict[str, Dict]:
    """Load picks from all other engines and determine consensus direction per symbol."""
    logger.info("Analyzing consensus direction from other engines...")
    symbol_votes = {}

    for source_file in CONSENSUS_SOURCES:
        path = PROJECT_ROOT / source_file
        try:
            if path.exists():
                data = json.loads(path.read_text())
                picks = data.get("consensus_picks", data.get("picks", []))
                for pick in picks:
                    sym = pick.get("symbol", "")
                    direction = pick.get("direction", "NEUTRAL")
                    if sym not in symbol_votes:
                        symbol_votes[sym] = {"LONG": 0, "SHORT": 0, "total": 0}
                    if direction in ("LONG", "SHORT"):
                        symbol_votes[sym][direction] += 1
                        symbol_votes[sym]["total"] += 1
        except Exception as e:
            logger.debug(f"Could not load {source_file}: {e}")

    consensus = {}
    for sym, votes in symbol_votes.items():
        total = votes["total"]
        if total == 0:
            consensus[sym] = {"direction": "NEUTRAL", "strength": 0, "long_pct": 50}
            continue
        long_pct = votes["LONG"] / total * 100
        if long_pct > 65:
            consensus[sym] = {"direction": "LONG", "strength": long_pct, "long_pct": long_pct}
        elif long_pct < 35:
            consensus[sym] = {"direction": "SHORT", "strength": 100 - long_pct, "long_pct": long_pct}
        else:
            consensus[sym] = {"direction": "MIXED", "strength": 50, "long_pct": long_pct}

        logger.info(f"  {sym}: {votes['LONG']}L / {votes['SHORT']}S → consensus={consensus[sym]['direction']} ({consensus[sym]['strength']:.0f}%)")

    return consensus


def compute_contrarian_signals(data) -> Dict[str, float]:
    """Compute mean-reversion / contrarian indicators."""
    close = data.close
    high = data.high
    low = data.low
    volume = data.volume

    if len(close) < 50:
        return {}

    # RSI extremes
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    alpha = 2.0 / 15
    avg_gain = np.zeros_like(gain)
    avg_loss = np.zeros_like(loss)
    avg_gain[0] = gain[0]
    avg_loss[0] = loss[0]
    for i in range(1, len(gain)):
        avg_gain[i] = alpha * gain[i] + (1 - alpha) * avg_gain[i - 1]
        avg_loss[i] = alpha * loss[i] + (1 - alpha) * avg_loss[i - 1]
    rs = avg_gain / (avg_loss + 1e-8)
    rsi = 100 - (100 / (1 + rs))

    # Bollinger Band position
    sma20 = np.convolve(close, np.ones(20) / 20, mode="same")
    std20 = np.array([np.std(close[max(0, i - 19):i + 1]) for i in range(len(close))])
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    bb_pctb = (close[-1] - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1] + 1e-8)

    # Volume spike (current vs average)
    vol_avg = np.mean(volume[-20:])
    vol_current = volume[-1]
    vol_spike = vol_current / (vol_avg + 1e-8)

    # Price distance from 20-SMA (mean reversion potential)
    mean_distance = (close[-1] - sma20[-1]) / (sma20[-1] + 1e-8) * 100

    # Consecutive same-direction bars (exhaustion signal)
    changes = np.diff(close[-10:])
    consecutive_down = 0
    consecutive_up = 0
    for c in reversed(changes):
        if c < 0:
            consecutive_down += 1
        else:
            break
    for c in reversed(changes):
        if c > 0:
            consecutive_up += 1
        else:
            break

    return {
        "rsi": float(rsi[-1]),
        "bb_pctb": float(bb_pctb),
        "vol_spike": float(vol_spike),
        "mean_distance_pct": float(mean_distance),
        "consecutive_down": consecutive_down,
        "consecutive_up": consecutive_up,
        "is_oversold": rsi[-1] < 30 and bb_pctb < 0.1,
        "is_overbought": rsi[-1] > 70 and bb_pctb > 0.9,
    }


def contrarian_fitness(base_fitness: float, trades: List[Dict], consensus_dir: str,
                        contrarian_signals: Dict) -> float:
    """Modified fitness that rewards contrarian behavior."""
    if not trades:
        return base_fitness

    # Count direction balance
    long_trades = sum(1 for t in trades if t.get("direction") == "LONG")
    short_trades = len(trades) - long_trades
    total = len(trades)

    # Reward going against consensus
    contrarian_bonus = 0
    if consensus_dir == "SHORT" and long_trades > short_trades:
        # Going LONG when everyone is SHORT — reward
        contrarian_bonus += 0.15
    elif consensus_dir == "LONG" and short_trades > long_trades:
        # Going SHORT when everyone is LONG — reward
        contrarian_bonus += 0.15

    # Reward balanced direction (not all one way)
    direction_balance = min(long_trades, short_trades) / (total + 1e-8)
    balance_bonus = direction_balance * 0.1  # Up to 0.05 bonus for 50/50

    # Reward mean-reversion entries
    reversion_bonus = 0
    rsi = contrarian_signals.get("rsi", 50)
    bb_pctb = contrarian_signals.get("bb_pctb", 0.5)
    if contrarian_signals.get("is_oversold") and long_trades > 0:
        reversion_bonus += 0.1
    if contrarian_signals.get("is_overbought") and short_trades > 0:
        reversion_bonus += 0.1

    # Penalize extreme directional bias (>80% one direction)
    bias_penalty = 0
    if total > 5:
        max_dir_pct = max(long_trades, short_trades) / total
        if max_dir_pct > 0.8:
            bias_penalty = (max_dir_pct - 0.8) * 0.5  # penalty for extreme bias

    adjusted = base_fitness + contrarian_bonus + balance_bonus + reversion_bonus - bias_penalty
    return adjusted


def evolve_contrarian(market_data: Dict, consensus: Dict, pop: int = 50, gens: int = 15) -> List[Dict]:
    """Evolve contrarian strategies."""
    logger.info(f"Evolving contrarian strategies: pop={pop}, gens={gens}")

    if not market_data:
        return []

    # Compute contrarian signals per symbol
    contrarian_signals = {}
    for sym, data in market_data.items():
        contrarian_signals[sym] = compute_contrarian_signals(data)
        signals = contrarian_signals[sym]
        logger.info(f"  {sym}: RSI={signals.get('rsi', 0):.1f} | BB%B={signals.get('bb_pctb', 0):.2f} | "
                     f"VolSpike={signals.get('vol_spike', 0):.1f}x | "
                     f"{'OVERSOLD' if signals.get('is_oversold') else 'OVERBOUGHT' if signals.get('is_overbought') else 'neutral'}")

    # Initialize population with mean-reversion-friendly parameters
    population = []
    for i in range(pop):
        strategy = _gp.random_strategy(generation=0, name_prefix="Rebel")
        # Tighter parameters for mean-reversion
        strategy.tp_pct = round(random.uniform(0.02, 0.06), 4)  # 2-6% TP
        strategy.sl_pct = round(random.uniform(0.01, 0.03), 4)  # 1-3% SL (tight)
        strategy.max_hold_bars = random.choice([6, 12, 18, 24, 36])  # Short holds
        population.append(strategy)

    best_ever = None
    best_fitness = -999

    for gen in range(gens):
        fitnesses = []

        for strategy in population:
            sym_results = []
            for sym, data in market_data.items():
                try:
                    result = _gp.backtest_strategy(strategy, data)
                    trades = result.get("trades", [])
                    con_dir = consensus.get(sym, {}).get("direction", "NEUTRAL")
                    con_signals = contrarian_signals.get(sym, {})

                    # Apply contrarian fitness adjustment
                    base_fitness = result.get("overall_fitness", -1)
                    adjusted = contrarian_fitness(base_fitness, trades, con_dir, con_signals)
                    result["overall_fitness"] = adjusted
                    sym_results.append(result)
                except Exception:
                    sym_results.append({"overall_fitness": -1})

            avg_fitness = np.mean([r.get("overall_fitness", -1) for r in sym_results])
            fitnesses.append(avg_fitness)

            if avg_fitness > best_fitness:
                best_fitness = avg_fitness
                best_ever = (strategy, sym_results, market_data)

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
                # Keep mean-reversion parameters
                child.tp_pct = round(np.clip(child.tp_pct, 0.02, 0.06), 4)
                child.sl_pct = round(np.clip(child.sl_pct, 0.01, 0.03), 4)
                child.max_hold_bars = random.choice([6, 12, 18, 24, 36])
            else:
                child = _gp.mutate_strategy(parent1, gen + 1)
                child.tp_pct = round(np.clip(child.tp_pct, 0.02, 0.06), 4)
                child.sl_pct = round(np.clip(child.sl_pct, 0.01, 0.03), 4)

            new_pop.append(child)

        population = new_pop
        avg = np.mean(fitnesses)
        logger.info(f"Gen {gen:2d} | Best Ever: {best_fitness:.4f} | Avg: {avg:.4f}")

    return _generate_picks(best_ever, consensus, contrarian_signals) if best_ever else []


def _generate_picks(best, consensus: Dict, contrarian_signals: Dict) -> List[Dict]:
    """Generate contrarian picks."""
    strategy, results, market_data = best
    picks = []
    now = datetime.now(timezone.utc).isoformat()

    for (sym, data), result in zip(market_data.items(), results):
        if result.get("overall_fitness", 0) < 0.15:
            continue

        trades = result.get("trades", [])
        if not trades:
            continue

        last_trade = trades[-1]
        direction = last_trade.get("direction", "LONG")

        con = consensus.get(sym, {})
        signals = contrarian_signals.get(sym, {})

        # Determine if this is actually contrarian
        is_contrarian = False
        if con.get("direction") == "SHORT" and direction == "LONG":
            is_contrarian = True
        elif con.get("direction") == "LONG" and direction == "SHORT":
            is_contrarian = True

        # Determine contrarian reason
        reason = "evolved_edge"
        if signals.get("is_oversold") and direction == "LONG":
            reason = "oversold_bounce"
        elif signals.get("is_overbought") and direction == "SHORT":
            reason = "overbought_fade"
        elif signals.get("consecutive_down", 0) >= 4 and direction == "LONG":
            reason = "exhaustion_reversal"
        elif signals.get("consecutive_up", 0) >= 4 and direction == "SHORT":
            reason = "exhaustion_reversal"
        elif is_contrarian:
            reason = "consensus_fade"

        confidence = min(result.get("overall_fitness", 0.5), 0.95)
        # Boost confidence for confirmed contrarian setups
        if is_contrarian and signals.get("vol_spike", 0) > 1.5:
            confidence = min(confidence * 1.1, 0.95)

        picks.append({
            "symbol": sym,
            "direction": direction,
            "entry_price": float(data.close[-1]),
            "confidence": round(confidence, 3),
            "strategy": strategy.name if hasattr(strategy, "name") else "Rebel",
            "source_system": "contrarian_evolver",
            "win_rate": result.get("win_rate", 0),
            "sharpe_ratio": result.get("sharpe_ratio", 0),
            "profit_factor": result.get("profit_factor", 0),
            "performance_score": result.get("overall_fitness", 0),
            "total_trades": result.get("total_trades", 0),
            "is_contrarian": bool(is_contrarian),
            "contrarian_reason": reason,
            "consensus_direction": con.get("direction", "UNKNOWN"),
            "rsi": signals.get("rsi", 50),
            "bb_pctb": round(signals.get("bb_pctb", 0.5), 2),
            "vol_spike": round(signals.get("vol_spike", 1.0), 2),
            "timestamp": now,
        })

    return picks


def run_contrarian_evolution():
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("REBEL: Contrarian DNA Evolution")
    logger.info("=" * 70)

    # Step 1: Analyze consensus from other engines
    consensus = load_consensus_direction()

    # Step 2: Fetch market data
    try:
        market_data = _gp.fetch_market_data(SYMBOLS, limit=750)
    except Exception as e:
        logger.warning(f"Fetch failed: {e}")
        return {"picks": []}

    if not market_data:
        logger.warning("No market data available")
        return {"picks": []}

    # Step 3: Evolve contrarian strategies
    picks = evolve_contrarian(market_data, consensus, pop=50, gens=15)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": "contrarian_evolver",
        "codename": "REBEL",
        "consensus_analyzed": len(consensus),
        "symbols": SYMBOLS,
        "total_picks": len(picks),
        "contrarian_picks": sum(1 for p in picks if p.get("is_contrarian")),
        "picks": picks,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2))
    logger.info(f"\nSaved {len(picks)} contrarian picks to {OUTPUT_PATH}")

    print(f"\n{'=' * 70}")
    print("REBEL — Contrarian DNA Evolution Results")
    print(f"{'=' * 70}")
    print(f"  Symbols: {', '.join(SYMBOLS)}")
    print(f"  Consensus analyzed: {len(consensus)} symbols")
    print(f"  Picks generated: {len(picks)} ({sum(1 for p in picks if p.get('is_contrarian'))} contrarian)")
    for p in picks[:5]:
        label = f"CONTRARIAN({p.get('contrarian_reason', '')})" if p.get("is_contrarian") else "aligned"
        print(f"    {p['direction']:5s} {p['symbol']:10s} | Score={p.get('performance_score',0):.3f} | "
              f"WR={p.get('win_rate',0):.0%} | RSI={p.get('rsi',0):.0f} | {label}")

    return result


if __name__ == "__main__":
    run_contrarian_evolution()
