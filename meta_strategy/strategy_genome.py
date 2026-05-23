"""Strategy DNA / Evolutionary Optimization for the Meta-Strategy Permutation Engine.

v2.0 — Generative Strategy Synthesizer with full genomic encoding.

Inspired by the "Strategy DNA" research concept: each trading strategy
combination is encoded as a full genome with 4 chromosome groups:

  1. ENTRY LOGIC GENES — indicator type, threshold, confirmation rules
  2. EXIT LOGIC GENES — take-profit/stop-loss modes, trailing rules
  3. RISK GENES — position sizing, max drawdown kill, volatility lookback
  4. META GENES — regime preference, correlation tolerance, adaptation rate

Plus structural genes:
  - systems: binary mask of which signal sources are active
  - logic_type: combination logic (majority, unanimous, weighted, bayesian, etc.)
  - weights: per-system confidence weights [0.0, 1.0]
  - regime_gate: which market regime activates this combo
  - min_agreement: minimum systems that must agree
  - confluence_window: time window in minutes for signal matching

Key features:
  - Regime-aware mutation: tighter risk in volatile, longer lookbacks in trending
  - Indicator gene library: consensus, weighted_vote, cascade, reversal_confirm
  - Crossover with gene-level blending for risk parameters
  - Multi-objective fitness with calmar ratio and statistical significance

Fitness function:
  sharpe*20 + PF*15 + (30-maxDD)*1.5 + WR*50 + trades/20 + calmar*10

Usage:
  python -m meta_strategy.strategy_genome
"""
import copy
import json
import random
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import numpy as np

from meta_strategy.db import get_db, register_permutation, get_winners

# ── Constants ─────────────────────────────────────────────────────

KNOWN_SYSTEMS = [
    # Core signal engines
    "alpha_engine", "claws_of_doom", "crypto_ml_edge", "mercury2",
    "regime_terminal", "social_predict", "goldmine", "stocks_comp",
    # ML Battleground systems
    "ml_bg_a", "ml_bg_b", "ml_bg_c", "ml_bg_d", "ml_bg_e", "ml_bg_ensemble",
    # KIMI systems (both current and legacy)
    "kimi_rotc", "kimi", "kimi_feb17",
    # Signal/breakout engines
    "signal_engine", "breakout_a", "breakout_b", "breakout_c",
    # ML/prediction systems
    "ensemble", "ml_crypto_pred", "claude_gainer", "crypto_gainer",
    # Cross-system and meta
    "incubator_fwd", "quantum_fusion", "fc_crypto_pro",
    "cross_agg", "predictions", "baby_bundle_top",
]

# Normalize system name aliases (different IDs that refer to same system)
SYSTEM_ALIASES = {
    "kimi": "kimi_rotc",
    "ml_bg_ensemble": "ensemble",
}

LOGIC_TYPES = [
    "majority", "unanimous", "weighted", "cascade",
    "inverse", "consensus_plus_inverse", "evolved",
    "bayesian", "dempster_shafer", "regime_aware",
]

REGIME_GATES = [
    "bull", "bear", "sideways", "all",
    "extreme_fear", "fear", "greed", "extreme_greed",
    "high_vol", "low_vol",
]

CONFLUENCE_WINDOWS = [15, 30, 60, 120, 240, 480, 1440]  # minutes

DATA_DIR = Path(__file__).parent / "data"
EVOLVED_PATH = DATA_DIR / "evolved_genomes.json"


def normalize_system_name(name: str) -> str:
    """Resolve system name aliases to canonical form."""
    return SYSTEM_ALIASES.get(name, name)

# ── Indicator Gene Library (entry/exit logic building blocks) ────

