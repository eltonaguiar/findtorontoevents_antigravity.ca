"""
DNA Mutation Backtest Runner
==============================
Backtests all 5 original strategies + 15 mutations (tight/loose/inverse).
180d, 4h, 5 symbols from Binance with 3+ endpoint failover.
Prints comparison table: Original vs Tight vs Loose vs Inverse.
"""

import sys
import os
import time
import signal
import numpy as np
import pandas as pd
import requests
from typing import List, Dict

# Timeout handler
class TimeoutError(Exception):
    pass

# ============================================================================
# DATA FETCHER (3+ endpoint failover per CLAUDE.md)
# ============================================================================

def fetch_binance_klines(symbol: str, interval: str = "4h",
                         days: int = 180) -> pd.DataFrame:
    endpoints = [
        "https://api.binance.com", "https://api1.binance.com",
        "https://api2.binance.com", "https://api3.binance.com",
    ]
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 24 * 60 * 60 * 1000
    all_data = []
    cur = start_ms

    while cur < end_ms:
        success = False
        for base in endpoints:
            try:
                resp = requests.get(f"{base}/api/v3/klines", params={
                    "symbol": symbol, "interval": interval,
                    "startTime": cur, "limit": 1000
                }, timeout=10)
                if resp.status_code == 200:
                    rows = resp.json()
                    if rows:
                        all_data.extend(rows)
                        cur = rows[-1][0] + 1
                        success = True
                        break
            except Exception:
                continue
        if not success:
            break
        time.sleep(0.15)

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_vol', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    df = df.drop_duplicates(subset='open_time').sort_values('open_time').reset_index(drop=True)
    return df


# ============================================================================
# GENERIC BACKTESTER
# ============================================================================

def backtest_strategy(strategy, data_dict, btc_data=None, lookahead=12,
                      is_btc_neutral=False):
    """Backtest a strategy across multiple symbols. Returns list of trade dicts."""
    all_results = []

    for sym, data in data_dict.items():
        if data.empty:
            continue

        try:
            if is_btc_neutral:
                # BTC-neutral strategies need walk-forward across full dataset
                results = _backtest_btc_neutral_wf(strategy, data, btc_data, sym,
                                                    lookahead)
            else:
                signals = strategy.generate_signals(data, sym)
                results = _evaluate_signals(signals, data, sym, lookahead)
        except Exception as e:
            print(f"    ERROR backtesting {sym}: {e}")
            continue

        all_results.extend(results)

    return all_results


def _evaluate_signals(signals, data, symbol, lookahead=12):
    """Evaluate signals against data."""
    results = []
    for sig in signals:
        entry_idx = (data['close'] - sig.entry_price).abs().idxmin()
        hit = False
        for j in range(entry_idx + 1, min(entry_idx + lookahead + 1, len(data))):
            bar_high = data['high'].iloc[j]
            bar_low = data['low'].iloc[j]

            if sig.direction == "SELL":
                if bar_low <= sig.take_profit:
                    pnl = (sig.entry_price - sig.take_profit) / sig.entry_price * 100
                    results.append({"symbol": symbol, "pnl_pct": pnl, "outcome": "TP"})
                    hit = True
                    break
                elif bar_high >= sig.stop_loss:
                    pnl = -(sig.stop_loss - sig.entry_price) / sig.entry_price * 100
                    results.append({"symbol": symbol, "pnl_pct": pnl, "outcome": "SL"})
                    hit = True
                    break
            else:
                if bar_high >= sig.take_profit:
                    pnl = (sig.take_profit - sig.entry_price) / sig.entry_price * 100
                    results.append({"symbol": symbol, "pnl_pct": pnl, "outcome": "TP"})
                    hit = True
                    break
                elif bar_low <= sig.stop_loss:
                    pnl = -(sig.entry_price - sig.stop_loss) / sig.entry_price * 100
                    results.append({"symbol": symbol, "pnl_pct": pnl, "outcome": "SL"})
                    hit = True
                    break

        if not hit:
            exit_price = data['close'].iloc[min(entry_idx + lookahead, len(data) - 1)]
            if sig.direction == "SELL":
                pnl = (sig.entry_price - exit_price) / sig.entry_price * 100
            else:
                pnl = (exit_price - sig.entry_price) / sig.entry_price * 100
            results.append({"symbol": symbol, "pnl_pct": pnl, "outcome": "EXPIRED"})

    return results


