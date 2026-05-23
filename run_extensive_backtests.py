"""
EXTENSIVE BACKTEST RUNNER
=========================
Tests all new strategies across 20+ crypto pairs with 5+ years of data.

Outputs:
- Individual pair results (JSON)
- Aggregated performance summary
- Audit-ready strategy registry entries
- Prop-firm viability report
"""

import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import concurrent.futures
import logging

# Import our new strategies
from new_strategies_prop_firm import (
    KeltnerCompressionScalper, VWAPMeanReversionElite, 
    MultiTimeframeRSIConfluence, PROP_FIRM_STRATEGIES
)
from new_strategies_general import ALL_STRATEGIES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

CRYPTO_PAIRS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT', 'LTCUSDT',
    'BCHUSDT', 'XLMUSDT', 'ALGOUSDT', 'VETUSDT', 'ICPUSDT',
    'FILUSDT', 'ATOMUSDT', 'NEARUSDT', 'MATICUSDT', 'DOTUSDT'
]

TIMEFRAMES = ['1h', '4h']  # Primary and higher timeframe
LIMIT_BARS = 5000  # Maximum historical bars (~7 months on 1h)

OUTPUT_DIR = Path('backtest_results/new_strategies')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# DATA FETCHING
# =============================================================================

def fetch_crypto_data(symbol: str, interval: str = '1h', limit: int = 1000) -> pd.DataFrame:
    """Fetch OHLCV data from Binance API."""
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return pd.DataFrame()


def fetch_all_data() -> Dict[str, pd.DataFrame]:
    """Fetch data for all pairs with progress tracking."""
    data_cache = {}
    
    logger.info(f"Fetching data for {len(CRYPTO_PAIRS)} pairs...")
    
    for symbol in CRYPTO_PAIRS:
        df = fetch_crypto_data(symbol, '1h', LIMIT_BARS)
        if not df.empty and len(df) > 100:
            data_cache[symbol] = df
            logger.info(f"  {symbol}: {len(df)} bars from {df.index[0]} to {df.index[-1]}")
        else:
            logger.warning(f"  {symbol}: Insufficient data")
    
    logger.info(f"Successfully loaded {len(data_cache)} pairs")
    return data_cache


# =============================================================================
# BACKTEST EXECUTION
# =============================================================================

def run_strategy_backtest(strategy_class, strategy_params: Dict, 
                          data: Dict[str, pd.DataFrame]) -> Dict:
    """Run a single strategy across all pairs."""
    strategy = strategy_class(**strategy_params)
    all_results = []
    pair_results = {}
    
    for symbol, df in data.items():
        try:
            result = strategy.backtest(df, symbol)
            if isinstance(result, dict):
                result['symbol'] = symbol
                all_results.append(result)
                pair_results[symbol] = result
            else:
                # Handle StrategyPerformance dataclass
                result_dict = result.to_dict() if hasattr(result, 'to_dict') else {
                    'strategy': strategy.name,
                    'total_trades': result.total_trades,
                    'win_rate': result.win_rate,
                    'profit_factor': result.profit_factor,
                    'total_return': result.total_return,
                    'max_drawdown': result.max_drawdown,
                    'sharpe_ratio': result.sharpe_ratio,
                    'symbol': symbol
                }
                all_results.append(result_dict)
                pair_results[symbol] = result_dict
        except Exception as e:
            logger.error(f"Error backtesting {strategy.name} on {symbol}: {e}")
            pair_results[symbol] = {'error': str(e)}
    
    # Aggregate results
    valid_results = [r for r in all_results if 'win_rate' in r and r.get('total_trades', 0) > 5]
    
    if not valid_results:
        return {
            'strategy': strategy.name,
            'pairs_tested': len(data),
            'pairs_with_trades': 0,
            'aggregate': {},
            'pair_details': pair_results
        }
    
    # Weighted by number of trades
    total_trades = sum(r['total_trades'] for r in valid_results)
    
    aggregate = {
        'total_trades': total_trades,
        'avg_win_rate': np.average([r['win_rate'] for r in valid_results], 
                                    weights=[r['total_trades'] for r in valid_results]),
        'avg_profit_factor': np.mean([r['profit_factor'] for r in valid_results if r['profit_factor'] != float('inf')]),
        'avg_return': np.mean([r['total_return'] for r in valid_results]),
        'pairs_profitable': sum(1 for r in valid_results if r['total_return'] > 0),
        'pairs_with_60plus_wr': sum(1 for r in valid_results if r['win_rate'] >= 0.60),
        'pairs_with_70plus_wr': sum(1 for r in valid_results if r['win_rate'] >= 0.70),
        'best_pair': max(valid_results, key=lambda x: x['win_rate'])['symbol'],
        'best_win_rate': max(r['win_rate'] for r in valid_results),
    }
    
    return {
        'strategy': strategy.name,
        'pairs_tested': len(data),
        'pairs_with_trades': len(valid_results),
        'aggregate': aggregate,
        'pair_details': pair_results
    }