ENTRY_INDICATOR_GENES = [
    # Original entry genes
    {"type": "consensus", "threshold": 0.6, "desc": "N systems agree above threshold"},
    {"type": "weighted_vote", "threshold": 0.5, "desc": "Confidence-weighted majority"},
    {"type": "cascade", "timeout_bars": 4, "desc": "Primary confirms, then secondary within timeout"},
    {"type": "reversal_confirm", "lookback": 3, "desc": "Signal + price reversal pattern"},
    {"type": "momentum_filter", "period": 14, "threshold": 0.0, "desc": "Only trade with momentum"},
    {"type": "volume_confirm", "mult": 1.5, "desc": "Require above-average volume"},
    {"type": "divergence_check", "period": 14, "desc": "RSI/price divergence confirmation"},
    {"type": "regime_filter", "allowed": ["bull", "sideways"], "desc": "Only trade in specified regimes"},
    # ML Confidence gates — lets evolution discover ML-mode signals outperform heuristic
    {"type": "ml_confidence_gate", "min_ml_score": 0.65, "require_ml_mode": True,
     "desc": "Only fire when ML system confidence exceeds threshold"},
    {"type": "ml_ensemble_gate", "min_models_agree": 2, "min_avg_score": 0.6,
     "desc": "Require multiple ML models to agree above threshold"},
    # On-chain data gates — exchange flow, MVRV, NVT
    {"type": "onchain_netflow_gate", "max_netflow_btc": 0, "desc": "Only long when exchange netflow negative (accumulation)"},
    {"type": "onchain_mvrv_gate", "max_mvrv_z": 3.0, "min_mvrv_z": -0.5,
     "desc": "Block longs when MVRV overvalued, block shorts when undervalued"},
    {"type": "onchain_composite_gate", "min_score": 0.6,
     "desc": "Require on-chain composite score (MVRV+Vol+F&G+Whale) above threshold"},
    # Funding rate gates — perp market structure signals
    {"type": "funding_rate_gate", "max_funding_pct": 0.01, "min_funding_pct": -0.01,
     "desc": "Gate based on current funding rate — block overleveraged direction"},
    {"type": "funding_divergence_gate", "lookback_hours": 48,
     "desc": "Detect funding rate divergence from price trend"},
    # Fear & Greed gates
    {"type": "fear_greed_gate", "min_fg": 0, "max_fg": 100,
     "desc": "Only trade within specified Fear & Greed range"},
    {"type": "extreme_sentiment_gate", "extreme_fear_max": 15, "extreme_greed_min": 85,
     "desc": "Contrarian gate — only fires at sentiment extremes"},
    # Cross-asset gates
    {"type": "btc_dominance_gate", "min_dom": 40.0, "max_dom": 65.0,
     "desc": "Gate altcoin trades based on BTC dominance range"},
    {"type": "cross_asset_correlation_gate", "asset": "SPX", "max_corr": 0.8,
     "desc": "Only trade when BTC-SPX correlation is below threshold"},
    {"type": "vix_gate", "max_vix": 30.0,
     "desc": "Block new longs above VIX threshold — panic mode"},
    # Session/time-of-day gates
    {"type": "session_gate", "sessions": ["london", "newyork"],
     "desc": "Only trade during specified market sessions"},
    {"type": "hour_range_gate", "start_hour_utc": 8, "end_hour_utc": 20,
     "desc": "Only trade within specified UTC hour range"},
    # Social/sentiment gates
    {"type": "social_sentiment_gate", "min_score": 0.6,
     "desc": "Require social sentiment score above threshold"},
    {"type": "whale_activity_gate", "min_whale_score": 0.5,
     "desc": "Only trade when whale accumulation signal is active"},
    # Volatility regime gates
    {"type": "atr_percentile_gate", "min_pct": 30, "max_pct": 85,
     "desc": "Trade only in moderate volatility range (ATR percentile)"},
    {"type": "dvol_gate", "max_dvol": 80.0,
     "desc": "Block trades when crypto implied vol (DVOL) is extreme"},
    # Liquidation data gates
    {"type": "liquidation_cascade_gate", "min_liq_usd": 50_000_000,
     "desc": "Contrarian long after large liquidation cascade"},
]

EXIT_INDICATOR_GENES = [
    {"type": "fixed_tp_sl", "tp_pct": 0.05, "sl_pct": 0.03},
    {"type": "trailing_stop", "trail_pct": 0.02, "activation_pct": 0.03},
    {"type": "time_exit", "max_bars": 48, "desc": "Exit after N bars regardless"},
    {"type": "signal_exit", "desc": "Exit when opposing signal fires"},
    {"type": "volatility_exit", "atr_mult": 2.0, "desc": "Exit at N*ATR from entry"},
    # New exit genes
    {"type": "partial_tp", "tp1_pct": 0.03, "tp1_close_pct": 0.5, "tp2_pct": 0.06,
     "desc": "Partial take-profit: close 50% at TP1, rest at TP2"},
    {"type": "regime_change_exit", "desc": "Exit when detected market regime changes"},
    {"type": "ml_confidence_exit", "min_hold_confidence": 0.4,
     "desc": "Exit when ML hold confidence drops below threshold"},
]

# ── Genome dataclass ──────────────────────────────────────────────