def _backtest_btc_neutral_wf(strategy, alt_data, btc_data, symbol, lookahead=12):
    """Walk-forward backtest for BTC-neutral strategies."""
    if btc_data is None or btc_data.empty:
        return []

    n = min(len(alt_data), len(btc_data))
    alt = alt_data.iloc[-n:].reset_index(drop=True)
    btc = btc_data.iloc[-n:].reset_index(drop=True)

    alt_ret = alt["close"].pct_change()
    btc_ret = btc["close"].pct_change()

    reg_window = strategy.reg_window if hasattr(strategy, 'reg_window') else 30
    z_window = strategy.z_window if hasattr(strategy, 'z_window') else 20
    z_entry = strategy.z_entry if hasattr(strategy, 'z_entry') else 2.0
    tp_atr_mult = strategy.tp_atr if hasattr(strategy, 'tp_atr') else 2.0
    sl_atr_mult = strategy.sl_atr if hasattr(strategy, 'sl_atr') else 1.5
    atr_period = strategy.atr_period if hasattr(strategy, 'atr_period') else 14

    # Rolling OLS residuals
    residuals = strategy._rolling_ols_residual(alt_ret, btc_ret, reg_window)
    z_mu = residuals.rolling(z_window, min_periods=z_window).mean()
    z_sd = residuals.rolling(z_window, min_periods=z_window).std(ddof=0).replace(0, np.nan)
    z_scores = (residuals - z_mu) / z_sd

    # ATR
    h, l, c = alt["high"], alt["low"], alt["close"]
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(atr_period, min_periods=1).mean()

    start_bar = reg_window + z_window + 5
    results = []

    # Determine if this is an inverse strategy
    is_inverse = hasattr(strategy, '__class__') and 'Inverse' in strategy.__class__.__name__

    for i in range(start_bar, len(alt) - lookahead):
        zv = z_scores.iloc[i]
        if np.isnan(zv):
            continue

        direction = None
        if is_inverse:
            # Inverse: short when z < -entry, long when z > entry
            if zv < -z_entry:
                direction = "SELL"
            elif zv > z_entry:
                direction = "BUY"
        else:
            # Normal: long when z < -entry, short when z > entry
            if zv < -z_entry:
                direction = "BUY"
            elif zv > z_entry:
                direction = "SELL"

        if direction is None:
            continue

        entry_price = alt["close"].iloc[i]
        atr_val = atr.iloc[i]
        if np.isnan(atr_val) or atr_val <= 0:
            continue

        tp_dist = atr_val * tp_atr_mult
        sl_dist = atr_val * sl_atr_mult

        if direction == "BUY":
            tp_price = entry_price + tp_dist
            sl_price = entry_price - sl_dist
        else:
            tp_price = entry_price - tp_dist
            sl_price = entry_price + sl_dist

        outcome = "EXPIRED"
        pnl_pct = 0.0
        for j in range(1, lookahead + 1):
            bar_idx = i + j
            bar_high = alt["high"].iloc[bar_idx]
            bar_low = alt["low"].iloc[bar_idx]

            if direction == "BUY":
                if bar_low <= sl_price:
                    outcome = "SL"
                    pnl_pct = -sl_dist / entry_price * 100
                    break
                if bar_high >= tp_price:
                    outcome = "TP"
                    pnl_pct = tp_dist / entry_price * 100
                    break
            else:
                if bar_high >= sl_price:
                    outcome = "SL"
                    pnl_pct = -sl_dist / entry_price * 100
                    break
                if bar_low <= tp_price:
                    outcome = "TP"
                    pnl_pct = tp_dist / entry_price * 100
                    break

        if outcome == "EXPIRED":
            exit_price = alt["close"].iloc[i + lookahead]
            if direction == "BUY":
                pnl_pct = (exit_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - exit_price) / entry_price * 100

        results.append({"symbol": symbol, "pnl_pct": round(pnl_pct, 3), "outcome": outcome})

    return results


