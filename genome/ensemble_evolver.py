"""
Ensemble Coevolution Engine
============================
Evolves teams of strategies that vote together as an ensemble.

Unlike evolving individual strategies, this system optimizes:
1. Which strategies are in the ensemble (member selection)
2. How much weight each member gets (voting power)
3. How votes are combined (consensus mechanisms)

Key difference from standard evolution:
- Fitness is evaluated at the ENSEMBLE level, not individual
- Selection favors ensembles that make better collective decisions
- Crossover swaps members between ensembles
- Mutation changes weights and consensus rules

This finds synergistic combinations that no single strategy can achieve.
"""

import copy
import hashlib
import json
import logging
import random
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# Direct file import to bypass genome/__init__.py pandas issue
import importlib.util as _ilu
_gp_path = str(Path(__file__).resolve().parent / "genetic_programmer.py")
_spec = _ilu.spec_from_file_location("genetic_programmer", _gp_path)
_gp_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_gp_mod)
OHLCVData = _gp_mod.OHLCVData
compute_features = _gp_mod.compute_features
fetch_market_data = _gp_mod.fetch_market_data
GPStrategy = _gp_mod.GPStrategy
random_strategy = _gp_mod.random_strategy
create_bonus_strategies = _gp_mod.create_bonus_strategies

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENOME_DIR = Path(__file__).resolve().parent
DB_PATH = GENOME_DIR / "ensemble_evolver.db"
ENSEMBLE_OUTPUT = GENOME_DIR / "data" / "ensemble_active_picks.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("EnsembleEvolver")


# =============================================================================
# Ensemble Consensus Mechanisms
# =============================================================================

class ConsensusType(Enum):
    """Different ways to combine ensemble member votes."""
    MAJORITY = "majority"           # Simple majority vote
    WEIGHTED = "weighted"           # Confidence-weighted vote
    UNANIMOUS = "unanimous"         # All must agree
    CASCADE = "cascade"             # Tiered voting (primary + confirmation)
    BAYESIAN = "bayesian"           # Bayesian belief combination
    DEMPSTER = "dempster_shafer"    # Dempster-Shafer evidence theory


@dataclass
class EnsembleMember:
    """A strategy within an ensemble with its voting parameters."""
    strategy: GPStrategy
    weight: float = 1.0              # Voting weight
    veto_power: bool = False         # Can this member veto?
    confidence_threshold: float = 0.5  # Minimum confidence to vote
    specialization: Optional[str] = None  # Symbol/regime specialty
    
    def get_vote(self, symbol: str, features: Dict[str, np.ndarray], 
                 bar_idx: int) -> Tuple[str, float]:
        """
        Get this member's vote for a given bar.
        Returns: (direction, confidence)
        """
        # Evaluate buy/sell trees
        buy_signal = self.strategy.buy_tree.evaluate(features)
        sell_signal = self.strategy.sell_tree.evaluate(features)
        
        b = buy_signal[bar_idx]
        s = sell_signal[bar_idx]
        
        # Determine vote
        if b > self.strategy.buy_threshold and s < -abs(self.strategy.sell_threshold):
            # Conflicting signals - abstain
            return "ABSTAIN", 0.0
        elif b > self.strategy.buy_threshold:
            confidence = min(abs(b) / 2, 1.0)
            return "LONG", confidence
        elif s < -abs(self.strategy.sell_threshold):
            confidence = min(abs(s) / 2, 1.0)
            return "SHORT", confidence
        else:
            return "ABSTAIN", 0.0