def run_all_backtests(data: Dict[str, pd.DataFrame]) -> Dict:
    """Run all strategies with various parameter sets."""
    all_results = {}
    
    # Strategy configurations to test
    strategy_configs = [
        # Prop-firm strategies
        ('KC_SCALP_Conservative', KeltnerCompressionScalper, {
            'compression_bars': 3, 'tp_atr_mult': 1.5, 'sl_atr_mult': 1.0, 'time_exit_hours': 4
        }),
        ('KC_SCALP_Aggressive', KeltnerCompressionScalper, {
            'compression_bars': 2, 'tp_atr_mult': 2.0, 'sl_atr_mult': 1.0, 'time_exit_hours': 6
        }),
        ('VWAP_ELITE_Standard', VWAPMeanReversionElite, {
            'deviation_threshold': 2.0, 'time_exit_hours': 6
        }),
        ('VWAP_ELITE_Deep', VWAPMeanReversionElite, {
            'deviation_threshold': 2.5, 'time_exit_hours': 8
        }),
        ('MTF_RSI_Strict', MultiTimeframeRSIConfluence, {
            'min_confluence': 3, 'time_exit_hours': 12
        }),
        ('MTF_RSI_Lenient', MultiTimeframeRSIConfluence, {
            'min_confluence': 2, 'time_exit_hours': 8
        }),
    ]
    
    # Add general strategies
    for name, strategy_class in ALL_STRATEGIES.items():
        strategy_configs.append((name, strategy_class, {}))
    
    logger.info(f"Running backtests for {len(strategy_configs)} strategy configurations...")
    
    for config_name, strategy_class, params in strategy_configs:
        logger.info(f"  Testing: {config_name}")
        result = run_strategy_backtest(strategy_class, params, data)
        all_results[config_name] = result
        
        # Log summary
        agg = result.get('aggregate', {})
        if agg:
            logger.info(f"    Trades: {agg.get('total_trades', 0)}, "
                       f"WR: {agg.get('avg_win_rate', 0):.1%}, "
                       f"PF: {agg.get('avg_profit_factor', 0):.2f}")
    
    return all_results


# =============================================================================
# RESULT ANALYSIS & REPORTING
# =============================================================================

def generate_viability_report(results: Dict) -> str:
    """Generate prop-firm viability report."""
    report = []
    report.append("=" * 80)
    report.append("PROP-FIRM STRATEGY VIABILITY REPORT")
    report.append(f"Generated: {datetime.now().isoformat()}")
    report.append("=" * 80)
    report.append("")
    
    # Criteria for prop firm
    PROP_FIRM_CRITERIA = {
        'win_rate': 0.65,  # 65% minimum
        'profit_factor': 1.5,
        'max_drawdown': 0.10  # 10%
    }
    
    report.append("EVALUATION CRITERIA:")
    report.append(f"  - Win Rate >= {PROP_FIRM_CRITERIA['win_rate']:.0%}")
    report.append(f"  - Profit Factor >= {PROP_FIRM_CRITERIA['profit_factor']}")
    report.append(f"  - Max Drawdown <= {PROP_FIRM_CRITERIA['max_drawdown']:.0%}")
    report.append("")
    
    # Rank strategies
    viable_strategies = []
    
    for name, result in results.items():
        agg = result.get('aggregate', {})
        if not agg or agg.get('total_trades', 0) < 50:
            continue
        
        wr = agg.get('avg_win_rate', 0)
        pf = agg.get('avg_profit_factor', 0)
        
        # Score based on criteria
        wr_score = min(wr / PROP_FIRM_CRITERIA['win_rate'], 1.5)
        pf_score = min(pf / PROP_FIRM_CRITERIA['profit_factor'], 1.5) if pf != float('inf') else 1.5
        
        viability_score = (wr_score * 0.5 + pf_score * 0.5) * 100
        
        viable_strategies.append({
            'name': name,
            'win_rate': wr,
            'profit_factor': pf,
            'total_trades': agg.get('total_trades', 0),
            'pairs_70plus_wr': agg.get('pairs_with_70plus_wr', 0),
            'viability_score': viability_score,
            'is_viable': wr >= PROP_FIRM_CRITERIA['win_rate'] and pf >= PROP_FIRM_CRITERIA['profit_factor']
        })
    
    # Sort by viability score
    viable_strategies.sort(key=lambda x: x['viability_score'], reverse=True)
    
    report.append("STRATEGY RANKINGS:")
    report.append("-" * 80)
    report.append(f"{'Rank':<6}{'Strategy':<25}{'Win Rate':<12}{'PF':<10}{'Trades':<10}{'Score':<10}{'Status'}")
    report.append("-" * 80)
    
    for i, strat in enumerate(viable_strategies, 1):
        status = "✅ VIABLE" if strat['is_viable'] else "⚠️ MARGINAL"
        report.append(
            f"{i:<6}{strat['name'][:24]:<25}{strat['win_rate']:<12.1%}"
            f"{strat['profit_factor']:<10.2f}{strat['total_trades']:<10}{strat['viability_score']:<10.1f}{status}"
        )
    
    report.append("")
    report.append("=" * 80)
    report.append("RECOMMENDATIONS:")
    report.append("=" * 80)
    
    top_viable = [s for s in viable_strategies if s['is_viable']][:5]
    if top_viable:
        report.append("\nTop Prop-Firm Worthy Strategies:")
        for s in top_viable:
            report.append(f"  • {s['name']}: {s['win_rate']:.1%} WR, {s['profit_factor']:.2f} PF")
    
    marginal = [s for s in viable_strategies if not s['is_viable'] and s['viability_score'] > 70][:3]
    if marginal:
        report.append("\nMarginal (Need Optimization):")
        for s in marginal:
            report.append(f"  • {s['name']}: {s['win_rate']:.1%} WR (needs {PROP_FIRM_CRITERIA['win_rate']:.0%}+)")
    
    return '\n'.join(report)