def compute_stats(results):
    """Compute trading statistics from results list."""
    if not results:
        return {"trades": 0, "wr": 0.0, "pf": 0.0, "avg_pnl": 0.0, "total_pnl": 0.0}

    total = len(results)
    wins = [r for r in results if r['pnl_pct'] > 0]
    losses = [r for r in results if r['pnl_pct'] <= 0]
    wr = len(wins) / total * 100 if total > 0 else 0
    gross_profit = sum(r['pnl_pct'] for r in wins) if wins else 0
    gross_loss = abs(sum(r['pnl_pct'] for r in losses)) if losses else 0.001
    pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
    avg_pnl = np.mean([r['pnl_pct'] for r in results])
    total_pnl = sum(r['pnl_pct'] for r in results)

    return {
        "trades": total,
        "wr": round(wr, 1),
        "pf": round(pf, 2),
        "avg_pnl": round(avg_pnl, 3),
        "total_pnl": round(total_pnl, 2)
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]

    print("=" * 90)
    print("DNA MUTATION BACKTEST — 5 Strategies x 4 Variants (Original + 3 Mutations)")
    print("  180 days | 4h candles | 5 symbols | 12-bar lookahead")
    print("=" * 90)

    # Fetch data once for all strategies
    print("\n--- Fetching data ---")
    data_dict = {}
    for sym in SYMBOLS:
        print(f"  Fetching {sym}...", end=" ", flush=True)
        df = fetch_binance_klines(sym, "4h", 180)
        data_dict[sym] = df
        print(f"{len(df)} bars" if not df.empty else "FAILED")
        time.sleep(0.2)

    btc_data = data_dict.get("BTCUSDT", pd.DataFrame())

    # Add sys path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # -----------------------------------------------------------------------
    # Strategy definitions: (name, module, class, is_btc_neutral)
    # -----------------------------------------------------------------------
    strategy_groups = [
        {
            "name": "multi_tf_bearish_confluence",
            "variants": [
                ("Original", "multi_tf_bearish_confluence", "MultiTFBearishConfluenceStrategy", False),
                ("Tight",    "multi_tf_bearish_confluence_tight", "MultiTFBearishConfluenceTightStrategy", False),
                ("Loose",    "multi_tf_bearish_confluence_loose", "MultiTFBearishConfluenceLooseStrategy", False),
                ("Inverse",  "multi_tf_bearish_confluence_inverse", "MultiTFBearishConfluenceInverseStrategy", False),
            ]
        },
        {
            "name": "volume_climax_reversal",
            "variants": [
                ("Original", "volume_climax_reversal", "VolumeClimaxReversalStrategy", False),
                ("Tight",    "volume_climax_reversal_tight", "VolumeClimaxReversalTightStrategy", False),
                ("Loose",    "volume_climax_reversal_loose", "VolumeClimaxReversalLooseStrategy", False),
                ("Inverse",  "volume_climax_reversal_inverse", "VolumeClimaxReversalInverseStrategy", False),
            ]
        },
        {
            "name": "ema_death_cross_short",
            "variants": [
                ("Original", "ema_death_cross_short", "EMADeathCrossShortStrategy", False),
                ("Tight",    "ema_death_cross_short_tight", "EMADeathCrossShortTightStrategy", False),
                ("Loose",    "ema_death_cross_short_loose", "EMADeathCrossShortLooseStrategy", False),
                ("Inverse",  "ema_death_cross_short_inverse", "EMADeathCrossShortInverseStrategy", False),
            ]
        },
        {
            "name": "adx_bollinger_regime_switch",
            "variants": [
                ("Original", "adx_bollinger_regime_switch", "ADXBollingerRegimeSwitchStrategy", False),
                ("Tight",    "adx_bollinger_regime_switch_tight", "ADXBollingerRegimeSwitchTightStrategy", False),
                ("Loose",    "adx_bollinger_regime_switch_loose", "ADXBollingerRegimeSwitchLooseStrategy", False),
                ("Inverse",  "adx_bollinger_regime_switch_inverse", "ADXBollingerRegimeSwitchInverseStrategy", False),
            ]
        },
        {
            "name": "btc_neutral_residual_mr",
            "variants": [
                ("Original", "btc_neutral_residual_mr", "BtcNeutralResidualMRStrategy", True),
                ("Tight",    "btc_neutral_residual_mr_tight", "BtcNeutralResidualMRTightStrategy", True),
                ("Loose",    "btc_neutral_residual_mr_loose", "BtcNeutralResidualMRLooseStrategy", True),
                ("Inverse",  "btc_neutral_residual_mr_inverse", "BtcNeutralResidualMRInverseStrategy", True),
            ]
        },
    ]

    all_group_results = {}

    for group in strategy_groups:
        group_name = group["name"]
        print(f"\n{'='*90}")
        print(f"STRATEGY: {group_name}")
        print(f"{'='*90}")

        group_results = {}

        for variant_name, module_name, class_name, is_btc_neutral in group["variants"]:
            print(f"\n  [{variant_name}] ", end="", flush=True)

            try:
                start_time = time.time()
                mod = __import__(module_name)
                strategy_class = getattr(mod, class_name)
                strategy = strategy_class()

                results = backtest_strategy(
                    strategy, data_dict, btc_data,
                    lookahead=12, is_btc_neutral=is_btc_neutral
                )

                elapsed = time.time() - start_time
                if elapsed > 60:
                    print(f"TIMEOUT ({elapsed:.0f}s) - skipped")
                    group_results[variant_name] = {"trades": 0, "wr": 0, "pf": 0,
                                                    "avg_pnl": 0, "total_pnl": 0,
                                                    "status": "TIMEOUT"}
                    continue

                stats = compute_stats(results)
                stats["status"] = "OK"
                group_results[variant_name] = stats
                print(f"{stats['trades']} trades | WR={stats['wr']:.1f}% | "
                      f"PF={stats['pf']:.2f} | avgPnL={stats['avg_pnl']:.3f}% | "
                      f"({elapsed:.1f}s)")

            except Exception as e:
                print(f"ERROR: {e}")
                group_results[variant_name] = {"trades": 0, "wr": 0, "pf": 0,
                                                "avg_pnl": 0, "total_pnl": 0,
                                                "status": f"ERROR: {str(e)[:40]}"}

        all_group_results[group_name] = group_results

    # =====================================================================
    # COMPARISON TABLE
    # =====================================================================
    print("\n\n" + "=" * 100)
    print("DNA MUTATION COMPARISON TABLE")
    print("=" * 100)
    print(f"{'Strategy':<35} {'Variant':<10} {'Trades':>6} {'WR%':>7} {'PF':>7} "
          f"{'AvgPnL%':>9} {'TotalPnL%':>10} {'Status':<12}")
    print("-" * 100)

    for group_name, variants in all_group_results.items():
        orig_stats = variants.get("Original", {})
        for variant_name, stats in variants.items():
            status = stats.get("status", "OK")
            # Determine if improved vs degraded
            if variant_name != "Original" and status == "OK" and orig_stats.get("status") == "OK":
                if stats["pf"] > orig_stats.get("pf", 0) * 1.05:
                    verdict = "IMPROVED"
                elif stats["pf"] < orig_stats.get("pf", 0) * 0.95:
                    verdict = "DEGRADED"
                else:
                    verdict = "NEUTRAL"
            elif status == "OK":
                verdict = "BASELINE"
            else:
                verdict = status[:12]

            print(f"{group_name:<35} {variant_name:<10} {stats.get('trades',0):>6} "
                  f"{stats.get('wr',0):>6.1f}% {stats.get('pf',0):>7.2f} "
                  f"{stats.get('avg_pnl',0):>8.3f}% {stats.get('total_pnl',0):>9.2f}% "
                  f"{verdict:<12}")
        print("-" * 100)

    # =====================================================================
    # WINNER SUMMARY
    # =====================================================================
    print("\n" + "=" * 100)
    print("MUTATION IMPACT SUMMARY")
    print("=" * 100)

    for group_name, variants in all_group_results.items():
        orig = variants.get("Original", {})
        if orig.get("status") != "OK":
            print(f"  {group_name}: Original failed, cannot compare")
            continue

        print(f"\n  {group_name} (Original: PF={orig['pf']:.2f}, WR={orig['wr']:.1f}%, "
              f"{orig['trades']} trades):")

        for vname in ["Tight", "Loose", "Inverse"]:
            v = variants.get(vname, {})
            if v.get("status") != "OK":
                print(f"    {vname:>8}: SKIPPED ({v.get('status', 'N/A')})")
                continue

            pf_delta = v['pf'] - orig['pf']
            wr_delta = v['wr'] - orig['wr']
            trade_delta = v['trades'] - orig['trades']

            if v['pf'] > orig['pf'] * 1.05:
                icon = "[+]"
            elif v['pf'] < orig['pf'] * 0.95:
                icon = "[-]"
            else:
                icon = "[=]"

            print(f"    {icon} {vname:>8}: PF={v['pf']:.2f} ({pf_delta:+.2f}) | "
                  f"WR={v['wr']:.1f}% ({wr_delta:+.1f}) | "
                  f"Trades={v['trades']} ({trade_delta:+d}) | "
                  f"AvgPnL={v['avg_pnl']:.3f}%")

    print("\n" + "=" * 100)
    print("DONE. 15 DNA mutations created and backtested.")
    print("=" * 100)