@dataclass
class StrategyEnsemble:
    """A team of strategies that vote together."""
    ensemble_id: str
    name: str
    members: List[EnsembleMember]
    consensus_type: ConsensusType
    generation: int = 0
    
    # Dynamic parameters
    min_participation: float = 0.5   # Min % of members that must vote
    consensus_threshold: float = 0.6  # % agreement needed
    
    # Performance tracking
    fitness: Dict = field(default_factory=dict)
    parent_ensembles: List[str] = field(default_factory=list)
    mutation_history: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def get_collective_decision(self, symbol: str, features: Dict[str, np.ndarray],
                                bar_idx: int) -> Tuple[Optional[str], float]:
        """
        Get the ensemble's collective trading decision.
        Returns: (direction or None, collective_confidence)
        """
        votes = []
        vetoes = []
        
        for member in self.members:
            direction, confidence = member.get_vote(symbol, features, bar_idx)
            
            if direction == "ABSTAIN":
                continue
            
            if confidence < member.confidence_threshold:
                continue
            
            if member.veto_power and direction in ["LONG", "SHORT"]:
                vetoes.append((member, direction))
            
            votes.append({
                "direction": direction,
                "confidence": confidence,
                "weight": member.weight
            })
        
        # Check vetoes
        for veto_member, veto_dir in vetoes:
            # A veto blocks the opposite direction
            opposite = "SHORT" if veto_dir == "LONG" else "LONG"
            votes = [v for v in votes if v["direction"] != opposite]
        
        # Check participation
        participation = len(votes) / len(self.members) if self.members else 0
        if participation < self.min_participation:
            return None, 0.0
        
        # Apply consensus mechanism
        if self.consensus_type == ConsensusType.MAJORITY:
            return self._majority_consensus(votes)
        elif self.consensus_type == ConsensusType.WEIGHTED:
            return self._weighted_consensus(votes)
        elif self.consensus_type == ConsensusType.UNANIMOUS:
            return self._unanimous_consensus(votes)
        elif self.consensus_type == ConsensusType.CASCADE:
            return self._cascade_consensus(votes)
        elif self.consensus_type == ConsensusType.BAYESIAN:
            return self._bayesian_consensus(votes)
        else:
            return self._majority_consensus(votes)
    
    def _majority_consensus(self, votes: List[Dict]) -> Tuple[Optional[str], float]:
        """Simple majority vote."""
        if not votes:
            return None, 0.0
        
        long_votes = sum(v["weight"] for v in votes if v["direction"] == "LONG")
        short_votes = sum(v["weight"] for v in votes if v["direction"] == "SHORT")
        total = long_votes + short_votes
        
        if total == 0:
            return None, 0.0
        
        long_pct = long_votes / total
        
        if long_pct >= self.consensus_threshold:
            return "LONG", long_pct
        elif long_pct <= (1 - self.consensus_threshold):
            return "SHORT", 1 - long_pct
        else:
            return None, max(long_pct, 1 - long_pct)
    
    def _weighted_consensus(self, votes: List[Dict]) -> Tuple[Optional[str], float]:
        """Confidence-weighted voting."""
        if not votes:
            return None, 0.0
        
        long_score = sum(v["weight"] * v["confidence"] 
                        for v in votes if v["direction"] == "LONG")
        short_score = sum(v["weight"] * v["confidence"]
                         for v in votes if v["direction"] == "SHORT")
        
        total = long_score + short_score
        if total == 0:
            return None, 0.0
        
        long_ratio = long_score / total
        
        if long_ratio >= self.consensus_threshold:
            return "LONG", long_ratio
        elif long_ratio <= (1 - self.consensus_threshold):
            return "SHORT", 1 - long_ratio
        else:
            return None, max(long_ratio, 1 - long_ratio)
    
    def _unanimous_consensus(self, votes: List[Dict]) -> Tuple[Optional[str], float]:
        """All participating members must agree."""
        if not votes:
            return None, 0.0
        
        directions = set(v["direction"] for v in votes)
        if len(directions) == 1:
            direction = list(directions)[0]
            avg_conf = np.mean([v["confidence"] for v in votes])
            return direction, avg_conf
        return None, 0.0
    
    def _cascade_consensus(self, votes: List[Dict]) -> Tuple[Optional[str], float]:
        """Tiered: primary voters decide, secondary confirms."""
        # Sort by weight (primary = highest weight)
        sorted_votes = sorted(votes, key=lambda v: v["weight"], reverse=True)
        
        # Top 30% are primary
        n_primary = max(1, int(len(sorted_votes) * 0.3))
        primary = sorted_votes[:n_primary]
        secondary = sorted_votes[n_primary:]
        
        # Primary decides
        long_primary = sum(v["weight"] for v in primary if v["direction"] == "LONG")
        short_primary = sum(v["weight"] for v in primary if v["direction"] == "SHORT")
        
        if long_primary > short_primary:
            primary_decision = "LONG"
        elif short_primary > long_primary:
            primary_decision = "SHORT"
        else:
            return None, 0.0
        
        # Secondary must not strongly oppose
        opp_direction = "SHORT" if primary_decision == "LONG" else "LONG"
        opp_strength = sum(v["weight"] for v in secondary if v["direction"] == opp_direction)
        total_secondary = sum(v["weight"] for v in secondary)
        
        if total_secondary > 0 and opp_strength / total_secondary > 0.5:
            return None, 0.0  # Secondary veto
        
        confidence = max(long_primary, short_primary) / (long_primary + short_primary)
        return primary_decision, confidence
    
    def _bayesian_consensus(self, votes: List[Dict]) -> Tuple[Optional[str], float]:
        """Combine beliefs using Bayesian updating."""
        if not votes:
            return None, 0.0
        
        # Start with neutral prior
        log_odds_long = 0.0
        
        for vote in votes:
            # Convert confidence to log-odds update
            conf = vote["confidence"] * vote["weight"]
            if vote["direction"] == "LONG":
                log_odds_long += np.log(conf / (1 - conf + 1e-8))
            else:
                log_odds_long -= np.log(conf / (1 - conf + 1e-8))
        
        # Convert back to probability
        prob_long = 1 / (1 + np.exp(-log_odds_long))
        
        if prob_long >= self.consensus_threshold:
            return "LONG", prob_long
        elif prob_long <= (1 - self.consensus_threshold):
            return "SHORT", 1 - prob_long
        else:
            return None, max(prob_long, 1 - prob_long)
    
    def to_dict(self) -> Dict:
        return {
            "ensemble_id": self.ensemble_id,
            "name": self.name,
            "generation": self.generation,
            "consensus_type": self.consensus_type.value,
            "min_participation": self.min_participation,
            "consensus_threshold": self.consensus_threshold,
            "member_count": len(self.members),
            "fitness": self.fitness,
            "parents": self.parent_ensembles,
            "created_at": self.created_at
        }


