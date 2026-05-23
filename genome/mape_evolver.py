"""
MAP-Elites Quality-Diversity Evolution Engine
==============================================
Illuminates the behavior space of trading strategies.

Unlike standard GP which converges to a single optimum, MAP-Elites maintains
an archive of high-performing strategies across different behavioral dimensions.
This discovers diverse strategy types: scalpers, swing traders, conservative,
aggressive, mean-reversion, trend-following, etc.

Inspired by: MAP-Elites algorithm (Mouret & Clune, 2015)
"""

import copy
import hashlib
import json
import logging
import random
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
import numpy as np

# Import from genetic_programmer using direct file import (avoids genome/__init__.py pandas issue)
import importlib.util
_gp_path = str(Path(__file__).resolve().parent / "genetic_programmer.py")
_spec = importlib.util.spec_from_file_location("genetic_programmer", _gp_path)
_gp_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gp_mod)
OHLCVData = _gp_mod.OHLCVData
compute_features = _gp_mod.compute_features
backtest_strategy = _gp_mod.backtest_strategy
fetch_market_data = _gp_mod.fetch_market_data
GPStrategy = _gp_mod.GPStrategy
GPNode = _gp_mod.GPNode
random_tree = _gp_mod.random_tree
random_strategy = _gp_mod.random_strategy
create_bonus_strategies = _gp_mod.create_bonus_strategies
crossover_strategies = _gp_mod.crossover_strategies
mutate_strategy = _gp_mod.mutate_strategy

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENOME_DIR = Path(__file__).resolve().parent
DB_PATH = GENOME_DIR / "mape_evolver.db"
ARCHIVE_PATH = GENOME_DIR / "data" / "mape_archive.json"
PICKS_OUTPUT = PROJECT_ROOT / "genome" / "data" / "mape_active_picks.json"

(GENOME_DIR / "data" / "mape_results").mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("MAPE_Evolver")


# =============================================================================
# Behavioral Descriptors - Define the dimensions of diversity
# =============================================================================

@dataclass
class BehaviorProfile:
    """
    Characterizes HOW a strategy behaves, not just how well it performs.
    These dimensions form the axes of the MAP-Elites archive.
    """
    # Dimension 1: Trade Frequency (0=swing, 1=scalper)
    trades_per_day: float = 0.0
    
    # Dimension 2: Risk Profile (0=conservative, 1=aggressive)  
    avg_hold_time_bars: float = 0.0
    max_position_exposure: float = 0.0  # inferred from SL/TP width
    
    # Dimension 3: Direction Bias (0=short_bias, 0.5=neutral, 1=long_bias)
    long_short_ratio: float = 0.5
    
    # Dimension 4: Market Regime Preference (0=trending, 1=mean_reverting)
    regime_preference: float = 0.5
    
    # Dimension 5: Signal Complexity (0=simple, 1=complex) - tree size
    tree_complexity: float = 0.0
    
    def to_grid_coords(self, grid_shape: Tuple[int, ...] = (5, 5, 3, 3, 3)) -> Tuple[int, ...]:
        """Map continuous behavior to discrete grid coordinates."""
        coords = []
        
        # Clip to [0, 1] and discretize
        freq = np.clip(self.trades_per_day / 10, 0, 1)  # Normalize to 0-1
        coords.append(int(freq * (grid_shape[0] - 1)))
        
        risk = np.clip(1 - (self.avg_hold_time_bars / 100), 0, 1)  # Shorter = riskier
        coords.append(int(risk * (grid_shape[1] - 1)))
        
        bias = np.clip(self.long_short_ratio, 0, 1)
        coords.append(int(bias * (grid_shape[2] - 1)))
        
        regime = np.clip(self.regime_preference, 0, 1)
        coords.append(int(regime * (grid_shape[3] - 1)))
        
        complexity = np.clip(self.tree_complexity / 50, 0, 1)
        coords.append(int(complexity * (grid_shape[4] - 1)))
        
        return tuple(coords)


