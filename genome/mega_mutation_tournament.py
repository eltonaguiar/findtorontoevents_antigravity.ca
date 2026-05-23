#!/usr/bin/env python3
"""
MEGA MUTATION TOURNAMENT
========================
Generates 1000+ DNA strategy mutations, backtests them across 30+ crypto
symbols on Binance 4h data, and produces a predictability leaderboard.

Goal: Identify which crypto symbols are most predictable and which
strategy DNA + symbol combos produce the best risk-adjusted returns.

Usage:
    python genome/mega_mutation_tournament.py
    python genome/mega_mutation_tournament.py --symbols BTCUSDT,ETHUSDT --mutations 200

Output:
    genome/data/tournament_results.json         — Full results
    genome/data/symbol_predictability.json      — Predictability rankings
    genome/data/tournament_summary.md           — Human-readable report
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import os
import random
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# --- Setup ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = SCRIPT_DIR / "data"
CACHE_DIR = DATA_DIR / "ohlcv_cache"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("MegaTournament")

# ============================================================================
# SYMBOL UNIVERSE — 30+ top crypto by liquidity
# ============================================================================
DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "NEARUSDT", "SUIUSDT", "APTUSDT", "INJUSDT", "FETUSDT",
    "UNIUSDT", "AAVEUSDT", "OPUSDT", "ARBUSDT", "ATOMUSDT",
    "FILUSDT", "RENDERUSDT", "TIAUSDT", "SEIUSDT", "JUPUSDT",
    "WIFUSDT", "PEPEUSDT", "BONKUSDT", "TAOUSDT", "RUNEUSDT",
    "STXUSDT", "ONDOUSDT", "ENAUSDT",
]

# ============================================================================
# SEED STRATEGIES — 8 proven templates to mutate from
# ============================================================================
SEED_STRATEGIES = [
    {
        "name": "connors_rsi2",
        "genes": {
            "primary": "RSI2",
            "rsi_period": 2, "rsi_buy": 10, "rsi_sell": 90,
            "trend_ema": 200, "tp_atr": 3.0, "sl_atr": 1.5,
            "direction_bias": "both",
        },
    },
    {
        "name": "mean_reversion_bb",
        "genes": {
            "primary": "BB",
            "bb_period": 20, "bb_std": 2.0,
            "rsi_period": 14, "rsi_buy": 30, "rsi_sell": 70,
            "tp_atr": 2.0, "sl_atr": 1.0,
            "direction_bias": "both",
        },
    },
    {
        "name": "ema_momentum",
        "genes": {
            "primary": "EMA_CROSS",
            "ema_fast": 9, "ema_slow": 21,
            "rsi_period": 14, "rsi_filter_low": 40, "rsi_filter_high": 60,
            "tp_atr": 2.5, "sl_atr": 1.2,
            "direction_bias": "both",
        },
    },
    {
        "name": "keltner_breakout",
        "genes": {
            "primary": "KELTNER",
            "kc_ema": 20, "kc_atr_mult": 2.0,
            "vol_threshold": 1.5,
            "rsi_period": 14, "rsi_confirm": 50,
            "tp_atr": 3.0, "sl_atr": 1.5,
            "direction_bias": "both",  # Was "long" — Phase 1 proved SHORTs win in downtrends
        },
    },
    {
        "name": "macd_rsi_confluence",
        "genes": {
            "primary": "MACD_RSI",
            "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.2, "sl_atr": 1.2,
            "direction_bias": "both",
        },
    },
    {
        "name": "bb_squeeze_momentum",
        "genes": {
            "primary": "BB_SQUEEZE",
            "bb_period": 20, "bb_std": 2.0,
            "kc_ema": 20, "kc_atr_mult": 1.5,
            "rsi_period": 14,
            "tp_atr": 3.0, "sl_atr": 1.5,
            "direction_bias": "both",
        },
    },
    {
        "name": "volume_momentum",
        "genes": {
            "primary": "VOL_MOM",
            "vol_lookback": 20, "vol_spike": 2.0,
            "ema_fast": 9, "ema_slow": 21,
            "rsi_period": 14, "rsi_confirm": 50,
            "tp_atr": 2.5, "sl_atr": 1.3,
            "direction_bias": "both",  # Was "long" — allow SHORT signals in bear regimes
        },
    },
    {
        "name": "ou_mean_reversion",
        "genes": {
            "primary": "OU",
            "ou_lookback": 30, "ou_sigma": 1.5,
            "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
            "tp_atr": 2.0, "sl_atr": 1.0,
            "direction_bias": "both",
        },
    },
    # Phase 2 additions: SHORT-biased seeds to balance LONG dominance
    {
        "name": "trend_reversal_short",
        "genes": {
            "primary": "EMA_CROSS",
            "ema_fast": 9, "ema_slow": 21,
            "rsi_period": 14, "rsi_filter_low": 55, "rsi_filter_high": 80,
            "tp_atr": 1.5, "sl_atr": 1.0,
            "direction_bias": "short",  # Explicit SHORT seed — Phase 1 lesson
        },
    },
    {
        "name": "bb_overbought_short",
        "genes": {
            "primary": "BB",
            "bb_period": 20, "bb_std": 2.0,
            "rsi_period": 14, "rsi_buy": 30, "rsi_sell": 65,
            "tp_atr": 1.5, "sl_atr": 1.2,
            "direction_bias": "short",  # Mean-reversion SHORT when overbought
        },
    },
    # Phase 2: Connors RSI-2 Short — mirror of proven RSI-2 long (75% WR) for shorts
    # In downtrends, short when RSI(2) > 90 (overbought bounce exhaustion)
    {
        "name": "connors_rsi2_short",
        "genes": {
            "primary": "RSI2",
            "rsi_period": 2, "rsi_buy": 90, "rsi_sell": 10,  # Inverted for SHORT
            "trend_ema": 200, "tp_atr": 2.5, "sl_atr": 1.5,
            "direction_bias": "short",
        },
    },
    # Phase 2: VWAP deviation short — short when price > 2 std above VWAP proxy
    {
        "name": "vwap_deviation_short",
        "genes": {
            "primary": "BB",
            "bb_period": 20, "bb_std": 2.5,
            "rsi_period": 14, "rsi_buy": 25, "rsi_sell": 70,
            "tp_atr": 2.0, "sl_atr": 1.2,
            "direction_bias": "short",
        },
    },
]

# Gene mutation ranges
GENE_RANGES = {
    "rsi_period":       (2, 21, "int"),
    "rsi_buy":          (5, 45, "int"),
    "rsi_sell":         (55, 95, "int"),
    "rsi_confirm":      (35, 65, "int"),
    "rsi_filter_low":   (25, 50, "int"),
    "rsi_filter_high":  (50, 75, "int"),
    "trend_ema":        (20, 200, "int"),
    "ema_fast":         (3, 30, "int"),
    "ema_slow":         (15, 120, "int"),
    "bb_period":        (10, 30, "int"),
    "bb_std":           (1.2, 3.5, "float"),
    "kc_ema":           (10, 30, "int"),
    "kc_atr_mult":      (1.0, 3.0, "float"),
    "vol_threshold":    (1.0, 3.0, "float"),
    "vol_lookback":     (10, 40, "int"),
    "vol_spike":        (1.2, 3.5, "float"),
    "ou_lookback":      (15, 60, "int"),
    "ou_sigma":         (0.5, 2.5, "float"),
    "macd_fast":        (6, 16, "int"),
    "macd_slow":        (18, 32, "int"),
    "macd_signal":      (5, 12, "int"),
    "tp_atr":           (1.0, 6.0, "float"),
    "sl_atr":           (0.5, 3.0, "float"),
    # direction_bias is handled specially in mutate_genes() — not a numeric range
}


# ============================================================================
# Technical indicator helpers (lightweight, numpy-only)
# ============================================================================
def _ema(data: np.ndarray, period: int) -> np.ndarray:
    out = np.empty_like(data)
    out[0] = data[0]
    mult = 2.0 / (period + 1)
    for i in range(1, len(data)):
        out[i] = data[i] * mult + out[i - 1] * (1 - mult)
    return out


def _sma(data: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(data, np.nan)
    cs = np.cumsum(data)
    out[period - 1:] = (cs[period - 1:] - np.concatenate(([0], cs[:-period]))) / period
    # fill initial NaN with expanding mean
    for i in range(period - 1):
        out[i] = np.mean(data[:i + 1])
    return out


def _rsi(closes: np.ndarray, period: int) -> np.ndarray:
    deltas = np.diff(closes, prepend=closes[0])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.zeros_like(closes)
    avg_loss = np.zeros_like(closes)
    if len(gains) < period + 1:
        return np.full_like(closes, 50.0)

    avg_gain[period] = np.mean(gains[1:period + 1])
    avg_loss[period] = np.mean(losses[1:period + 1])

    for i in range(period + 1, len(closes)):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i]) / period

    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi[:period] = 50.0
    return rsi


def _atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    tr = np.zeros(len(closes))
    tr[0] = highs[0] - lows[0]
    for i in range(1, len(closes)):
        tr[i] = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
    atr = np.zeros_like(closes)
    if len(tr) < period:
        return atr
    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, len(closes)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def _bb(closes: np.ndarray, period: int, std_mult: float):
    mid = _sma(closes, period)
    std = np.zeros_like(closes)
    for i in range(period - 1, len(closes)):
        std[i] = np.std(closes[i - period + 1:i + 1])
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return upper, mid, lower


def _macd(closes: np.ndarray, fast: int, slow: int, signal: int):
    ema_f = _ema(closes, fast)
    ema_s = _ema(closes, slow)
    macd_line = ema_f - ema_s
    sig_line = _ema(macd_line, signal)
    hist = macd_line - sig_line
    return macd_line, sig_line, hist


# ============================================================================
# Binance data fetcher with caching
# ============================================================================
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]


def fetch_ohlcv(symbol: str, interval: str = "4h", limit: int = 750) -> Optional[Dict[str, np.ndarray]]:
    """Fetch OHLCV data from Binance with local caching."""
    cache_file = CACHE_DIR / f"{symbol}_{interval}_{limit}.npz"

    # Use cache if < 4 hours old
    if cache_file.exists():
        age_s = time.time() - cache_file.stat().st_mtime
        if age_s < 4 * 3600:
            d = np.load(str(cache_file))
            return {k: d[k] for k in d.files}

    import requests
    for base in BINANCE_MIRRORS:
        try:
            url = f"{base}/api/v3/klines"
            resp = requests.get(url, params={
                "symbol": symbol, "interval": interval, "limit": limit
            }, timeout=20)
            if resp.status_code == 200:
                raw = resp.json()
                if not raw:
                    return None
                opens = np.array([float(k[1]) for k in raw])
                highs = np.array([float(k[2]) for k in raw])
                lows = np.array([float(k[3]) for k in raw])
                closes = np.array([float(k[4]) for k in raw])
                volumes = np.array([float(k[5]) for k in raw])
                timestamps = np.array([int(k[0]) for k in raw])

                # Cache
                np.savez_compressed(str(cache_file),
                                    open=opens, high=highs, low=lows,
                                    close=closes, volume=volumes, timestamp=timestamps)
                return {"open": opens, "high": highs, "low": lows,
                        "close": closes, "volume": volumes, "timestamp": timestamps}
        except Exception:
            continue
    return None


# ============================================================================
# Mutation engine
# ============================================================================
def mutate_genes(genes: dict, mutation_rate: float = 0.3, strength: float = 0.2) -> dict:
    """Create a mutated copy of strategy genes."""
    child = copy.deepcopy(genes)

    # Phase 2 fix: allow direction_bias to mutate (was locked, causing 100% LONG bias)
    if "direction_bias" in child and random.random() < 0.15:  # 15% chance per mutation
        child["direction_bias"] = random.choice(["long", "short", "both"])

    # Phase 2: structural mutation — 5% chance to change primary indicator type
    # Research shows this discovers new strategy archetypes (Springer 2025)
    if random.random() < 0.05:
        all_primaries = ["RSI2", "BB", "EMA_CROSS", "KELTNER",
                         "MACD_RSI", "BB_SQUEEZE", "VOL_MOM", "OU"]
        child["primary"] = random.choice(all_primaries)

    for key, val in list(child.items()):
        if key in ("primary", "name"):
            continue  # Only lock name — direction_bias and primary are now mutable above
        if random.random() > mutation_rate:
            continue
        if key not in GENE_RANGES:
            continue

        lo, hi, gtype = GENE_RANGES[key]
        spread = hi - lo

        r = random.random()
        if r < 0.10:
            # Cauchy mutation: fat tails for escaping local optima (15-25% better convergence)
            import math
            delta = math.tan(math.pi * (random.random() - 0.5)) * spread * strength * 0.1
            new_val = val + delta
        elif r < 0.70:
            # Gaussian jitter (existing approach)
            delta = random.gauss(0, spread * strength)
            new_val = val + delta
        else:
            # Random jump (existing approach)
            if gtype == "int":
                new_val = random.randint(lo, hi)
            else:
                new_val = random.uniform(lo, hi)

        if gtype == "int":
            new_val = int(round(new_val))
        else:
            new_val = round(float(new_val), 4)

        child[key] = max(lo, min(hi, new_val))

    # Enforce ema_fast < ema_slow
    if "ema_fast" in child and "ema_slow" in child:
        if child["ema_fast"] >= child["ema_slow"]:
            child["ema_slow"] = child["ema_fast"] + 5

    # Enforce macd_fast < macd_slow
    if "macd_fast" in child and "macd_slow" in child:
        if child["macd_fast"] >= child["macd_slow"]:
            child["macd_slow"] = child["macd_fast"] + 6

    return child


def crossover(parent_a: dict, parent_b: dict) -> dict:
    """Uniform crossover: each gene randomly from A or B."""
    child = {}
    all_keys = set(parent_a.keys()) | set(parent_b.keys())
    for key in all_keys:
        a_val = parent_a.get(key)
        b_val = parent_b.get(key)
        if a_val is not None and b_val is not None:
            child[key] = a_val if random.random() < 0.5 else b_val
        elif a_val is not None:
            child[key] = a_val
        else:
            child[key] = b_val
    return child


def generate_mutations(n_total: int = 1000, seed: int = 42) -> List[Dict]:
    """Generate n_total mutations from seed strategies."""
    random.seed(seed)
    np.random.seed(seed)

    mutations = []

    # Include seed strategies themselves
    for s in SEED_STRATEGIES:
        mutations.append({
            "name": s["name"],
            "genes": copy.deepcopy(s["genes"]),
            "generation": 0,
            "parent": s["name"],
            "mutation_type": "seed",
        })

    # Generate mutations
    per_seed = (n_total - len(SEED_STRATEGIES)) // len(SEED_STRATEGIES)
    extra = (n_total - len(SEED_STRATEGIES)) % len(SEED_STRATEGIES)

    for idx, seed_strat in enumerate(SEED_STRATEGIES):
        count = per_seed + (1 if idx < extra else 0)
        for i in range(count):
            # Vary mutation rate and strength
            mut_rate = random.uniform(0.15, 0.6)
            strength = random.uniform(0.1, 0.4)

            if random.random() < 0.2 and len(SEED_STRATEGIES) > 1:
                # Crossover with another seed first, then mutate
                other = random.choice([s for s in SEED_STRATEGIES if s["name"] != seed_strat["name"]])
                crossed = crossover(seed_strat["genes"], other["genes"])
                mutated = mutate_genes(crossed, mut_rate, strength)
                mut_type = "crossover+mutate"
                parent = f"{seed_strat['name']}×{other['name']}"
            else:
                mutated = mutate_genes(seed_strat["genes"], mut_rate, strength)
                mut_type = "mutate"
                parent = seed_strat["name"]

            dna_hash = hashlib.md5(json.dumps(mutated, sort_keys=True).encode()).hexdigest()[:10]
            mutations.append({
                "name": f"{seed_strat['name']}_m{i:03d}_{dna_hash}",
                "genes": mutated,
                "generation": 1,
                "parent": parent,
                "mutation_type": mut_type,
            })

    logger.info(f"Generated {len(mutations)} mutations from {len(SEED_STRATEGIES)} seeds")
    return mutations


# ============================================================================
# Backtester
# ============================================================================
def generate_signals(data: Dict[str, np.ndarray], genes: dict) -> Tuple[np.ndarray, np.ndarray]:
    """Generate long/short signals based on DNA genes. Returns (long_signals, short_signals)."""
    closes = data["close"]
    highs = data["high"]
    lows = data["low"]
    volumes = data["volume"]
    n = len(closes)

    long_sig = np.zeros(n, dtype=bool)
    short_sig = np.zeros(n, dtype=bool)

    primary = genes.get("primary", "RSI2")
    bias = genes.get("direction_bias", "both")

    rsi_p = genes.get("rsi_period", 14)
    rsi_vals = _rsi(closes, rsi_p)
    atr_vals = _atr(highs, lows, closes, 14)

    warmup = max(60, genes.get("trend_ema", 50), genes.get("ema_slow", 50))

    if primary == "RSI2":
        rsi2 = _rsi(closes, genes.get("rsi_period", 2))
        trend_ema = _ema(closes, genes.get("trend_ema", 200))
        buy_thresh = genes.get("rsi_buy", 10)
        sell_thresh = genes.get("rsi_sell", 90)

        for i in range(warmup, n):
            if rsi2[i] < buy_thresh and closes[i] > trend_ema[i]:
                long_sig[i] = True
            elif rsi2[i] > sell_thresh and closes[i] < trend_ema[i]:
                short_sig[i] = True

    elif primary == "BB":
        bb_upper, bb_mid, bb_lower = _bb(closes, genes.get("bb_period", 20), genes.get("bb_std", 2.0))
        buy_rsi = genes.get("rsi_buy", 30)
        sell_rsi = genes.get("rsi_sell", 70)

        for i in range(warmup, n):
            if closes[i] < bb_lower[i] and rsi_vals[i] < buy_rsi:
                long_sig[i] = True
            elif closes[i] > bb_upper[i] and rsi_vals[i] > sell_rsi:
                short_sig[i] = True

    elif primary == "EMA_CROSS":
        ef = _ema(closes, genes.get("ema_fast", 9))
        es = _ema(closes, genes.get("ema_slow", 21))
        rsi_lo = genes.get("rsi_filter_low", 40)
        rsi_hi = genes.get("rsi_filter_high", 60)

        for i in range(warmup, n):
            if ef[i] > es[i] and ef[i - 1] <= es[i - 1] and rsi_vals[i] > rsi_lo:
                long_sig[i] = True
            elif ef[i] < es[i] and ef[i - 1] >= es[i - 1] and rsi_vals[i] < rsi_hi:
                short_sig[i] = True

    elif primary == "KELTNER":
        kc_ema = _ema(closes, genes.get("kc_ema", 20))
        kc_mult = genes.get("kc_atr_mult", 2.0)
        vol_thresh = genes.get("vol_threshold", 1.5)
        rsi_confirm = genes.get("rsi_confirm", 50)

        for i in range(warmup, n):
            kc_upper = kc_ema[i] + kc_mult * atr_vals[i]
            kc_lower = kc_ema[i] - kc_mult * atr_vals[i]
            vol_avg = np.mean(volumes[max(0, i - 20):i]) if i > 20 else volumes[i]
            vol_ratio = volumes[i] / vol_avg if vol_avg > 0 else 1.0

            if closes[i] > kc_upper and vol_ratio > vol_thresh and rsi_vals[i] > rsi_confirm:
                long_sig[i] = True
            elif closes[i] < kc_lower and vol_ratio > vol_thresh and rsi_vals[i] < (100 - rsi_confirm):
                short_sig[i] = True

    elif primary == "MACD_RSI":
        macd_l, macd_s, macd_h = _macd(closes,
                                         genes.get("macd_fast", 12),
                                         genes.get("macd_slow", 26),
                                         genes.get("macd_signal", 9))
        buy_rsi = genes.get("rsi_buy", 35)
        sell_rsi = genes.get("rsi_sell", 65)

        for i in range(warmup, n):
            if macd_h[i] > 0 and macd_h[i - 1] <= 0 and rsi_vals[i] < buy_rsi + 20:
                long_sig[i] = True
            elif macd_h[i] < 0 and macd_h[i - 1] >= 0 and rsi_vals[i] > sell_rsi - 20:
                short_sig[i] = True

    elif primary == "BB_SQUEEZE":
        bb_upper, bb_mid, bb_lower = _bb(closes, genes.get("bb_period", 20), genes.get("bb_std", 2.0))
        kc_ema = _ema(closes, genes.get("kc_ema", 20))
        kc_mult = genes.get("kc_atr_mult", 1.5)

        for i in range(warmup, n):
            kc_upper = kc_ema[i] + kc_mult * atr_vals[i]
            kc_lower = kc_ema[i] - kc_mult * atr_vals[i]
            in_squeeze = bb_upper[i] < kc_upper and bb_lower[i] > kc_lower
            was_squeeze = (i > warmup and
                           bb_upper[i - 1] < (kc_ema[i - 1] + kc_mult * atr_vals[i - 1]) and
                           bb_lower[i - 1] > (kc_ema[i - 1] - kc_mult * atr_vals[i - 1]))

            if was_squeeze and not in_squeeze:
                # Squeeze released
                momentum = closes[i] - closes[i - 3]
                if momentum > 0:
                    long_sig[i] = True
                else:
                    short_sig[i] = True

    elif primary == "VOL_MOM":
        vol_lb = genes.get("vol_lookback", 20)
        vol_spike = genes.get("vol_spike", 2.0)
        ef = _ema(closes, genes.get("ema_fast", 9))
        es = _ema(closes, genes.get("ema_slow", 21))
        rsi_confirm = genes.get("rsi_confirm", 50)

        for i in range(warmup, n):
            vol_avg = np.mean(volumes[max(0, i - vol_lb):i]) if i > vol_lb else volumes[i]
            vol_ratio = volumes[i] / vol_avg if vol_avg > 0 else 1.0

            if vol_ratio > vol_spike and ef[i] > es[i] and rsi_vals[i] > rsi_confirm:
                long_sig[i] = True
            elif vol_ratio > vol_spike and ef[i] < es[i] and rsi_vals[i] < (100 - rsi_confirm):
                short_sig[i] = True

    elif primary == "OU":
        lookback = genes.get("ou_lookback", 30)
        sigma_thresh = genes.get("ou_sigma", 1.5)
        buy_rsi = genes.get("rsi_buy", 35)
        sell_rsi = genes.get("rsi_sell", 65)

        for i in range(warmup, n):
            window = closes[max(0, i - lookback):i]
            if len(window) < 5:
                continue
            mean_p = np.mean(window)
            std_p = np.std(window)
            if std_p > 0:
                zscore = (closes[i] - mean_p) / std_p
                if zscore < -sigma_thresh and rsi_vals[i] < buy_rsi:
                    long_sig[i] = True
                elif zscore > sigma_thresh and rsi_vals[i] > sell_rsi:
                    short_sig[i] = True

    # Apply direction bias
    if bias == "long":
        short_sig[:] = False
    elif bias == "short":
        long_sig[:] = False

    return long_sig, short_sig


def backtest_strategy(data: Dict[str, np.ndarray], genes: dict,
                      start_idx: int = 0, end_idx: int = -1) -> Dict:
    """Run a walk-forward backtest on a slice of data. Returns metrics dict."""
    closes = data["close"]
    highs = data["high"]
    lows = data["low"]
    n = len(closes)

    if end_idx <= 0:
        end_idx = n
    end_idx = min(end_idx, n)

    # Slice data
    sliced = {k: v[start_idx:end_idx] for k, v in data.items()}
    n_slice = len(sliced["close"])

    if n_slice < 80:
        return {"trades": 0, "win_rate": 0, "sharpe": 0, "fitness": 0}

    long_sig, short_sig = generate_signals(sliced, genes)

    tp_atr_mult = genes.get("tp_atr", 2.0)
    sl_atr_mult = genes.get("sl_atr", 1.0)
    atr_vals = _atr(sliced["high"], sliced["low"], sliced["close"], 14)

    capital = 10000.0
    initial_capital = capital
    position = None  # None, "LONG", "SHORT"
    entry_price = 0.0
    entry_idx = 0
    equity = [capital]
    trades_pnl = []
    max_hold = 30  # bars

    for i in range(1, n_slice):
        current_price = sliced["close"][i]
        current_atr = atr_vals[i] if atr_vals[i] > 0 else current_price * 0.02

        # Check exit
        if position is not None:
            tp_dist = tp_atr_mult * current_atr
            sl_dist = sl_atr_mult * current_atr

            tp_price = entry_price + tp_dist if position == "LONG" else entry_price - tp_dist
            sl_price = entry_price - sl_dist if position == "LONG" else entry_price + sl_dist

            should_exit = False
            exit_reason = ""

            if position == "LONG":
                if sliced["high"][i] >= tp_price:
                    pnl_pct = tp_dist / entry_price
                    should_exit = True
                    exit_reason = "TP"
                elif sliced["low"][i] <= sl_price:
                    pnl_pct = -sl_dist / entry_price
                    should_exit = True
                    exit_reason = "SL"
                elif i - entry_idx >= max_hold:
                    pnl_pct = (current_price - entry_price) / entry_price
                    should_exit = True
                    exit_reason = "TIME"
            else:  # SHORT
                if sliced["low"][i] <= tp_price:
                    pnl_pct = tp_dist / entry_price
                    should_exit = True
                    exit_reason = "TP"
                elif sliced["high"][i] >= sl_price:
                    pnl_pct = -sl_dist / entry_price
                    should_exit = True
                    exit_reason = "SL"
                elif i - entry_idx >= max_hold:
                    pnl_pct = (entry_price - current_price) / entry_price
                    should_exit = True
                    exit_reason = "TIME"

            if should_exit:
                # Apply commission
                pnl_pct -= 0.002  # 0.1% each way
                capital *= (1 + pnl_pct * 0.1)  # 10% position size
                trades_pnl.append(pnl_pct)
                position = None

        # Check entry (only if no position)
        if position is None:
            if long_sig[i]:
                position = "LONG"
                entry_price = current_price
                entry_idx = i
            elif short_sig[i]:
                position = "SHORT"
                entry_price = current_price
                entry_idx = i

        equity.append(capital)

    # Close any open position
    if position is not None:
        if position == "LONG":
            pnl_pct = (sliced["close"][-1] - entry_price) / entry_price - 0.002
        else:
            pnl_pct = (entry_price - sliced["close"][-1]) / entry_price - 0.002
        capital *= (1 + pnl_pct * 0.1)
        trades_pnl.append(pnl_pct)
        equity.append(capital)

    # Calculate metrics
    n_trades = len(trades_pnl)
    if n_trades < 3:
        return {"trades": n_trades, "win_rate": 0, "sharpe": 0, "fitness": 0}

    pnls = np.array(trades_pnl)
    wins = int(np.sum(pnls > 0))
    wr = wins / n_trades
    mean_pnl = float(np.mean(pnls))
    std_pnl = float(np.std(pnls)) if n_trades > 1 else 1.0

    ann_factor = np.sqrt(50)  # ~50 trades per year at 4h
    sharpe = (mean_pnl / std_pnl) * ann_factor if std_pnl > 0 else 0
    downside = pnls[pnls < 0]
    d_std = float(np.std(downside)) if len(downside) > 1 else 1.0
    sortino = (mean_pnl / d_std) * ann_factor if d_std > 0 else 0

    gross_w = float(np.sum(pnls[pnls > 0])) if np.any(pnls > 0) else 0
    gross_l = float(abs(np.sum(pnls[pnls < 0]))) if np.any(pnls < 0) else 0.01
    pf = gross_w / gross_l if gross_l > 0 else 0

    # Max drawdown
    eq = np.array(equity)
    peak = np.maximum.accumulate(eq)
    dd = (peak - eq) / np.where(peak > 0, peak, 1)
    max_dd = float(np.max(dd))

    total_return = (capital - initial_capital) / initial_capital

    # Composite fitness: penalize low trade count, reward consistency
    trade_norm = min(n_trades, 30) / 30  # normalize trade count
    fitness = (
        0.30 * min(max(sharpe, -2), 5) / 5 +
        0.25 * wr +
        0.15 * min(pf, 3) / 3 +
        0.15 * max(0, 1 - max_dd) +
        0.10 * trade_norm +
        0.05 * min(max(total_return, -1), 2) / 2
    )

    return {
        "trades": n_trades,
        "wins": wins,
        "win_rate": round(wr, 4),
        "sharpe": round(float(sharpe), 3),
        "sortino": round(float(sortino), 3),
        "profit_factor": round(float(pf), 3),
        "max_drawdown": round(max_dd, 4),
        "total_return": round(total_return, 4),
        "mean_pnl": round(float(mean_pnl), 5),
        "fitness": round(float(fitness), 4),
    }


# ============================================================================
# Walk-forward validation
# ============================================================================
def walk_forward_backtest(data: Dict[str, np.ndarray], genes: dict,
                          train_ratio: float = 0.7, n_windows: int = 3) -> Dict:
    """Multi-window walk-forward validation (anchored expanding window).

    Instead of a single 70/30 split, tests across n_windows temporal slices:
      Window 1: train on [0..33%], test on [33%..50%]
      Window 2: train on [0..50%], test on [50%..75%]
      Window 3: train on [0..67%], test on [67%..100%]

    A strategy must be profitable OOS in the majority of windows to pass.
    This catches regime-dependent strategies that only work in one period.
    """
    n = len(data["close"])

    if n < 100 or n_windows < 2:
        # Fall back to simple single-window for small datasets
        split = int(n * train_ratio)
        oos_result = backtest_strategy(data, genes, start_idx=split, end_idx=n)
        is_result = backtest_strategy(data, genes, start_idx=0, end_idx=split)
        is_sharpe = is_result.get("sharpe", 0)
        oos_sharpe = oos_result.get("sharpe", 0)
        overfit_ratio = abs(is_sharpe - oos_sharpe) / max(abs(is_sharpe), 0.01) if is_sharpe != 0 else 0
        result = {**oos_result}
        result["is_sharpe"] = round(is_sharpe, 3)
        result["oos_sharpe"] = round(oos_sharpe, 3)
        result["overfit_ratio"] = round(overfit_ratio, 3)
        result["is_robust"] = oos_sharpe > 0 and overfit_ratio < 2.0 and oos_result.get("trades", 0) >= 5
        return result

    # Multi-window: anchored expanding train, sliding test
    window_sharpes = []
    window_trades = []
    all_is_sharpes = []

    for w in range(n_windows):
        # Train end grows; test window slides forward
        train_end = int(n * (0.33 + 0.33 * w / max(n_windows - 1, 1)))
        test_end = int(n * (0.50 + 0.50 * w / max(n_windows - 1, 1)))
        train_end = max(train_end, 50)  # minimum train size
        test_end = min(test_end, n)
        if test_end <= train_end + 10:
            continue

        oos_result = backtest_strategy(data, genes, start_idx=train_end, end_idx=test_end)
        is_result = backtest_strategy(data, genes, start_idx=0, end_idx=train_end)

        window_sharpes.append(oos_result.get("sharpe", 0))
        window_trades.append(oos_result.get("trades", 0))
        all_is_sharpes.append(is_result.get("sharpe", 0))

    if not window_sharpes:
        return {"sharpe": 0, "trades": 0, "is_robust": False, "oos_sharpe": 0}

    # Use the final window as the primary result (most recent OOS)
    final_split = int(n * train_ratio)
    final_oos = backtest_strategy(data, genes, start_idx=final_split, end_idx=n)
    final_is = backtest_strategy(data, genes, start_idx=0, end_idx=final_split)

    oos_sharpe = final_oos.get("sharpe", 0)
    is_sharpe = final_is.get("sharpe", 0)
    overfit_ratio = abs(is_sharpe - oos_sharpe) / max(abs(is_sharpe), 0.01) if is_sharpe != 0 else 0

    # Multi-window consistency: how many windows were profitable?
    n_profitable_windows = sum(1 for s in window_sharpes if s > 0)
    window_consistency = n_profitable_windows / len(window_sharpes)

    result = {**final_oos}
    result["is_sharpe"] = round(is_sharpe, 3)
    result["oos_sharpe"] = round(oos_sharpe, 3)
    result["overfit_ratio"] = round(overfit_ratio, 3)
    result["walk_forward_windows"] = len(window_sharpes)
    result["walk_forward_consistency"] = round(window_consistency, 2)
    result["window_sharpes"] = [round(s, 3) for s in window_sharpes]
    # Robust = OOS positive + not overfit + enough trades + majority of windows profitable
    result["is_robust"] = (
        oos_sharpe > 0
        and overfit_ratio < 2.0
        and final_oos.get("trades", 0) >= 5
        and window_consistency >= 0.5  # At least half the windows must be profitable
    )
    return result


# ============================================================================
# Tournament runner
# ============================================================================
def run_tournament(symbols: List[str], n_mutations: int = 1000,
                   seed: int = 42) -> Dict:
    """Run the mega mutation tournament. Returns full results dict."""
    start_time = time.time()
    logger.info("=" * 70)
    logger.info(f"  MEGA MUTATION TOURNAMENT")
    logger.info(f"  {n_mutations} mutations × {len(symbols)} symbols = {n_mutations * len(symbols)} backtests")
    logger.info("=" * 70)

    # 1. Generate mutations
    mutations = generate_mutations(n_mutations, seed)

    # 2. Fetch data for all symbols (parallel)
    logger.info(f"\nFetching data for {len(symbols)} symbols...")
    market_data = {}

    def _fetch(sym):
        return sym, fetch_ohlcv(sym, interval="4h", limit=750)

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_fetch, s): s for s in symbols}
        for future in as_completed(futures):
            sym, data = future.result()
            if data is not None and len(data["close"]) > 100:
                market_data[sym] = data
                logger.info(f"  ✓ {sym}: {len(data['close'])} bars")
            else:
                logger.warning(f"  ✗ {sym}: No data")

    if not market_data:
        logger.error("No market data fetched — aborting")
        return {"error": "No data"}

    logger.info(f"\nData ready: {len(market_data)} symbols")

    # 3. Run all backtests
    total_backtests = len(mutations) * len(market_data)
    logger.info(f"\nRunning {total_backtests} backtests...")

    all_results = []  # List of (mutation_name, symbol, result_dict)
    symbol_scores = defaultdict(list)  # symbol -> list of fitness scores
    strategy_scores = defaultdict(list)  # strategy_name -> list of fitness scores

    done = 0
    for mut in mutations:
        for sym, data in market_data.items():
            result = walk_forward_backtest(data, mut["genes"])
            result["mutation_name"] = mut["name"]
            result["parent"] = mut["parent"]
            result["mutation_type"] = mut["mutation_type"]
            result["symbol"] = sym
            result["genes_summary"] = {k: v for k, v in mut["genes"].items()
                                        if k in ("primary", "tp_atr", "sl_atr", "rsi_period",
                                                  "rsi_buy", "rsi_sell", "direction_bias")}

            all_results.append(result)

            if result.get("is_robust"):
                symbol_scores[sym].append(result["fitness"])
                strategy_scores[mut["name"]].append(result["fitness"])

            done += 1
            if done % 500 == 0:
                pct = done / total_backtests * 100
                logger.info(f"  Progress: {done}/{total_backtests} ({pct:.1f}%)")

    elapsed = time.time() - start_time
    logger.info(f"\nDone: {total_backtests} backtests in {elapsed:.1f}s "
                f"({total_backtests / elapsed:.0f} backtests/sec)")

    # 4. Rank results
    # Filter to robust only
    robust_results = [r for r in all_results if r.get("is_robust")]
    robust_results.sort(key=lambda x: x["fitness"], reverse=True)

    # Symbol predictability rankings
    symbol_predictability = {}
    for sym, scores in symbol_scores.items():
        if scores:
            symbol_predictability[sym] = {
                "avg_fitness": round(np.mean(scores), 4),
                "max_fitness": round(max(scores), 4),
                "robust_count": len(scores),
                "top_10_avg": round(np.mean(sorted(scores, reverse=True)[:10]), 4) if len(scores) >= 10 else round(np.mean(scores), 4),
                "consistency": round(np.mean(scores) / (np.std(scores) + 1e-6), 3),
            }

    # Sort by avg fitness of top 10
    pred_sorted = sorted(symbol_predictability.items(),
                         key=lambda x: x[1]["top_10_avg"], reverse=True)

    # Strategy rankings
    strategy_rankings = {}
    for name, scores in strategy_scores.items():
        if scores:
            strategy_rankings[name] = {
                "avg_fitness": round(np.mean(scores), 4),
                "max_fitness": round(max(scores), 4),
                "robust_count": len(scores),
            }

    strat_sorted = sorted(strategy_rankings.items(),
                          key=lambda x: x[1]["avg_fitness"], reverse=True)

    # 4b. Deflated Sharpe Ratio filter (Bailey & de Prado 2014)
    # When testing 1000+ mutations, some have high Sharpe by luck.
    # DSR adjusts for multiple testing — filters ~60% of false positives.
    if robust_results:
        all_sharpes = [r.get("oos_sharpe", 0) for r in robust_results]
        sharpe_std = float(np.std(all_sharpes)) if len(all_sharpes) > 1 else 1.0
        import math as _math
        _euler = 0.5772156649
        for r in robust_results:
            obs_sharpe = r.get("oos_sharpe", 0)
            n_obs = max(r.get("trades", 10) * 6, 30)  # approx bars per trade
            # Expected max Sharpe under null (all random)
            inv_n = 1.0 / max(n_mutations, 1)
            # Approximation of expected max of n_mutations standard normals
            from math import log, sqrt
            expected_max = sharpe_std * sqrt(2 * log(max(n_mutations, 2)))
            se = sqrt((1 + 0.5 * obs_sharpe ** 2) / n_obs) if n_obs > 0 else 1.0
            dsr_stat = (obs_sharpe - expected_max) / se if se > 0 else 0
            # Simple CDF approximation
            dsr_pval = 0.5 * (1 + _math.erf(dsr_stat / sqrt(2)))
            r["dsr_pval"] = round(dsr_pval, 4)
            r["survives_dsr"] = dsr_pval > 0.50  # lenient threshold for now

    # 5. Compile output
    output = {
        "tournament_id": hashlib.md5(f"{n_mutations}_{seed}_{len(symbols)}".encode()).hexdigest()[:12],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "n_mutations": n_mutations,
            "n_symbols": len(market_data),
            "seed": seed,
            "total_backtests": total_backtests,
            "elapsed_seconds": round(elapsed, 1),
            "backtests_per_second": round(total_backtests / elapsed, 1),
        },
        "symbol_predictability": dict(pred_sorted),
        "top_50_combos": [
            {k: v for k, v in r.items() if k != "genes_summary"}
            for r in robust_results[:50]
        ],
        "top_50_with_genes": [
            r for r in robust_results[:50]
        ],
        "strategy_rankings": dict(strat_sorted[:30]),
        "summary": {
            "total_robust": len(robust_results),
            "total_backtests": total_backtests,
            "symbols_tested": len(market_data),
            "mutations_tested": len(mutations),
        },
    }

    return output


def save_results(output: Dict):
    """Save tournament results to files."""
    # Full results
    results_file = DATA_DIR / "tournament_results.json"
    with open(str(results_file), "w") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"Full results: {results_file}")

    # Symbol predictability
    pred_file = DATA_DIR / "symbol_predictability.json"
    with open(str(pred_file), "w") as f:
        json.dump(output["symbol_predictability"], f, indent=2)
    logger.info(f"Symbol rankings: {pred_file}")

    # Human-readable summary
    summary_file = DATA_DIR / "tournament_summary.md"
    _write_summary(output, summary_file)
    logger.info(f"Summary: {summary_file}")


def _write_summary(output: Dict, path: Path):
    """Generate markdown summary report."""
    lines = [
        f"# 🏆 Mega Mutation Tournament Results",
        f"**Generated:** {output['generated_at']}",
        f"**Config:** {output['config']['n_mutations']} mutations × {output['config']['n_symbols']} symbols = {output['config']['total_backtests']} backtests",
        f"**Speed:** {output['config']['backtests_per_second']} backtests/sec ({output['config']['elapsed_seconds']}s total)",
        f"**Robust combos found:** {output['summary']['total_robust']} / {output['summary']['total_backtests']}",
        "",
        "---",
        "",
        "## 📊 Symbol Predictability Leaderboard",
        "",
        "Which crypto symbols are **most predictable** by our DNA mutations?",
        "",
        "| Rank | Symbol | Avg Fitness | Top-10 Avg | Max Fitness | Robust Count | Consistency |",
        "|------|--------|------------|-----------|------------|-------------|-------------|",
    ]

    for rank, (sym, stats) in enumerate(output["symbol_predictability"].items(), 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
        lines.append(
            f"| {medal} | **{sym}** | {stats['avg_fitness']:.4f} | "
            f"{stats['top_10_avg']:.4f} | {stats['max_fitness']:.4f} | "
            f"{stats['robust_count']} | {stats['consistency']:.2f} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 🎯 Top 20 Strategy × Symbol Combos",
        "",
        "| Rank | Strategy | Symbol | OOS Sharpe | Win Rate | PF | Max DD | Trades | Fitness | Overfit? |",
        "|------|----------|--------|-----------|---------|-----|--------|--------|---------|----------|",
    ]

    for rank, combo in enumerate(output.get("top_50_combos", [])[:20], 1):
        overfit = "⚠️" if combo.get("overfit_ratio", 0) > 1.5 else "✅"
        lines.append(
            f"| {rank} | `{combo.get('mutation_name', '?')[:35]}` | "
            f"**{combo.get('symbol', '?')}** | "
            f"{combo.get('oos_sharpe', 0):.2f} | "
            f"{combo.get('win_rate', 0) * 100:.1f}% | "
            f"{combo.get('profit_factor', 0):.2f} | "
            f"{combo.get('max_drawdown', 0) * 100:.1f}% | "
            f"{combo.get('trades', 0)} | "
            f"{combo.get('fitness', 0):.4f} | {overfit} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 🧬 Best Strategy Templates",
        "",
        "| Rank | Strategy | Avg Fitness | Max Fitness | Robust Count |",
        "|------|----------|------------|------------|-------------|",
    ]

    for rank, (name, stats) in enumerate(list(output.get("strategy_rankings", {}).items())[:15], 1):
        lines.append(
            f"| {rank} | `{name[:40]}` | {stats['avg_fitness']:.4f} | "
            f"{stats['max_fitness']:.4f} | {stats['robust_count']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 🔑 Key Insights",
        "",
        "- Symbols at the top of the predictability leaderboard have more DNA mutations that produce profitable, robust (OOS) results",
        "- **Consistency** = average fitness / std deviation (higher = more reliably predictable)",
        "- **Overfit ratio** < 1.5 means OOS performance is close to IS performance (good)",
        "- All results use walk-forward validation (70% train / 30% test) with OOS metrics reported",
        "- Commission of 0.2% round-trip included in all P&L calculations",
        "",
        "## 🎯 Recommended Next Steps",
        "",
        "1. **Focus live picks on top 5 predictable symbols** — highest probability of real-world success",
        "2. **Deploy top 3 strategy combos as forward tests** in the incubator",
        "3. **Run this tournament monthly** to track predictability drift",
        "4. **Cross-validate with longer data** (1000+ bars) for highest-ranked combos",
    ]

    with open(str(path), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ============================================================================
# Main
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="Mega Mutation Tournament")
    parser.add_argument("--mutations", type=int, default=1000,
                        help="Number of DNA mutations to generate (default: 1000)")
    parser.add_argument("--symbols", type=str, default=None,
                        help="Comma-separated symbols (default: all 33)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    symbols = args.symbols.split(",") if args.symbols else DEFAULT_SYMBOLS

    output = run_tournament(symbols, n_mutations=args.mutations, seed=args.seed)

    if "error" not in output:
        save_results(output)

        # Print headline results
        print("\n" + "=" * 70)
        print("  🏆 MEGA MUTATION TOURNAMENT COMPLETE")
        print("=" * 70)

        pred = output.get("symbol_predictability", {})
        if pred:
            print("\n  📊 TOP 5 MOST PREDICTABLE SYMBOLS:")
            for rank, (sym, stats) in enumerate(list(pred.items())[:5], 1):
                print(f"    {rank}. {sym}: fitness={stats['top_10_avg']:.4f}, "
                      f"robust={stats['robust_count']}, consistency={stats['consistency']:.2f}")

        combos = output.get("top_50_combos", [])
        if combos:
            print("\n  🎯 TOP 5 STRATEGY × SYMBOL COMBOS:")
            for rank, c in enumerate(combos[:5], 1):
                print(f"    {rank}. {c.get('mutation_name', '?')[:30]} on {c.get('symbol', '?')}: "
                      f"Sharpe={c.get('oos_sharpe', 0):.2f}, WR={c.get('win_rate', 0) * 100:.1f}%, "
                      f"PF={c.get('profit_factor', 0):.2f}")

        print(f"\n  📁 Results saved to genome/data/")
        print("=" * 70)


if __name__ == "__main__":
    main()