# =============================================================================
# Ensemble Backtester
# =============================================================================

def backtest_ensemble(
    ensemble: StrategyEnsemble,
    data: OHLCVData,
    initial_capital: float = 10000.0,
    commission: float = 0.001
) -> Dict[str, Any]:
    """Backtest an ensemble strategy."""
    
    if len(data) < 100:
        return {"win_rate": 0, "sharpe_ratio": 0, "total_trades": 0, "overall_fitness": 0}
    
    features = compute_features(data)
    closes = data.close
    
    capital = initial_capital
    position = None
    trades = []
    equity = [capital]
    
    # Use first member's risk parameters
    tp_pct = ensemble.members[0].strategy.tp_pct if ensemble.members else 0.04
    sl_pct = ensemble.members[0].strategy.sl_pct if ensemble.members else 0.02
    max_hold = ensemble.members[0].strategy.max_hold_bars if ensemble.members else 48
    
    for i in range(50, len(data)):
        price = closes[i]
        
        # Check exits if in position
        if position is not None:
            entry_idx, entry_price, direction = position
            hold_bars = i - entry_idx
            
            if direction == "LONG":
                pnl_pct = (price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - price) / entry_price
            
            exit_reason = None
            if pnl_pct >= tp_pct:
                exit_reason = "TP"
            elif pnl_pct <= -sl_pct:
                exit_reason = "SL"
            elif hold_bars >= max_hold:
                exit_reason = "TIME"
            
            # Check for signal-based exit (opposite signal)
            if not exit_reason:
                new_signal, conf = ensemble.get_collective_decision(
                    "SYMBOL", features, i
                )
                if new_signal and new_signal != direction and conf > 0.6:
                    exit_reason = "SIGNAL"
            
            if exit_reason:
                net_pnl = pnl_pct - commission * 2
                capital *= (1 + net_pnl)
                trades.append({
                    "entry_idx": int(entry_idx), "exit_idx": int(i),
                    "direction": direction, "pnl_pct": round(net_pnl * 100, 4),
                    "exit_reason": exit_reason,
                })
                position = None
        
        # Check for entry
        if position is None:
            signal, conf = ensemble.get_collective_decision("SYMBOL", features, i)
            if signal == "LONG" and conf > 0.5:
                position = (i, price, "LONG")
            elif signal == "SHORT" and conf > 0.5:
                position = (i, price, "SHORT")
        
        equity.append(capital)
    
    if len(trades) < 5:
        return {"win_rate": 0, "sharpe_ratio": 0, "total_trades": len(trades), 
                "overall_fitness": 0, "trades": []}
    
    # Calculate metrics
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    win_rate = len(wins) / len(trades)
    
    total_win = sum(t["pnl_pct"] for t in wins) if wins else 0
    total_loss = abs(sum(t["pnl_pct"] for t in losses)) if losses else 0
    profit_factor = total_win / (total_loss + 1e-8)
    
    eq = np.array(equity)
    returns = np.diff(eq) / (eq[:-1] + 1e-8)
    returns = returns[returns != 0]
    sharpe = (np.mean(returns) / (np.std(returns) + 1e-8)) * np.sqrt(252 * 24) if len(returns) > 10 else 0
    
    peak = np.maximum.accumulate(eq)
    dd = (peak - eq) / (peak + 1e-8)
    max_dd = float(np.max(dd)) * 100
    total_return = (capital - initial_capital) / initial_capital * 100
    
    fitness = (
        0.25 * min(sharpe / 3, 1.0) +
        0.25 * win_rate +
        0.20 * min(profit_factor / 3, 1.0) +
        0.15 * max(0, min(total_return / 50, 1.0)) +
        0.15 * max(0, 1 - max_dd / 30)
    )
    if len(trades) < 20:
        fitness *= (len(trades) / 20)
    
    return {
        "win_rate": round(win_rate, 4),
        "profit_factor": round(min(float(profit_factor), 99), 4),
        "sharpe_ratio": round(float(sharpe), 4),
        "max_drawdown_pct": round(max_dd, 4),
        "total_return_pct": round(total_return, 4),
        "total_trades": len(trades),
        "wins": len(wins), "losses": len(losses),
        "overall_fitness": round(fitness, 4),
        "trades": trades[-10:],
    }