def extract_behavior_profile(strategy: GPStrategy, backtest_result: Dict) -> BehaviorProfile:
    """Extract behavioral characteristics from a strategy and its results."""
    trades = backtest_result.get("trades", [])
    total_trades = len(trades)
    
    if total_trades == 0:
        return BehaviorProfile()
    
    # Trade frequency (trades per day assuming 24 bars/day)
    bars = backtest_result.get("total_bars", 750)
    trades_per_day = (total_trades / bars) * 24
    
    # Average hold time
    if trades:
        hold_times = [t.get("exit_idx", 0) - t.get("entry_idx", 0) for t in trades]
        avg_hold = np.mean(hold_times)
    else:
        avg_hold = 0
    
    # Long/short ratio
    longs = sum(1 for t in trades if t.get("direction") == "LONG")
    long_ratio = longs / total_trades if total_trades > 0 else 0.5
    
    # Exposure from TP/SL settings
    exposure = strategy.tp_pct + strategy.sl_pct
    
    # Tree complexity
    buy_size = strategy.buy_tree.size()
    sell_size = strategy.sell_tree.size()
    complexity = (buy_size + sell_size) / 2
    
    # Estimate regime preference from indicators used
    regime_pref = 0.5  # Default neutral
    formula = strategy.buy_tree.to_string()
    if "rsi" in formula.lower() or "bb_" in formula.lower():
        regime_pref = 0.8  # Mean-reversion indicators
    elif "ema" in formula.lower() or "macd" in formula.lower():
        regime_pref = 0.2  # Trend indicators
    
    return BehaviorProfile(
        trades_per_day=trades_per_day,
        avg_hold_time_bars=avg_hold,
        max_position_exposure=exposure,
        long_short_ratio=long_ratio,
        regime_preference=regime_pref,
        tree_complexity=complexity
    )


# =============================================================================
# MAP-Elites Archive
# =============================================================================

@dataclass
class ArchiveCell:
    """A single cell in the MAP-Elites archive containing the best strategy for that behavior."""
    coords: Tuple[int, ...]
    strategy: Optional[GPStrategy] = None
    fitness: float = 0.0
    behavior: Optional[BehaviorProfile] = None
    occupancy_count: int = 0  # How many strategies have tried this cell
    
    def to_dict(self) -> Dict:
        return {
            "coords": self.coords,
            "fitness": self.fitness,
            "occupancy_count": self.occupancy_count,
            "strategy": self.strategy.to_dict() if self.strategy else None,
            "behavior": asdict(self.behavior) if self.behavior else None
        }


