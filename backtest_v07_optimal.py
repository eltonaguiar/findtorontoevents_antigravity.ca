"""
SSK_Claude v0.07 — Optimal Combination Test
=============================================
Tests ONLY the individually-positive changes combined:
  1. HTF Daily Trend Gate (+20.0% individual)
  2. Kaufman ER > 0.3 (+14.8% individual)
  3. Volume >= 1.5x filter (+10.2% individual)
  4. Partial TP at 1R + breakeven (+5.2% individual)

EXCLUDED (proven harmful):
  - ATR Percentile 20-95 (-35.3%, p=0.029 SIGNIFICANTLY harmful)
  - MACD Histogram Accel (-5.2%)
  - Adaptive SuperTrend (-14.5%)
"""

import numpy as np
import json
import os
import sys
from math import erfc, sqrt

sys.path.insert(0, os.path.dirname(__file__))
from backtest_v07 import run_v07, TEST_PAIRS, CONFIGS
from backtest_v05_vs_v06 import download_binance_klines

OPTIMAL_CONFIGS = {
    'v06_baseline': CONFIGS['v06_baseline'],
    'htf_ker': {
        'label': 'HTF + Kaufman ER',
        'htf_filter': True, 'vol_filter': False, 'atr_filter': False,
        'connors_rsi': False, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': False, 'kaufman_er': True,
    },
    'htf_ker_vol': {
        'label': 'HTF + KER + Volume',
        'htf_filter': True, 'vol_filter': True, 'atr_filter': False,
        'connors_rsi': False, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': False, 'kaufman_er': True,
    },
    'v07_optimal': {
        'label': 'v0.07 OPTIMAL (HTF+KER+Vol+Partial)',
        'htf_filter': True, 'vol_filter': True, 'atr_filter': False,
        'connors_rsi': False, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': True, 'kaufman_er': True,
    },
    'v07_opt_crsi': {
        'label': 'v0.07 OPT + Connors RSI',
        'htf_filter': True, 'vol_filter': True, 'atr_filter': False,
        'connors_rsi': True, 'macd_accel': False, 'adaptive_st': False,
        'partial_tp': True, 'kaufman_er': True,
    },
}


