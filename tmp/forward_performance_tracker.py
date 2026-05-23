#!/usr/bin/env python3
"""
Forward Performance Tracker — Ongoing stats per strategy and bucket.
Reads baby_strats_dashboard.json and computes Kelly, EV, ROI per strategy and bucket.
Designed to run periodically (e.g., daily via cron/GitHub Actions) to track if our
theory about negative-EV strategies is confirmed by forward data.
"""
import json, numpy as np, os
from datetime import datetime

def compute_kelly(pnls):
    """Compute Kelly Criterion from a list of PnL percentages."""
    if not pnls:
        return None, None
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    wr = len(wins) / len(pnls)
    avg_win = np.mean(wins) if wins else 0
    avg_loss = abs(np.mean(losses)) if losses else 0.001
    rr = avg_win / avg_loss if avg_loss > 0 else 999
    kelly = wr - (1 - wr) / rr if rr > 0 else wr
    ev = wr * avg_win - (1 - wr) * avg_loss
    return round(kelly * 100, 2), round(ev, 4)

def main():
    # Load data
    with open('battleground/data/baby_strats_dashboard.json') as f:
        data = json.load(f)

    with open('stabilization/disabled_strategies.json') as f:
        disabled_data = json.load(f)

    graveyard = set(disabled_data.get('graveyard', []))
    keep_list = set(disabled_data.get('keep_strategies', []))

    # Deduplicate strategies
    strat_data = {}
    for s in data['strategies']:
        name = s['name']
        ft = s.get('forward_trades', [])
        existing = strat_data.get(name)
        if existing is None or len(ft) > len(existing.get('forward_trades', [])):
            strat_data[name] = s

    # Compute per-strategy stats
    strategy_stats = []
    for name, s in strat_data.items():
        ft = s.get('forward_trades', [])
        pnls = [t.get('pnl_pct', 0) for t in ft]
        kelly_pct, ev = compute_kelly(pnls) if pnls else (None, None)
        wins = sum(1 for p in pnls if p > 0)

        strategy_stats.append({
            'name': name,
            'trades': len(ft),
            'wins': wins,
            'wr': round(wins / len(ft) * 100, 1) if ft else 0,
            'kelly_pct': kelly_pct,
            'ev_per_trade': ev,
            'sum_pnl': round(sum(pnls), 2),
            'avg_pnl': round(np.mean(pnls), 4) if pnls else 0,
            'roi_100': round(sum(p for p in pnls), 2),  # ROI on $100/trade
            'status': 'graveyard' if name in graveyard else ('keep' if name in keep_list else 'unclassified'),
            'category': s.get('category', 'unknown'),
        })

    # Sort by Kelly
    strategy_stats.sort(key=lambda x: (x['kelly_pct'] if x['kelly_pct'] is not None else -9999), reverse=True)

    # Bundles
    bundles = {
        'Forward Winners': ['drawdown_recovery_rsi', 'multi_period_rsi_confluence', 'crypto_keltner_compression_expansion_v1', 'crypto_vwap_volprofile_reversion_v1', 'crypto_vwap_deviation_reversion_volfilter_v1', 'crypto_soc_mtf_orb_pivots_a06_v1'],
        'Mean Reversion Elite': ['drawdown_recovery_rsi', 'multi_period_rsi_confluence', 'crypto_vwap_volprofile_reversion_v1', 'crypto_vwap_deviation_reversion_volfilter_v1'],
        'Cross-Agent Best': ['drawdown_recovery_rsi', 'crypto_keltner_compression_expansion_v1', 'crypto_vwap_volprofile_reversion_v1'],
        'Survivor Validated': ['crypto_keltner_compression_expansion_v1', 'crypto_vwap_deviation_reversion_volfilter_v1'],
        'Volatility Breakout': ['crypto_keltner_compression_expansion_v1', 'crypto_soc_mtf_orb_pivots_a06_v1'],
        'New Research (Mar 2026)': ['overnight_seasonality_btc', 'adx_range_mean_reversion', 'weekend_momentum', 'nr7_volatility_breakout', 'sma50_regime_filter', 'levine_adaptive_lookback_momentum', 'carter_squeeze_breakout'],
        'Mutual Fund Beaters': ['fomc_drift_calendar', 'contrarian_fg_tiered', 'dual_momentum_crypto', 'hurst_regime_filter', 'pairs_spread_btceth', 'dca_rsi_adaptive'],
        'Regime Adaptive': ['hurst_regime_filter', 'adx_range_mean_reversion', 'sma50_regime_filter'],
        'Calendar & Seasonal': ['fomc_drift_calendar', 'overnight_seasonality_btc', 'weekend_momentum'],
        'Contrarian Accumulators': ['contrarian_fg_tiered', 'dca_rsi_adaptive', 'drawdown_recovery_rsi'],
        'High Sharpe (Research)': ['dxy_weekly_drop', 'red_candle_mean_reversion', 'pairs_spread_btceth', 'hurst_regime_filter'],
    }

    bundle_stats = []
    for bname, strategies in bundles.items():
        all_pnls = []
        total_trades = 0
        total_wins = 0
        for sname in strategies:
            s = strat_data.get(sname, {})
            ft = s.get('forward_trades', [])
            for t in ft:
                pnl = t.get('pnl_pct', 0)
                all_pnls.append(pnl)
                total_trades += 1
                if pnl > 0:
                    total_wins += 1

        kelly_pct, ev = compute_kelly(all_pnls) if all_pnls else (None, None)
        bundle_stats.append({
            'name': bname,
            'strategies': strategies,
            'trades': total_trades,
            'wins': total_wins,
            'wr': round(total_wins / total_trades * 100, 1) if total_trades > 0 else 0,
            'kelly_pct': kelly_pct,
            'ev_per_trade': ev,
            'sum_pnl': round(sum(all_pnls), 2),
            'roi_100': round(sum(all_pnls), 2),
        })

    # Compute theory validation: graveyard vs keep performance
    graveyard_pnls = []
    keep_pnls = []
    for s in strategy_stats:
        if s['status'] == 'graveyard' and s['trades'] > 0:
            graveyard_pnls.extend([s['avg_pnl']] * s['trades'])
        elif s['status'] == 'keep' and s['trades'] > 0:
            keep_pnls.extend([s['avg_pnl']] * s['trades'])

    # Save report
    report = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'summary': {
            'total_strategies': len(strat_data),
            'graveyard_count': len([s for s in strategy_stats if s['status'] == 'graveyard']),
            'keep_count': len([s for s in strategy_stats if s['status'] == 'keep']),
            'total_forward_trades': sum(s['trades'] for s in strategy_stats),
            'overall_wr': round(sum(s['wins'] for s in strategy_stats) / max(sum(s['trades'] for s in strategy_stats), 1) * 100, 1),
            'overall_sum_pnl': round(sum(s['sum_pnl'] for s in strategy_stats), 2),
        },
        'theory_validation': {
            'hypothesis': 'Graveyarded strategies have negative EV, KEEP strategies have positive EV',
            'graveyard_avg_pnl': round(np.mean(graveyard_pnls), 4) if graveyard_pnls else None,
            'keep_avg_pnl': round(np.mean(keep_pnls), 4) if keep_pnls else None,
            'graveyard_trade_count': len(graveyard_pnls),
            'keep_trade_count': len(keep_pnls),
            'theory_confirmed': bool(np.mean(graveyard_pnls) < 0 and np.mean(keep_pnls) > 0) if graveyard_pnls and keep_pnls else None,
        },
        'strategies': strategy_stats,
        'bundles': bundle_stats,
    }

    os.makedirs('stabilization', exist_ok=True)
    with open('stabilization/forward_performance_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("=" * 90)
    print(f"FORWARD PERFORMANCE REPORT — {report['generated_at']}")
    print("=" * 90)

    print(f"\nSummary:")
    s = report['summary']
    print(f"  Total strategies: {s['total_strategies']} | Graveyard: {s['graveyard_count']} | Keep: {s['keep_count']}")
    print(f"  Total trades: {s['total_forward_trades']} | WR: {s['overall_wr']}% | Sum PnL: {s['overall_sum_pnl']:+.2f}%")

    tv = report['theory_validation']
    print(f"\nTheory Validation:")
    print(f"  Graveyard avg PnL: {tv['graveyard_avg_pnl']:+.4f}% ({tv['graveyard_trade_count']} trades)")
    print(f"  KEEP avg PnL: {tv['keep_avg_pnl']:+.4f}% ({tv['keep_trade_count']} trades)")
    print(f"  Theory confirmed: {tv['theory_confirmed']}")

    print(f"\nTop 10 Strategies (by Kelly):")
    for s in strategy_stats[:10]:
        kelly_str = f"{s['kelly_pct']:+.1f}%" if s['kelly_pct'] is not None else "N/A"
        print(f"  [{s['status']:10s}] {s['name']:50s} | {s['trades']:3d}t | WR {s['wr']:5.1f}% | Kelly {kelly_str:>8s} | PnL {s['sum_pnl']:+8.2f}%")

    print(f"\nBundle Performance:")
    for b in bundle_stats:
        kelly_str = f"{b['kelly_pct']:+.1f}%" if b['kelly_pct'] is not None else "N/A"
        print(f"  {b['name']:25s} | {b['trades']:3d}t | WR {b['wr']:5.1f}% | Kelly {kelly_str:>8s} | PnL {b['sum_pnl']:+8.2f}%")

    print(f"\nReport saved to stabilization/forward_performance_report.json")

if __name__ == '__main__':
    main()
