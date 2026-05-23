#!/usr/bin/env python3
"""
Strategy Genome Engine v1.0 — Genetic Algorithm for Trading Strategy Evolution

Inspired by: Elton's AI Research (Mercury Labs, KIMI Swarm, ChatGPT, Grok)

Core Concepts:
  1. StrategyDNA: Encode strategies as chromosomes (entry signals, regime gates, risk params)
  2. Crossover: Breed winning children from top-performing parents
  3. Mutation: Context-aware mutations based on market regime
  4. Phoenix: Revive failed strategies with conditional regime gates
  5. Walk-forward: Train/Validate/Test splits to prevent overfitting
  6. Tournament: Promote survivors, eliminate weak performers

Uses existing combinatory_backtester.py infrastructure:
  - 11 signal generators (7 failing + 4 winning)
  - 11 regime filters
  - Trade simulation with TP/SL/time exits
  - crypto_data.db (14 symbols, 1900+ hourly bars)

Usage:
    py -3.13 quant_lab/strategy_genome.py
    py -3.13 quant_lab/strategy_genome.py --generations 20 --population 40
    py -3.13 quant_lab/strategy_genome.py --mode phoenix
"""

import sqlite3
import json
import sys
import copy
import random
import hashlib
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "crypto_data.db"
GENOME_DB = ROOT / "quant_lab" / "genome_results" / "genome.db"
OUTPUT_DIR = ROOT / "quant_lab" / "genome_results"

# Import from combinatory_backtester
sys.path.insert(0, str(ROOT / "quant_lab"))
from combinatory_backtester import (
    rsi, ema, sma, atr, bollinger_bands, adx, hurst_exponent, volume_ratio,
    sig_monthly_seasonality, sig_fourier_cycle, sig_smart_money_fvg,
    sig_exchange_netflow, sig_price_touch_recurrence,
    sig_momentum_mean_rev_blend, sig_ict_fvg_selective,
    sig_autocorrelation, sig_multi_sigma_reversal,
    sig_hurst_regime, sig_volume_profile,
    simulate_trades, detect_regime, Trade
)


# =====================================================================
# Signal Registry — All available signal generators
# =====================================================================

SIGNAL_REGISTRY = {
    # Failing strategies (potential Phoenix candidates)
    "monthly_seasonality": {"func": "sig_monthly_seasonality", "category": "seasonal", "needs_month": True},
    "fourier_cycle":       {"func": "sig_fourier_cycle",       "category": "cycle"},
    "smart_money_fvg":     {"func": "sig_smart_money_fvg",     "category": "price_action"},
    "exchange_netflow":    {"func": "sig_exchange_netflow",     "category": "volume"},
    "price_touch_recurrence": {"func": "sig_price_touch_recurrence", "category": "support_resistance"},
    "momentum_mean_rev":   {"func": "sig_momentum_mean_rev_blend", "category": "momentum"},
    "ict_fvg_selective":   {"func": "sig_ict_fvg_selective",   "category": "price_action"},
    # Winning strategies
    "autocorrelation":     {"func": "sig_autocorrelation",     "category": "statistical"},
    "multi_sigma_reversal":{"func": "sig_multi_sigma_reversal","category": "mean_reversion"},
    "hurst_regime":        {"func": "sig_hurst_regime",        "category": "adaptive"},
    "volume_profile":      {"func": "sig_volume_profile",      "category": "volume"},
}

# Gate (regime filter) options
GATE_REGISTRY = {
    "no_filter":      {"desc": "No regime filter"},
    "crisis_only":    {"desc": "Only trade in crisis (DD>15%)"},
    "trending_only":  {"desc": "Only trade in trending markets"},
    "mean_rev_only":  {"desc": "Only trade in mean-reverting markets"},
    "high_vol_only":  {"desc": "Only trade in high volatility"},
    "low_vol_only":   {"desc": "Only trade in low volatility"},
    "not_crisis":     {"desc": "Exclude crisis periods"},
    "hurst_trending": {"desc": "Hurst > 0.60 (trending)"},
    "hurst_mr":       {"desc": "Hurst < 0.40 (mean-reverting)"},
    "strong_trend":   {"desc": "ADX > 30"},
    "weak_trend":     {"desc": "ADX < 20"},
}

# Combiner logic options
COMBINER_TYPES = ["majority", "unanimous", "any", "weighted", "conditional"]

# Exit overlay options
EXIT_OVERLAYS = {
    "standard":    {"tp_mult": 2.5, "sl_mult": 1.5, "max_hold": 48},
    "tight":       {"tp_mult": 1.5, "sl_mult": 1.0, "max_hold": 24},
    "wide":        {"tp_mult": 4.0, "sl_mult": 2.0, "max_hold": 72},
    "scalp":       {"tp_mult": 1.0, "sl_mult": 0.8, "max_hold": 12},
    "swing":       {"tp_mult": 5.0, "sl_mult": 2.5, "max_hold": 96},
}


# =====================================================================
# Strategy DNA — Genetic encoding of a trading strategy
# =====================================================================