@dataclass
class Genome:
    """A single strategy chromosome — full genomic encoding.

    Chromosome groups:
      1. Structural genes: systems, logic_type, weights, regime_gate, etc.
      2. Entry logic genes: indicator rules for signal generation
      3. Exit logic genes: how to close positions
      4. Risk genes: position sizing and drawdown controls
      5. Meta genes: adaptation parameters and correlation tolerance
    """

    # ── Structural genes ──
    systems: list[int]             # binary mask, len == len(KNOWN_SYSTEMS)
    logic_type: str                # one of LOGIC_TYPES
    weights: list[float]           # per-system weight [0.0, 1.0], same length as KNOWN_SYSTEMS
    regime_gate: str               # one of REGIME_GATES
    min_agreement: int             # 1..len(active systems)
    confluence_window: int         # minutes

    # ── Entry logic genes ──
    entry_genes: list = field(default_factory=lambda: [
        {"type": "consensus", "threshold": 0.6}
    ])

    # ── Exit logic genes ──
    exit_genes: list = field(default_factory=lambda: [
        {"type": "fixed_tp_sl", "tp_pct": 0.05, "sl_pct": 0.03}
    ])

    # ── Risk genes ──
    risk_genes: dict = field(default_factory=lambda: {
        "position_size_pct": 0.02,      # 2% per trade
        "sizing_mode": "fixed",          # fixed | kelly | half_kelly | volatility_scaled
        "max_drawdown_kill": 0.20,       # kill at 20% DD
        "max_correlated_positions": 3,   # max positions with >0.7 correlation
        "volatility_lookback": 20,       # bars for vol calculation
        "max_portfolio_heat": 0.10,      # max total portfolio risk (sum of open position risks)
        "drawdown_throttle": True,       # reduce sizing during drawdowns
    })

    # ── Meta genes ──
    meta_genes: dict = field(default_factory=lambda: {
        "regime_preference": "any",      # any, trending, mean_reverting, volatile
        "correlation_tolerance": 0.7,    # max allowed inter-system correlation
        "adaptation_rate": 0.01,         # learning rate for online updates
        "decay_factor": 0.95,            # weight decay for older signals
        "ml_system_priority": 1.0,       # weight multiplier for ML-backed systems (0.5-2.0)
        "onchain_weight": 0.5,           # how much on-chain signals influence entry (0.0-1.0)
        "sentiment_weight": 0.3,         # how much F&G/social sentiment influences entry (0.0-1.0)
        "cross_asset_awareness": True,   # whether to consider BTC dom, DXY, VIX
    })

    # ── Tracking ──
    fitness: float = 0.0
    combo_id: str = ""
    generation: int = 0
    metrics: dict = field(default_factory=dict)
    dna_hash: str = ""                   # unique identifier for this exact genome

    @property
    def active_systems(self) -> list[str]:
        """Return list of system names that are enabled."""
        return [KNOWN_SYSTEMS[i] for i, on in enumerate(self.systems) if on]

    @property
    def active_count(self) -> int:
        return sum(self.systems)

    def build_combo_id(self) -> str:
        """Generate combo_id string compatible with permutations table."""
        names = sorted(self.active_systems)
        self.combo_id = "+".join(names) + f"|{self.logic_type}"
        return self.combo_id

    def compute_dna_hash(self) -> str:
        """Generate unique hash for this genome's complete configuration."""
        import hashlib
        dna_string = json.dumps({
            "systems": self.systems,
            "logic_type": self.logic_type,
            "weights": [round(w, 2) for w in self.weights],
            "regime_gate": self.regime_gate,
            "entry_genes": self.entry_genes,
            "exit_genes": self.exit_genes,
            "risk_genes": self.risk_genes,
            "meta_genes": self.meta_genes,
        }, sort_keys=True)
        self.dna_hash = hashlib.md5(dna_string.encode()).hexdigest()[:12]
        return self.dna_hash

    def to_dict(self) -> dict:
        d = asdict(self)
        d["active_systems"] = self.active_systems
        d["dna_hash"] = self.compute_dna_hash()
        return d


# ── Random genome creation ────────────────────────────────────────


def random_genome(rng: np.random.Generator, generation: int = 0) -> Genome:
    """Create a random genome with 2-6 active systems and full chromosome set."""
    n = len(KNOWN_SYSTEMS)
    n_active = rng.integers(2, min(7, n + 1))
    mask = [0] * n
    for idx in rng.choice(n, size=n_active, replace=False):
        mask[idx] = 1

    weights = [round(float(rng.uniform(0.3, 1.0)), 2) if mask[i] else 0.0
               for i in range(n)]

    # Random entry logic genes (1-3 indicator genes)
    n_entry = int(rng.integers(1, 4))
    entry_genes = [
        copy.deepcopy(ENTRY_INDICATOR_GENES[int(rng.integers(0, len(ENTRY_INDICATOR_GENES)))])
        for _ in range(n_entry)
    ]

    # Random exit logic genes (1-2)
    n_exit = int(rng.integers(1, 3))
    exit_genes = [
        copy.deepcopy(EXIT_INDICATOR_GENES[int(rng.integers(0, len(EXIT_INDICATOR_GENES)))])
        for _ in range(n_exit)
    ]

    # Random risk genes
    risk_genes = {
        "position_size_pct": round(float(rng.uniform(0.01, 0.05)), 3),
        "max_drawdown_kill": round(float(rng.uniform(0.10, 0.30)), 2),
        "max_correlated_positions": int(rng.integers(1, 6)),
        "volatility_lookback": int(rng.choice([10, 14, 20, 30, 50])),
    }

    # Random meta genes
    meta_genes = {
        "regime_preference": str(rng.choice(["any", "trending", "mean_reverting", "volatile"])),
        "correlation_tolerance": round(float(rng.uniform(0.4, 0.9)), 2),
        "adaptation_rate": round(float(rng.uniform(0.005, 0.05)), 3),
        "decay_factor": round(float(rng.uniform(0.85, 0.99)), 2),
    }

    g = Genome(
        systems=mask,
        logic_type=str(rng.choice(LOGIC_TYPES)),
        weights=weights,
        regime_gate=str(rng.choice(REGIME_GATES)),
        min_agreement=int(rng.integers(1, n_active + 1)),
        confluence_window=int(rng.choice(CONFLUENCE_WINDOWS)),
        entry_genes=entry_genes,
        exit_genes=exit_genes,
        risk_genes=risk_genes,
        meta_genes=meta_genes,
        generation=generation,
    )
    g.build_combo_id()
    return g


