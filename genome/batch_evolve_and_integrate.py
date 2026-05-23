"""
Batch Evolution & Integration Pipeline
======================================

1. Runs MAP-Elites evolution to generate diverse strategies
2. Runs Ensemble coevolution to generate team strategies
3. Backtests all strategies across multiple symbols/timeframes
4. Filters viable strategies (fitness > 0.5, WR > 55%, Sharpe > 1.5)
5. Integrates viable strategies into ejaguiar1_stocks database
6. Creates forward-facing picks for live trading

Usage:
    python genome/batch_evolve_and_integrate.py --full-pipeline
    python genome/batch_evolve_and_integrate.py --mape-only --iterations 2000
    python genome/batch_evolve_and_integrate.py --ensemble-only --gens 20
"""

import copy
import hashlib
import json
import logging
import os
import random
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from genome.genetic_programmer import (
    OHLCVData, compute_features, backtest_strategy,
    fetch_market_data, GPStrategy, random_strategy,
    create_bonus_strategies
)
from genome.mape_evolver import (
    MAPElitesArchive, MAPElitesEvolver, 
    BehaviorProfile, extract_behavior_profile
)
from genome.ensemble_evolver import (
    EnsembleEvolutionEngine, StrategyEnsemble, 
    EnsembleMember, backtest_ensemble
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("BatchEvolve")


# =============================================================================
# Configuration
# =============================================================================

VIABILITY_THRESHOLDS = {
    "min_fitness": 0.50,
    "min_win_rate": 0.55,
    "min_sharpe": 1.5,
    "min_profit_factor": 1.2,
    "min_trades": 15,
    "max_drawdown": 25.0,  # %
}

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOGEUSDT"]
TIMEFRAMES = ["1h"]  # Can extend to "4h", "1d" for multi-timeframe

DB_PATH = PROJECT_ROOT / "paper_trading" / "data" / "paper.db"
AUDIT_DB_PATH = PROJECT_ROOT / "data" / "audit_trail.db"
RESULTS_DIR = PROJECT_ROOT / "genome" / "batch_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Viability Filter
# =============================================================================

@dataclass
class ViableStrategy:
    """A strategy that passed viability thresholds."""
    strategy_id: str
    name: str
    strategy_type: str  # "gp", "mape", "ensemble"
    source_file: str
    
    # Performance metrics
    fitness: float
    win_rate: float
    sharpe_ratio: float
    profit_factor: float
    max_drawdown: float
    total_trades: int
    total_return: float
    
    # Strategy details
    symbol: str
    direction: str
    tp_pct: float
    sl_pct: float
    buy_formula: str = ""
    sell_formula: str = ""
    
    # For ensembles
    member_count: int = 0
    consensus_type: str = ""
    
    # For MAP-Elites
    behavior_cell: str = ""
    trades_per_day: float = 0.0
    
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "strategy_type": self.strategy_type,
            "fitness": self.fitness,
            "win_rate": self.win_rate,
            "sharpe_ratio": self.sharpe_ratio,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown,
            "total_trades": self.total_trades,
            "total_return": self.total_return,
            "symbol": self.symbol,
            "direction": self.direction,
            "tp_pct": self.tp_pct,
            "sl_pct": self.sl_pct,
            "created_at": self.created_at
        }


def check_viability(metrics: Dict) -> Tuple[bool, float]:
    """
    Check if strategy metrics pass viability thresholds.
    Returns (is_viable, composite_score).
    """
    fitness = metrics.get("overall_fitness", 0)
    wr = metrics.get("win_rate", 0)
    sharpe = metrics.get("sharpe_ratio", 0)
    pf = metrics.get("profit_factor", 0)
    trades = metrics.get("total_trades", 0)
    dd = metrics.get("max_drawdown_pct", 100)
    
    # Must meet all minimum thresholds
    if fitness < VIABILITY_THRESHOLDS["min_fitness"]:
        return False, 0
    if wr < VIABILITY_THRESHOLDS["min_win_rate"]:
        return False, 0
    if sharpe < VIABILITY_THRESHOLDS["min_sharpe"]:
        return False, 0
    if pf < VIABILITY_THRESHOLDS["min_profit_factor"]:
        return False, 0
    if trades < VIABILITY_THRESHOLDS["min_trades"]:
        return False, 0
    if dd > VIABILITY_THRESHOLDS["max_drawdown"]:
        return False, 0
    
    # Composite score for ranking
    composite = (
        0.30 * fitness +
        0.25 * wr +
        0.20 * min(sharpe / 5, 1.0) +
        0.15 * min(pf / 3, 1.0) +
        0.10 * (1 - dd / 50)
    )
    
    return True, composite


