"""
Cross-Asset Superstar Strategy Tester
======================================
Tests 3 strategies across 4 asset classes (crypto, stocks, forex, commodities)
to find "WIN NO MATTER WHAT" superstars.

Superstar criteria:
- PF > 1.1 on at least 3 of 4 asset classes
- WR > 40% on all tested asset classes
- Works on 8+ of 12 symbols tested
"""

import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests

try:
    import yfinance as yf
except ImportError:
    print("ERROR: pip install yfinance")
    sys.exit(1)


# ==============================================================================
# GENERIC INDICATOR HELPERS
# ==============================================================================

def calc_ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def calc_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = data['high'], data['low'], data['close']
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calc_adx(data: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = data['high'], data['low'], data['close']
    n = period
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr = pd.concat([
        high - low, abs(high - close.shift()), abs(low - close.shift())
    ], axis=1).max(axis=1)
    atr_smooth = tr.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/n, min_periods=n, adjust=False).mean() / atr_smooth
    minus_di = 100 * minus_dm.ewm(alpha=1/n, min_periods=n, adjust=False).mean() / atr_smooth
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1e-10)
    adx = dx.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    return adx

def calc_bb(close: pd.Series, period: int = 20, std_mult: float = 2.2):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return mid, upper, lower


# ==============================================================================
# DATA FETCHERS
# ==============================================================================

def fetch_binance_klines(symbol: str, interval: str = "4h", days: int = 180) -> pd.DataFrame:
    """Fetch from Binance with 4-mirror failover."""
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
    df = df.drop_duplicates(subset='open_time').sort_values('open_time').reset_index(drop=True)
    return df