# ── Seed from DB ──────────────────────────────────────────────────


def seed_from_db(conn, max_seeds: int = 50) -> list[Genome]:
    """Load existing winning permutations as seed genomes."""
    winners = get_winners(conn, min_sharpe=0.1, min_trades=3)
    genomes = []

    for row in winners[:max_seeds]:
        systems_list = json.loads(row["systems"]) if isinstance(row["systems"], str) else row["systems"]
        mask = [1 if s in systems_list else 0 for s in KNOWN_SYSTEMS]
        n_active = sum(mask)
        if n_active < 2:
            continue

        # Reconstruct weights (equal if not stored)
        weights = [round(1.0 / n_active, 2) if mask[i] else 0.0
                   for i in range(len(KNOWN_SYSTEMS))]

        g = Genome(
            systems=mask,
            logic_type=row.get("logic_type", "majority"),
            weights=weights,
            regime_gate="all",
            min_agreement=min(2, n_active),
            confluence_window=60,
            generation=0,
        )
        g.build_combo_id()
        g.metrics = {
            "sharpe": row.get("sharpe", 0),
            "profit_factor": row.get("profit_factor", 0),
            "max_drawdown_pct": row.get("max_drawdown_pct", 0),
            "win_rate": row.get("win_rate", 0),
            "total_trades": row.get("total_trades", 0),
            "p_value": row.get("p_value", 1.0),
        }
        g.fitness = compute_fitness(g.metrics)
        genomes.append(g)

    return genomes


# ── Fitness function ──────────────────────────────────────────────


def compute_fitness(metrics: dict) -> float:
    """Composite fitness score matching the permutation engine scoring.

    Formula:
      sharpe*20 + PF*15 + (30 - maxDD)*1.5 + WR*50 + trades/20 + calmar*10

    Penalties:
      - fewer than 5 trades: fitness * 0.3
      - statistical significance bonus if p < 0.05
    """
    sharpe = metrics.get("sharpe", 0)
    pf = metrics.get("profit_factor", 0)
    max_dd = metrics.get("max_drawdown_pct", 100)
    wr = metrics.get("win_rate", 0)
    trades = metrics.get("total_trades", 0)
    p_value = metrics.get("p_value", 1.0)

    # Calmar = sharpe / max_dd (avoid div/0)
    calmar = sharpe / max(max_dd, 0.01) if max_dd > 0 else 0

    score = (
        sharpe * 20
        + pf * 15
        + (30 - max_dd) * 1.5
        + wr * 50
        + trades / 20
        + calmar * 10
    )

    # Penalty for too few trades
    if trades < 5:
        score *= 0.3

    # Bonus for statistical significance
    if p_value < 0.05:
        score *= 1.25

    return round(score, 4)


# ── Genetic operations ────────────────────────────────────────────