class MAPElitesArchive:
    """
    N-dimensional archive where each cell contains the best strategy 
    for a specific behavioral niche.
    """
    
    def __init__(self, grid_shape: Tuple[int, ...] = (5, 5, 3, 3, 3)):
        self.grid_shape = grid_shape
        self.archive: Dict[Tuple[int, ...], ArchiveCell] = {}
        self.elite_count = 0
        self.coverage = 0.0
        
    def get_cell(self, coords: Tuple[int, ...]) -> Optional[ArchiveCell]:
        return self.archive.get(coords)
    
    def attempt_add(self, strategy: GPStrategy, fitness: float, 
                    behavior: BehaviorProfile) -> bool:
        """
        Try to add a strategy to the archive.
        Returns True if it was added (improved its cell).
        """
        coords = behavior.to_grid_coords(self.grid_shape)
        
        cell = self.archive.get(coords)
        
        if cell is None:
            # New cell discovered!
            self.archive[coords] = ArchiveCell(
                coords=coords,
                strategy=strategy,
                fitness=fitness,
                behavior=behavior,
                occupancy_count=1
            )
            self.elite_count += 1
            return True
        
        cell.occupancy_count += 1
        
        # Competition: better fitness wins
        if fitness > cell.fitness:
            cell.strategy = strategy
            cell.fitness = fitness
            cell.behavior = behavior
            return True
        
        return False
    
    def get_random_elite(self) -> Optional[GPStrategy]:
        """Random selection from archive for mutation/crossover."""
        if not self.archive:
            return None
        cell = random.choice(list(self.archive.values()))
        return cell.strategy
    
    def get_all_elites(self) -> List[GPStrategy]:
        """Get all current elites."""
        return [c.strategy for c in self.archive.values() if c.strategy]
    
    def get_coverage_stats(self) -> Dict:
        """Statistics about archive coverage."""
        total_cells = np.prod(self.grid_shape)
        filled_cells = len(self.archive)
        
        # QD score: sum of all fitnesses (measures quality + diversity)
        qd_score = sum(c.fitness for c in self.archive.values())
        
        # Average fitness
        avg_fitness = qd_score / filled_cells if filled_cells > 0 else 0
        
        return {
            "total_cells": int(total_cells),
            "filled_cells": filled_cells,
            "coverage_pct": filled_cells / total_cells * 100,
            "qd_score": round(qd_score, 4),
            "avg_fitness": round(avg_fitness, 4),
            "max_fitness": max((c.fitness for c in self.archive.values()), default=0)
        }
    
    def save(self, path: Path):
        """Persist archive to JSON."""
        data = {
            "grid_shape": self.grid_shape,
            "stats": self.get_coverage_stats(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cells": {str(k): v.to_dict() for k, v in self.archive.items()}
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    def load(self, path: Path):
        """Load archive from JSON."""
        if not path.exists():
            return
        try:
            with open(path) as f:
                data = json.load(f)
            # Could reconstruct cells here if needed
            logger.info(f"Loaded archive with {len(data.get('cells', {}))} cells")
        except Exception as e:
            logger.warning(f"Failed to load archive: {e}")


# =============================================================================
# MAP-Elites Evolution Engine
# =============================================================================

class MAPElitesEvolver:
    """
    Quality-Diversity evolution using the MAP-Elites algorithm.
    
    Key differences from standard GP:
    - Maintains archive across behavioral dimensions, not just fitness
    - Selection favors exploration of under-represented niches
    - Goal is to illuminate what types of strategies work, not just find one winner
    """
    
    def __init__(self, 
                 iterations: int = 5000,
                 initial_random: int = 200,
                 mutation_rate: float = 0.20,
                 crossover_rate: float = 0.50,
                 grid_shape: Tuple[int, ...] = (5, 5, 3, 3, 3),
                 symbols: Optional[List[str]] = None):
        
        self.iterations = iterations
        self.initial_random = initial_random
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.grid_shape = grid_shape
        self.symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        
        self.archive = MAPElitesArchive(grid_shape)
        self.generation = 0
        self.stats_history: List[Dict] = []
        
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS mape_archive (
                cell_coords TEXT PRIMARY KEY,
                strategy_id TEXT, strategy_name TEXT,
                fitness REAL, behavior_json TEXT,
                created_at TEXT, generation INTEGER
            );
            CREATE TABLE IF NOT EXISTS mape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_timestamp TEXT, iterations INTEGER,
                final_coverage_pct REAL, qd_score REAL,
                best_fitness REAL, total_cells INTEGER
            );
        """)
        conn.commit()
        conn.close()
    
    def _evaluate_strategy(self, strategy: GPStrategy, 
                          market_data: Dict[str, OHLCVData]) -> Tuple[float, Dict, BehaviorProfile]:
        """Evaluate strategy across all symbols, return fitness + behavior."""
        all_results = {}
        for sym, data in market_data.items():
            try:
                result = backtest_strategy(strategy, data)
                all_results[sym] = result
            except Exception as e:
                logger.debug(f"Backtest error for {sym}: {e}")
                all_results[sym] = {"overall_fitness": 0, "trades": []}
        
        # Overall fitness is average across symbols
        fitnesses = [r.get("overall_fitness", 0) for r in all_results.values()]
        avg_fitness = np.mean(fitnesses) if fitnesses else 0
        
        # Get behavior from best-performing symbol
        best_sym = max(all_results.items(), key=lambda x: x[1].get("overall_fitness", 0))
        behavior = extract_behavior_profile(strategy, best_sym[1])
        
        strategy.fitness = {
            "overall_fitness": avg_fitness,
            "per_symbol": all_results
        }
        
        return avg_fitness, all_results, behavior
    
    def run_evolution(self, market_data: Dict[str, OHLCVData]) -> MAPElitesArchive:
        """
        Run MAP-Elites evolution.
        
        Algorithm:
        1. Initialize with random strategies (fill archive)
        2. For each iteration:
           - Select random elite from archive
           - Mutate or crossover
           - Evaluate and attempt to add to archive
        3. Return illuminated archive
        """
        logger.info("=" * 70)
        logger.info("MAP-ELITES QUALITY-DIVERSITY EVOLUTION")
        logger.info(f"Grid: {self.grid_shape} = {np.prod(self.grid_shape)} cells")
        logger.info(f"Iterations: {self.iterations} | Initial random: {self.initial_random}")
        logger.info("=" * 70)
        
        # Phase 1: Random initialization
        logger.info(f"\n[Phase 1] Random initialization ({self.initial_random} strategies)...")
        for i in range(self.initial_random):
            strategy = random_strategy(generation=0, name_prefix="MAPE_Init")
            fitness, results, behavior = self._evaluate_strategy(strategy, market_data)
            added = self.archive.attempt_add(strategy, fitness, behavior)
            
            if i % 50 == 0:
                stats = self.archive.get_coverage_stats()
                logger.info(f"  Init {i}/{self.initial_random} | "
                          f"Coverage: {stats['filled_cells']}/{stats['total_cells']} cells "
                          f"({stats['coverage_pct']:.1f}%) | QD: {stats['qd_score']:.2f}")
        
        # Phase 2: Illumination
        logger.info(f"\n[Phase 2] Illumination ({self.iterations} iterations)...")
        for iteration in range(self.iterations):
            self.generation = iteration
            
            # Selection: random elite from archive
            parent = self.archive.get_random_elite()
            if parent is None:
                parent = random_strategy(generation=iteration)
            
            # Variation
            if random.random() < self.crossover_rate and self.archive.elite_count > 5:
                parent2 = self.archive.get_random_elite()
                if parent2 is None:
                    parent2 = random_strategy(generation=iteration)
                child = crossover_strategies(parent, parent2, iteration)
            else:
                child = mutate_strategy(parent, iteration, self.mutation_rate)
            
            # Evaluation
            fitness, results, behavior = self._evaluate_strategy(child, market_data)
            
            # Addition attempt
            added = self.archive.attempt_add(child, fitness, behavior)
            
            # Logging
            if iteration % 500 == 0 or (added and iteration % 100 == 0):
                stats = self.archive.get_coverage_stats()
                logger.info(f"  Iter {iteration:5d} | "
                          f"Coverage: {stats['coverage_pct']:.1f}% | "
                          f"QD Score: {stats['qd_score']:.2f} | "
                          f"Best: {stats['max_fitness']:.3f} | "
                          f"{'+NEW' if added else ''}")
                self.stats_history.append({
                    "iteration": iteration,
                    **stats
                })
        
        # Final stats
        final_stats = self.archive.get_coverage_stats()
        logger.info("\n" + "=" * 70)
        logger.info("MAP-ELITES EVOLUTION COMPLETE")
        logger.info(f"Archive Coverage: {final_stats['coverage_pct']:.1f}%")
        logger.info(f"QD Score: {final_stats['qd_score']:.3f}")
        logger.info(f"Best Fitness: {final_stats['max_fitness']:.3f}")
        logger.info("=" * 70)
        
        self._save_results()
        return self.archive
    
    def _save_results(self):
        """Persist results to DB and JSON."""
        # Save archive
        self.archive.save(ARCHIVE_PATH)
        
        # Save picks for audit dashboard
        self._save_picks_json()
        
        # Save to DB
        conn = sqlite3.connect(str(DB_PATH))
        stats = self.archive.get_coverage_stats()
        
        conn.execute(
            """INSERT INTO mape_runs 
               (run_timestamp, iterations, final_coverage_pct, qd_score, best_fitness, total_cells)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (datetime.now(timezone.utc).isoformat(), self.iterations,
             stats['coverage_pct'], stats['qd_score'], stats['max_fitness'],
             stats['filled_cells'])
        )
        
        for coords, cell in self.archive.archive.items():
            if cell.strategy:
                conn.execute(
                    """INSERT OR REPLACE INTO mape_archive
                       (cell_coords, strategy_id, strategy_name, fitness, behavior_json, created_at, generation)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (str(coords), cell.strategy.strategy_id, cell.strategy.name,
                     cell.fitness, json.dumps(asdict(cell.behavior)),
                     datetime.now(timezone.utc).isoformat(), self.generation)
                )
        
        conn.commit()
        conn.close()
    
    def _save_picks_json(self):
        """Export top strategies from each cell for audit dashboard."""
        now = datetime.now(timezone.utc).isoformat()
        picks = []
        
        for coords, cell in self.archive.archive.items():
            if not cell.strategy or cell.fitness < 0.3:
                continue
            
            per_symbol = cell.strategy.fitness.get("per_symbol", {})
            for symbol, metrics in per_symbol.items():
                if metrics.get("overall_fitness", 0) < 0.3:
                    continue
                
                trades = metrics.get("trades", [])
                direction = trades[-1].get("direction", "LONG") if trades else "LONG"
                
                picks.append({
                    "symbol": symbol,
                    "direction": direction,
                    "confidence": min(cell.fitness * 1.2, 1.0),
                    "strategy": cell.strategy.name,
                    "source_system": "mape_evolver",
                    "win_rate": metrics.get("win_rate", 0),
                    "sharpe_ratio": metrics.get("sharpe_ratio", 0),
                    "profit_factor": metrics.get("profit_factor", 0),
                    "mape_cell": str(coords),
                    "behavior": {
                        "trades_per_day": round(cell.behavior.trades_per_day, 2),
                        "avg_hold_bars": round(cell.behavior.avg_hold_time_bars, 1),
                        "long_ratio": round(cell.behavior.long_short_ratio, 2),
                        "regime_pref": round(cell.behavior.regime_preference, 2)
                    },
                    "timestamp": now
                })
        
        output = {
            "generated_at": now,
            "system": "mape_evolver",
            "version": "1.0.0",
            "total_picks": len(picks),
            "archive_stats": self.archive.get_coverage_stats(),
            "picks": picks
        }
        
        with open(str(PICKS_OUTPUT), "w") as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Saved {len(picks)} MAP-Elites picks to {PICKS_OUTPUT}")


# =============================================================================
# Analysis Tools
# =============================================================================

def analyze_archive_diversity(archive: MAPElitesArchive) -> Dict:
    """Analyze the diversity of strategies in the archive."""
    if not archive.archive:
        return {}
    
    behaviors = [c.behavior for c in archive.archive.values() if c.behavior]
    
    analysis = {
        "trade_frequency_distribution": {
            "scalpers (>5/day)": sum(1 for b in behaviors if b.trades_per_day > 5),
            "active (2-5/day)": sum(1 for b in behaviors if 2 <= b.trades_per_day <= 5),
            "moderate (0.5-2/day)": sum(1 for b in behaviors if 0.5 <= b.trades_per_day < 2),
            "swing (<0.5/day)": sum(1 for b in behaviors if b.trades_per_day < 0.5)
        },
        "direction_bias": {
            "long_biased (>60%)": sum(1 for b in behaviors if b.long_short_ratio > 0.6),
            "balanced (40-60%)": sum(1 for b in behaviors if 0.4 <= b.long_short_ratio <= 0.6),
            "short_biased (<40%)": sum(1 for b in behaviors if b.long_short_ratio < 0.4)
        },
        "regime_preference": {
            "trend_following (<0.4)": sum(1 for b in behaviors if b.regime_preference < 0.4),
            "hybrid (0.4-0.6)": sum(1 for b in behaviors if 0.4 <= b.regime_preference <= 0.6),
            "mean_reversion (>0.6)": sum(1 for b in behaviors if b.regime_preference > 0.6)
        },
        "complexity_distribution": {
            "simple (<20 nodes)": sum(1 for b in behaviors if b.tree_complexity < 20),
            "medium (20-40)": sum(1 for b in behaviors if 20 <= b.tree_complexity <= 40),
            "complex (>40)": sum(1 for b in behaviors if b.tree_complexity > 40)
        }
    }
    
    return analysis


# =============================================================================
# Entry Point
# =============================================================================

def run_mape_evolution(symbols=None, iterations=3000, initial_random=150):
    """Main entry point for MAP-Elites evolution."""
    symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    logger.info("Fetching market data...")
    market_data = fetch_market_data(symbols, limit=750)
    
    if not market_data:
        logger.error("No market data available")
        return None
    
    evolver = MAPElitesEvolver(
        iterations=iterations,
        initial_random=initial_random,
        symbols=list(market_data.keys())
    )
    
    archive = evolver.run_evolution(market_data)
    
    # Analysis
    print("\n" + "=" * 70)
    print("STRATEGY DIVERSITY ANALYSIS")
    print("=" * 70)
    analysis = analyze_archive_diversity(archive)
    for category, stats in analysis.items():
        print(f"\n{category}:")
        for label, count in stats.items():
            print(f"  {label}: {count}")
    
    print(f"\nArchive saved to: {ARCHIVE_PATH}")
    print(f"Picks exported to: {PICKS_OUTPUT}")
    
    return archive


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MAP-Elites Quality-Diversity Evolution")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT", help="Symbols")
    parser.add_argument("--iterations", type=int, default=3000, help="Evolution iterations")
    parser.add_argument("--initial", type=int, default=150, help="Initial random population")
    args = parser.parse_args()
    
    symbols = [s.strip() for s in args.symbols.split(",")]
    run_mape_evolution(symbols=symbols, iterations=args.iterations, initial_random=args.initial)
