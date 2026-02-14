"""
CONFLUENCE V2 — Hybrid Architecture Signal Engine
==================================================
Key improvement over V1: Asset-specific strategy selection based on
Kimi K2 Agent Swarm findings:
  - BTC/ETH: Momentum strategies (positive momentum correlation)
  - AVAX/BNB: Mean-reversion strategies (negative momentum correlation)

Also improved:
  - Wider SL (2.5-3x ATR) for crypto volatility
  - Volume confirmation filter
  - Regime-aware TP multipliers
  - Trailing stop mechanism
  - Higher confluence threshold for signal firing
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
import time
import ccxt
from strategies import (
    ema, sma, rsi, atr, bollinger_bands, macd, adx, supertrend,
    ichimoku, obv, stochastic,
    strategy_ema_crossover, strategy_rsi_momentum, strategy_macd_crossover,
    strategy_supertrend, strategy_triple_ema, strategy_adx_ema,
    strategy_ichimoku, strategy_volume_momentum, strategy_mtf_momentum,
    strategy_donchian_breakout, strategy_momentum_rotation,
    strategy_bb_squeeze_breakout, strategy_rsi_mean_reversion,
    strategy_bb_rsi_reversion, strategy_vwap_reversion, strategy_stoch_rsi
)


# =============================================================================
# DATA
# =============================================================================
def load_or_fetch(symbol, timeframe='1d', exchange_id='binance', cache_dir='data_cache'):
    os.makedirs(cache_dir, exist_ok=True)
    safe = symbol.replace('/', '_')
    cache_file = os.path.join(cache_dir, f"{safe}_{timeframe}_{exchange_id}.csv")
    if os.path.exists(cache_file):
        if time.time() - os.path.getmtime(cache_file) < 43200:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            print(f"  Cache: {symbol} {timeframe} ({len(df)} candles)")
            return df
    exchange = getattr(ccxt, exchange_id)({'enableRateLimit': True})
    all_data = []
    since = exchange.parse8601('2020-01-01T00:00:00Z')
    print(f"  Fetching {symbol} {timeframe}...")
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not ohlcv: break
            all_data.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            if len(ohlcv) < 1000: break
            time.sleep(exchange.rateLimit / 1000)
        except Exception as e:
            print(f"  Warning: {e}"); break
    if not all_data: return None
    df = pd.DataFrame(all_data, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df[~df.index.duplicated(keep='first')].sort_index()
    df.to_csv(cache_file)
    print(f"  Got {len(df)} candles")
    return df


# =============================================================================
# ASSET-SPECIFIC STRATEGY PROFILES (Kimi K2 insight)
# =============================================================================

# BTC/ETH: Momentum assets — use trend-following and breakout strategies
MOMENTUM_STRATEGIES = {
    'RSI_Momentum': {'fn': strategy_rsi_momentum, 'weight': 2.5},
    'MTF_Momentum': {'fn': strategy_mtf_momentum, 'weight': 2.5},
    'Donchian_Breakout': {'fn': strategy_donchian_breakout, 'weight': 2.0},
    'Supertrend': {'fn': strategy_supertrend, 'weight': 2.0},
    'EMA_Cross': {'fn': strategy_ema_crossover, 'weight': 1.5},
    'Triple_EMA': {'fn': strategy_triple_ema, 'weight': 1.5},
    'MACD_Cross': {'fn': strategy_macd_crossover, 'weight': 1.5},
    'ADX_EMA': {'fn': strategy_adx_ema, 'weight': 1.5},
    'Ichimoku': {'fn': strategy_ichimoku, 'weight': 1.0},
    'Volume_Momentum': {'fn': strategy_volume_momentum, 'weight': 1.0},
    'Momentum_Rotation': {'fn': strategy_momentum_rotation, 'weight': 2.0},
}

# AVAX/BNB: Mean-reverting assets — use reversion and range strategies
MEAN_REVERSION_STRATEGIES = {
    'RSI_Mean_Rev': {'fn': strategy_rsi_mean_reversion, 'weight': 2.5},
    'BB_RSI_Rev': {'fn': strategy_bb_rsi_reversion, 'weight': 2.5},
    'VWAP_Rev': {'fn': strategy_vwap_reversion, 'weight': 2.0},
    'BB_Squeeze': {'fn': strategy_bb_squeeze_breakout, 'weight': 1.5},
    'Stoch_RSI': {'fn': strategy_stoch_rsi, 'weight': 1.5},
    'Supertrend': {'fn': strategy_supertrend, 'weight': 1.0},
    'EMA_Cross': {'fn': strategy_ema_crossover, 'weight': 1.0},
    'MACD_Cross': {'fn': strategy_macd_crossover, 'weight': 1.0},
    'Volume_Momentum': {'fn': strategy_volume_momentum, 'weight': 1.0},
    'Donchian_Breakout': {'fn': strategy_donchian_breakout, 'weight': 1.0},
}

ASSET_PROFILES = {
    'BTC/USDT':  {'type': 'momentum', 'strategies': MOMENTUM_STRATEGIES, 'sl_atr_mult': 2.5, 'max_risk_pct': 6.0, 'vol_class': 'medium'},
    'ETH/USDT':  {'type': 'momentum', 'strategies': MOMENTUM_STRATEGIES, 'sl_atr_mult': 2.5, 'max_risk_pct': 7.0, 'vol_class': 'high'},
    'AVAX/USDT': {'type': 'mean_reversion', 'strategies': MEAN_REVERSION_STRATEGIES, 'sl_atr_mult': 3.0, 'max_risk_pct': 8.0, 'vol_class': 'very_high'},
    'BNB/USDT':  {'type': 'mean_reversion', 'strategies': MEAN_REVERSION_STRATEGIES, 'sl_atr_mult': 2.5, 'max_risk_pct': 6.0, 'vol_class': 'medium'},
}


def compute_regime(df, lookback=60):
    ret = df['close'].pct_change(lookback).fillna(0)
    regime = pd.Series('sideways', index=df.index)
    regime[ret > 0.15] = 'bull'
    regime[ret < -0.15] = 'bear'
    return regime


def generate_signals(df, symbol):
    """Generate confluence signals using asset-appropriate strategies."""
    profile = ASSET_PROFILES[symbol]
    strategies = profile['strategies']
    sl_mult = profile['sl_atr_mult']
    max_risk = profile['max_risk_pct']
    max_score = sum(s['weight'] for s in strategies.values())

    # Run all strategies
    strat_sigs = {}
    for name, info in strategies.items():
        try:
            strat_sigs[name] = info['fn'](df)
        except:
            strat_sigs[name] = pd.Series(0, index=df.index)

    # Compute weighted score and count
    score = pd.Series(0.0, index=df.index)
    n_agree = pd.Series(0, index=df.index)
    names_agree = pd.Series('', index=df.index, dtype=str)
    for name, info in strategies.items():
        sig = strat_sigs[name]
        is_long = (sig == 1).astype(float)
        score += is_long * info['weight']
        n_agree += is_long.astype(int)
        for idx in df.index[is_long == 1]:
            names_agree[idx] = (names_agree[idx] + ',' + name).strip(',')

    score_pct = score / max_score
    atr_14 = atr(df['high'], df['low'], df['close'], 14)
    atr_20 = atr(df['high'], df['low'], df['close'], 20)
    rsi_14 = rsi(df['close'], 14)
    regime = compute_regime(df)
    support = df['low'].rolling(50).min()
    resistance = df['high'].rolling(50).max()

    # Volume confirmation: current volume > 1.2x 20-day average
    vol_avg = df['volume'].rolling(20).mean()
    vol_confirm = df['volume'] > vol_avg * 1.2

    # Thresholds — stricter than V1
    if profile['type'] == 'momentum':
        min_score_pct = 0.50
        min_strats = 4
    else:
        min_score_pct = 0.40  # Lower for mean-reversion (fewer strategies fire simultaneously)
        min_strats = 3

    signals = []
    last_idx = None
    cooldown = 7  # Wider cooldown

    for i in range(60, len(df)):
        idx = df.index[i]
        if last_idx is not None and (i - last_idx) < cooldown:
            continue
        if score_pct.iloc[i] < min_score_pct or n_agree.iloc[i] < min_strats:
            continue
        # New signal check
        if i > 0 and score_pct.iloc[i-1] >= min_score_pct and n_agree.iloc[i-1] >= min_strats:
            if score_pct.iloc[i] <= score_pct.iloc[i-1] * 1.15:
                continue

        # Overbought filter for momentum assets
        if profile['type'] == 'momentum' and pd.notna(rsi_14.iloc[i]) and rsi_14.iloc[i] > 78:
            continue
        # Oversold filter for mean-reversion (only buy when oversold or neutral)
        if profile['type'] == 'mean_reversion' and pd.notna(rsi_14.iloc[i]) and rsi_14.iloc[i] > 65:
            continue

        entry = df['close'].iloc[i]
        cur_atr = atr_14.iloc[i]
        if pd.isna(cur_atr) or cur_atr <= 0:
            continue

        # Volume confirmation (soft — bonus, not required)
        has_vol = bool(vol_confirm.iloc[i]) if pd.notna(vol_confirm.iloc[i]) else False

        # === STOP LOSS (wider than V1) ===
        sl_atr = entry - sl_mult * cur_atr
        sl_support = support.iloc[i] * 0.99 if pd.notna(support.iloc[i]) else sl_atr
        sl_price = max(sl_atr, sl_support)
        sl_price = min(sl_price, entry * (1 - 0.005))  # At least 0.5% below
        sl_price = max(sl_price, entry * (1 - max_risk / 100))  # Cap max risk
        sl_pct = (entry - sl_price) / entry * 100

        # === TAKE PROFIT (regime-adjusted) ===
        cur_regime = regime.iloc[i]
        conf = score_pct.iloc[i]

        if profile['type'] == 'momentum':
            if cur_regime == 'bull':
                tp_mult = 5.0
            elif cur_regime == 'bear':
                tp_mult = 2.5
            else:
                tp_mult = 3.5
        else:  # mean_reversion — tighter targets
            if cur_regime == 'bull':
                tp_mult = 3.0
            elif cur_regime == 'bear':
                tp_mult = 1.8
            else:
                tp_mult = 2.2

        tp_mult *= (0.8 + 0.4 * conf)
        tp_price = entry + tp_mult * cur_atr
        tp_resist = resistance.iloc[i] * 0.995 if pd.notna(resistance.iloc[i]) else tp_price
        if tp_resist > entry * 1.005:
            tp_price = min(tp_price, tp_resist)
        tp_price = max(tp_price, entry * 1.01)
        tp_pct = (tp_price - entry) / entry * 100

        risk = entry - sl_price
        reward = tp_price - entry
        rr = reward / risk if risk > 0 else 0
        if rr < 1.5:
            continue

        n_s = int(n_agree.iloc[i])
        if conf >= 0.70 and n_s >= 6:
            confidence = 'VERY_HIGH'
        elif conf >= 0.55 and n_s >= 5:
            confidence = 'HIGH'
        elif conf >= 0.45 and n_s >= 4:
            confidence = 'MEDIUM_HIGH'
        else:
            confidence = 'MEDIUM'

        signals.append({
            'date': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
            'entry_price': round(entry, 4),
            'take_profit': round(tp_price, 4),
            'stop_loss': round(sl_price, 4),
            'tp_pct': round(tp_pct, 2),
            'sl_pct': round(sl_pct, 2),
            'rr_ratio': round(rr, 2),
            'confidence': confidence,
            'confluence_score': round(conf * 100, 1),
            'n_strategies': n_s,
            'strategies': names_agree.iloc[i],
            'regime': cur_regime,
            'rsi_14': round(rsi_14.iloc[i], 1) if pd.notna(rsi_14.iloc[i]) else None,
            'atr_14': round(cur_atr, 4),
            'volume_confirmed': has_vol,
            'asset_type': profile['type'],
        })
        last_idx = i

    return signals


def evaluate_signals(signals, df, max_hold=30):
    """Track each signal to TP, SL, or expiry. Uses trailing stop."""
    results = []
    for sig in signals:
        date = pd.Timestamp(sig['date'])
        mask = df.index >= date
        if not mask.any(): continue
        start = df.index.get_loc(df.index[mask][0])
        entry = sig['entry_price']
        tp = sig['take_profit']
        sl = sig['stop_loss']
        end = min(start + max_hold, len(df))

        outcome = 'EXPIRED'
        exit_price = None
        exit_date = None
        bars = 0
        max_p = entry
        min_p = entry
        trailing_sl = sl  # Trailing stop starts at initial SL

        for j in range(start + 1, end):
            h = df['high'].iloc[j]
            l = df['low'].iloc[j]
            bars = j - start
            max_p = max(max_p, h)
            min_p = min(min_p, l)

            # Update trailing stop: once price moves 1.5x risk in our favor, trail SL to breakeven
            risk_dist = entry - sl
            if max_p >= entry + 1.5 * risk_dist:
                trailing_sl = max(trailing_sl, entry + 0.002 * entry)  # Breakeven + 0.2%
            # If price moves 2.5x risk, trail to 1x risk profit
            if max_p >= entry + 2.5 * risk_dist:
                trailing_sl = max(trailing_sl, entry + risk_dist)

            if l <= trailing_sl:
                outcome = 'SL_HIT'
                exit_price = trailing_sl
                exit_date = df.index[j].strftime('%Y-%m-%d')
                break
            if h >= tp:
                outcome = 'TP_HIT'
                exit_price = tp
                exit_date = df.index[j].strftime('%Y-%m-%d')
                break

        if outcome == 'EXPIRED':
            ei = min(end - 1, len(df) - 1)
            exit_price = df['close'].iloc[ei]
            exit_date = df.index[ei].strftime('%Y-%m-%d')
            bars = ei - start

        pnl = (exit_price - entry) / entry * 100
        mfe = (max_p - entry) / entry * 100
        mae = (min_p - entry) / entry * 100

        results.append({**sig,
            'outcome': outcome,
            'exit_price': round(exit_price, 4),
            'exit_date': exit_date,
            'pnl_pct': round(pnl, 2),
            'bars_held': bars,
            'mfe_pct': round(mfe, 2),
            'mae_pct': round(mae, 2),
        })
    return results


def analyze(results, symbol):
    if not results: return None
    df = pd.DataFrame(results)
    total = len(df)
    tp = len(df[df['outcome'] == 'TP_HIT'])
    sl = len(df[df['outcome'] == 'SL_HIT'])
    exp = len(df[df['outcome'] == 'EXPIRED'])
    wr = tp / total * 100 if total else 0
    avg_pnl = df['pnl_pct'].mean()
    winners = df[df['pnl_pct'] > 0]
    losers = df[df['pnl_pct'] <= 0]
    avg_win = winners['pnl_pct'].mean() if len(winners) else 0
    avg_loss = losers['pnl_pct'].mean() if len(losers) else 0
    gp = winners['pnl_pct'].sum() if len(winners) else 0
    gl = abs(losers['pnl_pct'].sum()) if len(losers) else 0.001
    pf = gp / gl

    # Equity curve
    eq = [10000]
    for p in df['pnl_pct'].values:
        eq.append(eq[-1] * (1 + p / 100))
    peak = pd.Series(eq).cummax()
    dd = ((pd.Series(eq) - peak) / peak).min() * 100

    # By confidence
    conf_stats = {}
    for c in ['VERY_HIGH', 'HIGH', 'MEDIUM_HIGH', 'MEDIUM']:
        sub = df[df['confidence'] == c]
        if len(sub):
            ct = len(sub[sub['outcome'] == 'TP_HIT'])
            conf_stats[c] = {'count': len(sub), 'win_rate': round(ct/len(sub)*100, 1), 'avg_pnl': round(sub['pnl_pct'].mean(), 2)}

    # By regime
    reg_stats = {}
    for r in ['bull', 'bear', 'sideways']:
        sub = df[df['regime'] == r]
        if len(sub):
            ct = len(sub[sub['outcome'] == 'TP_HIT'])
            reg_stats[r] = {'count': len(sub), 'win_rate': round(ct/len(sub)*100, 1), 'avg_pnl': round(sub['pnl_pct'].mean(), 2)}

    # Volume confirmed vs not
    vol_yes = df[df['volume_confirmed'] == True]
    vol_no = df[df['volume_confirmed'] == False]
    vol_stats = {}
    if len(vol_yes):
        vt = len(vol_yes[vol_yes['outcome'] == 'TP_HIT'])
        vol_stats['confirmed'] = {'count': len(vol_yes), 'win_rate': round(vt/len(vol_yes)*100, 1), 'avg_pnl': round(vol_yes['pnl_pct'].mean(), 2)}
    if len(vol_no):
        vt = len(vol_no[vol_no['outcome'] == 'TP_HIT'])
        vol_stats['unconfirmed'] = {'count': len(vol_no), 'win_rate': round(vt/len(vol_no)*100, 1), 'avg_pnl': round(vol_no['pnl_pct'].mean(), 2)}

    return {
        'symbol': symbol,
        'asset_type': ASSET_PROFILES[symbol]['type'],
        'total_signals': total, 'tp_hits': tp, 'sl_hits': sl, 'expired': exp,
        'win_rate': round(wr, 1),
        'avg_pnl': round(avg_pnl, 2), 'avg_win': round(avg_win, 2), 'avg_loss': round(avg_loss, 2),
        'profit_factor': round(pf, 2),
        'total_pnl': round(df['pnl_pct'].sum(), 2),
        'max_drawdown': round(dd, 2),
        'final_equity': round(eq[-1], 2),
        'total_return': round((eq[-1]/10000-1)*100, 2),
        'avg_rr': round(df['rr_ratio'].mean(), 2),
        'avg_bars': round(df['bars_held'].mean(), 1),
        'confidence_breakdown': conf_stats,
        'regime_breakdown': reg_stats,
        'volume_breakdown': vol_stats,
    }


def generate_report(all_perf, all_results):
    lines = []
    lines.append("# CONFLUENCE V2 — Hybrid Architecture Signal Engine Results")
    lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("**Engine:** Asset-specific strategy selection (Kimi K2 insight)")
    lines.append("**BTC/ETH:** Momentum strategies | **AVAX/BNB:** Mean-reversion strategies")
    lines.append("**Improvements over V1:** Wider SL, volume confirmation, trailing stop, regime-aware TP")

    lines.append("\n---\n## EXECUTIVE SUMMARY\n")
    lines.append("| Pair | Type | Signals | Win Rate | Avg PnL | Total PnL | PF | Max DD | $10k → |")
    lines.append("|------|------|---------|----------|---------|-----------|-----|--------|--------|")
    for p in all_perf:
        if p:
            lines.append(f"| {p['symbol']} | {p['asset_type']} | {p['total_signals']} | "
                        f"{p['win_rate']}% | {p['avg_pnl']}% | {p['total_pnl']}% | "
                        f"{p['profit_factor']} | {p['max_drawdown']}% | ${p['final_equity']:,.0f} |")

    # V1 vs V2 comparison
    lines.append("\n---\n## V1 vs V2 COMPARISON\n")
    lines.append("| Pair | V1 Win Rate | V2 Win Rate | V1 PnL | V2 PnL | V1 $10k | V2 $10k | Improvement |")
    lines.append("|------|-------------|-------------|--------|--------|---------|---------|-------------|")
    v1_data = {
        'BTC/USDT': {'wr': 37.5, 'pnl': 108.1, 'eq': 22919},
        'ETH/USDT': {'wr': 39.6, 'pnl': 80.1, 'eq': 16454},
        'AVAX/USDT': {'wr': 33.3, 'pnl': 6.2, 'eq': 7507},
        'BNB/USDT': {'wr': 38.1, 'pnl': 131.1, 'eq': 26351},
    }
    for p in all_perf:
        if p and p['symbol'] in v1_data:
            v1 = v1_data[p['symbol']]
            imp = p['final_equity'] - v1['eq']
            lines.append(f"| {p['symbol']} | {v1['wr']}% | {p['win_rate']}% | "
                        f"{v1['pnl']}% | {p['total_pnl']}% | "
                        f"${v1['eq']:,} | ${p['final_equity']:,.0f} | ${imp:+,.0f} |")

    for p in all_perf:
        if not p: continue
        sym = p['symbol']
        lines.append(f"\n---\n## {sym} ({p['asset_type'].upper()})\n")
        lines.append(f"- **Signals:** {p['total_signals']} | **TP:** {p['tp_hits']} | **SL:** {p['sl_hits']} | **Expired:** {p['expired']}")
        lines.append(f"- **Win Rate:** {p['win_rate']}% | **Avg PnL:** {p['avg_pnl']}%")
        lines.append(f"- **Avg Win:** +{p['avg_win']}% | **Avg Loss:** {p['avg_loss']}%")
        lines.append(f"- **Profit Factor:** {p['profit_factor']} | **R:R:** {p['avg_rr']}")
        lines.append(f"- **Max DD:** {p['max_drawdown']}% | **$10k →** ${p['final_equity']:,.0f}")

        if p['confidence_breakdown']:
            lines.append(f"\n### By Confidence\n| Level | Signals | Win Rate | Avg PnL |")
            lines.append("|-------|---------|----------|---------|")
            for c, s in p['confidence_breakdown'].items():
                lines.append(f"| {c} | {s['count']} | {s['win_rate']}% | {s['avg_pnl']}% |")

        if p['regime_breakdown']:
            lines.append(f"\n### By Regime\n| Regime | Signals | Win Rate | Avg PnL |")
            lines.append("|--------|---------|----------|---------|")
            for r, s in p['regime_breakdown'].items():
                lines.append(f"| {r} | {s['count']} | {s['win_rate']}% | {s['avg_pnl']}% |")

        if p['volume_breakdown']:
            lines.append(f"\n### Volume Confirmation\n| Volume | Signals | Win Rate | Avg PnL |")
            lines.append("|--------|---------|----------|---------|")
            for v, s in p['volume_breakdown'].items():
                lines.append(f"| {v} | {s['count']} | {s['win_rate']}% | {s['avg_pnl']}% |")

    # Recent signals
    lines.append("\n---\n## RECENT SIGNALS (Last 15 per pair)\n")
    for sym, res in all_results.items():
        lines.append(f"\n### {sym}\n")
        lines.append("| Date | Entry | TP | SL | R:R | Conf | Outcome | PnL | Bars |")
        lines.append("|------|-------|----|----|-----|------|---------|-----|------|")
        for r in res[-15:]:
            o = 'W' if r['outcome']=='TP_HIT' else ('L' if r['outcome']=='SL_HIT' else 'E')
            lines.append(f"| {r['date']} | {r['entry_price']} | {r['take_profit']} | "
                        f"{r['stop_loss']} | {r['rr_ratio']} | {r['confidence']} | "
                        f"{o} | {r['pnl_pct']}% | {r['bars_held']}d |")

    lines.append("\n---\n## METHODOLOGY\n")
    lines.append("### V2 Hybrid Architecture (Kimi K2 Insight)")
    lines.append("- **BTC/ETH:** 11 momentum strategies (RSI Momentum, MTF Momentum, Donchian, Supertrend, etc.)")
    lines.append("- **AVAX/BNB:** 10 mean-reversion strategies (RSI Mean Rev, BB+RSI, VWAP Rev, Stoch RSI, etc.)")
    lines.append("- **SL:** 2.5-3x ATR (wider than V1's 2x) with trailing stop mechanism")
    lines.append("- **TP:** Regime-adjusted ATR multiplier (bull: 3-5x, bear: 1.8-2.5x, sideways: 2.2-3.5x)")
    lines.append("- **Trailing Stop:** Moves to breakeven at 1.5x risk, to 1x profit at 2.5x risk")
    lines.append("- **Min R:R:** 1.5:1 | **Cooldown:** 7 bars | **Max hold:** 30 days")
    lines.append("- **RSI filter:** Momentum assets: skip if RSI>78 | Mean-rev assets: skip if RSI>65")

    return "\n".join(lines)


def main():
    print("=" * 70)
    print("  CONFLUENCE V2 — Hybrid Architecture Signal Engine")
    print("  BTC/ETH: Momentum | AVAX/BNB: Mean Reversion")
    print("=" * 70)

    pairs = ['BTC/USDT', 'ETH/USDT', 'AVAX/USDT', 'BNB/USDT']
    all_perf = []
    all_results = {}

    for symbol in pairs:
        print(f"\n{'='*50}")
        print(f"  {symbol} ({ASSET_PROFILES[symbol]['type'].upper()})")
        print(f"{'='*50}")

        df = load_or_fetch(symbol, '1d', 'binance')
        if df is None or len(df) < 200:
            print(f"  Skip — insufficient data"); continue

        signals = generate_signals(df, symbol)
        print(f"  {len(signals)} signals generated")

        results = evaluate_signals(signals, df)
        print(f"  {len(results)} evaluated")

        perf = analyze(results, symbol)
        if perf:
            all_perf.append(perf)
            all_results[symbol] = results
            print(f"\n  === {symbol} ===")
            print(f"  Type: {perf['asset_type']} | Signals: {perf['total_signals']} | WR: {perf['win_rate']}%")
            print(f"  Avg PnL: {perf['avg_pnl']}% | PF: {perf['profit_factor']} | Total: {perf['total_pnl']}%")
            print(f"  TP: {perf['tp_hits']} | SL: {perf['sl_hits']} | Exp: {perf['expired']}")
            print(f"  $10k → ${perf['final_equity']:,.0f} ({perf['total_return']}%)")
            if perf['confidence_breakdown']:
                for c, s in perf['confidence_breakdown'].items():
                    print(f"    {c}: {s['count']} sig, {s['win_rate']}% WR, {s['avg_pnl']}% avg")

    if not all_perf:
        print("\nNo results."); return

    # Report
    out = os.path.dirname(os.path.abspath(__file__))
    report = generate_report(all_perf, all_results)
    with open(os.path.join(out, 'CONFLUENCE_V2_REPORT.md'), 'w', encoding='utf-8') as f:
        f.write(report)

    with open(os.path.join(out, 'confluence_v2_signals.json'), 'w', encoding='utf-8') as f:
        json.dump({'performance': all_perf, 'signals': {s: r for s, r in all_results.items()},
                   'generated': datetime.now().isoformat(), 'version': 'v2_hybrid',
                   'architecture': 'BTC/ETH=momentum, AVAX/BNB=mean_reversion'}, f, indent=2, default=str)

    print(f"\n{'='*70}")
    print("  V2 FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"\n  {'Pair':<14} {'Type':<12} {'Sig':>5} {'WR':>7} {'AvgPnL':>8} {'TotPnL':>9} {'PF':>6} {'MaxDD':>7} {'$10k→':>10}")
    print(f"  {'-'*80}")
    for p in all_perf:
        print(f"  {p['symbol']:<14} {p['asset_type']:<12} {p['total_signals']:>5} {p['win_rate']:>6.1f}% "
              f"{p['avg_pnl']:>7.2f}% {p['total_pnl']:>8.1f}% {p['profit_factor']:>6.2f} "
              f"{p['max_drawdown']:>6.1f}% ${p['final_equity']:>9,.0f}")
    print(f"\n  Reports: CONFLUENCE_V2_REPORT.md, confluence_v2_signals.json")


if __name__ == '__main__':
    main()