def crossover(parent_a: Genome, parent_b: Genome, rng: np.random.Generator,
              generation: int) -> Genome:
    """Full genomic crossover: each chromosome group crossed independently.

    Structural genes: uniform per-position crossover
    Entry/exit genes: random selection from each parent's gene pool
    Risk genes: arithmetic blend with ±10% noise
    Meta genes: weighted average (better parent gets more weight)
    """
    n = len(KNOWN_SYSTEMS)

    # ── Structural genes ──

    # Systems mask: per-position coin flip
    child_mask = [
        parent_a.systems[i] if rng.random() < 0.5 else parent_b.systems[i]
        for i in range(n)
    ]
    if sum(child_mask) < 2:
        indices = list(range(n))
        rng.shuffle(indices)
        for idx in indices:
            if child_mask[idx] == 0:
                child_mask[idx] = 1
                if sum(child_mask) >= 2:
                    break

    # Weights: blend from both parents
    child_weights = [
        round((parent_a.weights[i] + parent_b.weights[i]) / 2, 2)
        if child_mask[i] else 0.0
        for i in range(n)
    ]

    logic = parent_a.logic_type if rng.random() < 0.5 else parent_b.logic_type
    regime = parent_a.regime_gate if rng.random() < 0.5 else parent_b.regime_gate
    min_ag = max(1, min((parent_a.min_agreement + parent_b.min_agreement) // 2,
                         sum(child_mask)))
    cw = parent_a.confluence_window if rng.random() < 0.5 else parent_b.confluence_window

    # ── Entry logic genes: pick from each parent's gene pool ──
    all_entry = parent_a.entry_genes + parent_b.entry_genes
    n_entry = max(1, min(len(all_entry), int(rng.integers(1, 4))))
    child_entry = [copy.deepcopy(all_entry[int(rng.integers(0, len(all_entry)))])
                   for _ in range(n_entry)]

    # ── Exit logic genes ──
    all_exit = parent_a.exit_genes + parent_b.exit_genes
    n_exit = max(1, min(len(all_exit), int(rng.integers(1, 3))))
    child_exit = [copy.deepcopy(all_exit[int(rng.integers(0, len(all_exit)))])
                  for _ in range(n_exit)]

    # ── Risk genes: arithmetic blend with noise ──
    child_risk = {}
    for key in parent_a.risk_genes:
        val_a = parent_a.risk_genes[key]
        val_b = parent_b.risk_genes[key]
        if isinstance(val_a, (int, float)):
            blended = (val_a + val_b) / 2 * float(rng.uniform(0.9, 1.1))
            child_risk[key] = type(val_a)(round(blended, 3) if isinstance(val_a, float) else int(blended))
        else:
            child_risk[key] = val_a if rng.random() < 0.5 else val_b

    # ── Meta genes: weighted average (fitter parent gets 60% weight) ──
    child_meta = {}
    better_parent = parent_a if parent_a.fitness >= parent_b.fitness else parent_b
    worse_parent = parent_b if parent_a.fitness >= parent_b.fitness else parent_a
    for key in parent_a.meta_genes:
        val_a = better_parent.meta_genes.get(key)
        val_b = worse_parent.meta_genes.get(key)
        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            child_meta[key] = round(val_a * 0.6 + val_b * 0.4, 3)
        else:
            child_meta[key] = val_a if rng.random() < 0.6 else val_b

    child = Genome(
        systems=child_mask,
        logic_type=logic,
        weights=child_weights,
        regime_gate=regime,
        min_agreement=min_ag,
        confluence_window=cw,
        entry_genes=child_entry,
        exit_genes=child_exit,
        risk_genes=child_risk,
        meta_genes=child_meta,
        generation=generation,
    )
    child.build_combo_id()
    return child


