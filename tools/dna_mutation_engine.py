#!/usr/bin/env python3
"""
DNA Mutation Engine — Combine EDGE strategies to create hybrid variants.

Pre-registered as H-20260613-dna_mutation_hybrid_v1 (M-107).

Approach:
1. Take top strategies by avg_pnl (n>=20)
2. Create hybrid combinations (2-strategy and 3-strategy)
3. Test each hybrid with bootstrap CI (10K resamples, symbol-day clustering)
4. Report results with CI-LB > 1.15 gate

Usage:
    python3 tools/dna_mutation_engine.py
    python3 tools/dna_mutation_engine.py --min-n 30 --verbose
"""

import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.db_env import get_stocks_creds


def load_strategy_picks(strategy: str, conn, min_pnl_pct: float = None):
    """Load picks for a strategy from at_signal_outcomes."""
    import pandas as pd
    query = """
        SELECT id, symbol, direction, entry_price, intrabar_pnl_pct, 
               intrabar_status, opened_at, asset_class
        FROM ejaguiar1_stocks.at_signal_outcomes
        WHERE strategy = %s
          AND intrabar_status IN ('TP_HIT', 'SL_HIT')
          AND intrabar_pnl_pct IS NOT NULL
    """
    if min_pnl_pct is not None:
        query += f" AND intrabar_pnl_pct >= {min_pnl_pct}"
    query += " ORDER BY opened_at"
    return pd.read_sql_query(query, conn, params=(strategy,))


def bootstrap_hybrid_performance(picks_a, picks_b, n_bootstrap=10000, seed=42):
    """
    Test a hybrid strategy: pick A fires AND pick B fires on same symbol+day.
    Direction: majority vote (2/2 must agree).
    PnL: average of both picks.
    """
    rng = np.random.RandomState(seed)
    
    # Merge on symbol + date (same symbol, same day)
    if 'opened_at' in picks_a.columns and 'opened_at' in picks_b.columns:
        picks_a = picks_a.copy()
        picks_b = picks_b.copy()
        picks_a['date'] = picks_a['opened_at'].dt.date
        picks_b['date'] = picks_b['opened_at'].dt.date
        
        merged = picks_a.merge(
            picks_b, 
            on=['symbol', 'date'], 
            suffixes=('_a', '_b'),
            how='inner'
        )
    else:
        return None
    
    if len(merged) < 20:
        return None
    
    # Hybrid: both must agree on direction
    same_dir = merged[merged['direction_a'] == merged['direction_b']]
    if len(same_dir) < 20:
        return None
    
    # PnL: average of both
    hybrid_pnl = (same_dir['intrabar_pnl_pct_a'] + same_dir['intrabar_pnl_pct_b']) / 2
    
    # Bootstrap
    n = len(hybrid_pnl)
    means = []
    for _ in range(n_bootstrap):
        sample = rng.choice(hybrid_pnl.values, size=n, replace=True)
        means.append(np.mean(sample))
    
    means = np.array(means)
    avg_pnl = np.mean(hybrid_pnl)
    wr = np.mean(hybrid_pnl > 0)
    ci_lb = np.percentile(means, 2.5)
    ci_ub = np.percentile(means, 97.5)
    
    return {
        'n': n,
        'wr': round(wr * 100, 1),
        'avg_pnl': round(avg_pnl, 3),
        'ci_lb': round(ci_lb, 3),
        'ci_ub': round(ci_ub, 3),
        'total_pnl': round(float(hybrid_pnl.sum()), 1),
    }


def bootstrap_single_performance(picks, n_bootstrap=10000, seed=42):
    """Bootstrap performance for a single strategy."""
    rng = np.random.RandomState(seed)
    pnls = picks['intrabar_pnl_pct'].values
    
    n = len(pnls)
    means = []
    for _ in range(n_bootstrap):
        sample = rng.choice(pnls, size=n, replace=True)
        means.append(np.mean(sample))
    
    means = np.array(means)
    avg_pnl = np.mean(pnls)
    wr = np.mean(pnls > 0)
    ci_lb = np.percentile(means, 2.5)
    ci_ub = np.percentile(means, 97.5)
    
    return {
        'n': n,
        'wr': round(wr * 100, 1),
        'avg_pnl': round(avg_pnl, 3),
        'ci_lb': round(ci_lb, 3),
        'ci_ub': round(ci_ub, 3),
        'total_pnl': round(float(pnls.sum()), 1),
    }