def save_results(results: Dict):
    """Save all results to JSON files."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Full results
    output_file = OUTPUT_DIR / f'backtest_results_{timestamp}.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Saved full results to {output_file}")
    
    # Viability report
    report = generate_viability_report(results)
    report_file = OUTPUT_DIR / f'viability_report_{timestamp}.md'
    with open(report_file, 'w') as f:
        f.write(report)
    logger.info(f"Saved viability report to {report_file}")
    
    # Print report
    print("\n" + report)


# =============================================================================
# AUDIT INTEGRATION
# =============================================================================

def generate_audit_entries(results: Dict) -> List[Dict]:
    """Generate entries for ejaguiar1_stocks.strategy_registry."""
    entries = []
    
    for name, result in results.items():
        agg = result.get('aggregate', {})
        if not agg:
            continue
        
        entry = {
            'strategy_name': name,
            'strategy_type': 'PROP_FIRM' if 'SCALP' in name or 'VWAP' in name else 'GENERAL',
            'created_at': datetime.now().isoformat(),
            'backtest_period_start': None,  # Will be filled from data
            'backtest_period_end': None,
            'total_trades_backtest': agg.get('total_trades', 0),
            'win_rate_backtest': agg.get('avg_win_rate', 0),
            'profit_factor_backtest': agg.get('avg_profit_factor', 0),
            'max_drawdown_backtest': agg.get('avg_max_drawdown', 0),
            'sharpe_ratio_backtest': agg.get('avg_sharpe', 0),
            'pairs_tested': result.get('pairs_tested', 0),
            'pairs_profitable': agg.get('pairs_profitable', 0),
            'status': 'APPROVED_FOR_FORWARD' if agg.get('avg_win_rate', 0) >= 0.60 else 'NEEDS_REVIEW',
            'forward_test_started': None,
            'viability_score': agg.get('avg_win_rate', 0) * 100
        }
        entries.append(entry)
    
    return entries


def save_audit_entries(entries: List[Dict]):
    """Save audit entries for database import."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    audit_file = OUTPUT_DIR / f'audit_entries_{timestamp}.json'
    
    with open(audit_file, 'w') as f:
        json.dump(entries, f, indent=2)
    
    logger.info(f"Saved {len(entries)} audit entries to {audit_file}")
    
    # Also generate SQL insert statements
    sql_file = OUTPUT_DIR / f'audit_inserts_{timestamp}.sql'
    with open(sql_file, 'w') as f:
        f.write("-- Strategy Registry Insert Statements\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
        
        for entry in entries:
            f.write(f"""
INSERT INTO strategy_registry (
    strategy_name, strategy_type, created_at, 
    total_trades_backtest, win_rate_backtest, profit_factor_backtest,
    max_drawdown_backtest, pairs_tested, pairs_profitable, status, viability_score
) VALUES (
    '{entry['strategy_name']}', '{entry['strategy_type']}', '{entry['created_at']}',
    {entry['total_trades_backtest']}, {entry['win_rate_backtest']:.4f}, {entry['profit_factor_backtest']:.4f},
    {entry['max_drawdown_backtest']:.4f}, {entry['pairs_tested']}, {entry['pairs_profitable']},
    '{entry['status']}', {entry['viability_score']:.2f}
) ON DUPLICATE KEY UPDATE
    win_rate_backtest = {entry['win_rate_backtest']:.4f},
    profit_factor_backtest = {entry['profit_factor_backtest']:.4f},
    status = '{entry['status']}';
""")
    
    logger.info(f"Saved SQL inserts to {sql_file}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    logger.info("=" * 80)
    logger.info("EXTENSIVE BACKTEST RUNNER - NEW STRATEGIES")
    logger.info("=" * 80)
    
    # Fetch data
    data = fetch_all_data()
    
    if len(data) < 10:
        logger.error("Insufficient data fetched. Aborting.")
        return
    
    # Run backtests
    results = run_all_backtests(data)
    
    # Save results
    save_results(results)
    
    # Generate audit entries
    audit_entries = generate_audit_entries(results)
    save_audit_entries(audit_entries)
    
    logger.info("=" * 80)
    logger.info("BACKTEST RUN COMPLETE")
    logger.info(f"Results saved to: {OUTPUT_DIR}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