def mutate(genome: Genome, rng: np.random.Generator, mutation_rate: float = 0.15,
           market_regime: str = "unknown") -> Genome:
    """Apply regime-aware mutations to a genome.

    The research insight: mutation strategy should adapt to market conditions.
    In volatile markets, tighten risk genes. In trending markets, extend lookbacks.

    Possible mutations (each applied independently with mutation_rate probability):
      - Flip a random system on/off
      - Change logic type
      - Perturb a weight by +/-0.1
      - Change regime gate
      - Change min_agreement by +/-1
      - Change confluence window
      - Mutate entry/exit indicator genes
      - Regime-aware risk gene mutations
      - Meta gene adaptation
    """
    g = copy.deepcopy(genome)
    n = len(KNOWN_SYSTEMS)

    # ── Structural gene mutations ──

    # Flip a system
    if rng.random() < mutation_rate:
        idx = int(rng.integers(0, n))
        g.systems[idx] = 1 - g.systems[idx]
        if sum(g.systems) < 2:
            g.systems[idx] = 1
            off_indices = [i for i in range(n) if g.systems[i] == 0]
            if off_indices:
                g.systems[int(rng.choice(off_indices))] = 1

    # Change logic type
    if rng.random() < mutation_rate:
        g.logic_type = str(rng.choice(LOGIC_TYPES))

    # Perturb a weight
    if rng.random() < mutation_rate:
        active_indices = [i for i in range(n) if g.systems[i] == 1]
        if active_indices:
            idx = int(rng.choice(active_indices))
            delta = float(rng.uniform(-0.1, 0.1))
            g.weights[idx] = round(max(0.05, min(1.0, g.weights[idx] + delta)), 2)

    # Change regime gate
    if rng.random() < mutation_rate:
        g.regime_gate = str(rng.choice(REGIME_GATES))

    # Change min_agreement
    if rng.random() < mutation_rate:
        delta = int(rng.choice([-1, 1]))
        g.min_agreement = max(1, min(g.min_agreement + delta, sum(g.systems)))

    # Change confluence window
    if rng.random() < mutation_rate:
        g.confluence_window = int(rng.choice(CONFLUENCE_WINDOWS))

    # ── Entry logic gene mutations ──

    if rng.random() < mutation_rate * 0.5:
        # Add a new indicator gene (5% chance)
        if len(g.entry_genes) < 4:
            new_gene = copy.deepcopy(
                ENTRY_INDICATOR_GENES[int(rng.integers(0, len(ENTRY_INDICATOR_GENES)))]
            )
            g.entry_genes.append(new_gene)
        # Or modify threshold on existing gene
        elif g.entry_genes:
            gene = g.entry_genes[int(rng.integers(0, len(g.entry_genes)))]
            if "threshold" in gene:
                gene["threshold"] = round(
                    max(0.1, min(0.9, gene["threshold"] + float(rng.uniform(-0.1, 0.1)))),
                    2,
                )

    # Remove a redundant entry gene (3% chance, keep at least 1)
    if rng.random() < 0.03 and len(g.entry_genes) > 1:
        g.entry_genes.pop(int(rng.integers(0, len(g.entry_genes))))

    # ── Exit logic gene mutations ──

    if rng.random() < mutation_rate * 0.5:
        if g.exit_genes:
            gene = g.exit_genes[int(rng.integers(0, len(g.exit_genes)))]
            if "tp_pct" in gene:
                gene["tp_pct"] = round(
                    max(0.01, min(0.15, gene["tp_pct"] + float(rng.uniform(-0.01, 0.01)))),
                    3,
                )
            if "sl_pct" in gene:
                gene["sl_pct"] = round(
                    max(0.005, min(0.08, gene["sl_pct"] + float(rng.uniform(-0.005, 0.005)))),
                    3,
                )

    # ── Regime-aware risk gene mutations (KEY DNA CONCEPT) ──

    if rng.random() < mutation_rate:
        if market_regime == "volatile":
            # Tighten risk controls in volatile markets
            g.risk_genes["position_size_pct"] = round(
                g.risk_genes["position_size_pct"] * float(rng.uniform(0.6, 0.9)), 3
            )
            g.risk_genes["max_drawdown_kill"] = round(
                g.risk_genes["max_drawdown_kill"] * float(rng.uniform(0.7, 0.9)), 2
            )
        elif market_regime == "trending":
            # Extend lookbacks in trending markets
            g.risk_genes["volatility_lookback"] = int(
                g.risk_genes["volatility_lookback"] * float(rng.uniform(1.1, 1.4))
            )
        elif market_regime == "sideways":
            # Tighter TP/SL for mean reversion
            for gene in g.exit_genes:
                if "tp_pct" in gene:
                    gene["tp_pct"] = round(gene["tp_pct"] * float(rng.uniform(0.7, 0.95)), 3)
        else:
            # Default: small random perturbation
            g.risk_genes["position_size_pct"] = round(
                max(0.005, min(0.10, g.risk_genes["position_size_pct"]
                    + float(rng.uniform(-0.005, 0.005)))),
                3,
            )

    # ── Meta gene mutations ──

    if rng.random() < mutation_rate * 0.3:
        g.meta_genes["correlation_tolerance"] = round(
            max(0.3, min(0.95, g.meta_genes["correlation_tolerance"]
                + float(rng.uniform(-0.05, 0.05)))),
            2,
        )
        g.meta_genes["decay_factor"] = round(
            max(0.80, min(0.99, g.meta_genes["decay_factor"]
                + float(rng.uniform(-0.02, 0.02)))),
            2,
        )

    # ── Cleanup ──

    # Sync weights for newly inactive systems
    for i in range(n):
        if g.systems[i] == 0:
            g.weights[i] = 0.0
        elif g.weights[i] == 0.0:
            g.weights[i] = round(float(rng.uniform(0.3, 1.0)), 2)

    # Clamp risk genes
    g.risk_genes["position_size_pct"] = max(0.005, min(0.10, g.risk_genes["position_size_pct"]))
    g.risk_genes["max_drawdown_kill"] = max(0.05, min(0.50, g.risk_genes["max_drawdown_kill"]))
    g.risk_genes["volatility_lookback"] = max(5, min(100, g.risk_genes["volatility_lookback"]))
    g.risk_genes["max_correlated_positions"] = max(1, min(10, g.risk_genes["max_correlated_positions"]))

    g.build_combo_id()
    return g


def tournament_select(population: list[Genome], rng: np.random.Generator,
                      tournament_size: int = 5) -> Genome:
    """Select best genome from a random subset of the population."""
    indices = rng.choice(len(population), size=min(tournament_size, len(population)),
                         replace=False)
    candidates = [population[i] for i in indices]
    return max(candidates, key=lambda g: g.fitness)


# ── Fitness evaluation from DB ────────────────────────────────────


