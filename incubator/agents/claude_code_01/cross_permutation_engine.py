"""
Cross-Permutation Analysis Engine
===================================
Takes top seed strategies, generates parameter permutations,
backtests each on BTC/ETH, and ranks by multi-objective score.

Output: cross_permutation_results.json with ranked strategy combos
"""

import json
import sys
import os
import math
import importlib.util
import traceback
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from dataclasses import dataclass, asdict

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).parent
ROOT = Path(__file__).resolve().parents[3]  # repo root (incubator/agents/claude_code_01/ → 3 levels up)

# Top seed strategies with known good Sharpe (from TIER1)
SEED_STRATEGIES = [
    # Survivor Tier
    {"name": "ConnorsRSI2MeanReversionStrategy", "file": "baby_strategies/connors_rsi2_mean_reversion.py", "sharpe": 1.17},
    {"name": "KeltnerMeanReversionStrategy", "file": "baby_strategies/keltner_mean_reversion.py", "sharpe": 2.06},
    {"name": "ConnorsR3MeanReversionStrategy", "file": "baby_strategies/connors_r3_mean_reversion.py", "sharpe": 1.53},
    {"name": "VolumePriceConfirmationReversalStrategy", "file": "baby_strategies/volume_price_confirmation_reversal.py", "sharpe": 3.93},
    {"name": "BollingerMeanReversionStrategy", "file": "baby_strategies/bollinger_mean_reversion.py", "sharpe": 0.72},
    {"name": "WilliamsRMeanReversionStrategy", "file": "baby_strategies/williams_r_mean_reversion.py", "sharpe": 0.39},
    # Baby Proven
    {"name": "IchimokuCloudBreakoutStrategy", "file": "baby_strategies/ichimoku_cloud_breakout.py", "sharpe": 16.75},
    {"name": "MACDTrendMomentumStrategy", "file": "baby_strategies/macd_trend_momentum.py", "sharpe": 5.90},
    {"name": "MarketStructureVolumeStrategy", "file": "baby_strategies/market_structure_volume.py", "sharpe": 6.22},
    {"name": "AdaptiveMomentumStrategy", "file": "baby_strategies/adaptive_momentum.py", "sharpe": 2.35},
    # Batch 2 Survivors
    {"name": "ConsecutiveDownRsiStrategy", "file": "baby_strategies/consecutive_down_rsi.py", "sharpe": 1.76},
    {"name": "Rsi2BbSqueezeStrategy", "file": "baby_strategies/rsi2_bb_squeeze.py", "sharpe": 1.11},
    # Research
    {"name": "LevineAdaptiveLookbackMomentumStrategy", "file": "baby_strategies/levine_adaptive_lookback_momentum.py", "sharpe": 7.57},
    {"name": "CarterSqueezeBreakoutStrategy", "file": "baby_strategies/carter_squeeze_breakout.py", "sharpe": 5.33},
    {"name": "PairsSpreadBTCETHStrategy", "file": "baby_strategies/pairs_spread_btceth.py", "sharpe": 3.77},
    # High-Sharpe Academic
    {"name": "VolScaledTsmomStrategy", "file": "incubator/agents/claude_code_01/crypto_volscaled_tsmom_v1.py", "sharpe": 7.49},
    {"name": "BettingAgainstBetaStrategy", "file": "incubator/agents/claude_code_01/crypto_betting_against_beta_v1.py", "sharpe": 2.57},
]

# Parameter permutation grid — TP/SL multipliers to test
TP_SL_GRID = [
    {"tp_atr_mult": 1.5, "sl_atr_mult": 0.5},
    {"tp_atr_mult": 1.5, "sl_atr_mult": 1.0},
    {"tp_atr_mult": 2.0, "sl_atr_mult": 0.75},
    {"tp_atr_mult": 2.0, "sl_atr_mult": 1.0},
    {"tp_atr_mult": 2.5, "sl_atr_mult": 1.0},
    {"tp_atr_mult": 2.5, "sl_atr_mult": 1.2},
    {"tp_atr_mult": 3.0, "sl_atr_mult": 1.0},
    {"tp_atr_mult": 3.0, "sl_atr_mult": 1.5},
    {"tp_atr_mult": 3.5, "sl_atr_mult": 1.5},
    {"tp_atr_mult": 4.0, "sl_atr_mult": 1.5},
]

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
KLINE_LIMIT = 500


def fetch_binance_klines(symbol, interval="1d", limit=500):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode())
    except (HTTPError, URLError) as e:
        print(f"  [ERROR] Failed to fetch {symbol}: {e}")
        return None
    return [{"open": float(k[1]), "high": float(k[2]), "low": float(k[3]),
             "close": float(k[4]), "volume": float(k[5])} for k in raw]


