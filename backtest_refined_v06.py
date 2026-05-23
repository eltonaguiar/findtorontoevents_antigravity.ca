"""
SSK_Claude — Refined v0.06 Tests
=================================
Based on individual isolation results:
- Change B (MinSigLvl 4 for EXTR) was the only positive change (+6.44%)
- Change C (MR distance 5%) never triggered — threshold too tight for crypto
- Changes A, D, E were neutral or negative

This script tests refined combinations:
1. B only (MinSigLvl 4 for EXTR)
2. B + C_10 (MR distance at 10% — more realistic for crypto)
3. B + C_15 (MR distance at 15%)
4. B + selective_A (only reclassify pairs that improved: APE→EXTR, skip INJ/ARB)
5. B + E_weak (trend bias only in RANGE regime, not globally)
6. B + DD_guard (reduce position after 3 consecutive losses — new idea)
"""

import pandas as pd
import numpy as np
import json
import os
import sys
from math import erfc, sqrt

sys.path.insert(0, os.path.dirname(__file__))
from backtest_v05_vs_v06 import (
    download_binance_klines, calc_rsi, calc_ema, calc_sma, calc_macd,
    calc_atr, calc_supertrend, calc_adx, calc_wavetrend, calc_stochrsi,
    get_v05_tier, get_tier_params, get_special_overrides
)


def get_selective_v06_tier(base):
    """Only reclassify pairs that individually improved."""
    tiers = {
        'TRX': 'LOW',
        'BTC': 'MED', 'BNB': 'MED', 'ALGO': 'MED', 'LTC': 'MED',
        'ETH': 'MHIGH', 'DOT': 'MHIGH', 'LINK': 'MHIGH', 'BCH': 'MHIGH', 'TON': 'MHIGH', 'HBAR': 'MHIGH',
        'DOGE': 'EXTR', 'SHIB': 'EXTR', 'FET': 'EXTR', 'SUI': 'EXTR', 'SEI': 'EXTR',
        'TIA': 'EXTR', 'DYDX': 'EXTR', 'STRK': 'EXTR', 'ZK': 'EXTR',
        # Only APE reclassified (was +31.05% in isolation test)
        'APE': 'EXTR',
        # INJ stays HIGH (reclassification lost -74.60%)
        # ARB stays HIGH (reclassification lost -8.49%)
    }
    return tiers.get(base, 'HIGH')


