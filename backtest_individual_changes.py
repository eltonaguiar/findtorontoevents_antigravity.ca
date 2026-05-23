"""
SSK_Claude — Individual Change Isolation Tester
================================================
Tests each proposed v0.06 change INDEPENDENTLY against v0.05 baseline.
This isolates which changes help vs hurt, since the bundled test (p=0.989) was inconclusive.

Changes tested individually:
  A) Tier reclassification only (POL→MHIGH, INJ/ARB/APE→EXTR, BNB/LTC→MHIGH)
  B) MinSigLvl 4 for EXTR only
  C) MR distance filter only (RSI/WT within 5% of EMA50)
  D) Tighter EXTR volAdj only (1.7→1.4)
  E) Trend bias filter only (counter-trend penalty)
"""

import pandas as pd
import numpy as np
import json
import os
import sys
from math import erfc, sqrt

# Reuse data and indicators from the main backtester
sys.path.insert(0, os.path.dirname(__file__))
from backtest_v05_vs_v06 import (
    download_binance_klines, calc_rsi, calc_ema, calc_sma, calc_macd,
    calc_atr, calc_supertrend, calc_adx, calc_wavetrend, calc_stochrsi,
    get_v05_tier, get_v06_tier, get_tier_params, get_special_overrides
)


def run_backtest_isolated(df, base, change=None):
    """
    Run backtest with a single change applied.
    change=None means v0.05 baseline.
    change='A' means only tier reclassification.
    change='B' means only minSigLvl 4 for EXTR.
    etc.
    """
    # Tier: use v06 tiers only if change A is active
    if change == 'A' or change == 'ALL':
        tier = get_v06_tier(base)
    else:
        tier = get_v05_tier(base)

    # Params: use v06 EXTR volAdj only if change D is active
    version_for_params = 'v06' if (change in ('D', 'ALL')) else 'v05'
    p = get_tier_params(tier, version_for_params)
    p.setdefault('rsi_len', 14)
    p.setdefault('macd_f', 12)
    p.setdefault('macd_s', 26)
    p.setdefault('macd_sig', 9)
    p = get_special_overrides(base, p)

    # Feature flags
    use_mr_distance = change in ('C', 'ALL')
    use_trend_bias = change in ('E', 'ALL')

    # MinSigLvl: raise to 4 for EXTR only if change B is active
    if change in ('B', 'ALL') and tier == 'EXTR':
        min_sig = 4
    else:
        min_sig = 3

    mr_max_dist = 5.0

    # Calculate indicators
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

    # TP/SL
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
        if use_mr_distance and not np.isnan(ema50.iloc[i]) and ema50.iloc[i] > 0:
            dist_pct = abs(close.iloc[i] - ema50.iloc[i]) / ema50.iloc[i] * 100
            if dist_pct > mr_max_dist:
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
        if use_trend_bias:
            if not np.isnan(ema50.iloc[i]) and close.iloc[i] < ema50.iloc[i]:
                b_score = max(0, b_score - 1)
            if not np.isnan(ema50.iloc[i]) and close.iloc[i] > ema50.iloc[i]:
                s_score = max(0, s_score - 1)

        is_buy = b_score >= min_sig and b_score > s_score

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
                in_trade = False
            elif tp_hit:
                pnl = (tp_level - entry_price) / entry_price * 100
                trades.append({'pnl': pnl, 'result': 'win'})
                in_trade = False
            elif sl_hit:
                pnl = -(abs(entry_price - sl_level) / entry_price * 100)
                trades.append({'pnl': pnl, 'result': 'loss'})
                in_trade = False
            elif bars_held >= max_hold:
                pnl = (close.iloc[i] - entry_price) / entry_price * 100
                result = 'win' if pnl > 0.1 else ('loss' if pnl < -0.1 else 'flat')
                trades.append({'pnl': pnl, 'result': result})
                in_trade = False

        if not in_trade and not pending and is_buy:
            pending = True

    # Metrics
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


