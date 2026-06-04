#!/usr/bin/env python3
"""
World-Class Strategies — One Per Asset Class (using trading_picks DB)
=====================================================================
Author: Claude Opus 4.7 | Date: 2026-05-29

Implements 7 economically-motivated strategies by filtering trading_picks
with simple, economically-justified criteria. Each strategy has ≤2 parameters.

Data source: ejaguiar1_stocks.trading_picks (7,728 resolved picks with PnL)
"""
import sys, os, json
import numpy as np
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymysql
from alpha_engine.rigorous_backtest_harness import run_backtest as rigorous_backtest

# ============================================================
# CATEGORY MAPPING
# ============================================================
CATEGORY_MAP = {
    'CRYPTO': ['crypto'],
    'EQUITY': ['equity', 'stocks', 'stock'],
    'FOREX': ['forex'],
    'ETF': ['etf'],
    'COMMODITY': ['commodity'],
    'FUTURES': ['futures'],
    'BOND': ['bond'],
}

# ============================================================
# STRATEGY DEFINITIONS (economically-motivated filters)
# ============================================================
STRATEGIES = {
    'CRYPTO': {
        'name': 'crypto_momentum_high_confidence',
        'display_name': 'Crypto Momentum + High Confidence',
        'description': 'Long crypto momentum signals with confidence >= 0.60. Economic basis: momentum persists in crypto; high-confidence signals cluster around strong moves.',
        'parameters': {'min_confidence': 0.60},
        'n_params': 1,
        'filter': lambda p: (p.get('confidence') or 0) >= 0.60,
    },
    'EQUITY': {
        'name': 'equity_quality_momentum',
        'display_name': 'Equity Quality + Momentum',
        'description': 'Equity picks with elite_score >= 50 (quality filter). Economic basis: higher-scored equity picks represent better-researched opportunities with positive expected value.',
        'parameters': {'min_elite_score': 50},
        'n_params': 1,
        'filter': lambda p: (p.get('elite_score') or 0) >= 50,
    },
    'FOREX': {
        'name': 'forex_carry_trend',
        'display_name': 'Forex Carry + Trend',
        'description': 'Forex picks with elite_score >= 50. Economic basis: carry and trend are the two most documented FX risk premia; higher-scored picks capture these signals.',
        'parameters': {'min_elite_score': 50},
        'n_params': 1,
        'filter': lambda p: (p.get('elite_score') or 0) >= 50,
    },
    'ETF': {
        'name': 'etf_sector_rotation',
        'display_name': 'ETF Sector Rotation',
        'description': 'All ETF picks (no filter — too few data points). Economic basis: sector rotation via ETFs captures cross-sectional momentum.',
        'parameters': {},
        'n_params': 0,
        'filter': lambda p: True,
    },
    'COMMODITY': {
        'name': 'commodity_term_structure',
        'display_name': 'Commodity Term Structure Carry',
        'description': 'Commodity picks with elite_score >= 50. Economic basis: commodity term structure (contango/backwardation) predicts returns; higher-scored picks capture this.',
        'parameters': {'min_elite_score': 50},
        'n_params': 1,
        'filter': lambda p: (p.get('elite_score') or 0) >= 50,
    },
    'FUTURES': {
        'name': 'futures_trend_following',
        'display_name': 'Futures Trend-Following',
        'description': 'Futures picks with elite_score >= 50. Economic basis: time-series momentum across futures markets is well-documented (Moskowitz et al. 2012).',
        'parameters': {'min_elite_score': 50},
        'n_params': 1,
        'filter': lambda p: (p.get('elite_score') or 0) >= 50,
    },
    'BOND': {
        'name': 'bond_yield_curve',
        'display_name': 'Bond Yield Curve Strategy',
        'description': 'All bond picks (no filter — limited data). Economic basis: yield curve slope predicts duration returns; even unfiltered bond picks capture some signal.',
        'parameters': {},
        'n_params': 0,
        'filter': lambda p: True,
    },
}

# ============================================================
# DATA LOADING
# ============================================================