def run_refined(df, base, config):
    """
    Run backtest with a specific config dict:
      min_sig_extr: int (3 or 4)
      mr_dist: float or None (MR distance threshold %, None=disabled)
      tier_fn: function to get tier
      trend_bias_mode: None, 'global', 'range_only'
      loss_streak_guard: bool (reduce scoring after 3 consecutive losses)
    """
    tier = config['tier_fn'](base)
    p = get_tier_params(tier, 'v05')  # Always use v05 params (D was rejected)
    p.setdefault('rsi_len', 14)
    p.setdefault('macd_f', 12)
    p.setdefault('macd_s', 26)
    p.setdefault('macd_sig', 9)
    p = get_special_overrides(base, p)

    min_sig = config.get('min_sig_extr', 3) if tier == 'EXTR' else 3
    mr_dist_threshold = config.get('mr_dist', None)
    trend_bias_mode = config.get('trend_bias_mode', None)
    loss_streak_guard = config.get('loss_streak_guard', False)

    close = df['close']
    high = df['high']
    low = df['low']
    hlc3 = (high + low + close) / 3

    rsi = calc_rsi(close, p['rsi_len'])
    macd_l, sig_l, macd_h = calc_macd(close, p['macd_f'], p['macd_s'], p['macd_sig'])
    st_val, st_dir = calc_supertrend(high, low, close, p['st_fact'], p['st_per'])
    ema_f = calc_ema(close, 9)
    ema_m = calc_ema(close, 21)
    ema_s = calc_ema(close, 50)
    wt1, wt2 = calc_wavetrend(hlc3, 10, 21)
    srsi_k, srsi_d = calc_stochrsi(close, 14, 3, 3)
    di_plus, di_minus, adx = calc_adx(high, low, close, 14)
    atr = calc_atr(high, low, close, 14)
    ema50 = calc_ema(close, 50)

    tp_base = 2.0
    sl_base = 1.0
    tp_mult = tp_base * p['vol_adj']
    sl_mult = sl_base * p['vol_adj']

    n = len(df)
    trades = []
    in_trade = False
    pending = False
    entry_price = 0.0
    entry_bar = 0
    tp_level = 0.0
    sl_level = 0.0
    max_hold = 15
    consecutive_losses = 0

    for i in range(max(60, p.get('rsi_len', 14) + 5), n):
        if np.isnan(adx.iloc[i]) or np.isnan(rsi.iloc[i]):
            continue

        adx_v = adx.iloc[i]
        regime = 'TREND' if adx_v >= p['adx_trend'] else ('MIXED' if adx_v >= p['adx_range'] else 'RANGE')
        is_trend = regime == 'TREND'
        is_range = regime == 'RANGE'

        rsi_buy_raw = rsi.iloc[i] < p['rsi_os']
        rsi_sell_raw = rsi.iloc[i] > p['rsi_ob']
        macd_buy = macd_l.iloc[i] > sig_l.iloc[i] and macd_h.iloc[i] > 0
        macd_sell = macd_l.iloc[i] < sig_l.iloc[i] and macd_h.iloc[i] < 0
        st_buy_raw = st_dir.iloc[i] < 0
        st_sell_raw = st_dir.iloc[i] > 0
        ema_bull_raw = ema_f.iloc[i] > ema_m.iloc[i] and ema_m.iloc[i] > ema_s.iloc[i]
        ema_bear_raw = ema_f.iloc[i] < ema_m.iloc[i] and ema_m.iloc[i] < ema_s.iloc[i]
        wt_buy_raw = (wt1.iloc[i] > wt2.iloc[i] and wt1.iloc[i-1] <= wt2.iloc[i-1] and wt1.iloc[i] < -60)
        wt_sell_raw = (wt1.iloc[i] < wt2.iloc[i] and wt1.iloc[i-1] >= wt2.iloc[i-1] and wt1.iloc[i] > 60)
        sr_buy = (not np.isnan(srsi_k.iloc[i]) and not np.isnan(srsi_d.iloc[i]) and
                  srsi_k.iloc[i] > srsi_d.iloc[i] and srsi_k.iloc[i-1] <= srsi_d.iloc[i-1] and srsi_k.iloc[i] < 20)
        sr_sell = (not np.isnan(srsi_k.iloc[i]) and not np.isnan(srsi_d.iloc[i]) and
                   srsi_k.iloc[i] < srsi_d.iloc[i] and srsi_k.iloc[i-1] >= srsi_d.iloc[i-1] and srsi_k.iloc[i] > 80)
        adx_bull = di_plus.iloc[i] > di_minus.iloc[i]
        adx_bear = di_minus.iloc[i] > di_plus.iloc[i]

        # Regime gating
        rsi_buy = False if is_trend else rsi_buy_raw
        rsi_sell = False if is_trend else rsi_sell_raw
        st_buy = False if is_range else st_buy_raw
        st_sell = False if is_range else st_sell_raw
        ema_bull = False if is_range else ema_bull_raw
        ema_bear = False if is_range else ema_bear_raw
        wt_buy = False if is_trend else wt_buy_raw
        wt_sell = False if is_trend else wt_sell_raw

        # MR distance filter
        if mr_dist_threshold is not None and not np.isnan(ema50.iloc[i]) and ema50.iloc[i] > 0:
            dist_pct = abs(close.iloc[i] - ema50.iloc[i]) / ema50.iloc[i] * 100
            if dist_pct > mr_dist_threshold:
                rsi_buy = False
                rsi_sell = False
                wt_buy = False
                wt_sell = False

        # Weighted consensus
        b_score = 0
        b_score += (2 if is_range else 1) if rsi_buy else 0
        b_score += (2 if is_trend else 1) if macd_buy else 0
        b_score += (2 if is_trend else 1) if st_buy else 0
        b_score += (2 if is_trend else 1) if ema_bull else 0
        b_score += (2 if is_range else 1) if wt_buy else 0
        b_score += 1 if sr_buy else 0
        b_score += 1 if adx_bull else 0

        s_score = 0
        s_score += (2 if is_range else 1) if rsi_sell else 0
        s_score += (2 if is_trend else 1) if macd_sell else 0
        s_score += (2 if is_trend else 1) if st_sell else 0
        s_score += (2 if is_trend else 1) if ema_bear else 0
        s_score += (2 if is_range else 1) if wt_sell else 0
        s_score += 1 if sr_sell else 0
        s_score += 1 if adx_bear else 0

        # Trend bias filter
        if trend_bias_mode == 'global':
            if not np.isnan(ema50.iloc[i]) and close.iloc[i] < ema50.iloc[i]:
                b_score = max(0, b_score - 1)
            if not np.isnan(ema50.iloc[i]) and close.iloc[i] > ema50.iloc[i]:
                s_score = max(0, s_score - 1)
        elif trend_bias_mode == 'range_only' and is_range:
            if not np.isnan(ema50.iloc[i]) and close.iloc[i] < ema50.iloc[i]:
                b_score = max(0, b_score - 1)
            if not np.isnan(ema50.iloc[i]) and close.iloc[i] > ema50.iloc[i]:
                s_score = max(0, s_score - 1)

        # Loss streak guard: require +1 extra after 3 consecutive losses
        effective_min_sig = min_sig
        if loss_streak_guard and consecutive_losses >= 3:
            effective_min_sig = min_sig + 1

        is_buy = b_score >= effective_min_sig and b_score > s_score

        # Trade management
        if pending and not in_trade:
            entry_price = df['open'].iloc[i]
            entry_bar = i
            tp_dist = atr.iloc[i] * tp_mult if not np.isnan(atr.iloc[i]) else entry_price * 0.02
            sl_dist = atr.iloc[i] * sl_mult if not np.isnan(atr.iloc[i]) else entry_price * 0.01
            tp_level = entry_price + tp_dist
            sl_level = entry_price - sl_dist
            in_trade = True
            pending = False

        if in_trade:
            tp_hit = high.iloc[i] >= tp_level
            sl_hit = low.iloc[i] <= sl_level
            bars_held = i - entry_bar

            if tp_hit and sl_hit:
                pnl = -(abs(entry_price - sl_level) / entry_price * 100)
                trades.append({'pnl': pnl, 'result': 'loss'})
                consecutive_losses += 1
                in_trade = False
            elif tp_hit:
                pnl = (tp_level - entry_price) / entry_price * 100
                trades.append({'pnl': pnl, 'result': 'win'})
                consecutive_losses = 0
                in_trade = False
            elif sl_hit:
                pnl = -(abs(entry_price - sl_level) / entry_price * 100)
                trades.append({'pnl': pnl, 'result': 'loss'})
                consecutive_losses += 1
                in_trade = False
            elif bars_held >= max_hold:
                pnl = (close.iloc[i] - entry_price) / entry_price * 100
                result = 'win' if pnl > 0.1 else ('loss' if pnl < -0.1 else 'flat')
                trades.append({'pnl': pnl, 'result': result})
                if result == 'loss':
                    consecutive_losses += 1
                else:
                    consecutive_losses = 0
                in_trade = False

        if not in_trade and not pending and is_buy:
            pending = True

    if not trades:
        return {'trades': 0, 'net_pnl': 0, 'pf': 0, 'wr': 0, 'sharpe': 0, 'max_dd': 0}

    wins = [t for t in trades if t['result'] == 'win']
    losses = [t for t in trades if t['result'] == 'loss']
    total = len(wins) + len(losses)
    wr = len(wins) / total * 100 if total > 0 else 0
    sum_win = sum(t['pnl'] for t in wins)
    sum_loss = sum(abs(t['pnl']) for t in losses)
    pf = sum_win / sum_loss if sum_loss > 0 else (99.9 if sum_win > 0 else 0)
    net_pnl = sum(t['pnl'] for t in trades)

    equity = [0]
    for t in trades:
        equity.append(equity[-1] + t['pnl'])
    equity = np.array(equity)
    peak = np.maximum.accumulate(equity)
    max_dd = (equity - peak).min()

    pnl_arr = np.array([t['pnl'] for t in trades])
    sharpe = np.mean(pnl_arr) / np.std(pnl_arr) * np.sqrt(min(total, 365)) if np.std(pnl_arr) > 0 else 0

    return {
        'trades': total, 'net_pnl': round(net_pnl, 2),
        'pf': round(pf, 3), 'wr': round(wr, 2),
        'sharpe': round(sharpe, 3), 'max_dd': round(max_dd, 2)
    }