def fetch_yfinance(symbol: str, period: str = "2y") -> pd.DataFrame:
    """Fetch OHLCV from yfinance."""
    try:
        tk = yf.Ticker(symbol)
        df = tk.history(period=period)
        if df.empty:
            return pd.DataFrame()
        df = df.rename(columns={
            'Open': 'open', 'High': 'high', 'Low': 'low',
            'Close': 'close', 'Volume': 'volume'
        })
        df = df[['open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
        return df
    except Exception as e:
        print(f"  yfinance error for {symbol}: {e}")
        return pd.DataFrame()


# ==============================================================================
# GENERIC WALK-FORWARD BACKTESTER
# ==============================================================================

def backtest_signals(signals, data, lookahead=12):
    """Walk-forward backtest: check TP/SL within lookahead bars."""
    results = []
    for sig in signals:
        entry_idx = (data['close'] - sig['entry_price']).abs().idxmin()
        hit = False
        for j in range(entry_idx + 1, min(entry_idx + lookahead + 1, len(data))):
            bar_high = data['high'].iloc[j]
            bar_low = data['low'].iloc[j]

            if sig['direction'] == "SELL":
                if bar_low <= sig['take_profit']:
                    pnl = (sig['entry_price'] - sig['take_profit']) / sig['entry_price'] * 100
                    results.append({"pnl_pct": pnl, "outcome": "TP", "direction": "SELL"})
                    hit = True; break
                elif bar_high >= sig['stop_loss']:
                    pnl = -(sig['stop_loss'] - sig['entry_price']) / sig['entry_price'] * 100
                    results.append({"pnl_pct": pnl, "outcome": "SL", "direction": "SELL"})
                    hit = True; break
            else:
                if bar_high >= sig['take_profit']:
                    pnl = (sig['take_profit'] - sig['entry_price']) / sig['entry_price'] * 100
                    results.append({"pnl_pct": pnl, "outcome": "TP", "direction": "BUY"})
                    hit = True; break
                elif bar_low <= sig['stop_loss']:
                    pnl = -(sig['entry_price'] - sig['stop_loss']) / sig['entry_price'] * 100
                    results.append({"pnl_pct": pnl, "outcome": "SL", "direction": "BUY"})
                    hit = True; break

        if not hit:
            exit_price = data['close'].iloc[min(entry_idx + lookahead, len(data) - 1)]
            if sig['direction'] == "SELL":
                pnl = (sig['entry_price'] - exit_price) / sig['entry_price'] * 100
            else:
                pnl = (exit_price - sig['entry_price']) / sig['entry_price'] * 100
            results.append({"pnl_pct": pnl, "outcome": "EXPIRED", "direction": sig['direction']})

    return results


# ==============================================================================
# STRATEGY 1: ADX + Bollinger Regime Switcher (generic)
# ==============================================================================

def adx_bb_regime_signals(data: pd.DataFrame, cooldown=4):
    """ADX + BB regime switcher - works on any OHLCV."""
    adx_period, bb_period, bb_std_mult = 14, 20, 2.2
    rsi_period, atr_period = 14, 14
    adx_idle, adx_breakout = 15, 25
    rsi_os, rsi_ob = 35, 65
    mr_sl_atr, bo_tp_atr, bo_sl_atr = 1.5, 2.5, 1.2

    min_len = bb_period + adx_period + 20
    if len(data) < min_len:
        return []

    adx = calc_adx(data, adx_period)
    rsi = calc_rsi(data['close'], rsi_period)
    atr = calc_atr(data, atr_period)
    bb_mid, bb_upper, bb_lower = calc_bb(data['close'], bb_period, bb_std_mult)

    signals = []
    last_bar = -cooldown

    for i in range(min_len, len(data)):
        if i - last_bar < cooldown:
            continue
        ca, cr, cat, cc = adx.iloc[i], rsi.iloc[i], atr.iloc[i], data['close'].iloc[i]
        cu, cl, cm = bb_upper.iloc[i], bb_lower.iloc[i], bb_mid.iloc[i]
        if any(pd.isna(v) for v in [ca, cr, cat, cu, cl, cm]) or cat <= 0:
            continue

        if ca < adx_idle:
            continue

        if ca <= adx_breakout:  # MEAN REVERSION
            if cc <= cl and cr < rsi_os:
                signals.append({"direction": "BUY", "entry_price": cc,
                    "take_profit": cm, "stop_loss": cc - cat * mr_sl_atr})
                last_bar = i
            elif cc >= cu and cr > rsi_ob:
                signals.append({"direction": "SELL", "entry_price": cc,
                    "take_profit": cm, "stop_loss": cc + cat * mr_sl_atr})
                last_bar = i
        else:  # BREAKOUT
            if cc > cu:
                signals.append({"direction": "BUY", "entry_price": cc,
                    "take_profit": cc + cat * bo_tp_atr, "stop_loss": cc - cat * bo_sl_atr})
                last_bar = i
            elif cc < cl:
                signals.append({"direction": "SELL", "entry_price": cc,
                    "take_profit": cc - cat * bo_tp_atr, "stop_loss": cc + cat * bo_sl_atr})
                last_bar = i

    return signals


# ==============================================================================
# STRATEGY 2: Residual Mean Reversion (generic anchor)
# ==============================================================================

def residual_mr_signals(data: pd.DataFrame, anchor_data: pd.DataFrame,
                        reg_window=30, z_window=20, z_entry=2.0,
                        tp_atr=2.0, sl_atr=1.5, atr_period=14):
    """Residual MR: regress asset vs anchor, trade z-score extremes."""
    min_bars = reg_window + z_window + 10
    if len(data) < min_bars or len(anchor_data) < min_bars:
        return []

    n = min(len(data), len(anchor_data))
    alt = data.iloc[-n:].reset_index(drop=True)
    anc = anchor_data.iloc[-n:].reset_index(drop=True)

    alt_ret = alt['close'].pct_change()
    anc_ret = anc['close'].pct_change()

    # Rolling OLS residuals
    residuals = pd.Series(np.nan, index=alt_ret.index)
    for i in range(reg_window, len(alt_ret)):
        y = alt_ret.iloc[i - reg_window:i].values.astype(float)
        x = anc_ret.iloc[i - reg_window:i].values.astype(float)
        if np.any(~np.isfinite(y)) or np.any(~np.isfinite(x)):
            continue
        x_mat = np.column_stack([np.ones(reg_window), x])
        try:
            coeffs = np.linalg.lstsq(x_mat, y, rcond=None)[0]
        except Exception:
            continue
        predicted = coeffs[0] + coeffs[1] * float(anc_ret.iloc[i])
        alt_val = float(alt_ret.iloc[i])
        if np.isfinite(predicted) and np.isfinite(alt_val):
            residuals.iloc[i] = alt_val - predicted

    # Z-score
    mu = residuals.rolling(z_window, min_periods=z_window).mean()
    sd = residuals.rolling(z_window, min_periods=z_window).std(ddof=0).replace(0, np.nan)
    z_scores = (residuals - mu) / sd

    atr = calc_atr(alt, atr_period)

    signals = []
    start = reg_window + z_window + 5
    cooldown_ct = 0

    for i in range(start, len(alt)):
        if cooldown_ct > 0:
            cooldown_ct -= 1
            continue
        zv = z_scores.iloc[i]
        if np.isnan(zv):
            continue
        cp = float(alt['close'].iloc[i])
        ca = float(atr.iloc[i])
        if np.isnan(ca) or ca <= 0:
            continue

        if zv < -z_entry:
            signals.append({"direction": "BUY", "entry_price": cp,
                "take_profit": cp + ca * tp_atr, "stop_loss": cp - ca * sl_atr})
            cooldown_ct = 4
        elif zv > z_entry:
            signals.append({"direction": "SELL", "entry_price": cp,
                "take_profit": cp - ca * tp_atr, "stop_loss": cp + ca * sl_atr})
            cooldown_ct = 4

    return signals


# ==============================================================================
# STRATEGY 3: EMA Death Cross Short (generic)
# ==============================================================================

def ema_death_cross_signals(data: pd.DataFrame, cooldown=4):
    """EMA(9) crosses below EMA(21) + ADX > 20 => SHORT."""
    ema_fast_p, ema_slow_p = 9, 21
    adx_period, atr_period = 14, 14
    adx_threshold = 20
    tp_atr, sl_atr = 2.5, 1.5

    min_len = max(ema_slow_p, adx_period * 3, atr_period) + 20
    if len(data) < min_len:
        return []

    ema_fast = calc_ema(data['close'], ema_fast_p)
    ema_slow = calc_ema(data['close'], ema_slow_p)
    adx = calc_adx(data, adx_period)
    atr = calc_atr(data, atr_period)

    signals = []
    last_bar = -cooldown

    for i in range(min_len, len(data)):
        if i - last_bar < cooldown:
            continue
        ca, cat, cc = adx.iloc[i], atr.iloc[i], data['close'].iloc[i]
        ef, es = ema_fast.iloc[i], ema_slow.iloc[i]
        pef, pes = ema_fast.iloc[i-1], ema_slow.iloc[i-1]
        if any(pd.isna(v) for v in [ca, cat, ef, es, pef, pes]) or cat <= 0:
            continue

        cross_down = pef >= pes and ef < es
        if cross_down and ca > adx_threshold:
            signals.append({"direction": "SELL", "entry_price": cc,
                "take_profit": cc - cat * tp_atr, "stop_loss": cc + cat * sl_atr})
            last_bar = i

    return signals


# ==============================================================================
# ASSET CLASS DEFINITIONS
# ==============================================================================

ASSET_CLASSES = {
    "crypto": {
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "source": "binance",
        "period": "180d",
    },
    "stocks": {
        "symbols": ["AAPL", "MSFT", "NVDA"],
        "source": "yfinance",
        "period": "2y",
    },
    "forex": {
        "symbols": ["EURUSD=X", "GBPUSD=X", "USDJPY=X"],
        "source": "yfinance",
        "period": "1y",
    },
    "commodities": {
        "symbols": ["GLD", "USO", "SLV"],
        "source": "yfinance",
        "period": "2y",
    },
}

# Anchors for residual MR strategy per asset class
ANCHOR_SYMBOLS = {
    "crypto": ("BTCUSDT", "binance"),
    "stocks": ("SPY", "yfinance"),
    "forex": ("DX-Y.NYB", "yfinance"),   # Dollar index as forex anchor
    "commodities": ("SPY", "yfinance"),   # SPY as broad anchor for commodities
}

STRATEGIES = {
    "adx_bollinger_regime_switch": adx_bb_regime_signals,
    "residual_mean_reversion": None,  # special handling (needs anchor)
    "ema_death_cross_short": ema_death_cross_signals,
}


# ==============================================================================
# COMPUTE STATS
# ==============================================================================

def compute_stats(results: list) -> dict:
    if not results:
        return {"trades": 0, "wr": 0, "pf": 0, "avg_pnl": 0}
    total = len(results)
    wins = [r for r in results if r['pnl_pct'] > 0]
    losses = [r for r in results if r['pnl_pct'] <= 0]
    wr = len(wins) / total * 100
    gp = sum(r['pnl_pct'] for r in wins) if wins else 0
    gl = abs(sum(r['pnl_pct'] for r in losses)) if losses else 0.001
    pf = gp / gl if gl > 0 else 999
    avg_pnl = np.mean([r['pnl_pct'] for r in results])
    return {"trades": total, "wr": round(wr, 1), "pf": round(pf, 2), "avg_pnl": round(avg_pnl, 3)}


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("CROSS-ASSET SUPERSTAR STRATEGY TESTER")
    print("Testing 3 strategies x 4 asset classes x 3 symbols = 36 tests")
    print("=" * 80)

    # Cache fetched data
    data_cache = {}
    anchor_cache = {}

    # Fetch all data first
    print("\n--- FETCHING DATA ---")
    for ac_name, ac_config in ASSET_CLASSES.items():
        for sym in ac_config["symbols"]:
            key = (ac_name, sym)
            if ac_config["source"] == "binance":
                print(f"  Fetching {sym} from Binance (4h, 180d)...", end=" ", flush=True)
                df = fetch_binance_klines(sym, "4h", 180)
            else:
                print(f"  Fetching {sym} from yfinance ({ac_config['period']})...", end=" ", flush=True)
                df = fetch_yfinance(sym, ac_config["period"])
            if df.empty:
                print("FAILED")
            else:
                print(f"{len(df)} bars")
            data_cache[key] = df
            time.sleep(0.1)

    # Fetch anchors for residual MR
    print("\n  Fetching anchor symbols for Residual MR...")
    for ac_name, (anchor_sym, anchor_src) in ANCHOR_SYMBOLS.items():
        cache_key = anchor_sym
        if cache_key not in anchor_cache:
            if anchor_src == "binance":
                print(f"    Anchor {anchor_sym} from Binance...", end=" ", flush=True)
                adf = fetch_binance_klines(anchor_sym, "4h", 180)
            else:
                print(f"    Anchor {anchor_sym} from yfinance (2y)...", end=" ", flush=True)
                adf = fetch_yfinance(anchor_sym, "2y")
            if adf.empty:
                print("FAILED")
            else:
                print(f"{len(adf)} bars")
            anchor_cache[cache_key] = adf
            time.sleep(0.1)

    # Run all strategy x asset class x symbol tests
    print("\n--- RUNNING BACKTESTS ---")
    all_results = {}  # {strategy: {asset_class: {symbol: stats}}}

    strategy_names = ["adx_bollinger_regime_switch", "residual_mean_reversion", "ema_death_cross_short"]

    for strat_name in strategy_names:
        all_results[strat_name] = {}
        print(f"\n{'='*70}")
        print(f"STRATEGY: {strat_name.upper()}")
        print(f"{'='*70}")

        for ac_name, ac_config in ASSET_CLASSES.items():
            all_results[strat_name][ac_name] = {}
            print(f"\n  Asset Class: {ac_name.upper()}")

            for sym in ac_config["symbols"]:
                df = data_cache.get((ac_name, sym), pd.DataFrame())
                if df.empty or len(df) < 60:
                    print(f"    {sym}: SKIP (insufficient data)")
                    all_results[strat_name][ac_name][sym] = {"trades": 0, "wr": 0, "pf": 0, "avg_pnl": 0, "status": "no_data"}
                    continue

                # Generate signals
                try:
                    if strat_name == "adx_bollinger_regime_switch":
                        sigs = adx_bb_regime_signals(df)
                    elif strat_name == "ema_death_cross_short":
                        sigs = ema_death_cross_signals(df)
                    elif strat_name == "residual_mean_reversion":
                        anchor_sym = ANCHOR_SYMBOLS[ac_name][0]
                        anchor_df = anchor_cache.get(anchor_sym, pd.DataFrame())
                        if anchor_df.empty:
                            print(f"    {sym}: SKIP (no anchor data)")
                            all_results[strat_name][ac_name][sym] = {"trades": 0, "wr": 0, "pf": 0, "avg_pnl": 0, "status": "no_anchor"}
                            continue
                        # For crypto: skip BTC itself (it's the anchor)
                        if ac_name == "crypto" and sym == "BTCUSDT":
                            print(f"    {sym}: SKIP (is the anchor)")
                            all_results[strat_name][ac_name][sym] = {"trades": 0, "wr": 0, "pf": 0, "avg_pnl": 0, "status": "is_anchor"}
                            continue
                        sigs = residual_mr_signals(df, anchor_df)
                    else:
                        sigs = []

                    if not sigs:
                        print(f"    {sym}: 0 signals generated")
                        all_results[strat_name][ac_name][sym] = {"trades": 0, "wr": 0, "pf": 0, "avg_pnl": 0, "status": "no_signals"}
                        continue

                    # Backtest
                    bt = backtest_signals(sigs, df, lookahead=12)
                    stats = compute_stats(bt)
                    stats["status"] = "ok"
                    all_results[strat_name][ac_name][sym] = stats
                    print(f"    {sym}: {stats['trades']} trades | WR={stats['wr']}% | PF={stats['pf']} | avgPnL={stats['avg_pnl']}%")

                except Exception as e:
                    print(f"    {sym}: ERROR - {e}")
                    all_results[strat_name][ac_name][sym] = {"trades": 0, "wr": 0, "pf": 0, "avg_pnl": 0, "status": f"error: {str(e)[:50]}"}

    # ==============================================================================
    # SUPERSTAR EVALUATION
    # ==============================================================================
    print("\n" + "=" * 80)
    print("SUPERSTAR EVALUATION")
    print("=" * 80)

    superstar_results = {}

    for strat_name in strategy_names:
        print(f"\n--- {strat_name.upper()} ---")

        # Per-asset-class aggregation
        ac_stats = {}
        symbols_passing = 0
        total_symbols_tested = 0

        for ac_name in ASSET_CLASSES:
            ac_trades = []
            for sym, stats in all_results[strat_name][ac_name].items():
                if stats.get("status") == "ok" and stats["trades"] > 0:
                    total_symbols_tested += 1
                    # Check if this symbol passes (PF>1.0 or WR>40%)
                    if stats["pf"] > 1.0 and stats["wr"] > 40:
                        symbols_passing += 1

            # Aggregate AC-level stats
            all_ac_results_list = []
            for sym, stats in all_results[strat_name][ac_name].items():
                if stats.get("status") == "ok" and stats["trades"] > 0:
                    all_ac_results_list.append(stats)

            if all_ac_results_list:
                total_trades = sum(s["trades"] for s in all_ac_results_list)
                # Weighted average WR and PnL
                weighted_wr = sum(s["wr"] * s["trades"] for s in all_ac_results_list) / total_trades
                weighted_pnl = sum(s["avg_pnl"] * s["trades"] for s in all_ac_results_list) / total_trades
                # Aggregate PF: sum gross profits vs gross losses across all symbols
                total_gp = sum(max(0, s["avg_pnl"] * s["trades"]) for s in all_ac_results_list)
                total_gl = sum(abs(min(0, s["avg_pnl"] * s["trades"])) for s in all_ac_results_list)
                agg_pf = total_gp / total_gl if total_gl > 0.001 else (99.99 if total_gp > 0 else 0)

                ac_stats[ac_name] = {
                    "trades": total_trades,
                    "wr": round(weighted_wr, 1),
                    "pf": round(agg_pf, 2),
                    "avg_pnl": round(weighted_pnl, 3)
                }
            else:
                ac_stats[ac_name] = {"trades": 0, "wr": 0, "pf": 0, "avg_pnl": 0}

        # Superstar criteria
        pf_passing_acs = sum(1 for ac, s in ac_stats.items() if s["pf"] > 1.1 and s["trades"] > 0)
        wr_all_pass = all(s["wr"] > 40 for ac, s in ac_stats.items() if s["trades"] > 0)
        acs_with_trades = sum(1 for ac, s in ac_stats.items() if s["trades"] > 0)

        is_superstar = (pf_passing_acs >= 3 and wr_all_pass and symbols_passing >= 8)

        for ac_name, s in ac_stats.items():
            pf_flag = "OK" if s["pf"] > 1.1 else "FAIL"
            wr_flag = "OK" if s["wr"] > 40 else "FAIL"
            print(f"  {ac_name:12s}: {s['trades']:3d} trades | WR={s['wr']:5.1f}% [{wr_flag}] | PF={s['pf']:5.2f} [{pf_flag}] | avgPnL={s['avg_pnl']:+.3f}%")

        print(f"\n  PF>1.1 on {pf_passing_acs}/4 asset classes (need 3+)")
        print(f"  WR>40% on all: {'YES' if wr_all_pass else 'NO'}")
        print(f"  Symbols passing: {symbols_passing}/{total_symbols_tested} (need 8+)")
        label = "SUPERSTAR" if is_superstar else "NOT SUPERSTAR"
        print(f"  ==> {label}")

        superstar_results[strat_name] = {
            "is_superstar": is_superstar,
            "ac_stats": ac_stats,
            "pf_passing_acs": pf_passing_acs,
            "wr_all_pass": wr_all_pass,
            "symbols_passing": symbols_passing,
            "total_symbols_tested": total_symbols_tested,
            "per_symbol": all_results[strat_name],
        }

    # ==============================================================================
    # SUMMARY TABLE
    # ==============================================================================
    print("\n" + "=" * 80)
    print("FINAL SUMMARY TABLE")
    print("=" * 80)
    print(f"\n{'Strategy':<35} {'Crypto':>10} {'Stocks':>10} {'Forex':>10} {'Commod':>10} {'Star?':>8}")
    print("-" * 83)
    for strat_name in strategy_names:
        sr = superstar_results[strat_name]
        row = f"{strat_name:<35}"
        for ac in ["crypto", "stocks", "forex", "commodities"]:
            s = sr["ac_stats"].get(ac, {})
            if s.get("trades", 0) > 0:
                row += f"  PF={s['pf']:4.2f}"
            else:
                row += f"  {'N/A':>7}"
        row += f"  {'YES' if sr['is_superstar'] else 'NO':>5}"
        print(row)

    print(f"\n{'Strategy':<35} {'PF>1.1 ACs':>12} {'WR>40 all':>10} {'Syms OK':>10}")
    print("-" * 67)
    for strat_name in strategy_names:
        sr = superstar_results[strat_name]
        print(f"{strat_name:<35} {sr['pf_passing_acs']:>7}/4     {'YES' if sr['wr_all_pass'] else 'NO':>6}     {sr['symbols_passing']:>3}/{sr['total_symbols_tested']}")

    # ==============================================================================
    # SAVE RESULTS JSON
    # ==============================================================================
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "..", "..", "alpha_engine", "data", "superstar_analysis.json")
    output_path = os.path.normpath(output_path)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "test_config": {
            "strategies": strategy_names,
            "asset_classes": {k: v["symbols"] for k, v in ASSET_CLASSES.items()},
            "superstar_criteria": {
                "pf_min": 1.1,
                "pf_min_asset_classes": 3,
                "wr_min": 40,
                "wr_all_asset_classes": True,
                "min_symbols_passing": 8,
            }
        },
        "results": {},
    }

    superstars_found = []
    for strat_name in strategy_names:
        sr = superstar_results[strat_name]
        # Convert per_symbol stats for JSON serialization
        per_sym_clean = {}
        for ac, syms in sr["per_symbol"].items():
            per_sym_clean[ac] = {}
            for sym, stats in syms.items():
                per_sym_clean[ac][sym] = {k: (float(v) if isinstance(v, (np.floating, np.integer)) else v) for k, v in stats.items()}

        ac_stats_clean = {}
        for ac, stats in sr["ac_stats"].items():
            ac_stats_clean[ac] = {k: (float(v) if isinstance(v, (np.floating, np.integer)) else v) for k, v in stats.items()}

        output["results"][strat_name] = {
            "is_superstar": sr["is_superstar"],
            "label": f"{strat_name}_MULTIASSETSYMBOL_SUPERSTAR" if sr["is_superstar"] else strat_name,
            "pf_passing_asset_classes": sr["pf_passing_acs"],
            "wr_all_pass": sr["wr_all_pass"],
            "symbols_passing": sr["symbols_passing"],
            "total_symbols_tested": sr["total_symbols_tested"],
            "asset_class_stats": ac_stats_clean,
            "per_symbol_stats": per_sym_clean,
        }
        if sr["is_superstar"]:
            superstars_found.append(strat_name)

    output["superstars"] = superstars_found
    output["superstar_count"] = len(superstars_found)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    # List superstars
    if superstars_found:
        print(f"\n{'='*80}")
        print(f"SUPERSTARS FOUND: {len(superstars_found)}")
        for s in superstars_found:
            print(f"  - {s}_MULTIASSETSYMBOL_SUPERSTAR")
        print(f"{'='*80}")
    else:
        print(f"\nNo superstars found meeting all criteria.")
        # Show closest
        closest = max(strategy_names, key=lambda s: superstar_results[s]["pf_passing_acs"])
        sr = superstar_results[closest]
        print(f"Closest: {closest} (PF>1.1 on {sr['pf_passing_acs']}/4 ACs, {sr['symbols_passing']} symbols passing)")

    print("\nDone.")
