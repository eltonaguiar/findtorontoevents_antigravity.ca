#!/usr/bin/env python3
"""
Audit Ensemble Evolution Engine
===============================
New evolution style: Evolves optimal weights for aggregating picks from ALL audit sources.

Unlike DNA (param opt) and GP (formula invention), this meta-evolves ENSEMBLES across 40+ existing systems.

Genome: weight vector per source (softmax normalized).
Fitness: Weighted average historical performance proxy + current signal strength + diversity.
Output: Top ensembles' consensus picks for audit integration.

Run: python genome/audit_ensemble_evolver.py --pop 50 --gens 20
"""

import argparse
import json
import logging
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

# Logging setup
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'audit_ensemble_evolver.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AuditEnsembleEvolver')

ROOT = Path(__file__).parent.parent

# All audit sources from dashboard_generator.py (active_picks paths)
AUDIT_SOURCES = [
    ('alpha_engine', 'alpha_engine/data/active_picks.json', 'alpha_engine/data/closed_picks.json'),
    ('battleground', 'battleground/data/active_picks.json', 'battleground/data/closed_picks.json'),
    ('mercury2', 'mercury2/data/active_picks.json', 'mercury2/data/closed_picks.json'),
    ('paper_trading', 'paper_trading/data/active_picks.json', 'paper_trading/data/closed_picks.json'),
    ('ml_bg_system_a', 'ml_battleground/system_a_filter/data/active_picks.json', 'ml_battleground/system_a_filter/data/closed_picks.json'),
    ('ml_bg_system_b', 'ml_battleground/system_b_regime/data/active_picks.json', 'ml_battleground/system_b_regime/data/closed_picks.json'),
    ('ml_bg_system_c', 'ml_battleground/system_c_deeplearn/data/active_picks.json', 'ml_battleground/system_c_deeplearn/data/closed_picks.json'),
    ('ml_bg_system_d', 'ml_battleground/system_d_carry/data/active_picks.json', 'ml_battleground/system_d_carry/data/closed_picks.json'),
    ('ml_bg_system_e', 'ml_battleground/system_e_momentum/data/active_picks.json', 'ml_battleground/system_e_momentum/data/closed_picks.json'),
    ('ml_bg_system_f', 'ml_battleground/system_f_clawsofdoom/data/active_picks.json', 'ml_battleground/system_f_clawsofdoom/data/closed_picks.json'),
    ('ml_bg_ensemble', 'ml_battleground/ensemble_data/active_picks.json', 'ml_battleground/ensemble_data/closed_picks.json'),
    ('breakout_a_sr', 'breakout_arena/approach_a_sr_breakout/data/active_picks.json', 'breakout_arena/approach_a_sr_breakout/data/closed_picks.json'),
    ('breakout_b_ml', 'breakout_arena/approach_b_ml_breakout/data/active_picks.json', 'breakout_arena/approach_b_ml_breakout/data/closed_picks.json'),
    ('breakout_c_spike', 'breakout_arena/approach_c_spike_reverse/data/active_picks.json', 'breakout_arena/approach_c_spike_reverse/data/closed_picks.json'),
    ('crypto_signal_engine', 'crypto_signal_engine/data/active_picks.json', 'crypto_signal_engine/data/closed_picks.json'),
    ('coinglass', 'coinglass_strategies/data/active_picks.json', None),
    ('crypto_ml_edge', 'crypto_ml_edge/data/active_picks.json', None),
    ('rl_agent', 'rl_agent/data/active_picks.json', None),
    ('genome', 'genome/data/gp_active_picks.json', None),
    ('predictions', 'predictions/data/active_predictions.json', None),
    ('super_signals', 'cross_aggregation/data/super_signals.json', None),
    ('regime_terminal', 'regime_terminal/data/active_signals.json', None),
    ('ml_crypto_pred', 'ml_crypto_predictor/enhanced_models/live_picks/active_picks.json', None),
    ('riseoftheclaw', 'riseoftheclaw/data/active_picks.json', None),
    ('crypto_gainer_ml', 'crypto_gainer_ml/tracker/live_picks.json', None),
    ('abc_forward_a', 'ml_battleground/abc_forward_test/data/approach_a_picks.json', None),
    ('abc_forward_b', 'ml_battleground/abc_forward_test/data/approach_b_picks.json', None),
    ('abc_forward_c', 'ml_battleground/abc_forward_test/data/approach_c_picks.json', None),
    ('fc_crypto_pro', 'data/fc_crypto_pro_picks.json', None),
    ('aggregated_picks', 'data/aggregated_picks.json', None),
    ('signal_aggregator', 'signal_aggregator/data/master_picks_tracker.json', None),
    ('kimi_live_signals', 'KIMI_RISEOFTHECLAW/data/live_signals_now.json', None),
    ('kimi_signal_tracking', 'riseoftheclaw/data/signal_tracking.json', None),
    ('goldmine_unified', 'data/goldmine/unified_picks.json', None),
    ('incubator_gainer', 'incubator/agents/claude_code_01/data/gainer_scores_latest.json', None),
    ('stocks_competition', 'STOCKS/competition/forward_picks.json', None),
    ('stocks_crypto_comp', 'STOCKS/competition/competition-crypto.json', None),
    ('quan_engine', 'quan_engine/data/active_signals.json', None),
    ('alpha_engine_fast', 'alpha_engine/data/active_picks_fast.json', 'alpha_engine/data/closed_picks_fast.json'),
    ('genetic_programmer', 'genome/data/gp_active_picks.json', None),  # GP already listed as 'genome'
]

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'DOGEUSDT']  # Focus on majors