def evaluate_genome_from_db(conn, genome: Genome) -> float:
    """Look up metrics for this genome's combo_id in permutation_results.

    If the exact combo_id is not found, estimate fitness by averaging metrics
    of similar combos (same systems, different logic).
    """
    combo_id = genome.build_combo_id()

    # Direct match
    row = conn.execute("""
        SELECT sharpe, profit_factor, max_drawdown_pct, win_rate,
               total_trades, p_value
        FROM permutation_results
        WHERE combo_id = ?
        ORDER BY last_updated DESC LIMIT 1
    """, (combo_id,)).fetchone()

    if row:
        metrics = dict(row)
        genome.metrics = metrics
        genome.fitness = compute_fitness(metrics)
        return genome.fitness

    # Approximate: find combos sharing at least 70% of systems
    active = genome.active_systems
    if not active:
        genome.fitness = 0.0
        return 0.0

    all_results = conn.execute("""
        SELECT pr.sharpe, pr.profit_factor, pr.max_drawdown_pct,
               pr.win_rate, pr.total_trades, pr.p_value, p.systems
        FROM permutation_results pr
        JOIN permutations p ON p.combo_id = pr.combo_id
        WHERE pr.total_trades >= 3
    """).fetchall()

    if not all_results:
        # No data at all: assign baseline fitness from genome structure
        genome.metrics = _estimate_structural_fitness(genome)
        genome.fitness = compute_fitness(genome.metrics)
        return genome.fitness

    # Find similar combos by Jaccard similarity
    scores = []
    for r in all_results:
        rd = dict(r)
        try:
            other_sys = set(json.loads(rd["systems"]))
        except (json.JSONDecodeError, TypeError):
            continue
        active_set = set(active)
        jaccard = len(active_set & other_sys) / max(len(active_set | other_sys), 1)
        if jaccard >= 0.5:
            scores.append((jaccard, rd))

    if not scores:
        genome.metrics = _estimate_structural_fitness(genome)
        genome.fitness = compute_fitness(genome.metrics)
        return genome.fitness

    # Weighted average by Jaccard similarity
    total_w = sum(s[0] for s in scores)
    metrics = {}
    for key in ["sharpe", "profit_factor", "max_drawdown_pct", "win_rate",
                "total_trades", "p_value"]:
        metrics[key] = sum(s[0] * s[1].get(key, 0) for s in scores) / max(total_w, 1e-9)

    # Discount for being an approximation
    genome.metrics = metrics
    genome.fitness = compute_fitness(metrics) * 0.85
    return genome.fitness


def _estimate_structural_fitness(genome: Genome) -> dict:
    """Heuristic fitness estimate when no DB data exists.

    Rewards diversity (more systems), balanced weights, and moderate agreement.
    """
    n_active = genome.active_count
    if n_active < 2:
        return {"sharpe": 0, "profit_factor": 0, "max_drawdown_pct": 100,
                "win_rate": 0, "total_trades": 0, "p_value": 1.0}

    # More systems = potentially better diversification (diminishing returns)
    diversity_bonus = min(n_active / 6.0, 1.0)

    # Weight balance: prefer not all-same weights
    active_weights = [genome.weights[i] for i in range(len(KNOWN_SYSTEMS))
                      if genome.systems[i]]
    weight_std = float(np.std(active_weights)) if len(active_weights) > 1 else 0
    balance_score = min(weight_std * 5, 0.5)

    # Agreement ratio
    agreement_ratio = genome.min_agreement / max(n_active, 1)
    agreement_score = 1.0 - abs(agreement_ratio - 0.5) * 2  # best at 50%

    base_wr = 0.50 + diversity_bonus * 0.05 + balance_score * 0.02 + agreement_score * 0.03

    return {
        "sharpe": diversity_bonus * 0.8,
        "profit_factor": 1.0 + diversity_bonus * 0.3,
        "max_drawdown_pct": 15 + (1 - diversity_bonus) * 10,
        "win_rate": base_wr,
        "total_trades": 3,  # low count triggers penalty
        "p_value": 0.15,
    }


# ── Evolution engine ──────────────────────────────────────────────