# =============================================================================
# Ensemble Evolution Engine
# =============================================================================

class EnsembleEvolutionEngine:
    """
    Evolves ensembles of strategies using cooperative coevolution.
    
    Key insight: A mediocre strategy might be valuable if it provides
    diversity to an ensemble. Evolution optimizes the TEAM, not individuals.
    """
    
    def __init__(self,
                 population_size: int = 50,
                 generations: int = 30,
                 ensemble_size_range: Tuple[int, int] = (3, 8),
                 mutation_rate: float = 0.25,
                 crossover_rate: float = 0.60,
                 symbols: Optional[List[str]] = None):
        
        self.population_size = population_size
        self.generations = generations
        self.ensemble_size_range = ensemble_size_range
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        
        self.population: List[StrategyEnsemble] = []
        self.hall_of_fame: List[StrategyEnsemble] = []
        self.evolution_history: List[Dict] = []
        
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ensembles (
                ensemble_id TEXT PRIMARY KEY, name TEXT, generation INTEGER,
                consensus_type TEXT, member_count INTEGER,
                fitness_json TEXT, created_at TEXT, status TEXT DEFAULT 'EVOLVED'
            );
            CREATE TABLE IF NOT EXISTS ensemble_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, run_timestamp TEXT,
                generations INTEGER, population_size INTEGER,
                best_fitness REAL, avg_fitness REAL
            );
        """)
        conn.commit()
        conn.close()
    
    def _create_random_ensemble(self, generation: int = 0,
                                candidate_strategies: Optional[List[GPStrategy]] = None
                                ) -> StrategyEnsemble:
        """Create a random ensemble."""
        size = random.randint(*self.ensemble_size_range)
        
        members = []
        for i in range(size):
            if candidate_strategies and random.random() < 0.7:
                strategy = random.choice(candidate_strategies)
            else:
                strategy = random_strategy(generation=generation)
            
            members.append(EnsembleMember(
                strategy=strategy,
                weight=round(random.uniform(0.5, 2.0), 2),
                veto_power=random.random() < 0.1,
                confidence_threshold=round(random.uniform(0.3, 0.7), 2)
            ))
        
        eid = f"ens_{hashlib.md5(f'{datetime.now().timestamp()}_{random.random()}'.encode()).hexdigest()[:12]}"
        
        return StrategyEnsemble(
            ensemble_id=eid,
            name=f"Ensemble_G{generation}_{eid[-6:]}",
            members=members,
            consensus_type=random.choice(list(ConsensusType)),
            generation=generation,
            min_participation=round(random.uniform(0.3, 0.7), 2),
            consensus_threshold=round(random.uniform(0.5, 0.8), 2)
        )
    
    def _evaluate_ensemble(self, ensemble: StrategyEnsemble,
                          market_data: Dict[str, OHLCVData]) -> float:
        """Evaluate ensemble across all symbols."""
        all_results = {}
        
        for sym, data in market_data.items():
            try:
                result = backtest_ensemble(ensemble, data)
                all_results[sym] = result
            except Exception as e:
                logger.debug(f"Backtest error: {e}")
                all_results[sym] = {"overall_fitness": 0}
        
        avg_fitness = np.mean([r.get("overall_fitness", 0) for r in all_results.values()])
        ensemble.fitness = {
            "overall_fitness": round(avg_fitness, 4),
            "per_symbol": all_results
        }
        
        return avg_fitness
    
    def _tournament_select(self, scored: List[Tuple[StrategyEnsemble, float]], 
                          k: int = 3) -> StrategyEnsemble:
        """Tournament selection."""
        contenders = random.sample(scored, min(k, len(scored)))
        return max(contenders, key=lambda x: x[1])[0]
    
    def _crossover_ensembles(self, p1: StrategyEnsemble, p2: StrategyEnsemble,
                            generation: int) -> StrategyEnsemble:
        """Create child ensemble by mixing members."""
        # Mix members
        all_members = p1.members + p2.members
        
        # Select unique strategies
        seen_hashes = set()
        unique_members = []
        for m in all_members:
            h = m.strategy.dna_hash()
            if h not in seen_hashes:
                seen_hashes.add(h)
                unique_members.append(m)
        
        # Sample from combined pool
        target_size = random.randint(*self.ensemble_size_range)
        if len(unique_members) <= target_size:
            child_members = unique_members
        else:
            # Weight by fitness contribution (simplified: just random for now)
            child_members = random.sample(unique_members, target_size)
        
        # Average the weights for shared members
        for cm in child_members:
            p1_match = next((m for m in p1.members if m.strategy.dna_hash() == cm.strategy.dna_hash()), None)
            p2_match = next((m for m in p2.members if m.strategy.dna_hash() == cm.strategy.dna_hash()), None)
            
            if p1_match and p2_match:
                cm.weight = round((p1_match.weight + p2_match.weight) / 2, 2)
        
        eid = f"ens_{hashlib.md5(f'{datetime.now().timestamp()}_{random.random()}'.encode()).hexdigest()[:12]}"
        
        return StrategyEnsemble(
            ensemble_id=eid,
            name=f"EnsembleX_G{generation}_{eid[-6:]}",
            members=child_members,
            consensus_type=random.choice([p1.consensus_type, p2.consensus_type]),
            generation=generation,
            min_participation=round((p1.min_participation + p2.min_participation) / 2, 2),
            consensus_threshold=round((p1.consensus_threshold + p2.consensus_threshold) / 2, 2),
            parent_ensembles=[p1.ensemble_id, p2.ensemble_id],
            mutation_history=[f"crossover({p1.name}, {p2.name})"]
        )
    
    def _mutate_ensemble(self, ensemble: StrategyEnsemble, 
                        generation: int) -> StrategyEnsemble:
        """Mutate an ensemble."""
        child = copy.deepcopy(ensemble)
        child.generation = generation
        child.parent_ensembles = [ensemble.ensemble_id]
        
        mutations = []
        
        # Mutate weights
        if random.random() < 0.5:
            for m in child.members:
                if random.random() < self.mutation_rate:
                    m.weight = round(np.clip(m.weight + random.gauss(0, 0.3), 0.1, 5.0), 2)
            mutations.append("weight_perturb")
        
        # Add new member
        if random.random() < 0.3 and len(child.members) < self.ensemble_size_range[1]:
            new_strategy = random_strategy(generation=generation)
            child.members.append(EnsembleMember(
                strategy=new_strategy,
                weight=round(random.uniform(0.5, 2.0), 2)
            ))
            mutations.append("add_member")
        
        # Remove random member
        if random.random() < 0.2 and len(child.members) > self.ensemble_size_range[0]:
            child.members.pop(random.randint(0, len(child.members) - 1))
            mutations.append("remove_member")
        
        # Change consensus type
        if random.random() < 0.15:
            child.consensus_type = random.choice(list(ConsensusType))
            mutations.append("consensus_switch")
        
        # Perturb thresholds
        if random.random() < 0.3:
            child.consensus_threshold = round(np.clip(
                child.consensus_threshold + random.gauss(0, 0.1), 0.5, 0.95
            ), 2)
            mutations.append("threshold_perturb")
        
        eid = f"ens_{hashlib.md5(f'{datetime.now().timestamp()}_{random.random()}'.encode()).hexdigest()[:12]}"
        child.ensemble_id = eid
        child.name = f"EnsembleM_G{generation}_{eid[-6:]}"
        child.mutation_history = ensemble.mutation_history[-3:] + mutations
        
        return child
    
    def run_evolution(self, market_data: Dict[str, OHLCVData],
                     seed_strategies: Optional[List[GPStrategy]] = None
                     ) -> List[StrategyEnsemble]:
        """Run ensemble evolution."""
        logger.info("=" * 70)
        logger.info("ENSEMBLE COEVOLUTION ENGINE")
        logger.info(f"Population: {self.population_size} | Generations: {self.generations}")
        logger.info(f"Ensemble size: {self.ensemble_size_range}")
        logger.info("=" * 70)
        
        # Initialize population
        logger.info("\nInitializing population...")
        self.population = [
            self._create_random_ensemble(0, seed_strategies)
            for _ in range(self.population_size)
        ]
        
        best_overall = 0
        
        for gen in range(self.generations):
            # Evaluate
            scored = []
            for ens in self.population:
                fitness = self._evaluate_ensemble(ens, market_data)
                scored.append((ens, fitness))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            best_fit = scored[0][1]
            avg_fit = np.mean([s[1] for s in scored])
            
            # Update hall of fame
            for ens, f in scored[:5]:
                if f > 0.3 and not any(h.ensemble_id == ens.ensemble_id for h in self.hall_of_fame):
                    self.hall_of_fame.append(ens)
            
            if best_fit > best_overall:
                best_overall = best_fit
            
            self.evolution_history.append({
                "generation": gen,
                "best_fitness": round(best_fit, 4),
                "avg_fitness": round(avg_fit, 4),
                "best_ensemble": scored[0][0].name
            })
            
            logger.info(f"Gen {gen:3d} | Best: {best_fit:.4f} | Avg: {avg_fit:.4f} | "
                       f"Hall of Fame: {len(self.hall_of_fame)}")
            
            # Create next generation
            elite_count = max(2, int(self.population_size * 0.1))
            next_gen = [e for e, _ in scored[:elite_count]]
            
            while len(next_gen) < self.population_size:
                if random.random() < self.crossover_rate and len(scored) > 5:
                    p1 = self._tournament_select(scored)
                    p2 = self._tournament_select(scored)
                    child = self._crossover_ensembles(p1, p2, gen + 1)
                    if random.random() < self.mutation_rate:
                        child = self._mutate_ensemble(child, gen + 1)
                    next_gen.append(child)
                else:
                    parent = self._tournament_select(scored)
                    next_gen.append(self._mutate_ensemble(parent, gen + 1))
            
            self.population = next_gen
        
        # Final evaluation
        final_scored = []
        for ens in self.population:
            fitness = self._evaluate_ensemble(ens, market_data)
            final_scored.append((ens, fitness))
        
        final_scored.sort(key=lambda x: x[1], reverse=True)
        winners = [e for e, _ in final_scored[:10]]
        
        self._save_results(winners)
        
        return winners
    
    def _save_results(self, winners: List[StrategyEnsemble]):
        """Save results to DB and JSON."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Save to DB
        conn = sqlite3.connect(str(DB_PATH))
        for w in winners:
            conn.execute(
                """INSERT OR REPLACE INTO ensembles
                   (ensemble_id, name, generation, consensus_type, member_count,
                    fitness_json, created_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (w.ensemble_id, w.name, w.generation, w.consensus_type.value,
                 len(w.members), json.dumps(w.fitness), now,
                 "WINNER" if w.fitness.get("overall_fitness", 0) > 0.5 else "EVOLVED")
            )
        
        if winners:
            conn.execute(
                """INSERT INTO ensemble_runs
                   (run_timestamp, generations, population_size, best_fitness, avg_fitness)
                   VALUES (?, ?, ?, ?, ?)""",
                (now, self.generations, self.population_size,
                 winners[0].fitness.get("overall_fitness", 0),
                 np.mean([w.fitness.get("overall_fitness", 0) for w in winners]))
            )
        
        conn.commit()
        conn.close()
        
        # Save picks
        self._save_picks_json(winners)
    
    def _save_picks_json(self, winners: List[StrategyEnsemble]):
        """Export ensemble picks for audit dashboard."""
        now = datetime.now(timezone.utc).isoformat()
        picks = []
        
        for w in winners[:5]:
            per_symbol = w.fitness.get("per_symbol", {})
            for symbol, metrics in per_symbol.items():
                if metrics.get("overall_fitness", 0) < 0.3:
                    continue
                
                trades = metrics.get("trades", [])
                direction = trades[-1].get("direction", "LONG") if trades else "LONG"
                
                picks.append({
                    "symbol": symbol,
                    "direction": direction,
                    "confidence": min(metrics.get("overall_fitness", 0.5) * 1.2, 1.0),
                    "strategy": w.name,
                    "source_system": "ensemble_evolver",
                    "consensus_type": w.consensus_type.value,
                    "member_count": len(w.members),
                    "win_rate": metrics.get("win_rate", 0),
                    "sharpe_ratio": metrics.get("sharpe_ratio", 0),
                    "profit_factor": metrics.get("profit_factor", 0),
                    "timestamp": now
                })
        
        output = {
            "generated_at": now,
            "system": "ensemble_evolver",
            "version": "1.0.0",
            "total_picks": len(picks),
            "picks": picks
        }
        
        with open(str(ENSEMBLE_OUTPUT), "w") as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Saved {len(picks)} ensemble picks to {ENSEMBLE_OUTPUT}")


# =============================================================================
# Entry Point
# =============================================================================

def run_ensemble_evolution(symbols=None, population_size=40, generations=25):
    """Run ensemble coevolution."""
    symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    logger.info("Fetching market data...")
    market_data = fetch_market_data(symbols, limit=750)
    
    if not market_data:
        logger.error("No market data")
        return None
    
    # Create some seed strategies
    seed_strategies = [random_strategy(0) for _ in range(20)]
    seed_strategies.extend(create_bonus_strategies())
    
    engine = EnsembleEvolutionEngine(
        population_size=population_size,
        generations=generations,
        symbols=list(market_data.keys())
    )
    
    winners = engine.run_evolution(market_data, seed_strategies)
    
    print("\n" + "=" * 70)
    print("ENSEMBLE COEVOLUTION RESULTS")
    print("=" * 70)
    for i, w in enumerate(winners[:5], 1):
        f = w.fitness.get("overall_fitness", 0)
        print(f"  {i}. {w.name}")
        print(f"     Consensus: {w.consensus_type.value} | Members: {len(w.members)}")
        print(f"     Fitness: {f:.4f}")
        print(f"     Members:")
        for m in w.members[:3]:
            print(f"       - {m.strategy.name} (weight: {m.weight})")
        if len(w.members) > 3:
            print(f"       ... and {len(w.members) - 3} more")
    
    return winners


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ensemble Coevolution Engine")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT")
    parser.add_argument("--pop", type=int, default=40)
    parser.add_argument("--gens", type=int, default=25)
    args = parser.parse_args()
    
    symbols = [s.strip() for s in args.symbols.split(",")]
    run_ensemble_evolution(symbols, args.pop, args.gens)