# =============================================================================
# Extended Backtesting (Multiple Symbols/Timeframes)
# =============================================================================

def extended_backtest_strategy(
    strategy: GPStrategy,
    symbols: List[str] = None,
    timeframes: List[str] = ["1h"]
) -> Dict[str, Dict]:
    """
    Backtest a strategy across multiple symbols and timeframes.
    Returns per-symbol results with viability checks.
    """
    symbols = symbols or SYMBOLS
    all_results = {}
    
    for tf in timeframes:
        market_data = fetch_market_data(symbols, timeframe=tf, limit=750)
        
        for sym, data in market_data.items():
            try:
                result = backtest_strategy(strategy, data)
                result["timeframe"] = tf
                result["symbol"] = sym
                
                is_viable, score = check_viability(result)
                result["is_viable"] = is_viable
                result["viability_score"] = score
                
                all_results[f"{sym}_{tf}"] = result
            except Exception as e:
                logger.warning(f"Backtest failed for {sym} {tf}: {e}")
                all_results[f"{sym}_{tf}"] = {
                    "overall_fitness": 0, "is_viable": False,
                    "symbol": sym, "timeframe": tf
                }
    
    return all_results


def extended_backtest_ensemble(
    ensemble: StrategyEnsemble,
    symbols: List[str] = None,
    timeframes: List[str] = ["1h"]
) -> Dict[str, Dict]:
    """Backtest an ensemble across multiple symbols/timeframes."""
    symbols = symbols or SYMBOLS
    all_results = {}
    
    for tf in timeframes:
        market_data = fetch_market_data(symbols, timeframe=tf, limit=750)
        
        for sym, data in market_data.items():
            try:
                result = backtest_ensemble(ensemble, data)
                result["timeframe"] = tf
                result["symbol"] = sym
                
                is_viable, score = check_viability(result)
                result["is_viable"] = is_viable
                result["viability_score"] = score
                
                all_results[f"{sym}_{tf}"] = result
            except Exception as e:
                logger.warning(f"Ensemble backtest failed for {sym} {tf}: {e}")
                all_results[f"{sym}_{tf}"] = {
                    "overall_fitness": 0, "is_viable": False,
                    "symbol": sym, "timeframe": tf
                }
    
    return all_results


# =============================================================================
# Database Integration
# =============================================================================

def init_strategy_registry_table():
    """Create table for evolved strategies in paper trading DB."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS evolved_strategies (
            strategy_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            strategy_type TEXT NOT NULL,
            source_file TEXT,
            fitness REAL,
            win_rate REAL,
            sharpe_ratio REAL,
            profit_factor REAL,
            max_drawdown REAL,
            total_trades INTEGER,
            total_return REAL,
            symbol TEXT,
            direction TEXT,
            tp_pct REAL,
            sl_pct REAL,
            buy_formula TEXT,
            sell_formula TEXT,
            member_count INTEGER,
            consensus_type TEXT,
            behavior_cell TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TEXT,
            last_used_at TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_evolved_fitness ON evolved_strategies(fitness);
        CREATE INDEX IF NOT EXISTS idx_evolved_viable ON evolved_strategies(is_active, fitness);
    """)
    conn.commit()
    conn.close()