def load_strategy_class(file_path, class_name):
    full_path = ROOT / file_path
    if not full_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(class_name, str(full_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[class_name] = mod
    spec.loader.exec_module(mod)
    return getattr(mod, class_name, None)


def backtest_signals(signals_with_idx, prices, max_hold=30):
    wins = 0
    losses = 0
    total_pnl = 0.0
    pnls = []
    max_dd = 0.0
    equity = 100.0
    peak_equity = 100.0

    for sig_idx, sig in signals_with_idx:
        entry = sig.entry_price
        tp = sig.take_profit
        sl = sig.stop_loss
        direction = sig.direction

        outcome = None
        exit_price = entry
        for j in range(sig_idx + 1, min(sig_idx + max_hold, len(prices))):
            bar = prices[j]
            if direction == "BUY":
                if bar["high"] >= tp:
                    outcome = "WIN"; exit_price = tp; break
                if bar["low"] <= sl:
                    outcome = "LOSS"; exit_price = sl; break
            else:
                if bar["low"] <= tp:
                    outcome = "WIN"; exit_price = tp; break
                if bar["high"] >= sl:
                    outcome = "LOSS"; exit_price = sl; break

        if outcome is None:
            exit_price = prices[min(sig_idx + max_hold - 1, len(prices) - 1)]["close"]
            if direction == "BUY":
                outcome = "WIN" if exit_price > entry else "LOSS"
            else:
                outcome = "WIN" if exit_price < entry else "LOSS"

        if direction == "BUY":
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100

        if outcome == "WIN":
            wins += 1
        else:
            losses += 1
        total_pnl += pnl_pct
        pnls.append(pnl_pct)

        # Track equity curve for drawdown
        equity *= (1 + pnl_pct / 100)
        peak_equity = max(peak_equity, equity)
        dd = (peak_equity - equity) / peak_equity * 100
        max_dd = max(max_dd, dd)

    total = wins + losses
    if total == 0:
        return None

    win_rate = wins / total * 100
    avg_pnl = total_pnl / total

    # Sharpe from trade returns
    if len(pnls) >= 2:
        mean_p = sum(pnls) / len(pnls)
        var_p = sum((p - mean_p) ** 2 for p in pnls) / (len(pnls) - 1)
        std_p = math.sqrt(var_p) if var_p > 0 else 0.001
        if std_p < 0.001:
            sharpe = 0.0
        else:
            sharpe_per_trade = mean_p / std_p
            trades_per_year = max(len(pnls) * (365 / 500), 1)
            sharpe = sharpe_per_trade * math.sqrt(trades_per_year)
            sharpe = max(-99.99, min(99.99, sharpe))
    else:
        sharpe = 0

    # Sortino (downside deviation)
    neg_pnls = [p for p in pnls if p < 0]
    if neg_pnls:
        down_var = sum(p ** 2 for p in neg_pnls) / len(neg_pnls)
        down_dev = math.sqrt(down_var) if down_var > 0 else 0.001
        sortino = (sum(pnls) / len(pnls)) / down_dev * math.sqrt(max(len(pnls) * (365 / 500), 1))
    else:
        sortino = sharpe * 2  # No losses

    # Profit factor
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else 99.0

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "total_pnl_pct": round(total_pnl, 2),
        "avg_pnl_pct": round(avg_pnl, 3),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "profit_factor": round(profit_factor, 2),
    }


def compute_composite_score(stats):
    """Multi-objective score: 0.4*Sharpe - 0.3*MaxDD + 0.2*PF + 0.1*WR"""
    sharpe_norm = min(stats["sharpe"] / 5.0, 1.0)  # normalize to 0-1
    dd_norm = min(stats["max_drawdown_pct"] / 30.0, 1.0)
    pf_norm = min(stats["profit_factor"] / 3.0, 1.0)
    wr_norm = stats["win_rate"] / 100.0
    return round(0.4 * sharpe_norm - 0.3 * dd_norm + 0.2 * pf_norm + 0.1 * wr_norm, 4)


def main():
    import pandas as pd
    import numpy as np

    print(f"\n{'='*70}")
    print(f"CROSS-PERMUTATION ANALYSIS ENGINE")
    print(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*70}")
    print(f"Seed strategies: {len(SEED_STRATEGIES)}")
    print(f"TP/SL permutations: {len(TP_SL_GRID)}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Total combos: ~{len(SEED_STRATEGIES) * len(TP_SL_GRID) * len(SYMBOLS)}")
    print()

    # Fetch market data
    market_data = {}
    for sym in SYMBOLS:
        print(f"Fetching {sym}...")
        rows = fetch_binance_klines(sym, "1d", KLINE_LIMIT)
        if rows:
            market_data[sym] = rows
            print(f"  Got {len(rows)} bars")

    if not market_data:
        print("No data. Exiting.")
        return

    all_results = []
    loaded_cache = {}

    for seed in SEED_STRATEGIES:
        strat_name = seed["name"]
        strat_file = seed["file"]
        print(f"\n--- {strat_name} (base Sharpe: {seed['sharpe']}) ---")

        # Load strategy class
        if strat_name not in loaded_cache:
            try:
                cls = load_strategy_class(strat_file, strat_name)
                if cls is None:
                    print(f"  File not found: {strat_file}")
                    continue
                loaded_cache[strat_name] = cls
            except Exception as e:
                print(f"  Load error: {e}")
                continue
        cls = loaded_cache[strat_name]

        for perm_idx, perm in enumerate(TP_SL_GRID):
            # Create strategy with permuted params
            try:
                strategy = cls(perm)
            except TypeError:
                try:
                    strategy = cls()
                except Exception:
                    continue

            combo_results = {}
            for sym, rows in market_data.items():
                try:
                    df = pd.DataFrame(rows)
                    signals_with_idx = []
                    start = min(280, len(df) - 20)
                    for i in range(start, len(df)):
                        window = df.iloc[:i+1].copy().reset_index(drop=True)
                        sigs = strategy.generate_signals(window, sym)
                        if sigs:
                            signals_with_idx.append((i, sigs[-1]))

                    if not signals_with_idx:
                        continue

                    stats = backtest_signals(signals_with_idx, rows)
                    if stats:
                        combo_results[sym] = stats
                except Exception as e:
                    pass  # Skip broken combos silently

            if not combo_results:
                continue

            # Combined score across both symbols
            if len(combo_results) == 2:
                combined_sharpe = sum(s["sharpe"] for s in combo_results.values()) / 2
                combined_dd = max(s["max_drawdown_pct"] for s in combo_results.values())
                combined_pf = sum(s["profit_factor"] for s in combo_results.values()) / 2
                combined_wr = sum(s["win_rate"] for s in combo_results.values()) / 2
                combined_pnl = sum(s["total_pnl_pct"] for s in combo_results.values())
                combined_trades = sum(s["total_trades"] for s in combo_results.values())

                combined_stats = {
                    "sharpe": round(combined_sharpe, 2),
                    "max_drawdown_pct": round(combined_dd, 2),
                    "profit_factor": round(combined_pf, 2),
                    "win_rate": round(combined_wr, 1),
                }
                combined_score = compute_composite_score(combined_stats)
            else:
                sym_name = list(combo_results.keys())[0]
                combined_score = compute_composite_score(combo_results[sym_name])
                combined_pnl = combo_results[sym_name]["total_pnl_pct"]
                combined_trades = combo_results[sym_name]["total_trades"]

            result = {
                "strategy": strat_name,
                "params": perm,
                "combined_score": combined_score,
                "combined_pnl": round(combined_pnl, 2),
                "combined_trades": combined_trades,
                "per_symbol": combo_results,
            }
            all_results.append(result)

        print(f"  Tested {len(TP_SL_GRID)} permutations")

    # Sort by combined score
    all_results.sort(key=lambda x: x["combined_score"], reverse=True)

    # Print top 30
    print(f"\n{'='*70}")
    print("TOP 30 STRATEGY-PARAMETER COMBINATIONS")
    print(f"{'='*70}")
    print(f"{'Rank':<5} {'Strategy':<40} {'TP/SL':>10} {'Score':>7} {'PnL%':>8} {'Trades':>7}")
    print("-" * 80)
    for i, r in enumerate(all_results[:30], 1):
        tp = r["params"].get("tp_atr_mult", "?")
        sl = r["params"].get("sl_atr_mult", "?")
        sym_detail = ""
        for sym, stats in r["per_symbol"].items():
            sym_detail += f" | {sym[:3]}:S{stats['sharpe']}/WR{stats['win_rate']}%/DD{stats['max_drawdown_pct']}%"
        print(f"{i:<5} {r['strategy'][:40]:<40} {tp}/{sl}    {r['combined_score']:>6.4f} {r['combined_pnl']:>+7.1f}% {r['combined_trades']:>6}")
        if sym_detail:
            print(f"      {sym_detail.strip()}")

    # Save results
    output = SCRIPT_DIR / "cross_permutation_results.json"
    with open(output, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {output}")
    print(f"Total combos evaluated: {len(all_results)}")

    # Export top 15 as incubator candidates
    candidates = all_results[:15]
    candidates_file = SCRIPT_DIR / "cross_perm_incubator_candidates.json"
    with open(candidates_file, "w") as f:
        json.dump(candidates, f, indent=2)
    print(f"Top 15 incubator candidates saved to: {candidates_file}")

    return all_results


if __name__ == "__main__":
    main()