TEST_PAIRS = [
    ('TRXUSDT', 'TRX'), ('BTCUSDT', 'BTC'), ('ALGOUSDT', 'ALGO'),
    ('ETHUSDT', 'ETH'), ('DOTUSDT', 'DOT'),
    ('SOLUSDT', 'SOL'), ('XRPUSDT', 'XRP'),
    ('INJUSDT', 'INJ'), ('ARBUSDT', 'ARB'), ('APEUSDT', 'APE'),
    ('DOGEUSDT', 'DOGE'), ('FETUSDT', 'FET'),
    ('DYDXUSDT', 'DYDX'), ('SHIBUSDT', 'SHIB'),
]


CONFIGS = {
    'baseline': {
        'label': 'v0.05 BASELINE',
        'tier_fn': get_v05_tier,
        'min_sig_extr': 3,
        'mr_dist': None,
        'trend_bias_mode': None,
        'loss_streak_guard': False,
    },
    'B_only': {
        'label': 'B: MinSigLvl 4 EXTR',
        'tier_fn': get_v05_tier,
        'min_sig_extr': 4,
        'mr_dist': None,
        'trend_bias_mode': None,
        'loss_streak_guard': False,
    },
    'B_C10': {
        'label': 'B + MR dist 10%',
        'tier_fn': get_v05_tier,
        'min_sig_extr': 4,
        'mr_dist': 10.0,
        'trend_bias_mode': None,
        'loss_streak_guard': False,
    },
    'B_C15': {
        'label': 'B + MR dist 15%',
        'tier_fn': get_v05_tier,
        'min_sig_extr': 4,
        'mr_dist': 15.0,
        'trend_bias_mode': None,
        'loss_streak_guard': False,
    },
    'B_selA': {
        'label': 'B + Selective Reclass (APE only)',
        'tier_fn': get_selective_v06_tier,
        'min_sig_extr': 4,
        'mr_dist': None,
        'trend_bias_mode': None,
        'loss_streak_guard': False,
    },
    'B_E_range': {
        'label': 'B + Trend Bias (RANGE only)',
        'tier_fn': get_v05_tier,
        'min_sig_extr': 4,
        'mr_dist': None,
        'trend_bias_mode': 'range_only',
        'loss_streak_guard': False,
    },
    'B_streak': {
        'label': 'B + Loss Streak Guard',
        'tier_fn': get_v05_tier,
        'min_sig_extr': 4,
        'mr_dist': None,
        'trend_bias_mode': None,
        'loss_streak_guard': True,
    },
    'B_selA_streak': {
        'label': 'B + Selective Reclass + Streak Guard',
        'tier_fn': get_selective_v06_tier,
        'min_sig_extr': 4,
        'mr_dist': None,
        'trend_bias_mode': None,
        'loss_streak_guard': True,
    },
}