def register_viable_strategy(vs: ViableStrategy):
    """Register a viable strategy in the database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """INSERT OR REPLACE INTO evolved_strategies
           (strategy_id, name, strategy_type, source_file, fitness, win_rate,
            sharpe_ratio, profit_factor, max_drawdown, total_trades, total_return,
            symbol, direction, tp_pct, sl_pct, buy_formula, sell_formula,
            member_count, consensus_type, behavior_cell, is_active, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (vs.strategy_id, vs.name, vs.strategy_type, vs.source_file,
         vs.fitness, vs.win_rate, vs.sharpe_ratio, vs.profit_factor,
         vs.max_drawdown, vs.total_trades, vs.total_return,
         vs.symbol, vs.direction, vs.tp_pct, vs.sl_pct,
         vs.buy_formula, vs.sell_formula, vs.member_count,
         vs.consensus_type, vs.behavior_cell, 1, vs.created_at)
    )
    conn.commit()
    conn.close()
    logger.info(f"Registered viable strategy: {vs.name} ({vs.strategy_type}, fitness={vs.fitness:.3f})")


def create_forward_pick(vs: ViableStrategy, current_price: float = 0):
    """Create a forward-facing pick for the strategy."""
    pick_id = f"evp_{hashlib.md5(f'{vs.strategy_id}_{datetime.now().timestamp()}'.encode()).hexdigest()[:12]}"
    
    # Calculate TP/SL prices based on direction
    if vs.direction == "LONG":
        tp_price = current_price * (1 + vs.tp_pct) if current_price > 0 else 0
        sl_price = current_price * (1 - vs.sl_pct) if current_price > 0 else 0
    else:
        tp_price = current_price * (1 - vs.tp_pct) if current_price > 0 else 0
        sl_price = current_price * (1 + vs.sl_pct) if current_price > 0 else 0
    
    pick = {
        "pick_id": pick_id,
        "strategy_id": vs.strategy_id,
        "symbol": vs.symbol,
        "direction": vs.direction,
        "entry_price": current_price,
        "take_profit": tp_price,
        "stop_loss": sl_price,
        "confidence": min(vs.fitness, 1.0),
        "strategy_name": vs.name,
        "strategy_type": vs.strategy_type,
        "fitness": vs.fitness,
        "win_rate": vs.win_rate,
        "sharpe": vs.sharpe_ratio,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PENDING",
        "source": "evolved_strategies"
    }
    
    return pick