@dataclass
class StrategyDNA:
    """Genomic encoding of a trading strategy."""
    # --- Entry chromosome ---
    signals: List[str] = field(default_factory=list)       # Signal IDs from SIGNAL_REGISTRY
    combiner: str = "majority"                              # How signals combine
    invert: List[bool] = field(default_factory=list)       # Per-signal inversion flag
    min_confidence: float = 0.5                             # Min agreement threshold

    # --- Gate chromosome ---
    gate: str = "no_filter"                                 # Regime filter
    secondary_gate: str = "no_filter"                       # Optional second gate (AND logic)

    # --- Risk chromosome ---
    tp_mult: float = 2.5          # TP = entry +/- tp_mult * ATR
    sl_mult: float = 1.5          # SL = entry -/+ sl_mult * ATR
    max_hold: int = 48            # Max bars before forced exit
    position_size: float = 0.1    # Fraction of capital per trade

    # --- Meta genes ---
    regime_preference: str = "any"
    symbol_specialist: str = ""   # Empty = generic; symbol = specialist
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    mutation_tag: str = ""
    origin: str = "seed"          # seed, crossover, mutation, phoenix

    def get_id(self) -> str:
        """Deterministic hash of this DNA configuration."""
        content = json.dumps({
            "signals": sorted(self.signals),
            "combiner": self.combiner,
            "invert": self.invert,
            "min_confidence": self.min_confidence,
            "gate": self.gate,
            "secondary_gate": self.secondary_gate,
            "tp_mult": round(self.tp_mult, 2),
            "sl_mult": round(self.sl_mult, 2),
            "max_hold": self.max_hold,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def get_name(self) -> str:
        """Human-readable name."""
        sigs = "+".join(s[:6] for s in self.signals)
        inv = "INV_" if any(self.invert) else ""
        gate_str = f"@{self.gate}" if self.gate != "no_filter" else ""
        return f"{inv}{sigs}_{self.combiner}{gate_str}_g{self.generation}"

    def to_dict(self) -> dict:
        return asdict(self)


# =====================================================================
# Fitness Evaluation — Backtest a StrategyDNA on price data
# =====================================================================

def precompute_regime_series(close, high, low, volume, interval=12):
    """Precompute regime detection as a series (avoiding O(N^2))."""
    n = len(close)
    regimes = [None] * n

    # Precompute indicators as full series
    atr_series = atr(high, low, close, 14)
    adx_series = adx(high, low, close, 14)
    roc_series = close.pct_change(20) * 100

    # Compute ATR ratio (current/60-bar mean)
    atr_60_mean = atr_series.rolling(60).mean()

    # Compute rolling peak and drawdown
    peak_30 = close.rolling(30).max()

    for i in range(200, n, interval):
        h = hurst_exponent(close[max(0, i-200):i+1])
        adx_val = float(adx_series.iloc[i]) if not np.isnan(adx_series.iloc[i]) else 20
        roc_20d = float(roc_series.iloc[i]) if not np.isnan(roc_series.iloc[i]) else 0
        atr_ratio = float(atr_series.iloc[i] / atr_60_mean.iloc[i]) if (
            not np.isnan(atr_60_mean.iloc[i]) and atr_60_mean.iloc[i] > 0) else 1.0
        dd = (float(close.iloc[i]) / float(peak_30.iloc[i]) - 1) * 100 if float(peak_30.iloc[i]) > 0 else 0

        if dd < -15:
            regime = "CRISIS"
        elif atr_ratio > 2.0:
            regime = "HIGH_VOLATILITY"
        elif atr_ratio < 0.5:
            regime = "LOW_VOLATILITY"
        elif h > 0.65 and adx_val > 25:
            regime = "TRENDING_UP" if roc_20d > 0 else "TRENDING_DOWN"
        elif h < 0.40:
            regime = "MEAN_REVERTING"
        else:
            regime = "NEUTRAL"

        vol_regime = "HIGH" if atr_ratio > 1.5 else "LOW" if atr_ratio < 0.7 else "NORMAL"

        regime_dict = {
            "regime": regime, "hurst": round(h, 4), "adx": round(adx_val, 2),
            "roc_20d": round(roc_20d, 2), "atr_ratio": round(atr_ratio, 4),
            "drawdown": round(dd, 2), "vol_regime": vol_regime,
        }

        # Forward-fill for interval bars
        for j in range(i, min(i + interval, n)):
            regimes[j] = regime_dict

    # Fill any remaining None gaps
    last_valid = {"regime": "NEUTRAL", "hurst": 0.5, "adx": 20, "roc_20d": 0,
                  "atr_ratio": 1.0, "drawdown": 0, "vol_regime": "NORMAL"}
    for i in range(n):
        if regimes[i] is None:
            regimes[i] = last_valid
        else:
            last_valid = regimes[i]

    return regimes


def apply_gate(signal: int, regime: dict, gate: str) -> int:
    """Apply a regime gate to a signal."""
    if gate == "no_filter":
        return signal
    elif gate == "crisis_only":
        return signal if regime["regime"] == "CRISIS" else 0
    elif gate == "trending_only":
        return signal if regime["regime"].startswith("TRENDING") else 0
    elif gate == "mean_rev_only":
        return signal if regime["regime"] == "MEAN_REVERTING" else 0
    elif gate == "high_vol_only":
        return signal if regime["vol_regime"] == "HIGH" else 0
    elif gate == "low_vol_only":
        return signal if regime["vol_regime"] == "LOW" else 0
    elif gate == "not_crisis":
        return signal if regime["regime"] != "CRISIS" else 0
    elif gate == "hurst_trending":
        return signal if regime["hurst"] > 0.60 else 0
    elif gate == "hurst_mr":
        return signal if regime["hurst"] < 0.40 else 0
    elif gate == "strong_trend":
        return signal if regime["adx"] > 30 else 0
    elif gate == "weak_trend":
        return signal if regime["adx"] < 20 else 0
    return signal


def generate_signal(sig_id: str, close, high, low, volume, i, month=1, invert=False) -> int:
    """Generate a signal from a registered strategy at bar i."""
    func_map = {
        "monthly_seasonality": lambda: sig_monthly_seasonality(close, high, low, volume, i, month),
        "fourier_cycle": lambda: sig_fourier_cycle(close, high, low, volume, i),
        "smart_money_fvg": lambda: sig_smart_money_fvg(close, high, low, volume, i),
        "exchange_netflow": lambda: sig_exchange_netflow(close, high, low, volume, i),
        "price_touch_recurrence": lambda: sig_price_touch_recurrence(close, high, low, volume, i),
        "momentum_mean_rev": lambda: sig_momentum_mean_rev_blend(close, high, low, volume, i),
        "ict_fvg_selective": lambda: sig_ict_fvg_selective(close, high, low, volume, i),
        "autocorrelation": lambda: sig_autocorrelation(close, high, low, volume, i),
        "multi_sigma_reversal": lambda: sig_multi_sigma_reversal(close, high, low, volume, i),
        "hurst_regime": lambda: sig_hurst_regime(close, high, low, volume, i),
        "volume_profile": lambda: sig_volume_profile(close, high, low, volume, i),
    }
    if sig_id not in func_map:
        return 0
    sig = func_map[sig_id]()
    if invert:
        sig = -sig
    return sig


def combine_signals(votes: List[int], combiner: str, min_confidence: float = 0.5) -> int:
    """Combine multiple signal votes into a single decision."""
    if not votes:
        return 0
    non_zero = [v for v in votes if v != 0]
    if not non_zero:
        return 0

    if combiner == "unanimous":
        # All must agree on same direction
        if all(v > 0 for v in non_zero):
            return 1
        elif all(v < 0 for v in non_zero):
            return -1
        return 0

    elif combiner == "any":
        # First non-zero signal wins
        return non_zero[0]

    elif combiner == "majority":
        bulls = sum(1 for v in votes if v > 0)
        bears = sum(1 for v in votes if v < 0)
        threshold = len(votes) * min_confidence
        if bulls >= threshold:
            return 1
        elif bears >= threshold:
            return -1
        return 0

    elif combiner == "weighted":
        # Simple weighted sum (equal weights for now)
        score = sum(votes) / len(votes)
        if score > min_confidence:
            return 1
        elif score < -min_confidence:
            return -1
        return 0

    elif combiner == "conditional":
        # First signal is primary, rest are confirmations
        primary = votes[0]
        if primary == 0:
            return 0
        confirmers = votes[1:]
        confirms = sum(1 for v in confirmers if v == primary)
        if confirms >= len(confirmers) * 0.5:
            return primary
        return 0

    return 0


def precompute_all_signals(close, high, low, volume, timestamps) -> Dict[str, np.ndarray]:
    """Precompute all 11 signal series once per symbol. Major optimization."""
    n = len(close)
    signal_cache = {}

    for sig_id in SIGNAL_REGISTRY:
        series = np.zeros(n, dtype=int)
        for i in range(200, n):
            try:
                ts = pd.Timestamp(timestamps.iloc[i])
                month = ts.month
            except Exception:
                month = 1
            series[i] = generate_signal(sig_id, close, high, low, volume, i, month, False)
        signal_cache[sig_id] = series
        print(f"    Precomputed {sig_id}: {np.count_nonzero(series)} non-zero signals")

    return signal_cache


def evaluate_dna(dna: StrategyDNA, close, high, low, volume, timestamps,
                 regimes, symbol: str, signal_cache: Dict[str, np.ndarray] = None) -> Dict:
    """Backtest a StrategyDNA and return performance metrics."""
    n = len(close)
    signals = np.zeros(n, dtype=int)

    for i in range(200, n):
        # Get individual signal votes from cache or compute
        votes = []
        for idx, sig_id in enumerate(dna.signals):
            inv = dna.invert[idx] if idx < len(dna.invert) else False
            if signal_cache and sig_id in signal_cache:
                vote = int(signal_cache[sig_id][i]) if i < len(signal_cache[sig_id]) else 0
                if inv:
                    vote = -vote
            else:
                try:
                    ts = pd.Timestamp(timestamps.iloc[i])
                    month = ts.month
                except Exception:
                    month = 1
                vote = generate_signal(sig_id, close, high, low, volume, i, month, inv)
            votes.append(vote)

        # Combine votes
        raw_signal = combine_signals(votes, dna.combiner, dna.min_confidence)

        # Apply regime gates
        regime = regimes[i] if i < len(regimes) else regimes[-1]
        gated = apply_gate(raw_signal, regime, dna.gate)
        if dna.secondary_gate != "no_filter":
            gated = apply_gate(gated, regime, dna.secondary_gate)

        signals[i] = gated

    # Simulate trades
    trades = simulate_trades(
        close, high, low, volume, timestamps,
        signals.tolist(), symbol,
        dna.get_name(), dna.get_id(),
        tp_mult=dna.tp_mult, sl_mult=dna.sl_mult,
        max_hold=dna.max_hold
    )

    return compute_fitness(trades, dna)


def compute_fitness(trades: List[Trade], dna: StrategyDNA) -> Dict:
    """Compute fitness metrics from a list of trades."""
    if not trades:
        return {
            "dna_id": dna.get_id(), "name": dna.get_name(),
            "trades": 0, "win_rate": 0, "total_pnl": 0, "sharpe": 0,
            "max_dd": 0, "profit_factor": 0, "expectancy": 0,
            "fitness_score": -999, "avg_pnl": 0, "avg_bars": 0,
        }

    pnls = [t.pnl_pct for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / len(pnls) if pnls else 0
    total_pnl = sum(pnls)
    avg_pnl = np.mean(pnls)
    std_pnl = np.std(pnls) if len(pnls) > 1 else 1
    sharpe = (avg_pnl / std_pnl * np.sqrt(252)) if std_pnl > 0 else 0

    # Max drawdown
    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    max_dd = abs(float(np.min(dd))) if len(dd) > 0 else 0

    # Profit factor
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.001
    pf = gross_profit / gross_loss

    # Expectancy
    avg_win = np.mean(wins) if wins else 0
    avg_loss = abs(np.mean(losses)) if losses else 0.001
    expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss

    avg_bars = np.mean([t.bars_held for t in trades])

    # Composite fitness score (matches Grok's Gold tier criteria)
    # Penalize low trade count heavily
    trade_penalty = 0 if len(pnls) >= 20 else -5 * (20 - len(pnls))
    overfit_penalty = 0
    if len(pnls) < 10:
        overfit_penalty = -10

    fitness = (
        0.30 * min(sharpe, 10) +           # Cap Sharpe contribution
        0.20 * (win_rate * 100 - 50) / 10 + # Win rate above 50%
        0.20 * (1 - min(max_dd / 30, 1)) * 5 + # DD below 30%
        0.15 * min(pf, 5) +                 # Profit factor
        0.15 * min(expectancy * 10, 5) +     # Expectancy
        trade_penalty / 10 +
        overfit_penalty / 10
    )

    return {
        "dna_id": dna.get_id(),
        "name": dna.get_name(),
        "trades": len(pnls),
        "win_rate": round(win_rate * 100, 2),
        "total_pnl": round(total_pnl, 4),
        "sharpe": round(sharpe, 4),
        "max_dd": round(max_dd, 4),
        "profit_factor": round(pf, 4),
        "expectancy": round(expectancy, 4),
        "fitness_score": round(fitness, 4),
        "avg_pnl": round(avg_pnl, 4),
        "avg_bars": round(avg_bars, 1),
    }


# =====================================================================
# Seed Population — Create initial strategies
# =====================================================================

def create_seed_population(size: int = 30) -> List[StrategyDNA]:
    """Create initial population from existing strategies + random combos."""
    population = []

    # 1. Solo strategies (11 base strategies)
    all_signals = list(SIGNAL_REGISTRY.keys())
    for sig in all_signals:
        dna = StrategyDNA(
            signals=[sig], combiner="any", invert=[False],
            gate="no_filter", origin="seed"
        )
        population.append(dna)

    # 2. Solo inverted (failing strategies only)
    failing = ["monthly_seasonality", "fourier_cycle", "smart_money_fvg",
               "exchange_netflow", "price_touch_recurrence",
               "momentum_mean_rev", "ict_fvg_selective"]
    for sig in failing:
        dna = StrategyDNA(
            signals=[sig], combiner="any", invert=[True],
            gate="no_filter", origin="seed", mutation_tag="inverted"
        )
        population.append(dna)

    # 3. Top combo from combinatory backtester: winners + crisis gate
    dna = StrategyDNA(
        signals=["autocorrelation", "multi_sigma_reversal", "hurst_regime", "volume_profile"],
        combiner="majority", invert=[False]*4,
        gate="crisis_only", secondary_gate="hurst_mr",
        origin="seed", mutation_tag="proven_ensemble"
    )
    population.append(dna)

    # 4. Phoenix combos: failing + winning with regime gates
    gates = ["crisis_only", "mean_rev_only", "low_vol_only", "trending_only"]
    for fail_sig in failing[:4]:
        gate = random.choice(gates)
        winner = random.choice(["autocorrelation", "hurst_regime", "volume_profile"])
        dna = StrategyDNA(
            signals=[fail_sig, winner],
            combiner="conditional",
            invert=[True, False],  # Invert failing, keep winner
            gate=gate,
            origin="phoenix",
            mutation_tag=f"phoenix_{fail_sig}"
        )
        population.append(dna)

    # 5. Random combos to fill to target size
    all_gates = list(GATE_REGISTRY.keys())
    all_combiners = COMBINER_TYPES
    while len(population) < size:
        n_signals = random.randint(2, 4)
        chosen_sigs = random.sample(all_signals, n_signals)
        inverts = [random.random() < 0.3 for _ in chosen_sigs]  # 30% chance to invert
        dna = StrategyDNA(
            signals=chosen_sigs,
            combiner=random.choice(all_combiners),
            invert=inverts,
            min_confidence=random.choice([0.3, 0.5, 0.6, 0.7]),
            gate=random.choice(all_gates),
            tp_mult=random.choice([1.5, 2.0, 2.5, 3.0, 4.0]),
            sl_mult=random.choice([1.0, 1.5, 2.0]),
            max_hold=random.choice([24, 36, 48, 72]),
            origin="random"
        )
        population.append(dna)

    return population[:size]


# =====================================================================
# Genetic Operators — Crossover, Mutation, Selection
# =====================================================================

def crossover(parent_a: StrategyDNA, parent_b: StrategyDNA, gen: int) -> StrategyDNA:
    """Breed two parents into a child via uniform crossover."""
    child = StrategyDNA()
    child.generation = gen
    child.parent_ids = [parent_a.get_id(), parent_b.get_id()]
    child.origin = "crossover"

    # Signal chromosome: merge unique signals from both parents
    all_sigs = list(set(parent_a.signals + parent_b.signals))
    if len(all_sigs) < 2:
        # Add a random signal to ensure diversity
        extra = [s for s in SIGNAL_REGISTRY if s not in all_sigs]
        if extra:
            all_sigs.append(random.choice(extra))
    n_sigs = random.randint(min(2, len(all_sigs)), min(4, len(all_sigs)))
    child.signals = random.sample(all_sigs, n_sigs)

    # Inversion: inherit from whichever parent had the signal
    child.invert = []
    for sig in child.signals:
        if sig in parent_a.signals:
            idx = parent_a.signals.index(sig)
            inv = parent_a.invert[idx] if idx < len(parent_a.invert) else False
        elif sig in parent_b.signals:
            idx = parent_b.signals.index(sig)
            inv = parent_b.invert[idx] if idx < len(parent_b.invert) else False
        else:
            inv = False
        child.invert.append(inv)

    # Combiner: randomly pick from parents
    child.combiner = random.choice([parent_a.combiner, parent_b.combiner])
    child.min_confidence = random.choice([parent_a.min_confidence, parent_b.min_confidence])

    # Gate: randomly pick from parents
    child.gate = random.choice([parent_a.gate, parent_b.gate])
    child.secondary_gate = random.choice([parent_a.secondary_gate, parent_b.secondary_gate])

    # Risk: blend
    child.tp_mult = round((parent_a.tp_mult + parent_b.tp_mult) / 2 * random.uniform(0.9, 1.1), 2)
    child.sl_mult = round((parent_a.sl_mult + parent_b.sl_mult) / 2 * random.uniform(0.9, 1.1), 2)
    child.max_hold = int((parent_a.max_hold + parent_b.max_hold) / 2)

    # Clamp values
    child.tp_mult = max(0.5, min(6.0, child.tp_mult))
    child.sl_mult = max(0.3, min(4.0, child.sl_mult))
    child.max_hold = max(6, min(120, child.max_hold))

    return child


def mutate(dna: StrategyDNA, gen: int, regime_hint: str = "any") -> StrategyDNA:
    """Context-aware mutation of a strategy DNA."""
    mutant = copy.deepcopy(dna)
    mutant.generation = gen
    mutant.parent_ids = [dna.get_id()]
    mutant.origin = "mutation"

    # Pick a random mutation type
    mutation = random.choice([
        "add_signal", "remove_signal", "flip_invert",
        "change_gate", "change_combiner", "tweak_risk",
        "add_secondary_gate", "regime_adapt"
    ])

    all_sigs = list(SIGNAL_REGISTRY.keys())
    all_gates = list(GATE_REGISTRY.keys())

    if mutation == "add_signal" and len(mutant.signals) < 5:
        available = [s for s in all_sigs if s not in mutant.signals]
        if available:
            new_sig = random.choice(available)
            mutant.signals.append(new_sig)
            mutant.invert.append(random.random() < 0.3)
            mutant.mutation_tag = f"+{new_sig[:6]}"

    elif mutation == "remove_signal" and len(mutant.signals) > 1:
        idx = random.randrange(len(mutant.signals))
        removed = mutant.signals.pop(idx)
        if idx < len(mutant.invert):
            mutant.invert.pop(idx)
        mutant.mutation_tag = f"-{removed[:6]}"

    elif mutation == "flip_invert":
        if mutant.invert:
            idx = random.randrange(len(mutant.invert))
            mutant.invert[idx] = not mutant.invert[idx]
            mutant.mutation_tag = f"flip_{mutant.signals[idx][:6]}"

    elif mutation == "change_gate":
        mutant.gate = random.choice(all_gates)
        mutant.mutation_tag = f"gate={mutant.gate[:8]}"

    elif mutation == "change_combiner":
        mutant.combiner = random.choice(COMBINER_TYPES)
        mutant.mutation_tag = f"comb={mutant.combiner[:6]}"

    elif mutation == "tweak_risk":
        which = random.choice(["tp", "sl", "hold"])
        if which == "tp":
            mutant.tp_mult = round(mutant.tp_mult * random.uniform(0.7, 1.3), 2)
            mutant.tp_mult = max(0.5, min(6.0, mutant.tp_mult))
        elif which == "sl":
            mutant.sl_mult = round(mutant.sl_mult * random.uniform(0.7, 1.3), 2)
            mutant.sl_mult = max(0.3, min(4.0, mutant.sl_mult))
        else:
            mutant.max_hold = int(mutant.max_hold * random.uniform(0.7, 1.3))
            mutant.max_hold = max(6, min(120, mutant.max_hold))
        mutant.mutation_tag = f"risk_{which}"

    elif mutation == "add_secondary_gate":
        mutant.secondary_gate = random.choice(all_gates)
        mutant.mutation_tag = f"+gate2={mutant.secondary_gate[:8]}"

    elif mutation == "regime_adapt":
        # Context-aware: adapt to regime hint
        if regime_hint == "volatile":
            mutant.sl_mult = round(mutant.sl_mult * 0.8, 2)
            mutant.tp_mult = round(mutant.tp_mult * 1.2, 2)
            mutant.gate = "high_vol_only"
        elif regime_hint == "trending":
            mutant.gate = "trending_only"
            mutant.max_hold = min(120, int(mutant.max_hold * 1.3))
        elif regime_hint == "mean_reverting":
            mutant.gate = "mean_rev_only"
            mutant.tp_mult = round(mutant.tp_mult * 0.8, 2)
        mutant.mutation_tag = f"regime_{regime_hint[:6]}"

    return mutant


def select_parents(population: List[StrategyDNA], fitnesses: List[Dict],
                   n_parents: int = 10) -> List[Tuple[StrategyDNA, Dict]]:
    """Tournament selection: pick the best from random subsets."""
    paired = list(zip(population, fitnesses))
    paired.sort(key=lambda x: x[1].get("fitness_score", -999), reverse=True)

    # Elitism: always include top 2
    selected = paired[:2]

    # Tournament for the rest
    while len(selected) < n_parents and len(paired) > 2:
        tournament = random.sample(paired[2:], min(3, len(paired) - 2))
        winner = max(tournament, key=lambda x: x[1].get("fitness_score", -999))
        if winner not in selected:
            selected.append(winner)

    return selected


# =====================================================================
# Phoenix Analyzer — Revive failed strategies
# =====================================================================

def phoenix_analysis(population: List[StrategyDNA], fitnesses: List[Dict],
                     gen: int) -> List[StrategyDNA]:
    """
    Find strategies that failed overall but worked in specific regimes.
    Create conditional Phoenix variants.
    """
    phoenix_children = []
    paired = list(zip(population, fitnesses))

    # Find failures (fitness < 0 or WR < 40%)
    failures = [(dna, f) for dna, f in paired
                if f.get("fitness_score", 0) < 0 and f.get("trades", 0) >= 5]

    # Find winners (fitness > 2)
    winners = [(dna, f) for dna, f in paired
               if f.get("fitness_score", 0) > 2 and f.get("trades", 0) >= 10]

    if not winners:
        return []

    for fail_dna, fail_fit in failures[:5]:  # Top 5 failures only
        # Try combining each failure with each regime gate + a winner
        for gate in ["crisis_only", "mean_rev_only", "low_vol_only", "hurst_mr", "trending_only"]:
            # Phoenix: failed signal (inverted) + winner + regime gate
            for win_dna, win_fit in winners[:3]:
                phoenix = StrategyDNA(
                    signals=fail_dna.signals + win_dna.signals[:2],
                    combiner="conditional",
                    invert=[not inv for inv in fail_dna.invert] + [False] * min(2, len(win_dna.signals)),
                    min_confidence=0.5,
                    gate=gate,
                    tp_mult=win_dna.tp_mult,
                    sl_mult=win_dna.sl_mult,
                    max_hold=win_dna.max_hold,
                    generation=gen,
                    parent_ids=[fail_dna.get_id(), win_dna.get_id()],
                    origin="phoenix",
                    mutation_tag=f"phoenix_{fail_dna.signals[0][:6]}+{win_dna.signals[0][:6]}@{gate[:8]}"
                )
                phoenix_children.append(phoenix)

    # Limit to avoid explosion
    random.shuffle(phoenix_children)
    return phoenix_children[:15]


# =====================================================================
# Walk-Forward Validation
# =====================================================================

def walk_forward_evaluate(dna: StrategyDNA, close, high, low, volume,
                          timestamps, symbol: str,
                          train_pct=0.5, val_pct=0.25) -> Dict:
    """
    Walk-forward evaluation: Train → Validate → Test.
    Only accept if consistent across all three periods.
    """
    n = len(close)
    train_end = int(n * train_pct)
    val_end = int(n * (train_pct + val_pct))

    # Precompute regimes for full series
    regimes = precompute_regime_series(close, high, low, volume)

    # Full period evaluation
    full_result = evaluate_dna(dna, close, high, low, volume, timestamps, regimes, symbol)

    # Train period
    train_result = evaluate_dna(
        dna, close[:train_end], high[:train_end], low[:train_end],
        volume[:train_end], timestamps[:train_end],
        regimes[:train_end], symbol
    )

    # Validation period
    val_result = evaluate_dna(
        dna, close[train_end:val_end], high[train_end:val_end],
        low[train_end:val_end], volume[train_end:val_end],
        timestamps[train_end:val_end],
        regimes[train_end:val_end], symbol
    )

    # Test period (out-of-sample)
    test_result = evaluate_dna(
        dna, close[val_end:], high[val_end:], low[val_end:],
        volume[val_end:], timestamps[val_end:],
        regimes[val_end:], symbol
    )

    # Consistency score
    sharpes = [train_result["sharpe"], val_result["sharpe"], test_result["sharpe"]]
    valid_sharpes = [s for s in sharpes if s != 0]
    if valid_sharpes and max(valid_sharpes) > 0:
        consistency = min(valid_sharpes) / (max(valid_sharpes) + 0.001)
    else:
        consistency = 0

    full_result["train_sharpe"] = train_result["sharpe"]
    full_result["val_sharpe"] = val_result["sharpe"]
    full_result["test_sharpe"] = test_result["sharpe"]
    full_result["consistency"] = round(consistency, 4)
    full_result["train_trades"] = train_result["trades"]
    full_result["val_trades"] = val_result["trades"]
    full_result["test_trades"] = test_result["trades"]

    # Adjust fitness for consistency
    if consistency < 0.3 and full_result["trades"] > 10:
        full_result["fitness_score"] *= 0.5  # Penalize inconsistent strategies
    if test_result["sharpe"] < 0:
        full_result["fitness_score"] *= 0.3  # Heavy penalty for OOS failure

    return full_result


# =====================================================================
# Evolution Engine — Main GA Loop
# =====================================================================

def evolve(symbols: List[str] = None, generations: int = 10,
           pop_size: int = 30, elite_keep: int = 5,
           crossover_rate: float = 0.5, mutation_rate: float = 0.3,
           phoenix_rate: float = 0.2) -> Dict:
    """
    Main evolution loop.
    Returns the top strategies found across all generations.
    """
    if symbols is None:
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "XRP/USDT"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load price data
    print(f"\n{'='*70}")
    print(f"  STRATEGY GENOME ENGINE v1.0")
    print(f"  Symbols: {', '.join(symbols)}")
    print(f"  Generations: {generations} | Population: {pop_size}")
    print(f"{'='*70}\n")

    data = {}
    conn = sqlite3.connect(str(DB_PATH))
    for sym in symbols:
        try:
            df = pd.read_sql(
                "SELECT timestamp, open, high, low, close, volume FROM klines "
                "WHERE pair = ? ORDER BY timestamp",
                conn, params=(sym,)
            )
            if len(df) < 300:
                print(f"  SKIP {sym}: only {len(df)} bars")
                continue
            data[sym] = df
            print(f"  Loaded {sym}: {len(df)} bars")
        except Exception as e:
            print(f"  SKIP {sym}: {e}")
    conn.close()

    if not data:
        print("ERROR: No data loaded!")
        return {}

    # Precompute regimes AND signals per symbol (major optimization)
    print("\n  Precomputing regime series + signal caches...")
    regime_cache = {}
    signal_caches = {}
    for sym, df in data.items():
        close = df["close"].astype(float)
        high_s = df["high"].astype(float)
        low_s = df["low"].astype(float)
        vol_s = df["volume"].astype(float)
        ts = df["timestamp"]
        print(f"  [{sym}] Computing regimes...")
        regime_cache[sym] = precompute_regime_series(close, high_s, low_s, vol_s)
        print(f"  [{sym}] Computing all 11 signal series...")
        signal_caches[sym] = precompute_all_signals(close, high_s, low_s, vol_s, ts)

    # Create initial population
    population = create_seed_population(pop_size)
    print(f"\n  Seed population: {len(population)} strategies")

    all_results = []
    best_ever = {"fitness_score": -999}
    best_ever_dna = None

    for gen in range(generations):
        print(f"\n--- Generation {gen+1}/{generations} ---")

        # Evaluate all strategies across all symbols
        gen_fitnesses = []
        for idx, dna in enumerate(population):
            dna.generation = gen

            # Aggregate fitness across symbols
            sym_results = []
            for sym, df in data.items():
                if dna.symbol_specialist and dna.symbol_specialist != sym:
                    continue
                close = df["close"].astype(float)
                high_s = df["high"].astype(float)
                low_s = df["low"].astype(float)
                vol_s = df["volume"].astype(float)
                ts = df["timestamp"]
                regimes = regime_cache[sym]
                sig_cache = signal_caches.get(sym)

                result = evaluate_dna(dna, close, high_s, low_s, vol_s, ts, regimes, sym, sig_cache)
                result["symbol"] = sym
                sym_results.append(result)

            # Aggregate: average fitness across symbols
            if sym_results:
                agg = {
                    "dna_id": dna.get_id(),
                    "name": dna.get_name(),
                    "generation": gen,
                    "origin": dna.origin,
                    "mutation_tag": dna.mutation_tag,
                    "signals": dna.signals,
                    "gate": dna.gate,
                    "combiner": dna.combiner,
                    "trades": sum(r["trades"] for r in sym_results),
                    "win_rate": round(np.mean([r["win_rate"] for r in sym_results if r["trades"] > 0] or [0]), 2),
                    "total_pnl": round(sum(r["total_pnl"] for r in sym_results), 4),
                    "sharpe": round(np.mean([r["sharpe"] for r in sym_results if r["trades"] > 0] or [0]), 4),
                    "max_dd": round(max(r["max_dd"] for r in sym_results) if sym_results else 0, 4),
                    "fitness_score": round(np.mean([r["fitness_score"] for r in sym_results]), 4),
                    "symbols_tested": len(sym_results),
                    "per_symbol": sym_results,
                }
            else:
                agg = {"dna_id": dna.get_id(), "fitness_score": -999, "trades": 0}

            gen_fitnesses.append(agg)

            # Track best ever
            if agg.get("fitness_score", -999) > best_ever.get("fitness_score", -999):
                best_ever = agg
                best_ever_dna = copy.deepcopy(dna)

        # Sort by fitness
        gen_fitnesses.sort(key=lambda x: x.get("fitness_score", -999), reverse=True)

        # Report top 5
        print(f"  Top 5 this generation:")
        for i, f in enumerate(gen_fitnesses[:5]):
            print(f"    {i+1}. {f.get('name','?')[:50]:50s}  "
                  f"Fitness={f.get('fitness_score',0):7.3f}  "
                  f"WR={f.get('win_rate',0):5.1f}%  "
                  f"Sharpe={f.get('sharpe',0):6.2f}  "
                  f"PnL={f.get('total_pnl',0):8.2f}  "
                  f"Trades={f.get('trades',0):4d}")

        all_results.extend(gen_fitnesses)

        # --- Create next generation ---
        if gen < generations - 1:
            next_pop = []

            # Elitism: keep top performers
            paired = list(zip(population, gen_fitnesses))
            paired.sort(key=lambda x: x[1].get("fitness_score", -999), reverse=True)
            for dna, _ in paired[:elite_keep]:
                next_pop.append(copy.deepcopy(dna))

            # Crossover
            parents = select_parents(population, gen_fitnesses, n_parents=10)
            n_crossover = int(pop_size * crossover_rate)
            for _ in range(n_crossover):
                if len(parents) >= 2:
                    p1, p2 = random.sample(parents, 2)
                    child = crossover(p1[0], p2[0], gen + 1)
                    next_pop.append(child)

            # Mutation
            n_mutation = int(pop_size * mutation_rate)
            for _ in range(n_mutation):
                base = random.choice(parents)[0]
                regime_hint = random.choice(["any", "volatile", "trending", "mean_reverting"])
                mutant = mutate(base, gen + 1, regime_hint)
                next_pop.append(mutant)

            # Phoenix revival
            n_phoenix = int(pop_size * phoenix_rate)
            phoenix_children = phoenix_analysis(population, gen_fitnesses, gen + 1)
            next_pop.extend(phoenix_children[:n_phoenix])

            # Fill remaining with random
            while len(next_pop) < pop_size:
                random_dna = create_seed_population(1)[0]
                random_dna.generation = gen + 1
                random_dna.origin = "immigrant"
                next_pop.append(random_dna)

            population = next_pop[:pop_size]

    # ─── Final Results ───
    print(f"\n{'='*70}")
    print(f"  EVOLUTION COMPLETE")
    print(f"{'='*70}")

    # Deduplicate and sort all results
    seen = set()
    unique_results = []
    for r in all_results:
        rid = r.get("dna_id", "")
        if rid not in seen:
            seen.add(rid)
            unique_results.append(r)
    unique_results.sort(key=lambda x: x.get("fitness_score", -999), reverse=True)

    # Print top 20
    print(f"\n  TOP 20 STRATEGIES (across all generations):")
    print(f"  {'#':>3}  {'Name':50s}  {'Fit':>7}  {'WR%':>5}  {'Sharpe':>7}  {'PnL':>8}  {'Trades':>6}  {'Origin':10s}")
    print(f"  {'-'*100}")
    for i, r in enumerate(unique_results[:20]):
        print(f"  {i+1:3d}  {r.get('name','?')[:50]:50s}  "
              f"{r.get('fitness_score',0):7.3f}  "
              f"{r.get('win_rate',0):5.1f}  "
              f"{r.get('sharpe',0):7.3f}  "
              f"{r.get('total_pnl',0):8.2f}  "
              f"{r.get('trades',0):6d}  "
              f"{r.get('origin','')[:10]:10s}")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = OUTPUT_DIR / f"genome_results_{timestamp}.json"
    # Strip per_symbol details to keep file small
    save_results = []
    for r in unique_results[:100]:
        sr = {k: v for k, v in r.items() if k != "per_symbol"}
        save_results.append(sr)

    with open(results_file, "w") as f:
        json.dump(save_results, f, indent=2, default=str)
    print(f"\n  Results saved to: {results_file}")

    # Save best DNA
    if best_ever_dna:
        best_file = OUTPUT_DIR / f"best_dna_{timestamp}.json"
        with open(best_file, "w") as f:
            json.dump(best_ever_dna.to_dict(), f, indent=2)
        print(f"  Best DNA saved to: {best_file}")

    # Save population state for resuming
    pop_file = OUTPUT_DIR / f"population_{timestamp}.json"
    with open(pop_file, "w") as f:
        json.dump([dna.to_dict() for dna in population], f, indent=2)
    print(f"  Population saved to: {pop_file}")

    return {
        "top_strategies": unique_results[:20],
        "best": best_ever,
        "best_dna": best_ever_dna.to_dict() if best_ever_dna else None,
        "total_evaluated": len(all_results),
        "unique_strategies": len(unique_results),
    }


# =====================================================================
# Forward Test Portfolio Tracker
# =====================================================================

def init_portfolio_db():
    """Initialize SQLite database for forward-test tracking."""
    GENOME_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(GENOME_DB))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS strategy_registry (
            dna_id TEXT PRIMARY KEY,
            name TEXT,
            dna_json TEXT,
            generation INTEGER,
            origin TEXT,
            status TEXT DEFAULT 'INCUBATOR',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fitness_score REAL,
            backtest_sharpe REAL,
            backtest_wr REAL,
            backtest_trades INTEGER,
            backtest_pnl REAL
        );

        CREATE TABLE IF NOT EXISTS forward_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP,
            dna_id TEXT,
            symbol TEXT,
            direction INTEGER,
            entry_price REAL,
            take_profit REAL,
            stop_loss REAL,
            regime TEXT,
            confidence REAL,
            FOREIGN KEY (dna_id) REFERENCES strategy_registry(dna_id)
        );

        CREATE TABLE IF NOT EXISTS forward_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dna_id TEXT,
            symbol TEXT,
            direction TEXT,
            entry_price REAL,
            exit_price REAL,
            entry_time TIMESTAMP,
            exit_time TIMESTAMP,
            pnl_pct REAL,
            exit_reason TEXT,
            regime TEXT,
            FOREIGN KEY (dna_id) REFERENCES strategy_registry(dna_id)
        );

        CREATE TABLE IF NOT EXISTS evolution_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            generation INTEGER,
            population_size INTEGER,
            best_fitness REAL,
            best_dna_id TEXT,
            best_name TEXT,
            avg_fitness REAL,
            phoenix_count INTEGER
        );

        CREATE TABLE IF NOT EXISTS promotion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            dna_id TEXT,
            from_status TEXT,
            to_status TEXT,
            reason TEXT
        );
    """)
    conn.commit()
    return conn


def register_top_strategies(results: Dict, top_n: int = 20):
    """Register top genome strategies into the portfolio tracker DB."""
    conn = init_portfolio_db()
    cursor = conn.cursor()

    top = results.get("top_strategies", [])[:top_n]
    for r in top:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO strategy_registry
                (dna_id, name, dna_json, generation, origin, fitness_score,
                 backtest_sharpe, backtest_wr, backtest_trades, backtest_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r.get("dna_id", ""),
                r.get("name", ""),
                json.dumps(r.get("signals", [])),
                r.get("generation", 0),
                r.get("origin", ""),
                r.get("fitness_score", 0),
                r.get("sharpe", 0),
                r.get("win_rate", 0),
                r.get("trades", 0),
                r.get("total_pnl", 0),
            ))
        except Exception as e:
            print(f"  Warning: Failed to register {r.get('dna_id','')}: {e}")

    conn.commit()
    print(f"\n  Registered {len(top)} strategies in portfolio DB: {GENOME_DB}")
    conn.close()


# =====================================================================
# Main Entry Point
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Strategy Genome Engine")
    parser.add_argument("--generations", type=int, default=10, help="Number of GA generations")
    parser.add_argument("--population", type=int, default=30, help="Population size")
    parser.add_argument("--symbols", nargs="*", default=None, help="Symbols to test")
    parser.add_argument("--mode", choices=["evolve", "phoenix", "full"], default="evolve",
                        help="Run mode: evolve (GA), phoenix (revival only), full (evolve + walk-forward)")
    parser.add_argument("--elite", type=int, default=5, help="Elite strategies to keep per generation")
    args = parser.parse_args()

    symbols = args.symbols or ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "XRP/USDT"]

    if args.mode == "phoenix":
        # Phoenix-only mode: create seed, evaluate, then phoenix analysis
        print("Running Phoenix-only analysis...")
        results = evolve(symbols, generations=3, pop_size=20)
    elif args.mode == "full":
        # Full mode: evolve + walk-forward validation on top strategies
        results = evolve(symbols, args.generations, args.population, args.elite)
        # Walk-forward on top 10
        print("\n\n--- Walk-Forward Validation on Top 10 ---")
        conn = sqlite3.connect(str(DB_PATH))
        for sym in symbols:
            try:
                df = pd.read_sql(
                    "SELECT timestamp, open, high, low, close, volume FROM klines "
                    "WHERE pair = ? ORDER BY timestamp",
                    conn, params=(sym,)
                )
            except Exception:
                continue
            close = df["close"].astype(float)
            high_s = df["high"].astype(float)
            low_s = df["low"].astype(float)
            vol_s = df["volume"].astype(float)
            ts = df["timestamp"]

            for r in results.get("top_strategies", [])[:10]:
                dna = StrategyDNA(**{k: v for k, v in (results.get("best_dna") or {}).items()
                                    if k in StrategyDNA.__dataclass_fields__})
                wf = walk_forward_evaluate(dna, close, high_s, low_s, vol_s, ts, sym)
                print(f"  {sym:12s} | Train={wf.get('train_sharpe',0):6.2f} "
                      f"Val={wf.get('val_sharpe',0):6.2f} "
                      f"Test={wf.get('test_sharpe',0):6.2f} "
                      f"Consistency={wf.get('consistency',0):5.3f}")
        conn.close()
    else:
        results = evolve(symbols, args.generations, args.population, args.elite)

    # Register top strategies
    if results:
        register_top_strategies(results)

    return results


if __name__ == "__main__":
    main()
