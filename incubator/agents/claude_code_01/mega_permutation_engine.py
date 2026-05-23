"""
Mega Cross-Permutation Engine v2
==================================
Expands to 1000s of combinations by:
1. Testing 15+ seed strategies across expanded TP/SL/lookback grids
2. Layering additional technical filters (volume, oscillators, trend)
3. Multi-objective ranking with Sharpe, DD, PF, WR
4. Creating new combo strategies from top findings

Total target: ~2000-5000 permutations across BTC + ETH
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
from itertools import product

if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).parent

# === SEED STRATEGIES ===
SEED_STRATEGIES = [
    {"name": "ConnorsRSI2MeanReversionStrategy", "file": "baby_strategies/connors_rsi2_mean_reversion.py", "sharpe": 1.17, "type": "mean_reversion"},
    {"name": "KeltnerMeanReversionStrategy", "file": "baby_strategies/keltner_mean_reversion.py", "sharpe": 2.06, "type": "mean_reversion"},
    {"name": "ConnorsR3MeanReversionStrategy", "file": "baby_strategies/connors_r3_mean_reversion.py", "sharpe": 1.53, "type": "mean_reversion"},
    {"name": "VolumePriceConfirmationReversalStrategy", "file": "baby_strategies/volume_price_confirmation_reversal.py", "sharpe": 3.93, "type": "reversal"},
    {"name": "BollingerMeanReversionStrategy", "file": "baby_strategies/bollinger_mean_reversion.py", "sharpe": 0.72, "type": "mean_reversion"},
    {"name": "WilliamsRMeanReversionStrategy", "file": "baby_strategies/williams_r_mean_reversion.py", "sharpe": 0.39, "type": "mean_reversion"},
    {"name": "MarketStructureVolumeStrategy", "file": "baby_strategies/market_structure_volume.py", "sharpe": 6.22, "type": "breakout"},
    {"name": "AdaptiveMomentumStrategy", "file": "baby_strategies/adaptive_momentum.py", "sharpe": 2.35, "type": "momentum"},
    {"name": "ConsecutiveDownRsiStrategy", "file": "baby_strategies/consecutive_down_rsi.py", "sharpe": 1.76, "type": "mean_reversion"},
    {"name": "Rsi2BbSqueezeStrategy", "file": "baby_strategies/rsi2_bb_squeeze.py", "sharpe": 1.11, "type": "mean_reversion"},
    {"name": "LevineAdaptiveLookbackMomentumStrategy", "file": "baby_strategies/levine_adaptive_lookback_momentum.py", "sharpe": 7.57, "type": "momentum"},
    {"name": "CarterSqueezeBreakoutStrategy", "file": "baby_strategies/carter_squeeze_breakout.py", "sharpe": 5.33, "type": "breakout"},
    {"name": "PairsSpreadBTCETHStrategy", "file": "baby_strategies/pairs_spread_btceth.py", "sharpe": 3.77, "type": "stat_arb"},
    {"name": "VolScaledTsmomStrategy", "file": "incubator/agents/claude_code_01/crypto_volscaled_tsmom_v1.py", "sharpe": 7.49, "type": "momentum"},
    {"name": "BettingAgainstBetaStrategy", "file": "incubator/agents/claude_code_01/crypto_betting_against_beta_v1.py", "sharpe": 2.57, "type": "vol_regime"},
    {"name": "VolatilityScaledMomentumStrategy", "file": "baby_strategies/volatility_scaled_momentum.py", "sharpe": 0.32, "type": "momentum"},
    {"name": "RSIVolumeMeanReversionStrategy", "file": "baby_strategies/rsi_volume_mean_reversion.py", "sharpe": 0.70, "type": "mean_reversion"},
    {"name": "SMA50RegimeFilterStrategy", "file": "baby_strategies/sma50_regime_filter.py", "sharpe": 1.9, "type": "regime"},
    {"name": "RedCandleMeanReversionStrategy", "file": "baby_strategies/red_candle_mean_reversion.py", "sharpe": 1.8, "type": "mean_reversion"},
    {"name": "DualMomentumCryptoStrategy", "file": "baby_strategies/dual_momentum_crypto.py", "sharpe": 1.0, "type": "momentum"},
    {"name": "NR7VolatilityBreakoutStrategy", "file": "baby_strategies/nr7_volatility_breakout.py", "sharpe": 0.0, "type": "breakout"},
    {"name": "VelocityGainerStrategy", "file": "incubator/agents/claude_code_01/crypto_velocity_gainer_v1.py", "sharpe": 0.0, "type": "gainer"},
    {"name": "GainerPredictor1hStrategy", "file": "incubator/agents/claude_code_01/crypto_gainer_predictor_1h_v1.py", "sharpe": 0.0, "type": "gainer"},
]

# === EXPANDED PARAMETER GRID ===
TP_VALUES = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
SL_VALUES = [0.3, 0.5, 0.75, 1.0, 1.2, 1.5, 2.0]

# Technical filter layers
TECH_LAYERS = [
    {"name": "none", "filter": None},
    {"name": "vol_above_avg", "filter": "volume_above_avg"},
    {"name": "rsi_not_overbought", "filter": "rsi_below_70"},
    {"name": "ema_trend_aligned", "filter": "ema_20_above_50"},
    {"name": "atr_expanding", "filter": "atr_expanding"},
    {"name": "macd_positive", "filter": "macd_hist_positive"},
    {"name": "bb_not_upper", "filter": "bb_below_upper"},
    {"name": "obv_rising", "filter": "obv_slope_positive"},
]

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
KLINE_LIMIT = 500


def fetch_binance_klines(symbol, interval="1d", limit=500):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (HTTPError, URLError) as e:
        print(f"  [ERROR] {symbol}: {e}")
        return None


def parse_klines(raw):
    return [{"open": float(k[1]), "high": float(k[2]), "low": float(k[3]),
             "close": float(k[4]), "volume": float(k[5])} for k in raw]


def load_strategy_class(file_path, class_name):
    full_path = ROOT / file_path
    if not full_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(class_name, str(full_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[class_name + "_mod"] = mod
    spec.loader.exec_module(mod)
    return getattr(mod, class_name, None)


def apply_tech_filter(data, signals_with_idx, filter_name):
    """Apply a technical filter layer to reduce false signals."""
    import pandas as pd
    import numpy as np

    if filter_name is None or not signals_with_idx:
        return signals_with_idx

    df = pd.DataFrame(data)
    close = df['close'].astype(float)
    volume = df['volume'].astype(float)

    filtered = []
    for idx, sig in signals_with_idx:
        if idx >= len(df):
            continue
        passes = True

        if filter_name == "volume_above_avg":
            avg_vol = volume.iloc[max(0, idx-20):idx].mean()
            passes = volume.iloc[idx] > avg_vol if avg_vol > 0 else True

        elif filter_name == "rsi_below_70":
            if idx >= 14:
                delta = close.diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = (-delta.clip(upper=0)).rolling(14).mean()
                rs = gain.iloc[idx] / (loss.iloc[idx] + 1e-9)
                rsi = 100 - (100 / (1 + rs))
                passes = rsi < 70

        elif filter_name == "ema_20_above_50":
            if idx >= 50:
                ema20 = close.ewm(span=20).mean().iloc[idx]
                ema50 = close.ewm(span=50).mean().iloc[idx]
                if sig.direction == "BUY":
                    passes = ema20 > ema50
                else:
                    passes = ema20 < ema50

        elif filter_name == "atr_expanding":
            if idx >= 28:
                tr = pd.concat([
                    df['high'].astype(float) - df['low'].astype(float),
                    (df['high'].astype(float) - close.shift()).abs(),
                    (df['low'].astype(float) - close.shift()).abs()
                ], axis=1).max(axis=1)
                atr14 = tr.rolling(14).mean()
                atr14_avg = atr14.iloc[max(0, idx-50):idx].mean()
                passes = atr14.iloc[idx] > atr14_avg * 1.1 if atr14_avg > 0 else True

        elif filter_name == "macd_hist_positive":
            if idx >= 26:
                ema12 = close.ewm(span=12).mean()
                ema26 = close.ewm(span=26).mean()
                macd_line = ema12 - ema26
                signal_line = macd_line.ewm(span=9).mean()
                hist = macd_line.iloc[idx] - signal_line.iloc[idx]
                if sig.direction == "BUY":
                    passes = hist > 0
                else:
                    passes = hist < 0

        elif filter_name == "bb_below_upper":
            if idx >= 20:
                sma20 = close.rolling(20).mean().iloc[idx]
                std20 = close.rolling(20).std().iloc[idx]
                upper = sma20 + 2 * std20
                if sig.direction == "BUY":
                    passes = close.iloc[idx] < upper
                else:
                    passes = close.iloc[idx] > sma20 - 2 * std20

        elif filter_name == "obv_slope_positive":
            if idx >= 10:
                direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
                obv = (direction * volume).cumsum()
                slope = obv.iloc[idx] - obv.iloc[idx-10]
                if sig.direction == "BUY":
                    passes = slope > 0
                else:
                    passes = slope < 0

        if passes:
            filtered.append((idx, sig))

    return filtered


def backtest_signals(signals_with_idx, prices, tp_mult=None, sl_mult=None, max_hold=30):
    """Backtest with optional TP/SL override."""
    wins = 0
    losses = 0
    pnls = []
    equity = 100.0
    peak_equity = 100.0
    max_dd = 0.0

    for sig_idx, sig in signals_with_idx:
        entry = sig.entry_price
        tp = sig.take_profit
        sl = sig.stop_loss
        direction = sig.direction

        # Override TP/SL if provided
        if tp_mult is not None and sl_mult is not None and entry > 0:
            # Estimate ATR from TP/SL spread
            orig_tp_dist = abs(tp - entry)
            orig_sl_dist = abs(sl - entry)
            avg_dist = (orig_tp_dist + orig_sl_dist) / 2
            if avg_dist > 0:
                atr_est = avg_dist
            else:
                atr_est = entry * 0.02
            if direction == "BUY":
                tp = entry + atr_est * tp_mult
                sl = entry - atr_est * sl_mult
            else:
                tp = entry - atr_est * tp_mult
                sl = entry + atr_est * sl_mult

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

        pnl_pct = ((exit_price - entry) / entry * 100) if direction == "BUY" else ((entry - exit_price) / entry * 100)
        wins += 1 if outcome == "WIN" else 0
        losses += 1 if outcome == "LOSS" else 0
        pnls.append(pnl_pct)
        equity *= (1 + pnl_pct / 100)
        peak_equity = max(peak_equity, equity)
        max_dd = max(max_dd, (peak_equity - equity) / peak_equity * 100)

    total = wins + losses
    if total < 2:
        return None

    win_rate = wins / total * 100
    mean_p = sum(pnls) / len(pnls)
    var_p = sum((p - mean_p) ** 2 for p in pnls) / (len(pnls) - 1)
    std_p = math.sqrt(var_p) if var_p > 0 else 0.001
    if std_p < 0.001:
        sharpe = 0.0
    else:
        sharpe = (mean_p / std_p) * math.sqrt(max(len(pnls) * 365 / 500, 1))
        sharpe = max(-99.99, min(99.99, sharpe))

    neg_pnls = [p for p in pnls if p < 0]
    if neg_pnls:
        down_dev = math.sqrt(sum(p**2 for p in neg_pnls) / len(neg_pnls))
        sortino = mean_p / (down_dev if down_dev > 0 else 0.001) * math.sqrt(max(len(pnls) * 365 / 500, 1))
        sortino = max(-99.99, min(99.99, sortino))
    else:
        sortino = sharpe * 2

    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    pf = gross_win / gross_loss if gross_loss > 0 else 99.0

    return {
        "trades": total, "wins": wins, "losses": losses,
        "win_rate": round(win_rate, 1), "pnl": round(sum(pnls), 2),
        "avg_pnl": round(mean_p, 3), "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2), "max_dd": round(max_dd, 2),
        "profit_factor": round(pf, 2),
    }


def composite_score(s):
    sh = min(s["sharpe"] / 5.0, 1.0)
    dd = min(s["max_dd"] / 30.0, 1.0)
    pf = min(s["profit_factor"] / 3.0, 1.0)
    wr = s["win_rate"] / 100.0
    return round(0.35 * sh - 0.25 * dd + 0.25 * pf + 0.15 * wr, 4)


def main():
    import pandas as pd
    import numpy as np

    print(f"\n{'='*70}")
    print(f"MEGA CROSS-PERMUTATION ENGINE v2")
    print(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*70}")

    total_combos = len(SEED_STRATEGIES) * len(TP_VALUES) * len(SL_VALUES) * len(TECH_LAYERS)
    print(f"Strategies: {len(SEED_STRATEGIES)}")
    print(f"TP values: {len(TP_VALUES)} | SL values: {len(SL_VALUES)}")
    print(f"Tech layers: {len(TECH_LAYERS)}")
    print(f"TOTAL COMBINATIONS: {total_combos}")
    print(f"Symbols: {', '.join(SYMBOLS)}")

    # Fetch data
    market_data = {}
    for sym in SYMBOLS:
        print(f"\nFetching {sym}...")
        raw = fetch_binance_klines(sym, "1d", KLINE_LIMIT)
        if raw:
            market_data[sym] = parse_klines(raw)
            print(f"  {len(market_data[sym])} bars")

    if not market_data:
        print("No data. Exit.")
        return

    # Pre-build DataFrames
    market_dfs = {sym: pd.DataFrame(rows) for sym, rows in market_data.items()}

    all_results = []
    loaded = {}
    strat_count = 0
    combo_count = 0

    for seed in SEED_STRATEGIES:
        name = seed["name"]
        if name not in loaded:
            try:
                cls = load_strategy_class(seed["file"], name)
                if cls is None:
                    continue
                loaded[name] = cls
            except Exception as e:
                print(f"  Skip {name}: {e}")
                continue

        cls = loaded[name]
        strat_count += 1
        print(f"\n[{strat_count}/{len(SEED_STRATEGIES)}] {name} (type: {seed['type']})")

        # Generate base signals once per symbol
        base_signals = {}
        for sym, rows in market_data.items():
            df = market_dfs[sym]
            sigs = []
            try:
                try:
                    strategy = cls({})
                except TypeError:
                    strategy = cls()
                start = min(280, len(df) - 20)
                for i in range(start, len(df)):
                    window = df.iloc[:i+1].copy().reset_index(drop=True)
                    result = strategy.generate_signals(window, sym)
                    if result:
                        sigs.append((i, result[-1]))
            except Exception:
                pass
            base_signals[sym] = sigs

        total_base = sum(len(s) for s in base_signals.values())
        if total_base == 0:
            print(f"  No base signals. Skip.")
            continue
        print(f"  Base signals: {total_base} ({', '.join(f'{k}:{len(v)}' for k,v in base_signals.items())})")

        # Test all TP/SL x tech_layer combos
        perm_count = 0
        for tp, sl, layer in product(TP_VALUES, SL_VALUES, TECH_LAYERS):
            if sl >= tp:
                continue  # Skip invalid combos where SL >= TP

            combo_results = {}
            for sym, sigs in base_signals.items():
                if not sigs:
                    continue
                filtered = apply_tech_filter(market_data[sym], sigs, layer["filter"])
                if not filtered:
                    continue
                stats = backtest_signals(filtered, market_data[sym], tp_mult=tp, sl_mult=sl)
                if stats:
                    combo_results[sym] = stats

            if not combo_results:
                continue

            # Combined metrics
            all_sharpes = [s["sharpe"] for s in combo_results.values()]
            all_dds = [s["max_dd"] for s in combo_results.values()]
            all_pfs = [s["profit_factor"] for s in combo_results.values()]
            all_wrs = [s["win_rate"] for s in combo_results.values()]
            all_pnls = [s["pnl"] for s in combo_results.values()]
            all_trades = [s["trades"] for s in combo_results.values()]

            combined = {
                "sharpe": round(sum(all_sharpes) / len(all_sharpes), 2),
                "max_dd": round(max(all_dds), 2),
                "profit_factor": round(sum(all_pfs) / len(all_pfs), 2),
                "win_rate": round(sum(all_wrs) / len(all_wrs), 1),
            }
            score = composite_score(combined)

            all_results.append({
                "strategy": name,
                "type": seed["type"],
                "tp": tp, "sl": sl,
                "layer": layer["name"],
                "score": score,
                "combined_sharpe": combined["sharpe"],
                "combined_dd": combined["max_dd"],
                "combined_pf": combined["profit_factor"],
                "combined_wr": combined["win_rate"],
                "combined_pnl": round(sum(all_pnls), 2),
                "combined_trades": sum(all_trades),
                "per_symbol": combo_results,
            })
            perm_count += 1
            combo_count += 1

        print(f"  Tested {perm_count} valid permutations")

    # Sort by score
    all_results.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n{'='*70}")
    print(f"RESULTS: {combo_count} total combos evaluated")
    print(f"{'='*70}")

    # Print top 50
    print(f"\nTOP 50 STRATEGY COMBINATIONS:")
    print(f"{'Rk':<4} {'Strategy':<35} {'TP/SL':>7} {'Layer':<18} {'Score':>6} {'Sharpe':>7} {'DD%':>6} {'PF':>5} {'WR%':>6} {'PnL%':>8} {'Trd':>5}")
    print("-" * 110)
    for i, r in enumerate(all_results[:50], 1):
        print(f"{i:<4} {r['strategy'][:35]:<35} {r['tp']}/{r['sl']:<5} {r['layer'][:18]:<18} "
              f"{r['score']:>5.3f} {r['combined_sharpe']:>6.1f} {r['combined_dd']:>5.1f} "
              f"{r['combined_pf']:>4.1f} {r['combined_wr']:>5.1f} {r['combined_pnl']:>+7.1f} {r['combined_trades']:>5}")

    # Summary stats
    print(f"\n{'='*70}")
    print(f"SUMMARY BY STRATEGY TYPE:")
    print(f"{'='*70}")
    types = {}
    for r in all_results:
        t = r["type"]
        if t not in types:
            types[t] = {"count": 0, "best_score": 0, "best_name": ""}
        types[t]["count"] += 1
        if r["score"] > types[t]["best_score"]:
            types[t]["best_score"] = r["score"]
            types[t]["best_name"] = f"{r['strategy']} TP{r['tp']}/SL{r['sl']} +{r['layer']}"

    for t, info in sorted(types.items(), key=lambda x: x[1]["best_score"], reverse=True):
        print(f"  {t:<20} {info['count']:>5} combos | Best: {info['best_score']:.3f} — {info['best_name']}")

    # Layer effectiveness analysis
    print(f"\n{'='*70}")
    print(f"TECHNICAL LAYER EFFECTIVENESS:")
    print(f"{'='*70}")
    layer_stats = {}
    for r in all_results:
        ln = r["layer"]
        if ln not in layer_stats:
            layer_stats[ln] = {"scores": [], "sharpes": []}
        layer_stats[ln]["scores"].append(r["score"])
        layer_stats[ln]["sharpes"].append(r["combined_sharpe"])

    for ln, ls in sorted(layer_stats.items(), key=lambda x: sum(x[1]["scores"])/len(x[1]["scores"]) if x[1]["scores"] else 0, reverse=True):
        avg_s = sum(ls["scores"]) / len(ls["scores"]) if ls["scores"] else 0
        avg_sh = sum(ls["sharpes"]) / len(ls["sharpes"]) if ls["sharpes"] else 0
        top_s = max(ls["scores"]) if ls["scores"] else 0
        print(f"  {ln:<25} Avg Score: {avg_s:.4f} | Avg Sharpe: {avg_sh:.1f} | Best: {top_s:.4f} | N={len(ls['scores'])}")

    # Save all results
    output_file = SCRIPT_DIR / "mega_permutation_results.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    # Save top 30 candidates
    candidates_file = SCRIPT_DIR / "mega_perm_top_candidates.json"
    with open(candidates_file, "w") as f:
        json.dump(all_results[:30], f, indent=2)

    print(f"\nAll results: {output_file}")
    print(f"Top candidates: {candidates_file}")

    return all_results


if __name__ == "__main__":
    main()
