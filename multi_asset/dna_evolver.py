#!/usr/bin/env python3
"""
MULTI-ASSET DNA EVOLVER
========================
Evolves strategy parameters per asset class using the genome/dna_engine.py
infrastructure. Creates asset-specific and generic strategies, backtests them,
and outputs evolved picks alongside the static scanner strategies.

Architecture:
  1. Define gene space per asset class (TP/SL multipliers, RSI thresholds, etc.)
  2. Create initial population from proven base strategies
  3. Walk-forward backtest each candidate
  4. Select winners, mutate, crossover for next generation
  5. Output evolved picks to multi_asset/data/evolved_picks.json
"""

from __future__ import annotations

import json
import copy
import hashlib
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance required")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Gene definitions per asset class
# ---------------------------------------------------------------------------

# Base gene ranges that apply to all assets
BASE_GENES = {
    "rsi_period":    {"min": 2,   "max": 21,  "type": "int"},
    "rsi_oversold":  {"min": 5,   "max": 40,  "type": "int"},
    "rsi_overbought":{"min": 60,  "max": 95,  "type": "int"},
    "ema_fast":      {"min": 5,   "max": 30,  "type": "int"},
    "ema_slow":      {"min": 20,  "max": 100, "type": "int"},
    "bb_period":     {"min": 10,  "max": 30,  "type": "int"},
    "bb_std":        {"min": 1.5, "max": 3.0, "type": "float"},
    "atr_mult_tp":   {"min": 1.0, "max": 5.0, "type": "float"},
    "atr_mult_sl":   {"min": 0.5, "max": 2.5, "type": "float"},
    "adx_threshold": {"min": 15,  "max": 40,  "type": "int"},
    "macd_fast":     {"min": 8,   "max": 16,  "type": "int"},
    "macd_slow":     {"min": 20,  "max": 30,  "type": "int"},
    "macd_signal":   {"min": 5,   "max": 12,  "type": "int"},
    "max_hold_days":  {"min": 3,   "max": 20,  "type": "int"},
}

# Asset-class-specific risk genes
ASSET_RISK_GENES = {
    "futures": {
        "tp_pct": {"min": 0.03, "max": 0.10, "type": "float"},
        "sl_pct": {"min": 0.02, "max": 0.05, "type": "float"},
    },
    "stock": {
        "tp_pct": {"min": 0.05, "max": 0.15, "type": "float"},
        "sl_pct": {"min": 0.03, "max": 0.08, "type": "float"},
    },
    "forex": {
        "tp_pct": {"min": 0.01, "max": 0.04, "type": "float"},
        "sl_pct": {"min": 0.005, "max": 0.02, "type": "float"},
    },
    "etf": {
        "tp_pct": {"min": 0.05, "max": 0.12, "type": "float"},
        "sl_pct": {"min": 0.03, "max": 0.06, "type": "float"},
    },
    "penny": {
        "tp_pct": {"min": 0.08, "max": 0.25, "type": "float"},
        "sl_pct": {"min": 0.05, "max": 0.12, "type": "float"},
    },
}

# Proven seed strategies (from backtest results)
SEED_STRATEGIES = [
    {
        "name": "connors_rsi2",
        "genes": {"rsi_period": 2, "rsi_oversold": 10, "rsi_overbought": 90,
                  "ema_fast": 5, "ema_slow": 200, "bb_period": 20, "bb_std": 2.0,
                  "atr_mult_tp": 3.0, "atr_mult_sl": 1.5, "adx_threshold": 20,
                  "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
                  "max_hold_days": 5},
    },
    {
        "name": "mean_reversion",
        "genes": {"rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70,
                  "ema_fast": 9, "ema_slow": 50, "bb_period": 20, "bb_std": 2.0,
                  "atr_mult_tp": 2.0, "atr_mult_sl": 1.0, "adx_threshold": 25,
                  "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
                  "max_hold_days": 10},
    },
    {
        "name": "ema_momentum",
        "genes": {"rsi_period": 14, "rsi_oversold": 40, "rsi_overbought": 60,
                  "ema_fast": 9, "ema_slow": 21, "bb_period": 20, "bb_std": 2.0,
                  "atr_mult_tp": 2.5, "atr_mult_sl": 1.0, "adx_threshold": 20,
                  "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
                  "max_hold_days": 15},
    },
]