def main():
    # Download data
    print("Downloading data...")
    data_cache = {}
    for symbol, base in TEST_PAIRS:
        print(f"  {symbol}...", end='', flush=True)
        df = download_binance_klines(symbol, '1h', 1095)
        if df is not None and len(df) >= 500:
            data_cache[base] = df
            print(f" {len(df)} bars")
        else:
            print(f" SKIP")

    bases = list(data_cache.keys())
    print(f"\n{len(bases)} pairs loaded\n")

    # Run all configs
    all_results = {}
    for cfg_key, cfg in CONFIGS.items():
        print(f"{'='*60}")
        print(f"  {cfg['label']}")
        print(f"{'='*60}")
        all_results[cfg_key] = {}
        for base, df in data_cache.items():
            r = run_refined(df, base, cfg)
            all_results[cfg_key][base] = r
            print(f"  {base:6s}: Tr={r['trades']:4d}  PnL={r['net_pnl']:>8.2f}%  PF={r['pf']:.3f}  WR={r['wr']:.1f}%  Sharpe={r['sharpe']:.3f}")

    # Compare each config vs baseline
    baseline = all_results['baseline']
    config_keys = [k for k in CONFIGS if k != 'baseline']

    print(f"\n{'='*100}")
    print("  COMPARISON vs BASELINE")
    print(f"{'='*100}")
    print(f"\n{'Config':<35} {'Mean ΔPnL':>10} {'Mean ΔPF':>9} {'Mean ΔSh':>9} {'Mean ΔDD':>9} {'Imp/Wrs':>8} {'t-stat':>7} {'p-value':>8} {'Sig':>4}")
    print("-" * 105)

    best_config = None
    best_pnl_d = -999

    for cfg_key in config_keys:
        changed = all_results[cfg_key]
        common = [b for b in bases if baseline[b]['trades'] > 0 and changed[b]['trades'] > 0]

        bp = np.array([baseline[b]['net_pnl'] for b in common])
        cp = np.array([changed[b]['net_pnl'] for b in common])
        diffs = cp - bp
        mean_d = np.mean(diffs)
        std_d = np.std(diffs, ddof=1) if len(diffs) > 1 else 0
        t_stat = mean_d / (std_d / np.sqrt(len(diffs))) if std_d > 0 else 0
        p_value = erfc(abs(t_stat) / sqrt(2)) if std_d > 0 else 1.0

        bpf = np.array([baseline[b]['pf'] for b in common])
        cpf = np.array([changed[b]['pf'] for b in common])
        bsh = np.array([baseline[b]['sharpe'] for b in common])
        csh = np.array([changed[b]['sharpe'] for b in common])
        bdd = np.array([baseline[b]['max_dd'] for b in common])
        cdd = np.array([changed[b]['max_dd'] for b in common])

        imp = sum(1 for d in diffs if d > 0.5)
        wrs = sum(1 for d in diffs if d < -0.5)
        sig = "***" if p_value < 0.01 else ("**" if p_value < 0.05 else ("*" if p_value < 0.10 else ""))

        print(f"{CONFIGS[cfg_key]['label']:<35} {mean_d:>+9.2f}% {np.mean(cpf-bpf):>+8.4f} {np.mean(csh-bsh):>+8.3f} {np.mean(cdd-bdd):>+8.2f} {imp:>3}/{wrs:<3} {t_stat:>7.3f} {p_value:>8.4f} {sig:>4}")

        if mean_d > best_pnl_d:
            best_pnl_d = mean_d
            best_config = cfg_key

    print(f"\nBest config: {best_config} ({CONFIGS[best_config]['label']}) with mean ΔPnL = {best_pnl_d:+.2f}%")

    # Per-pair breakdown for the best config
    print(f"\n{'='*80}")
    print(f"  BEST CONFIG PER-PAIR BREAKDOWN: {CONFIGS[best_config]['label']}")
    print(f"{'='*80}")
    changed = all_results[best_config]
    print(f"{'Pair':<6} {'Base PnL':>9} {'New PnL':>9} {'Delta':>8} {'Base PF':>8} {'New PF':>8} {'Base Tr':>7} {'New Tr':>7} {'Base Sh':>8} {'New Sh':>8}")
    print("-" * 90)
    for b in bases:
        if baseline[b]['trades'] > 0 and changed[b]['trades'] > 0:
            d = changed[b]['net_pnl'] - baseline[b]['net_pnl']
            marker = '+' if d > 0.5 else ('-' if d < -0.5 else '=')
            print(f"{b:<6} {baseline[b]['net_pnl']:>8.2f}% {changed[b]['net_pnl']:>8.2f}% {d:>+7.2f}% {baseline[b]['pf']:>8.3f} {changed[b]['pf']:>8.3f} {baseline[b]['trades']:>7} {changed[b]['trades']:>7} {baseline[b]['sharpe']:>8.3f} {changed[b]['sharpe']:>8.3f} {marker}")

    # Save
    os.makedirs('backtest_results', exist_ok=True)
    output = {}
    for cfg_key in all_results:
        output[cfg_key] = {b: r for b, r in all_results[cfg_key].items()}
    with open('backtest_results/refined_v06.json', 'w') as f:
        json.dump(output, f, indent=2, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else x)
    print(f"\nResults saved to backtest_results/refined_v06.json")


if __name__ == '__main__':
    main()