class EvolutionEngine:
    """Evolutionary optimizer for strategy permutations."""

    def __init__(self, population_size: int = 100, seed: Optional[int] = None):
        self.population_size = population_size
        self.rng = np.random.default_rng(seed)
        self.population: list[Genome] = []
        self.best_per_generation: list[dict] = []
        self.conn = None

    def initialize(self) -> None:
        """Seed population from DB winners + random genomes."""
        self.conn = get_db()

        # Load existing winners
        seeds = seed_from_db(self.conn, max_seeds=self.population_size // 2)
        print(f"Seeded {len(seeds)} genomes from DB winners")

        self.population = seeds[:]

        # Fill remainder with random genomes
        while len(self.population) < self.population_size:
            self.population.append(random_genome(self.rng, generation=0))

        # Trim if over-seeded
        self.population = self.population[:self.population_size]

        # Evaluate all genomes
        for g in self.population:
            if g.fitness == 0.0:
                evaluate_genome_from_db(self.conn, g)

        self._sort_population()

    def evolve(self, generations: int = 50) -> list[Genome]:
        """Run the evolutionary loop.

        Each generation:
          1. Elitism: top 10% survive unchanged
          2. Tournament selection of parents
          3. Crossover to produce children
          4. Mutation of children
          5. Evaluate fitness
          6. Replace population (elites + children)
        """
        if not self.population:
            self.initialize()

        elite_count = max(2, self.population_size // 10)

        for gen in range(1, generations + 1):
            # Elitism: preserve top performers
            self._sort_population()
            elites = [copy.deepcopy(g) for g in self.population[:elite_count]]
            for e in elites:
                e.generation = gen

            # Breed new children
            children: list[Genome] = []
            target = self.population_size - elite_count

            while len(children) < target:
                parent_a = tournament_select(self.population, self.rng)
                parent_b = tournament_select(self.population, self.rng)

                # Avoid self-crossover
                attempts = 0
                while parent_b.combo_id == parent_a.combo_id and attempts < 5:
                    parent_b = tournament_select(self.population, self.rng)
                    attempts += 1

                child = crossover(parent_a, parent_b, self.rng, generation=gen)
                child = mutate(child, self.rng)
                children.append(child)

            # Evaluate children
            for child in children:
                evaluate_genome_from_db(self.conn, child)

            # New population = elites + children
            self.population = elites + children[:target]
            self._sort_population()

            best = self.population[0]
            self.best_per_generation.append({
                "generation": gen,
                "combo_id": best.combo_id,
                "fitness": best.fitness,
                "active_systems": best.active_systems,
                "logic_type": best.logic_type,
                "regime_gate": best.regime_gate,
            })

            if gen % 10 == 0 or gen == 1:
                avg_fit = sum(g.fitness for g in self.population) / len(self.population)
                print(f"  Gen {gen:3d} | best={best.fitness:8.2f} "
                      f"avg={avg_fit:7.2f} | {best.combo_id}")

        return self.population

    def top_n(self, n: int = 10) -> list[Genome]:
        """Return top N genomes by fitness."""
        self._sort_population()
        return self.population[:n]

    def save_evolved(self, path: Optional[Path] = None) -> Path:
        """Save top genomes to JSON."""
        out_path = path or EVOLVED_PATH
        out_path.parent.mkdir(parents=True, exist_ok=True)

        top = self.top_n(50)
        data = {
            "evolved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generations": len(self.best_per_generation),
            "population_size": self.population_size,
            "total_evaluated": self.population_size * max(len(self.best_per_generation), 1),
            "best_fitness": top[0].fitness if top else 0,
            "convergence": [g for g in self.best_per_generation],
            "top_genomes": [g.to_dict() for g in top],
        }

        out_path.write_text(json.dumps(data, indent=2, default=str))
        return out_path

    def write_winners_to_db(self, top_n: int = 20) -> int:
        """Register top evolved genomes back to permutations table."""
        if not self.conn:
            self.conn = get_db()

        count = 0
        for genome in self.top_n(top_n):
            if genome.active_count < 2:
                continue

            systems = genome.active_systems
            weights_dict = {KNOWN_SYSTEMS[i]: genome.weights[i]
                           for i in range(len(KNOWN_SYSTEMS))
                           if genome.systems[i]}

            combo_id = genome.build_combo_id()
            parameters = {
                "regime_gate": genome.regime_gate,
                "confluence_window": genome.confluence_window,
                "evolved_fitness": genome.fitness,
                "evolved_generation": genome.generation,
            }

            register_permutation(
                self.conn,
                combo_id=combo_id,
                systems=systems,
                logic_type="evolved",
                weights=weights_dict,
                min_agreement=genome.min_agreement,
                parameters=parameters,
            )
            count += 1

        print(f"Registered {count} evolved permutations to DB")
        return count

    def _sort_population(self) -> None:
        """Sort population by fitness, descending."""
        self.population.sort(key=lambda g: g.fitness, reverse=True)

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None


# ── Main ──────────────────────────────────────────────────────────


def main():
    """Run evolutionary optimization and print results."""
    print("=" * 70)
    print("Strategy Genome - Evolutionary Optimization Engine")
    print("=" * 70)

    engine = EvolutionEngine(population_size=100, seed=42)

    print("\n[1/4] Initializing population from DB + random genomes...")
    engine.initialize()
    print(f"  Population: {len(engine.population)} genomes")
    if engine.population:
        print(f"  Best seed fitness: {engine.population[0].fitness:.2f}")

    print("\n[2/4] Running evolution (50 generations)...")
    engine.evolve(generations=50)

    print("\n[3/4] Top 10 evolved genomes:")
    print("-" * 70)
    for i, genome in enumerate(engine.top_n(10), 1):
        systems_str = ", ".join(genome.active_systems[:4])
        if genome.active_count > 4:
            systems_str += f" +{genome.active_count - 4} more"
        print(f"  #{i:2d} | fitness={genome.fitness:8.2f} | "
              f"{genome.logic_type:20s} | regime={genome.regime_gate:8s} | "
              f"systems=[{systems_str}]")
        if genome.metrics:
            m = genome.metrics
            print(f"       sharpe={m.get('sharpe', 0):.2f} "
                  f"PF={m.get('profit_factor', 0):.2f} "
                  f"WR={m.get('win_rate', 0):.1%} "
                  f"DD={m.get('max_drawdown_pct', 0):.1f}% "
                  f"trades={m.get('total_trades', 0):.0f}")

    print("\n[4/4] Saving results...")
    out_path = engine.save_evolved()
    print(f"  Saved to: {out_path}")

    n_written = engine.write_winners_to_db(top_n=20)
    print(f"  Wrote {n_written} evolved combos to meta_strategy.db")

    engine.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