# Symbol universes per asset class
SYMBOLS = {
    "futures": ["ES=F", "NQ=F", "YM=F", "CL=F", "GC=F", "SI=F", "ZN=F"],
    "stock":   ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "V"],
    "forex":   ["EURUSD=X", "USDJPY=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X"],
    "etf":     ["SPY", "QQQ", "XLK", "XLF", "XLE", "GLD", "TLT", "IWM",
                # Leveraged 3x bull/bear pairs for tactical regime plays
                "TQQQ", "SQQQ", "SPXL", "SPXS", "FAS", "FAZ", "SOXL", "SOXS",
                "TNA", "TZA", "LABU", "LABD", "NUGT", "DUST", "UVXY", "SVXY"],
    "penny":   ["SOFI", "NIO", "PLTR", "MARA", "RIOT", "IONQ"],
}


# ---------------------------------------------------------------------------
# Technical indicators (lightweight, same as scanner.py)
# ---------------------------------------------------------------------------
def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()

def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def rsi(s: pd.Series, n: int) -> pd.Series:
    delta = s.diff()
    gain = delta.clip(lower=0).rolling(n).mean()
    loss = (-delta.clip(upper=0)).rolling(n).mean()
    rs = gain / loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))

def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"].shift(1)
    tr = pd.concat([h - l, (h - c).abs(), (l - c).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def bollinger_bands(s: pd.Series, n: int, std_mult: float):
    mid = sma(s, n)
    std = s.rolling(n).std()
    return mid, mid + std_mult * std, mid - std_mult * std

def macd(s: pd.Series, fast: int, slow: int, signal: int):
    ema_fast = ema(s, fast)
    ema_slow = ema(s, slow)
    macd_line = ema_fast - ema_slow
    sig_line = ema(macd_line, signal)
    return macd_line, sig_line, macd_line - sig_line

def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    plus_dm = (h - h.shift(1)).clip(lower=0)
    minus_dm = (l.shift(1) - l).clip(lower=0)
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    atr_val = tr.rolling(n).mean()
    plus_di = 100 * (plus_dm.rolling(n).mean() / atr_val.replace(0, 1e-10))
    minus_di = 100 * (minus_dm.rolling(n).mean() / atr_val.replace(0, 1e-10))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-10)
    return dx.rolling(n).mean()


# ---------------------------------------------------------------------------
# DNA Strategy evaluation
# ---------------------------------------------------------------------------
def evaluate_strategy(genes: dict, df: pd.DataFrame, asset_class: str,
                      tp_pct: float, sl_pct: float) -> dict:
    """
    Backtest a DNA-parameterized strategy on historical data.
    Returns fitness metrics: trades, win_rate, sharpe, sortino, profit_factor, etc.
    """
    close = df["Close"]
    max_hold = genes.get("max_hold_days", 10)
    min_window = max(genes.get("ema_slow", 200), 50) + 10

    if len(df) < min_window + 20:
        return {"trades": 0, "win_rate": 0, "sharpe": 0, "sortino": 0, "fitness": 0}

    # Compute indicators with DNA parameters
    rsi_vals = rsi(close, genes["rsi_period"])
    ema_fast_vals = ema(close, genes["ema_fast"])
    ema_slow_vals = ema(close, genes["ema_slow"])
    bb_mid, bb_upper, bb_lower = bollinger_bands(close, genes["bb_period"], genes["bb_std"])
    macd_line, macd_sig, macd_hist = macd(close, genes["macd_fast"], genes["macd_slow"], genes["macd_signal"])
    adx_vals = adx(df, 14)
    atr_vals = atr(df, 14)

    trades = []
    step = 3

    for i in range(min_window, len(df) - max_hold, step):
        r = rsi_vals.iloc[i]
        ef = ema_fast_vals.iloc[i]
        es = ema_slow_vals.iloc[i]
        bl = bb_lower.iloc[i]
        mh = macd_hist.iloc[i]
        adx_v = adx_vals.iloc[i]
        entry_price = float(close.iloc[i])

        if pd.isna(r) or pd.isna(ef) or pd.isna(es) or pd.isna(bl):
            continue

        # Signal logic: combine multiple conditions with DNA params
        signal = None

        # Connors RSI2 variant
        if r < genes["rsi_oversold"] and ef > es:
            signal = "LONG"
        # Mean reversion: price below lower BB + RSI oversold
        elif close.iloc[i] < bl and r < genes["rsi_oversold"] + 10:
            signal = "LONG"
        # MACD momentum + trend
        elif mh > 0 and ef > es and adx_v > genes["adx_threshold"]:
            signal = "LONG"
        # Overbought short (only for certain assets)
        elif r > genes["rsi_overbought"] and ef < es and asset_class in ("futures", "forex"):
            signal = "SHORT"

        if signal is None:
            continue

        # Simulate trade
        tp = entry_price * (1 + tp_pct) if signal == "LONG" else entry_price * (1 - tp_pct)
        sl = entry_price * (1 - sl_pct) if signal == "LONG" else entry_price * (1 + sl_pct)

        future = df.iloc[i + 1:i + 1 + max_hold]
        pnl = 0
        exit_reason = "TIME_EXPIRY"

        for j in range(len(future)):
            bar_h = float(future["High"].iloc[j])
            bar_l = float(future["Low"].iloc[j])

            if signal == "LONG":
                if bar_l <= sl:
                    pnl = -sl_pct
                    exit_reason = "STOP_LOSS"
                    break
                if bar_h >= tp:
                    pnl = tp_pct
                    exit_reason = "TAKE_PROFIT"
                    break
            else:
                if bar_h >= sl:
                    pnl = -sl_pct
                    exit_reason = "STOP_LOSS"
                    break
                if bar_l <= tp:
                    pnl = tp_pct
                    exit_reason = "TAKE_PROFIT"
                    break

        if pnl == 0:
            exit_price = float(future["Close"].iloc[-1]) if len(future) > 0 else entry_price
            pnl = (exit_price / entry_price - 1) if signal == "LONG" else (1 - exit_price / entry_price)

        trades.append(pnl)

    if len(trades) < 3:
        return {"trades": len(trades), "win_rate": 0, "sharpe": 0, "sortino": 0, "fitness": 0}

    pnls = np.array(trades)
    wins = int(np.sum(pnls > 0))
    wr = wins / len(pnls)
    mean_pnl = float(np.mean(pnls))
    std_pnl = float(np.std(pnls)) if len(pnls) > 1 else 1.0
    ann = np.sqrt(50)

    sharpe = (mean_pnl / std_pnl) * ann if std_pnl > 0 else 0
    downside = pnls[pnls < 0]
    d_std = float(np.std(downside)) if len(downside) > 1 else 1.0
    sortino = (mean_pnl / d_std) * ann if d_std > 0 else 0

    gross_w = float(np.sum(pnls[pnls > 0])) if np.any(pnls > 0) else 0
    gross_l = float(np.abs(np.sum(pnls[pnls < 0]))) if np.any(pnls < 0) else 1.0
    pf = gross_w / gross_l if gross_l > 0 else 0

    # Max drawdown
    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    max_dd = float(np.max(peak - equity)) if len(equity) > 0 else 0

    # Composite fitness: WR(30) + Sortino(25) + Sharpe(15) + PF(15) + LowDD(15)
    fitness = (wr * 30) + (min(sortino, 5) / 5 * 25) + (min(sharpe, 5) / 5 * 15) + \
              (min(pf, 3) / 3 * 15) + ((1 - min(max_dd, 1)) * 15)

    return {
        "trades": len(trades),
        "wins": wins,
        "win_rate": round(wr, 4),
        "sharpe": round(float(sharpe), 2),
        "sortino": round(float(sortino), 2),
        "profit_factor": round(float(pf), 2),
        "max_dd": round(max_dd, 4),
        "mean_pnl": round(float(mean_pnl), 4),
        "total_return": round(float(np.sum(pnls)), 4),
        "fitness": round(float(fitness), 2),
    }


# ---------------------------------------------------------------------------
# Genetic operators
# ---------------------------------------------------------------------------
def random_gene_value(gene_def: dict) -> Any:
    if gene_def["type"] == "int":
        return random.randint(gene_def["min"], gene_def["max"])
    return round(random.uniform(gene_def["min"], gene_def["max"]), 4)


def mutate(genes: dict, asset_class: str, rate: float = 0.2) -> dict:
    """Mutate a fraction of genes with jitter or random replacement."""
    child = copy.deepcopy(genes)
    all_defs = {**BASE_GENES, **ASSET_RISK_GENES.get(asset_class, {})}

    for key, gdef in all_defs.items():
        if key not in child:
            continue
        if random.random() > rate:
            continue

        # 50% chance: jitter (±15%), 50% chance: random
        if random.random() < 0.5:
            val = child[key]
            jitter = val * random.uniform(-0.15, 0.15)
            new_val = val + jitter
            if gdef["type"] == "int":
                new_val = int(round(new_val))
            new_val = max(gdef["min"], min(gdef["max"], new_val))
            child[key] = round(new_val, 4) if gdef["type"] == "float" else int(new_val)
        else:
            child[key] = random_gene_value(gdef)

    return child


def crossover(parent_a: dict, parent_b: dict) -> dict:
    """Uniform crossover: each gene randomly from parent A or B."""
    child = {}
    for key in set(parent_a.keys()) | set(parent_b.keys()):
        if key in parent_a and key in parent_b:
            child[key] = parent_a[key] if random.random() < 0.5 else parent_b[key]
        elif key in parent_a:
            child[key] = parent_a[key]
        else:
            child[key] = parent_b[key]
    return child


# ---------------------------------------------------------------------------
# Evolution engine
# ---------------------------------------------------------------------------
def evolve_for_asset_class(
    asset_class: str,
    symbols: list[str],
    generations: int = 10,
    population_size: int = 20,
    elite_ratio: float = 0.2,
) -> list[dict]:
    """
    Run a genetic algorithm to evolve strategy parameters for a given asset class.
    Returns top N strategies with their fitness scores.
    """
    print(f"\n{'='*60}")
    print(f"  DNA EVOLUTION: {asset_class.upper()} ({len(symbols)} symbols)")
    print(f"  Pop={population_size}, Gen={generations}, Elite={elite_ratio}")
    print(f"{'='*60}")

    risk_genes = ASSET_RISK_GENES.get(asset_class, ASSET_RISK_GENES["stock"])

    # Fetch data for all symbols
    data = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            df = ticker.history(period="1y", interval="1d")
            if df is not None and len(df) > 100:
                data[sym] = df
                print(f"  [data] {sym}: {len(df)} bars")
        except Exception as e:
            print(f"  [data] {sym}: FAILED ({e})")

    if not data:
        print("  NO DATA — skipping evolution")
        return []

    # Initialize population from seed strategies
    population = []
    for seed in SEED_STRATEGIES:
        genes = copy.deepcopy(seed["genes"])
        # Add asset-specific risk params
        genes["tp_pct"] = (risk_genes["tp_pct"]["min"] + risk_genes["tp_pct"]["max"]) / 2
        genes["sl_pct"] = (risk_genes["sl_pct"]["min"] + risk_genes["sl_pct"]["max"]) / 2
        population.append({"name": seed["name"], "genes": genes, "fitness": 0})

    # Fill rest with mutations of seeds
    while len(population) < population_size:
        parent = random.choice(SEED_STRATEGIES)
        genes = mutate(copy.deepcopy(parent["genes"]), asset_class, rate=0.4)
        genes["tp_pct"] = random_gene_value(risk_genes["tp_pct"])
        genes["sl_pct"] = random_gene_value(risk_genes["sl_pct"])
        population.append({
            "name": f"{parent['name']}_mut{len(population)}",
            "genes": genes,
            "fitness": 0,
        })

    # Evolution loop
    for gen in range(generations):
        # Evaluate all candidates across all symbols
        for ind in population:
            total_fitness = 0
            total_count = 0
            for sym, df in data.items():
                tp = ind["genes"].get("tp_pct", 0.08)
                sl = ind["genes"].get("sl_pct", 0.04)
                result = evaluate_strategy(ind["genes"], df, asset_class, tp, sl)
                if result["trades"] >= 3:
                    total_fitness += result["fitness"]
                    total_count += 1
                    ind["last_result"] = result

            ind["fitness"] = total_fitness / max(total_count, 1)

        # Sort by fitness
        population.sort(key=lambda x: x["fitness"], reverse=True)

        best = population[0]
        avg_fit = np.mean([p["fitness"] for p in population])
        print(f"  Gen {gen+1}/{generations}: best={best['fitness']:.1f} "
              f"({best['name']}), avg={avg_fit:.1f}")

        # Select elite
        n_elite = max(2, int(len(population) * elite_ratio))
        elite = population[:n_elite]

        # Create next generation
        next_gen = copy.deepcopy(elite)  # keep elite

        while len(next_gen) < population_size:
            if random.random() < 0.7:
                # Crossover two parents from top 50%
                p1 = random.choice(population[:len(population) // 2])
                p2 = random.choice(population[:len(population) // 2])
                child_genes = crossover(p1["genes"], p2["genes"])
                child_genes = mutate(child_genes, asset_class, rate=0.15)
                next_gen.append({
                    "name": f"x_{p1['name'][:8]}_{p2['name'][:8]}",
                    "genes": child_genes,
                    "fitness": 0,
                })
            else:
                # Mutate a random elite
                parent = random.choice(elite)
                child_genes = mutate(parent["genes"], asset_class, rate=0.25)
                next_gen.append({
                    "name": f"m_{parent['name'][:12]}",
                    "genes": child_genes,
                    "fitness": 0,
                })

        population = next_gen

    # Final evaluation
    for ind in population:
        total_fitness = 0
        total_count = 0
        best_result = None
        for sym, df in data.items():
            tp = ind["genes"].get("tp_pct", 0.08)
            sl = ind["genes"].get("sl_pct", 0.04)
            result = evaluate_strategy(ind["genes"], df, asset_class, tp, sl)
            if result["trades"] >= 3:
                total_fitness += result["fitness"]
                total_count += 1
                if best_result is None or result["fitness"] > best_result.get("fitness", 0):
                    best_result = result
        ind["fitness"] = total_fitness / max(total_count, 1)
        ind["best_result"] = best_result or {}

    population.sort(key=lambda x: x["fitness"], reverse=True)

    # Return top strategies
    top = population[:5]
    print(f"\n  TOP {len(top)} EVOLVED STRATEGIES:")
    for i, s in enumerate(top):
        r = s.get("best_result", {})
        print(f"    #{i+1} {s['name']}: fitness={s['fitness']:.1f}, "
              f"WR={r.get('win_rate', 0)*100:.1f}%, "
              f"Sharpe={r.get('sharpe', 0)}, Sortino={r.get('sortino', 0)}")

    return top


def run_evolution(asset_classes: list[str] | None = None):
    """Run evolution across specified asset classes."""
    if asset_classes is None:
        asset_classes = list(SYMBOLS.keys())

    all_results = {}
    start = time.time()

    for ac in asset_classes:
        syms = SYMBOLS.get(ac, [])
        if not syms:
            continue
        top = evolve_for_asset_class(ac, syms, generations=8, population_size=15)
        all_results[ac] = [
            {
                "name": s["name"],
                "asset_class": ac.upper(),
                "fitness": s["fitness"],
                "genes": s["genes"],
                "result": s.get("best_result", {}),
                "evolved_at": datetime.now(timezone.utc).isoformat(),
            }
            for s in top
        ]

    # Save results
    output_file = SCRIPT_DIR / "data" / "evolved_strategies.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    elapsed = time.time() - start
    total_strats = sum(len(v) for v in all_results.values())
    print(f"\n{'='*60}")
    print(f"  EVOLUTION COMPLETE: {total_strats} strategies across {len(all_results)} classes")
    print(f"  Saved to: {output_file}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"{'='*60}")

    return all_results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Asset DNA Evolver")
    parser.add_argument("--futures", action="store_true")
    parser.add_argument("--forex", action="store_true")
    parser.add_argument("--stocks", action="store_true")
    parser.add_argument("--etfs", action="store_true")
    parser.add_argument("--penny", action="store_true")
    parser.add_argument("--all", action="store_true", default=True)
    args = parser.parse_args()

    classes = []
    if args.futures:
        classes.append("futures")
    if args.forex:
        classes.append("forex")
    if args.stocks:
        classes.append("stock")
    if args.etfs:
        classes.append("etf")
    if args.penny:
        classes.append("penny")

    if not classes:
        classes = None  # all

    run_evolution(classes)