def main():
    print("=" * 80)
    print("  v0.07 OPTIMAL COMBINATION TEST")
    print("  Only combining proven-positive changes")
    print("=" * 80)

    # Download data
    print("\nDownloading data...")
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
    for cfg_key, cfg in OPTIMAL_CONFIGS.items():
        label = cfg['label']
        print(f"{'='*70}")
        print(f"  {label}")
        print(f"{'='*70}")
        all_results[cfg_key] = {}
        for base, df in data_cache.items():
            r = run_v07(df, base, cfg)
            all_results[cfg_key][base] = r
            print(f"  {base:6s}: Tr={r['trades']:4d}  PnL={r['net_pnl']:>8.2f}%  PF={r['pf']:.3f}  WR={r['wr']:.1f}%  Sh={r['sharpe']:.3f}  DD={r['max_dd']:.1f}%  Avg={r['avg_trade']:.4f}%")

    # Compare
    baseline = all_results['v06_baseline']
    print(f"\n{'='*120}")
    print("  COMPARISON vs v0.06 BASELINE")
    print(f"{'='*120}")
    print(f"\n{'Config':<48} {'ΔPnL':>8} {'ΔPF':>7} {'ΔWR':>7} {'ΔSh':>7} {'ΔDD':>7} {'I/W':>5} {'t':>7} {'p':>8} {'Sig':>4}")
    print("-" * 120)

    for cfg_key in [k for k in OPTIMAL_CONFIGS if k != 'v06_baseline']:
        changed = all_results[cfg_key]
        common = [b for b in bases if baseline[b]['trades'] > 0 and changed[b]['trades'] > 0]
        if not common:
            continue

        bp = np.array([baseline[b]['net_pnl'] for b in common])
        cp = np.array([changed[b]['net_pnl'] for b in common])
        diffs = cp - bp
        mean_d = np.mean(diffs)
        std_d = np.std(diffs, ddof=1) if len(diffs) > 1 else 0
        t_stat = mean_d / (std_d / np.sqrt(len(diffs))) if std_d > 0 else 0
        p_value = erfc(abs(t_stat) / sqrt(2)) if std_d > 0 else 1.0

        bpf = np.array([baseline[b]['pf'] for b in common])
        cpf = np.array([changed[b]['pf'] for b in common])
        bwr = np.array([baseline[b]['wr'] for b in common])
        cwr = np.array([changed[b]['wr'] for b in common])
        bsh = np.array([baseline[b]['sharpe'] for b in common])
        csh = np.array([changed[b]['sharpe'] for b in common])
        bdd = np.array([baseline[b]['max_dd'] for b in common])
        cdd = np.array([changed[b]['max_dd'] for b in common])

        imp = sum(1 for d in diffs if d > 0.5)
        wrs = sum(1 for d in diffs if d < -0.5)
        sig = "***" if p_value < 0.01 else ("**" if p_value < 0.05 else ("*" if p_value < 0.10 else ""))

        print(f"{OPTIMAL_CONFIGS[cfg_key]['label']:<48} {mean_d:>+7.1f}% {np.mean(cpf-bpf):>+6.3f} {np.mean(cwr-bwr):>+6.1f}% {np.mean(csh-bsh):>+6.3f} {np.mean(cdd-bdd):>+6.1f} {imp:>2}/{wrs:<2} {t_stat:>7.3f} {p_value:>8.4f} {sig:>4}")

    # Per-pair detail for optimal
    for detail_key in ['v07_optimal', 'v07_opt_crsi']:
        if detail_key not in all_results:
            continue
        changed = all_results[detail_key]
        print(f"\n{'='*110}")
        print(f"  PER-PAIR: {OPTIMAL_CONFIGS[detail_key]['label']}")
        print(f"{'='*110}")
        print(f"{'Pair':<6} {'BasePnL':>8} {'NewPnL':>8} {'Δ':>7} {'BaseWR':>7} {'NewWR':>7} {'BaseTr':>7} {'NewTr':>7} {'BaseSh':>8} {'NewSh':>8} {'NewDD':>7} {'NewPF':>7}")
        print("-" * 110)
        total_base_pnl = 0
        total_new_pnl = 0
        winners_base = 0
        winners_new = 0
        for b in bases:
            if baseline[b]['trades'] > 0 and changed[b]['trades'] > 0:
                d = changed[b]['net_pnl'] - baseline[b]['net_pnl']
                marker = '+' if d > 0.5 else ('-' if d < -0.5 else '=')
                total_base_pnl += baseline[b]['net_pnl']
                total_new_pnl += changed[b]['net_pnl']
                if baseline[b]['net_pnl'] > 0:
                    winners_base += 1
                if changed[b]['net_pnl'] > 0:
                    winners_new += 1
                print(f"{b:<6} {baseline[b]['net_pnl']:>7.1f}% {changed[b]['net_pnl']:>7.1f}% {d:>+6.1f}% {baseline[b]['wr']:>6.1f}% {changed[b]['wr']:>6.1f}% {baseline[b]['trades']:>7} {changed[b]['trades']:>7} {baseline[b]['sharpe']:>8.3f} {changed[b]['sharpe']:>8.3f} {changed[b]['max_dd']:>6.1f}% {changed[b]['pf']:>6.3f} {marker}")
        print(f"\n{'TOTAL':<6} {total_base_pnl:>7.1f}% {total_new_pnl:>7.1f}% {total_new_pnl-total_base_pnl:>+6.1f}%")
        print(f"Profitable pairs: {winners_base}/{len(bases)} -> {winners_new}/{len(bases)}")

        # Sharpe comparison
        base_sharpes = [baseline[b]['sharpe'] for b in bases if baseline[b]['trades'] > 0]
        new_sharpes = [changed[b]['sharpe'] for b in bases if changed[b]['trades'] > 0]
        print(f"Avg Sharpe: {np.mean(base_sharpes):.3f} -> {np.mean(new_sharpes):.3f}")
        print(f"Median Sharpe: {np.median(base_sharpes):.3f} -> {np.median(new_sharpes):.3f}")
        print(f"Avg WR: {np.mean([baseline[b]['wr'] for b in bases]):.1f}% -> {np.mean([changed[b]['wr'] for b in bases]):.1f}%")
        print(f"Avg Trades: {np.mean([baseline[b]['trades'] for b in bases]):.0f} -> {np.mean([changed[b]['trades'] for b in bases]):.0f}")

    # Save
    os.makedirs('backtest_results', exist_ok=True)
    output = {}
    for cfg_key in all_results:
        output[cfg_key] = {b: r for b, r in all_results[cfg_key].items()}
    with open('backtest_results/v07_optimal.json', 'w') as f:
        json.dump(output, f, indent=2, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else x)
    print(f"\nResults saved to backtest_results/v07_optimal.json")


if __name__ == '__main__':
    main()