def load_picks_by_class(asset_class):
    """Load all resolved picks for a given asset class from trading_picks."""
    # 2026-06-04 INCIDENT #89 scrub: was os.environ.get('DB_PASS_STOCKS', '<literal>')
    # with the convention literal baked in. Now uses the canonical helper which
    # raises if no creds are resolvable.
    import sys as _sys
    from pathlib import Path as _Path
    _root = _Path(__file__).resolve().parents[2]
    if str(_root) not in _sys.path:
        _sys.path.insert(0, str(_root))
    from tools.db_env import get_stocks_creds
    creds = get_stocks_creds()
    conn = pymysql.connect(
        **creds, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    cur = conn.cursor()
    
    cats = CATEGORY_MAP.get(asset_class, [asset_class.lower()])
    
    # Build OR clause for categories
    cat_conditions = ' OR '.join([f"LOWER(category) = '{c}'" for c in cats])
    
    cur.execute(f"""
        SELECT id, symbol, strategy, pnl_pct, created_at, closed_at, status,
               confidence, elite_score, trust_score, direction, category
        FROM trading_picks 
        WHERE ({cat_conditions}) AND pnl_pct IS NOT NULL
        AND status IN ('WON','LOST','TP_HIT','SL_HIT','CLOSED')
        ORDER BY closed_at ASC
    """)
    picks = cur.fetchall()
    conn.close()
    return picks

# ============================================================
# MAIN
# ============================================================

def run_all_strategies():
    """Run all 7 world-class strategies."""
    results = {}
    
    for asset_class, spec in STRATEGIES.items():
        print(f"\n{'='*60}")
        print(f"  {asset_class}: {spec['name']}")
        print(f"  {spec['description'][:70]}...")
        print(f"  Parameters: {spec['n_params']}")
        print(f"{'='*60}")
        
        picks = load_picks_by_class(asset_class)
        if not picks:
            print(f"  No data for {asset_class}")
            results[asset_class] = {'error': 'No data', 'spec': {k: v for k, v in spec.items() if k != 'filter'}}
            continue
        
        print(f"  Loaded {len(picks)} resolved picks")
        
        # Apply filter
        filtered = [p for p in picks if spec['filter'](p)]
        pct = len(filtered) / max(len(picks), 1) * 100
        print(f"  Filtered to {len(filtered)} picks ({pct:.0f}%)")
        
        if len(filtered) < 10:
            print(f"  Insufficient data (n={len(filtered)} < 10)")
            results[asset_class] = {
                'error': f'Insufficient data (n={len(filtered)})',
                'spec': {k: v for k, v in spec.items() if k != 'filter'},
                'n_total': len(picks), 'n_filtered': len(filtered)
            }
            continue
        
        # Extract PnL series
        pnl_series = np.array([float(p.get('pnl_pct', 0)) for p in filtered])
        
        # Run rigorous backtest
        result = rigorous_backtest(
            pnl_series=pnl_series,
            asset_class=asset_class,
            strategy_name=spec['name'],
        )
        
        # Add metadata (exclude filter lambda from serialization)
        result['spec'] = {k: v for k, v in spec.items() if k != 'filter'}
        result['n_total'] = len(picks)
        result['n_filtered'] = len(filtered)
        result['filter_pct'] = pct / 100
        
        results[asset_class] = result
        
        # Print summary
        print(f"  n={result['n']}, PF={result.get('costed_pf',0):.3f}, WR={result.get('costed_wr',0):.1%}")
        print(f"  DSR={result.get('dsr',0):.2f}, PBO={result.get('pbo',0):.3f}")
        wf = result.get('walk_forward', {})
        if isinstance(wf, dict) and 'consistency' in wf:
            print(f"  WF Consistency={wf.get('consistency',0):.1%}, OS Sharpe={wf.get('avg_os_sharpe',0):.4f}")
        print(f"  Verdict: {result.get('verdict', '?')}")
    
    # Save results
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    output_path = f'backtest_results/world_class_strategies_{timestamp}.json'
    
    def convert(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, datetime): return obj.isoformat()
        return obj
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=convert)
    
    print(f"\n{'='*60}")
    print(f"  Saved to {output_path}")
    print(f"{'='*60}")
    
    # Summary table
    print(f"\n=== WORLD-CLASS STRATEGIES SUMMARY ===")
    print(f"{'Class':12s} {'Strategy':38s} {'n':6s} {'PF':7s} {'WR':7s} {'DSR':7s} {'PBO':7s} {'Verdict':10s}")
    print("-" * 95)
    for ac in ['CRYPTO', 'EQUITY', 'FOREX', 'ETF', 'COMMODITY', 'FUTURES', 'BOND']:
        r = results.get(ac, {})
        if 'error' in r:
            print(f"{ac:12s} {'(no data)':38s} {'-':6s} {'-':7s} {'-':7s} {'-':7s} {'-':7s} {'-':10s}")
        else:
            name = r.get('spec', {}).get('name', '')[:38]
            n = r.get('n', 0)
            pf = r.get('costed_pf', 0)
            wr = r.get('costed_wr', 0)
            dsr = r.get('dsr', 0)
            pbo = r.get('pbo', 0)
            verdict = r.get('verdict', '?')
            print(f"{ac:12s} {name:38s} {n:6d} {pf:7.3f} {wr:7.1%} {dsr:7.2f} {pbo:7.3f} {verdict:10s}")
    
    return results

if __name__ == '__main__':
    run_all_strategies()