# Representative pairs — same 14 that had data in the bundled test
TEST_PAIRS = [
    ('TRXUSDT', 'TRX'), ('BTCUSDT', 'BTC'), ('ALGOUSDT', 'ALGO'),
    ('ETHUSDT', 'ETH'), ('DOTUSDT', 'DOT'),
    ('SOLUSDT', 'SOL'), ('XRPUSDT', 'XRP'),
    ('INJUSDT', 'INJ'), ('ARBUSDT', 'ARB'), ('APEUSDT', 'APE'),
    ('DOGEUSDT', 'DOGE'), ('FETUSDT', 'FET'),
    ('DYDXUSDT', 'DYDX'), ('SHIBUSDT', 'SHIB'),
]

CHANGES = {
    None: 'BASELINE (v0.05)',
    'A': 'Tier Reclassification',
    'B': 'MinSigLvl 4 for EXTR',
    'C': 'MR Distance Filter',
    'D': 'Tighter EXTR volAdj (1.7→1.4)',
    'E': 'Trend Bias Filter',
}


def main():
    # Download data once
    print("Downloading data for all pairs...")
    data_cache = {}
    for symbol, base in TEST_PAIRS:
        print(f"  {symbol}...", end='', flush=True)
        df = download_binance_klines(symbol, '1h', 1095)
        if df is not None and len(df) >= 500:
            data_cache[base] = df
            print(f" {len(df)} bars")
        else:
            print(f" SKIP (insufficient data)")

    bases = list(data_cache.keys())
    print(f"\n{len(bases)} pairs loaded: {', '.join(bases)}\n")

    # Run baseline + each individual change
    results = {}  # results[change][base] = metrics dict
    for change_key in [None, 'A', 'B', 'C', 'D', 'E']:
        label = CHANGES[change_key]
        print(f"{'='*70}")
        print(f"  Testing: {label}")
        print(f"{'='*70}")
        results[change_key] = {}
        for base, df in data_cache.items():
            r = run_backtest_isolated(df, base, change=change_key)
            results[change_key][base] = r
            print(f"  {base:6s}: Tr={r['trades']:4d}  PnL={r['net_pnl']:>8.2f}%  PF={r['pf']:.3f}  WR={r['wr']:.1f}%  Sharpe={r['sharpe']:.3f}  DD={r['max_dd']:.1f}%")

    # ══════════════════════════════════════════════════════════════════════════
    # COMPARISON TABLE
    # ══════════════════════════════════════════════════════════════════════════
    baseline = results[None]

    print(f"\n{'='*90}")
    print("  INDIVIDUAL CHANGE IMPACT vs BASELINE")
    print(f"{'='*90}")

    summary = {}
    for change_key in ['A', 'B', 'C', 'D', 'E']:
        label = CHANGES[change_key]
        changed = results[change_key]

        # Only compare pairs where both have trades
        common = [b for b in bases if baseline[b]['trades'] > 0 and changed[b]['trades'] > 0]

        baseline_pnls = np.array([baseline[b]['net_pnl'] for b in common])
        changed_pnls = np.array([changed[b]['net_pnl'] for b in common])
        diffs = changed_pnls - baseline_pnls

        mean_d = np.mean(diffs)
        std_d = np.std(diffs, ddof=1) if len(diffs) > 1 else 0
        t_stat = mean_d / (std_d / np.sqrt(len(diffs))) if std_d > 0 else 0
        p_value = erfc(abs(t_stat) / sqrt(2)) if std_d > 0 else 1.0

        improved = sum(1 for d in diffs if d > 0.5)
        worsened = sum(1 for d in diffs if d < -0.5)

        # Also track PF and Sharpe changes
        baseline_pfs = np.array([baseline[b]['pf'] for b in common])
        changed_pfs = np.array([changed[b]['pf'] for b in common])
        pf_diffs = changed_pfs - baseline_pfs
        mean_pf_d = np.mean(pf_diffs)

        baseline_sharpes = np.array([baseline[b]['sharpe'] for b in common])
        changed_sharpes = np.array([changed[b]['sharpe'] for b in common])
        sharpe_diffs = changed_sharpes - baseline_sharpes
        mean_sharpe_d = np.mean(sharpe_diffs)

        # Max DD improvement (less negative = better)
        baseline_dds = np.array([baseline[b]['max_dd'] for b in common])
        changed_dds = np.array([changed[b]['max_dd'] for b in common])
        dd_diffs = changed_dds - baseline_dds  # positive = worse DD
        mean_dd_d = np.mean(dd_diffs)

        sig = "***" if p_value < 0.01 else ("**" if p_value < 0.05 else ("*" if p_value < 0.10 else ""))

        summary[change_key] = {
            'label': label,
            'mean_pnl_d': mean_d,
            'mean_pf_d': mean_pf_d,
            'mean_sharpe_d': mean_sharpe_d,
            'mean_dd_d': mean_dd_d,
            't_stat': t_stat,
            'p_value': p_value,
            'improved': improved,
            'worsened': worsened,
            'n': len(common),
            'sig': sig,
        }

        print(f"\n--- Change {change_key}: {label} ---")
        print(f"  Pairs: {len(common)} | Improved: {improved} | Worsened: {worsened}")
        print(f"  Mean PnL delta: {mean_d:+.2f}% | Mean PF delta: {mean_pf_d:+.4f} | Mean Sharpe delta: {mean_sharpe_d:+.3f}")
        print(f"  Mean DD delta: {mean_dd_d:+.2f}% (negative=better)")
        print(f"  t-stat: {t_stat:.3f} | p-value: {p_value:.4f} {sig}")

        # Per-pair breakdown for this change
        print(f"  {'Pair':<6} {'Base PnL':>9} {'Chg PnL':>9} {'Delta':>8} {'Base PF':>8} {'Chg PF':>8} {'Base Tr':>7} {'Chg Tr':>7}")
        for b in common:
            bp = baseline[b]['net_pnl']
            cp = changed[b]['net_pnl']
            d = cp - bp
            marker = '+' if d > 0.5 else ('-' if d < -0.5 else '=')
            print(f"  {b:<6} {bp:>8.2f}% {cp:>8.2f}% {d:>+7.2f}% {baseline[b]['pf']:>8.3f} {changed[b]['pf']:>8.3f} {baseline[b]['trades']:>7} {changed[b]['trades']:>7} {marker}")

    # ══════════════════════════════════════════════════════════════════════════
    # FINAL RECOMMENDATIONS
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n{'='*90}")
    print("  RECOMMENDATIONS")
    print(f"{'='*90}")

    print(f"\n{'Change':<40} {'Mean ΔPnL':>10} {'Mean ΔPF':>9} {'Mean ΔSharpe':>13} {'p-value':>9} {'Verdict':>15}")
    print("-" * 100)

    for ck in ['A', 'B', 'C', 'D', 'E']:
        s = summary[ck]
        if s['p_value'] < 0.05:
            verdict = "ADOPT" if s['mean_pnl_d'] > 0 else "REJECT"
        elif s['p_value'] < 0.10:
            verdict = "MARGINAL+"  if s['mean_pnl_d'] > 0 else "MARGINAL-"
        else:
            verdict = "NEUTRAL" if abs(s['mean_pnl_d']) < 2 else ("LEAN ADOPT" if s['mean_pnl_d'] > 0 else "LEAN REJECT")

        # Also consider if DD improved even when PnL is neutral
        if verdict == "NEUTRAL" and s['mean_dd_d'] < -5:
            verdict = "ADOPT (DD)"

        print(f"{ck}: {s['label']:<37} {s['mean_pnl_d']:>+9.2f}% {s['mean_pf_d']:>+8.4f} {s['mean_sharpe_d']:>+12.3f} {s['p_value']:>9.4f} {verdict:>15} {s['sig']}")

    # Save detailed results
    output = {
        'summary': {k: {kk: (vv if not isinstance(vv, np.floating) else float(vv)) for kk, vv in v.items()} for k, v in summary.items()},
        'per_change': {}
    }
    for ck in [None, 'A', 'B', 'C', 'D', 'E']:
        key = 'baseline' if ck is None else ck
        output['per_change'][key] = {b: r for b, r in results[ck].items()}

    os.makedirs('backtest_results', exist_ok=True)
    with open('backtest_results/individual_changes.json', 'w') as f:
        json.dump(output, f, indent=2, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else x)
    print(f"\nDetailed results saved to backtest_results/individual_changes.json")


if __name__ == '__main__':
    main()