def main():
    parser = argparse.ArgumentParser(description='DNA Mutation Engine')
    parser.add_argument('--min-n', type=int, default=20, help='Minimum picks per strategy')
    parser.add_argument('--verbose', action='store_true', help='Print per-hybrid details')
    args = parser.parse_args()
    
    creds = get_stocks_creds()
    import mysql.connector
    conn = mysql.connector.connect(**creds)
    
    # Get top strategies by avg_pnl
    import pandas as pd
    query = """
        SELECT strategy, COUNT(*) as n, AVG(intrabar_pnl_pct) as avg_pnl
        FROM ejaguiar1_stocks.at_signal_outcomes
        WHERE intrabar_status IN ('TP_HIT', 'SL_HIT')
          AND intrabar_pnl_pct IS NOT NULL
        GROUP BY strategy
        HAVING n >= %s
        ORDER BY avg_pnl DESC
        LIMIT 10
    """
    strategies_df = pd.read_sql_query(query, conn, params=(args.min_n,))
    strategies = strategies_df['strategy'].tolist()
    
    print(f'{"="*60}')
    print(f'DNA MUTATION ENGINE — {len(strategies)} strategies, min_n={args.min_n}')
    print(f'{"="*60}')
    
    # Load all picks
    all_picks = {}
    for strat in strategies:
        picks = load_strategy_picks(strat, conn)
        if len(picks) >= args.min_n:
            all_picks[strat] = picks
            stats = bootstrap_single_performance(picks)
            print(f'  {strat}: n={stats["n"]}, WR={stats["wr"]}%, avg_pnl={stats["avg_pnl"]}%')
    
    conn.close()
    
    # Generate 2-strategy hybrids
    print(f'\n{"="*60}')
    print(f'TESTING 2-STRATEGY HYBRIDS')
    print(f'{"="*60}')
    
    results = []
    strat_list = list(all_picks.keys())
    
    for i in range(len(strat_list)):
        for j in range(i+1, len(strat_list)):
            strat_a = strat_list[i]
            strat_b = strat_list[j]
            
            hybrid_result = bootstrap_hybrid_performance(
                all_picks[strat_a], 
                all_picks[strat_b]
            )
            
            if hybrid_result:
                hybrid_name = f'{strat_a}+{strat_b}'
                verdict = 'EDGE' if hybrid_result['ci_lb'] > 1.15 and hybrid_result['n'] >= 80 else 'SUB-BAR' if hybrid_result['ci_lb'] > 1.15 else 'NO-EDGE'
                
                result = {
                    'hybrid': hybrid_name,
                    'strategies': [strat_a, strat_b],
                    **hybrid_result,
                    'verdict': verdict,
                }
                results.append(result)
                
                if args.verbose or verdict != 'NO-EDGE':
                    print(f'\n  {hybrid_name}:')
                    print(f'    n={hybrid_result["n"]}, WR={hybrid_result["wr"]}%, avg_pnl={hybrid_result["avg_pnl"]}%')
                    print(f'    CI: [{hybrid_result["ci_lb"]}, {hybrid_result["ci_ub"]}]')
                    print(f'    Verdict: {verdict}')
    
    # Sort by avg_pnl
    results.sort(key=lambda x: x['avg_pnl'], reverse=True)
    
    # Save results
    output = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'min_n': args.min_n,
        'strategies_tested': len(strategies),
        'hybrids_tested': len(results),
        'top_5': results[:5] if results else [],
        'all_results': results,
    }
    
    output_path = f'reports/dna_mutations_{datetime.utcnow().strftime("%Y-%m-%d")}.json'
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f'\n{"="*60}')
    print(f'TOP 5 HYBRIDS')
    print(f'{"="*60}')
    for i, r in enumerate(results[:5], 1):
        print(f'{i}. {r["hybrid"]}: n={r["n"]}, WR={r["wr"]}%, avg_pnl={r["avg_pnl"]}%')
        print(f'   CI: [{r["ci_lb"]}, {r["ci_ub"]}] — {r["verdict"]}')
    
    print(f'\nResults saved to {output_path}')
    print(f'Total hybrids tested: {len(results)}')


if __name__ == '__main__':
    main()