def save_forward_picks(picks: List[Dict]):
    """Save forward picks to JSON and database."""
    # Save to JSON
    output_file = RESULTS_DIR / "forward_picks.json"
    with open(output_file, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_picks": len(picks),
            "picks": picks
        }, f, indent=2)
    
    # Save to positions table (as pending)
    conn = sqlite3.connect(str(DB_PATH))
    for pick in picks:
        conn.execute(
            """INSERT INTO positions
               (id, symbol, direction, entry_price, current_price, tp, sl,
                strategy, strategy_name, portfolio_type, conviction_tier,
                position_size_usd, shares, entry_date, status, confidence, reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pick["pick_id"], pick["symbol"], pick["direction"],
             pick["entry_price"], pick["entry_price"], pick["take_profit"],
             pick["stop_loss"], pick["strategy_id"], pick["strategy_name"],
             "evolved", "high" if pick["confidence"] > 0.7 else "medium",
             1000.0, 0, datetime.now(timezone.utc).isoformat(),
             "PENDING", pick["confidence"], f"Evolved strategy with fitness {pick['fitness']:.3f}")
        )
    conn.commit()
    conn.close()
    
    logger.info(f"Saved {len(picks)} forward picks")


# =============================================================================
# Main Pipeline
# =============================================================================

class BatchEvolutionPipeline:
    """Orchestrates the full evolution → backtest → integration pipeline."""
    
    def __init__(self):
        self.viable_strategies: List[ViableStrategy] = []
        self.all_results: Dict = {}
        
    def run_mape_phase(self, iterations: int = 2000, initial_random: int = 150) -> List[ViableStrategy]:
        """Run MAP-Elites evolution and extract viable strategies."""
        logger.info("=" * 70)
        logger.info("PHASE 1: MAP-Elites Quality-Diversity Evolution")
        logger.info("=" * 70)
        
        # Fetch data
        market_data = fetch_market_data(SYMBOLS, limit=750)
        if not market_data:
            logger.error("No market data available")
            return []
        
        # Run MAP-Elites
        evolver = MAPElitesEvolver(
            iterations=iterations,
            initial_random=initial_random,
            symbols=list(market_data.keys())
        )
        
        archive = evolver.run_evolution(market_data)
        
        # Extract viable strategies from archive
        viable = []
        for coords, cell in archive.archive.items():
            if not cell.strategy:
                continue
            
            # Get per-symbol results
            per_symbol = cell.strategy.fitness.get("per_symbol", {})
            
            for sym, metrics in per_symbol.items():
                is_viable, score = check_viability(metrics)
                
                if is_viable:
                    trades = metrics.get("trades", [])
                    direction = trades[-1].get("direction", "LONG") if trades else "LONG"
                    
                    vs = ViableStrategy(
                        strategy_id=cell.strategy.strategy_id,
                        name=f"MAPE_{cell.strategy.name}",
                        strategy_type="mape",
                        source_file="genome/mape_evolver.py",
                        fitness=metrics.get("overall_fitness", 0),
                        win_rate=metrics.get("win_rate", 0),
                        sharpe_ratio=metrics.get("sharpe_ratio", 0),
                        profit_factor=metrics.get("profit_factor", 0),
                        max_drawdown=metrics.get("max_drawdown_pct", 0),
                        total_trades=metrics.get("total_trades", 0),
                        total_return=metrics.get("total_return_pct", 0),
                        symbol=sym,
                        direction=direction,
                        tp_pct=cell.strategy.tp_pct,
                        sl_pct=cell.strategy.sl_pct,
                        buy_formula=cell.strategy.buy_tree.to_string()[:200],
                        sell_formula=cell.strategy.sell_tree.to_string()[:200],
                        behavior_cell=str(coords),
                        trades_per_day=cell.behavior.trades_per_day if cell.behavior else 0
                    )
                    
                    viable.append(vs)
                    register_viable_strategy(vs)
        
        logger.info(f"MAP-Elites found {len(viable)} viable strategies")
        return viable
    
    def run_ensemble_phase(self, population: int = 40, generations: int = 25) -> List[ViableStrategy]:
        """Run Ensemble coevolution and extract viable strategies."""
        logger.info("=" * 70)
        logger.info("PHASE 2: Ensemble Coevolution")
        logger.info("=" * 70)
        
        # Fetch data
        market_data = fetch_market_data(SYMBOLS, limit=750)
        if not market_data:
            logger.error("No market data available")
            return []
        
        # Create seed strategies
        seed_strategies = [random_strategy(0) for _ in range(15)]
        seed_strategies.extend(create_bonus_strategies())
        
        # Run ensemble evolution
        engine = EnsembleEvolutionEngine(
            population_size=population,
            generations=generations,
            symbols=list(market_data.keys())
        )
        
        winners = engine.run_evolution(market_data, seed_strategies)
        
        # Extract viable ensembles
        viable = []
        for ens in winners:
            per_symbol = ens.fitness.get("per_symbol", {})
            
            for sym, metrics in per_symbol.items():
                is_viable, score = check_viability(metrics)
                
                if is_viable:
                    trades = metrics.get("trades", [])
                    direction = trades[-1].get("direction", "LONG") if trades else "LONG"
                    
                    vs = ViableStrategy(
                        strategy_id=ens.ensemble_id,
                        name=f"ENS_{ens.name}",
                        strategy_type="ensemble",
                        source_file="genome/ensemble_evolver.py",
                        fitness=metrics.get("overall_fitness", 0),
                        win_rate=metrics.get("win_rate", 0),
                        sharpe_ratio=metrics.get("sharpe_ratio", 0),
                        profit_factor=metrics.get("profit_factor", 0),
                        max_drawdown=metrics.get("max_drawdown_pct", 0),
                        total_trades=metrics.get("total_trades", 0),
                        total_return=metrics.get("total_return_pct", 0),
                        symbol=sym,
                        direction=direction,
                        tp_pct=ens.members[0].strategy.tp_pct if ens.members else 0.04,
                        sl_pct=ens.members[0].strategy.sl_pct if ens.members else 0.02,
                        member_count=len(ens.members),
                        consensus_type=ens.consensus_type.value
                    )
                    
                    viable.append(vs)
                    register_viable_strategy(vs)
        
        logger.info(f"Ensemble evolution found {len(viable)} viable strategies")
        return viable
    
    def generate_forward_picks(self):
        """Generate forward-facing picks from all viable strategies."""
        logger.info("=" * 70)
        logger.info("PHASE 3: Generating Forward Picks")
        logger.info("=" * 70)
        
        # Sort by composite score
        sorted_strategies = sorted(
            self.viable_strategies,
            key=lambda s: s.fitness * s.win_rate * s.sharpe_ratio,
            reverse=True
        )
        
        # Take top 50
        top_strategies = sorted_strategies[:50]
        
        # Create picks (would need current prices in real scenario)
        picks = []
        for vs in top_strategies:
            pick = create_forward_pick(vs, current_price=0)  # Price to be filled at execution
            picks.append(pick)
        
        save_forward_picks(picks)
        
        logger.info(f"Generated {len(picks)} forward picks")
        return picks
    
    def run_full_pipeline(self, mape_iters: int = 2000, ens_gens: int = 25):
        """Run the complete pipeline."""
        logger.info("\n" + "=" * 70)
        logger.info("BATCH EVOLUTION & INTEGRATION PIPELINE")
        logger.info(f"Started: {datetime.now(timezone.utc).isoformat()}")
        logger.info("=" * 70)
        
        # Initialize database
        init_strategy_registry_table()
        
        # Phase 1: MAP-Elites
        mape_viable = self.run_mape_phase(iterations=mape_iters)
        self.viable_strategies.extend(mape_viable)
        
        # Phase 2: Ensemble
        ens_viable = self.run_ensemble_phase(generations=ens_gens)
        self.viable_strategies.extend(ens_viable)
        
        # Phase 3: Forward picks
        picks = self.generate_forward_picks()
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total viable strategies: {len(self.viable_strategies)}")
        logger.info(f"  - MAP-Elites: {len(mape_viable)}")
        logger.info(f"  - Ensemble: {len(ens_viable)}")
        logger.info(f"Forward picks generated: {len(picks)}")
        
        # Save summary
        summary = {
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_viable": len(self.viable_strategies),
            "mape_count": len(mape_viable),
            "ensemble_count": len(ens_viable),
            "forward_picks": len(picks),
            "strategies": [vs.to_dict() for vs in self.viable_strategies]
        }
        
        with open(RESULTS_DIR / "pipeline_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        return self.viable_strategies


# =============================================================================
# Command Line Interface
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Batch Evolution & Integration Pipeline")
    parser.add_argument("--full-pipeline", action="store_true", help="Run complete pipeline")
    parser.add_argument("--mape-only", action="store_true", help="Run only MAP-Elites")
    parser.add_argument("--ensemble-only", action="store_true", help="Run only Ensemble")
    parser.add_argument("--mape-iters", type=int, default=2000, help="MAP-Elites iterations")
    parser.add_argument("--ens-gens", type=int, default=25, help="Ensemble generations")
    parser.add_argument("--quick", action="store_true", help="Quick mode (fewer iterations)")
    args = parser.parse_args()
    
    pipeline = BatchEvolutionPipeline()
    
    if args.quick:
        args.mape_iters = 500
        args.ens_gens = 10
    
    if args.mape_only:
        pipeline.run_mape_phase(iterations=args.mape_iters)
    elif args.ensemble_only:
        pipeline.run_ensemble_phase(generations=args.ens_gens)
    else:
        # Default to full pipeline
        pipeline.run_full_pipeline(
            mape_iters=args.mape_iters,
            ens_gens=args.ens_gens
        )


if __name__ == "__main__":
    main()