@dataclass
class SourceMetrics:
    hist_wr: float = 0.5
    hist_sharpe_proxy: float = 0.0
    recent_trades: int = 0

class AuditEnsembleEvolver:
    def __init__(self, population_size: int = 50, generations: int = 20, symbols: List[str] = None):
        self.population_size = population_size
        self.generations = generations
        self.symbols = symbols or SYMBOLS
        self.sources = [s[0] for s in AUDIT_SOURCES]
        self.num_sources = len(self.sources)
        self.active_picks: Dict[str, List[Dict]] = {}
        self.closed_picks: Dict[str, List[Dict]] = {}
        self.source_metrics: Dict[str, SourceMetrics] = {}
        self.population: List[np.ndarray] = []
        logger.info(f'Audit Ensemble Evolver: {self.num_sources} sources, pop={population_size}, gens={generations}')

    def load_data(self):
        '''Load active and closed picks from all sources.'''
        self.active_picks = {}
        self.closed_picks = {}
        for sys_name, active_path_rel, closed_path_rel in AUDIT_SOURCES:
            active_path = ROOT / active_path_rel
            data = self._safe_load_json(active_path)
            if data and 'picks' in data:
                self.active_picks[sys_name] = data['picks']
            else:
                self.active_picks[sys_name] = []

            if closed_path_rel:
                closed_path = ROOT / closed_path_rel
                closed_data = self._safe_load_json(closed_path)
                if closed_data and 'picks' in closed_data:
                    self.closed_picks[sys_name] = closed_data['picks'][-50:]  # Last 50 trades
                else:
                    self.closed_picks[sys_name] = []
            else:
                self.closed_picks[sys_name] = []

        self._compute_source_metrics()
        logger.info(f'Loaded data: {len(self.active_picks)} active sources, avg {np.mean([len(p) for p in self.active_picks.values()]):.1f} picks/source')

    def _safe_load_json(self, path: Path) -> Dict:
        try:
            if path.exists():
                return json.loads(path.read_text())
        except Exception as e:
            logger.debug(f'Failed to load {path}: {e}')
        return {}

    def _compute_source_metrics(self):
        '''Compute historical WR and Sharpe proxy from recent closed picks.'''
        for sys_name in self.sources:
            closed = self.closed_picks.get(sys_name, [])
            if not closed:
                self.source_metrics[sys_name] = SourceMetrics()
                continue

            pnl_pcts = [float(p.get('pnl_pct', 0)) for p in closed if p.get('pnl_pct')]
            if pnl_pcts:
                wr = sum(1 for p in pnl_pcts if p > 0) / len(pnl_pcts)
                sharpe_proxy = np.mean(pnl_pcts) / (np.std(pnl_pcts) + 1e-8)
            else:
                wr, sharpe_proxy = 0.5, 0.0

            self.source_metrics[sys_name] = SourceMetrics(wr, sharpe_proxy, len(pnl_pcts))

    def initialize_population(self):
        '''Random init population as logit vectors (for softmax).'''
        self.population = [np.random.normal(0, 1, self.num_sources) for _ in range(self.population_size)]

    def fitness(self, genome: np.ndarray) -> float:
        '''Fitness: weighted signal strength proxy + diversity.'''
        exp_g = np.exp(genome - np.max(genome))  # Numerically stable softmax
        weights = exp_g / exp_g.sum()  # Positive weights summing to 1
        total_fitness = 0.0

        # Per-symbol ensemble strength
        for sym in self.symbols:
            sym_signals = np.zeros(self.num_sources)
            for i, sys_name in enumerate(self.sources):
                picks = self.active_picks.get(sys_name, [])
                sym_picks = [p for p in picks if p.get('symbol') == sym]
                if sym_picks:
                    dirs = sum(1 if p.get('direction') == 'LONG' else -1 if p.get('direction') == 'SHORT' else 0 for p in sym_picks)
                    conf_avg = np.mean([float(p.get('confidence', 0.5)) for p in sym_picks])
                    hist_wr = self.source_metrics[sys_name].hist_wr
                    sym_signals[i] = dirs * conf_avg * hist_wr

            ensemble_strength = np.abs(np.dot(weights, sym_signals))
            total_fitness += ensemble_strength

        # Diversity penalty/reward: encourage broad usage
        diversity = 1 - np.std(weights)  # Higher if uniform
        total_fitness += diversity * 0.1 * len(self.symbols)

        # Concentration penalty: avoid over-reliance on few sources
        entropy = -np.sum(weights * np.log(weights + 1e-8))
        total_fitness += entropy * 0.05

        return total_fitness

    def select_parents(self, fits: np.ndarray, num_parents: int) -> List[Tuple[float, np.ndarray]]:
        '''Tournament selection.'''
        parents = []
        for _ in range(num_parents):
            i1, i2 = random.sample(range(self.population_size), 2)
            if fits[i1] > fits[i2]:
                parents.append((fits[i1], self.population[i1].copy()))
            else:
                parents.append((fits[i2], self.population[i2].copy()))
        return parents

    def crossover(self, parent1: np.ndarray, parent2: np.ndarray) -> np.ndarray:
        '''Single-point crossover.'''
        point = random.randint(1, self.num_sources - 1)
        child = np.concatenate([parent1[:point], parent2[point:]])
        return child

    def mutate(self, genome: np.ndarray, rate: float = 0.2) -> np.ndarray:
        '''Add Gaussian noise.'''
        noise = np.random.normal(0, 0.5, self.num_sources)
        mask = np.random.random(self.num_sources) < rate
        genome[mask] += noise[mask]
        return genome

    def evolve(self):
        '''Main evolution loop.'''
        self.load_data()
        self.initialize_population()

        stagnation = 0
        best_fitness = -np.inf
        history = []

        for gen in range(self.generations):
            fits = np.array([self.fitness(ind) for ind in self.population])
            max_fit = np.max(fits)
            avg_fit = np.mean(fits)
            history.append({'generation': gen, 'best_fitness': max_fit, 'avg_fitness': avg_fit})

            if max_fit > best_fitness:
                best_fitness = max_fit
                stagnation = 0
            else:
                stagnation += 1

            logger.info(f'Gen {gen:2d} | Best: {max_fit:.4f} | Avg: {avg_fit:.4f} | Stag: {stagnation}')

            # Elitism: keep top 10%
            elite_size = max(2, self.population_size // 10)
            elite_idx = np.argsort(fits)[-elite_size:]
            new_pop = [self.population[i].copy() for i in elite_idx]

            # Select parents, crossover, mutate
            num_offspring = self.population_size - elite_size
            parents = self.select_parents(fits, num_offspring * 2)
            while len(new_pop) < self.population_size:
                p1, g1 = random.choice(parents)
                p2, g2 = random.choice(parents)
                child = self.crossover(g1, g2)
                child = self.mutate(child, rate=0.15 + 0.1 * (stagnation / 5))
                new_pop.append(child)

            self.population = new_pop[:self.population_size]

        # Final top 10
        final_fits = np.array([self.fitness(ind) for ind in self.population])
        top_idx = np.argsort(final_fits)[-10:]
        winners = [(self.population[i], final_fits[i]) for i in top_idx]

        self._generate_picks(winners)
        self._save_results(history, winners)
        logger.info('Evolution complete. Picks saved to genome/data/ae_active_picks.json')

    def _generate_picks(self, winners: List[Tuple[np.ndarray, float]]):
        '''Generate consensus picks from top ensembles.'''
        picks = []
        source_idx = {src: i for i, src in enumerate(self.sources)}

        for sym in self.symbols:
            # Average weights from top 3 ensembles
            top_weights = np.mean([w[0] for w in winners[:3]], axis=0)
            exp_w = np.exp(top_weights - np.max(top_weights))
            weights = exp_w / exp_w.sum()

            sym_signals = np.zeros(self.num_sources)
            for i, sys_name in enumerate(self.sources):
                picks_sys = self.active_picks.get(sys_name, [])
                sym_picks = [p for p in picks_sys if p.get('symbol') == sym]
                if sym_picks:
                    dirs = sum(1 if p.get('direction') == 'LONG' else -1 if p.get('direction') == 'SHORT' else 0 for p in sym_picks)
                    conf_avg = np.mean([float(p.get('confidence', 0.5)) for p in sym_picks])
                    hist_wr = self.source_metrics[sys_name].hist_wr
                    sym_signals[i] = dirs * conf_avg * hist_wr * weights[i]

            ensemble_bias = np.sum(sym_signals)
            if abs(ensemble_bias) > 0.5:  # Threshold
                direction = 'LONG' if ensemble_bias > 0 else 'SHORT'
                conf = min(abs(ensemble_bias), 1.0)
                top_sources = [self.sources[i] for i in np.argsort(np.abs(sym_signals))[-3:]]
                picks.append({
                    'symbol': sym,
                    'direction': direction,
                    'confidence': conf,
                    'strategy': f'AuditEnsemble_{direction}',
                    'source_system': 'audit_ensemble',
                    'top_sources': top_sources,
                    'ensemble_bias': float(ensemble_bias),
                    'timestamp': datetime.utcnow().isoformat()
                })

        # Save 30 picks (top 6 per symbol x 5)
        picks.sort(key=lambda p: p['confidence'], reverse=True)
        top_picks = picks[:30]
        # Feed hygiene: strip zero-entry or resolved picks
        try:
            sys.path.insert(0, str(ROOT))
            from alpha_engine.feed_hygiene import sanitize_active_picks
            top_picks = sanitize_active_picks(top_picks)
        except Exception:
            top_picks = [p for p in top_picks if float(p.get('entry_price') or 0) > 0]
        output = {
            'total_picks': len(top_picks),
            'timestamp': datetime.utcnow().isoformat(),
            'top_ensemble_fitness': float(np.max([w[1] for w in winners])),
            'picks': top_picks
        }
        (ROOT / 'genome/data/ae_active_picks.json').write_text(json.dumps(output, indent=2))
        logger.info(f'Saved {len(top_picks)} ensemble picks')

    def _save_results(self, history: List[Dict], winners: List[Tuple]):
        log_path = Path(__file__).parent / 'ae_results' / 'evolution_log.json'
        log_path.parent.mkdir(exist_ok=True)
        results = {
            'run_timestamp': datetime.utcnow().isoformat(),
            'sources_count': self.num_sources,
            'history': history,
            'hall_of_fame': [{'weights': w[0].tolist(), 'fitness': float(w[1])} for w in winners]
        }
        log_path.write_text(json.dumps(results, indent=2))

def main():
    parser = argparse.ArgumentParser(description='Audit Ensemble Evolution')
    parser.add_argument('--pop', type=int, default=50, help='Population size')
    parser.add_argument('--gens', type=int, default=20, help='Generations')
    parser.add_argument('--symbols', nargs='*', default=SYMBOLS, help='Symbols')
    args = parser.parse_args()

    evolver = AuditEnsembleEvolver(args.pop, args.gens, args.symbols)
    evolver.evolve()

if __name__ == '__main__':
    main()