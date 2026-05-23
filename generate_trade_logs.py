#!/usr/bin/env python3
"""
Generate SYNTHETIC Trade-by-Trade Breakdown for Testing/Development
====================================================================
WARNING: This script generates RANDOMLY fabricated trade data.
All records are labeled is_synthetic=True / data_source=RANDOMLY_GENERATED.
These records must NEVER be used for live audit, compliance, or performance
reporting. They exist solely for schema testing and UI development.

Requires --synthetic flag to run, preventing accidental execution.

Output formats:
- CSV (for Excel/analysis)
- JSON (for database import)
- SQL (for direct DB insertion)
"""

import json
import csv
import os
import argparse
from datetime import datetime, timedelta
import random
import hashlib

os.makedirs('backtest_results/futures_comparison/trade_logs', exist_ok=True)

# =============================================================================
# TRADE GENERATION CONFIGURATION
# =============================================================================

STRATEGIES = {
    'KC_SCALP_v1': {
        'win_rate': 0.73,
        'profit_factor': 1.92,
        'avg_win': 0.0045,
        'avg_loss': 0.0030,
        'total_trades': 1247,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT', 'LTCUSDT'],
        'symbol_weights': [0.20, 0.18, 0.15, 0.10, 0.08, 0.07, 0.07, 0.06, 0.05, 0.04],
        'direction_bias': 0.55,  # 55% long
        'timeframe': '1h',
        'start_date': '2020-01-01',
        'end_date': '2025-02-28'
    },
    'MTF_RSI_v1': {
        'win_rate': 0.71,
        'profit_factor': 1.85,
        'avg_win': 0.0060,
        'avg_loss': 0.0035,
        'total_trades': 756,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT', 'AVAXUSDT', 'LINKUSDT', 'XRPUSDT', 'BNBUSDT', 'LTCUSDT'],
        'symbol_weights': [0.18, 0.16, 0.14, 0.12, 0.10, 0.09, 0.08, 0.06, 0.04, 0.03],
        'direction_bias': 0.50,
        'timeframe': '1h',
        'start_date': '2020-01-01',
        'end_date': '2025-02-28'
    },
    'FLASH_REV_v1': {
        'win_rate': 0.76,
        'profit_factor': 2.40,
        'avg_win': 0.0150,
        'avg_loss': 0.0060,
        'total_trades': 234,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'LINKUSDT', 'ADAUSDT', 'DOTUSDT', 'XRPUSDT', 'BNBUSDT', 'DOGEUSDT'],
        'symbol_weights': [0.20, 0.18, 0.15, 0.12, 0.10, 0.08, 0.06, 0.05, 0.04, 0.02],
        'direction_bias': 0.0,  # All long (crash reversal)
        'timeframe': '1h',
        'start_date': '2020-01-01',
        'end_date': '2025-02-28'
    },
    'FUNDING_PRO_v1': {
        'win_rate': 0.68,
        'profit_factor': 1.92,
        'avg_win': 0.0070,
        'avg_loss': 0.0040,
        'total_trades': 567,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT', 'BNBUSDT'],
        'symbol_weights': [0.22, 0.18, 0.15, 0.12, 0.10, 0.08, 0.06, 0.04, 0.03, 0.02],
        'direction_bias': 0.50,
        'timeframe': '1h',
        'start_date': '2020-01-01',
        'end_date': '2025-02-28'
    },
    'VWAP_ELITE_v1': {
        'win_rate': 0.69,
        'profit_factor': 1.78,
        'avg_win': 0.0050,
        'avg_loss': 0.0032,
        'total_trades': 892,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'LINKUSDT', 'AVAXUSDT', 'LTCUSDT', 'DOTUSDT'],
        'symbol_weights': [0.18, 0.17, 0.14, 0.11, 0.10, 0.09, 0.08, 0.06, 0.04, 0.03],
        'direction_bias': 0.50,
        'timeframe': '1h',
        'start_date': '2020-01-01',
        'end_date': '2025-02-28'
    },
    'BB_SQUEEZE_v1': {
        'win_rate': 0.67,
        'profit_factor': 1.78,
        'avg_win': 0.0055,
        'avg_loss': 0.0035,
        'total_trades': 678,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'MATICUSDT', 'ADAUSDT', 'LINKUSDT', 'DOTUSDT', 'XRPUSDT', 'BNBUSDT'],
        'symbol_weights': [0.19, 0.17, 0.15, 0.12, 0.10, 0.09, 0.07, 0.05, 0.04, 0.02],
        'direction_bias': 0.50,
        'timeframe': '1h',
        'start_date': '2020-01-01',
        'end_date': '2025-02-28'
    }
}

# =============================================================================
# TRADE GENERATION
# =============================================================================

def generate_trade_id(strategy, symbol, entry_time, direction):
    """Generate unique trade ID for audit trail."""
    data = f"{strategy}_{symbol}_{entry_time.isoformat()}_{direction}"
    return hashlib.md5(data.encode()).hexdigest()[:16].upper()

def generate_trades(strategy_name, config):
    """Generate realistic trade-by-trade breakdown."""
    trades = []
    
    start_date = datetime.strptime(config['start_date'], '%Y-%m-%d')
    end_date = datetime.strptime(config['end_date'], '%Y-%m-%d')
    total_days = (end_date - start_date).days
    
    win_rate = config['win_rate']
    avg_win = config['avg_win']
    avg_loss = config['avg_loss']
    total_trades = config['total_trades']
    
    # Expected wins and losses
    expected_wins = int(total_trades * win_rate)
    expected_losses = total_trades - expected_wins
    
    wins_created = 0
    losses_created = 0
    
    for i in range(total_trades):
        # Determine symbol based on weights
        symbol = random.choices(config['symbols'], weights=config['symbol_weights'])[0]
        
        # Determine direction
        if config['direction_bias'] == 0.0:
            direction = 'LONG'
        elif config['direction_bias'] == 1.0:
            direction = 'SHORT'
        else:
            direction = 'LONG' if random.random() < config['direction_bias'] else 'SHORT'
        
        # Determine win/loss
        if wins_created < expected_wins and losses_created < expected_losses:
            is_win = random.random() < win_rate
        elif wins_created < expected_wins:
            is_win = True
        else:
            is_win = False
        
        if is_win:
            wins_created += 1
            pnl_pct = avg_win * random.uniform(0.7, 1.4)
            exit_reason = random.choice(['TAKE_PROFIT', 'TIME_EXIT', 'TRAILING_STOP'])
        else:
            losses_created += 1
            pnl_pct = -avg_loss * random.uniform(0.8, 1.2)
            exit_reason = random.choice(['STOP_LOSS', 'TIME_EXIT'])
        
        # Generate timestamps
        trade_day = random.randint(0, total_days)
        entry_time = start_date + timedelta(days=trade_day, hours=random.randint(0, 23))
        hold_hours = random.uniform(2, 12) if strategy_name != 'FLASH_REV_v1' else random.uniform(6, 18)
        exit_time = entry_time + timedelta(hours=hold_hours)
        
        # Ensure exit is before end_date
        if exit_time > end_date:
            exit_time = end_date - timedelta(hours=1)
            entry_time = exit_time - timedelta(hours=hold_hours)
        
        # Generate prices
        base_price = random.uniform(100, 50000) if 'BTC' in symbol else random.uniform(10, 5000)
        if direction == 'LONG':
            entry_price = base_price
            exit_price = entry_price * (1 + pnl_pct)
            stop_loss = entry_price * 0.985
            take_profit = entry_price * 1.025
        else:
            entry_price = base_price
            exit_price = entry_price * (1 - pnl_pct)
            stop_loss = entry_price * 1.015
            take_profit = entry_price * 0.975
        
        # Calculate metrics
        position_size = random.uniform(0.08, 0.12)  # 8-12% of capital
        capital_at_risk = 10000 * position_size  # Assuming $10k account
        pnl_amount = capital_at_risk * pnl_pct
        
        trade = {
            'trade_id': generate_trade_id(strategy_name, symbol, entry_time, direction),
            'strategy': strategy_name,
            'symbol': symbol,
            'direction': direction,
            'entry_time': entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'exit_time': exit_time.strftime('%Y-%m-%d %H:%M:%S'),
            'entry_price': round(entry_price, 8),
            'exit_price': round(exit_price, 8),
            'stop_loss': round(stop_loss, 8),
            'take_profit': round(take_profit, 8),
            'position_size_pct': round(position_size, 4),
            'capital_at_risk': round(capital_at_risk, 2),
            'pnl_pct': round(pnl_pct * 100, 4),
            'pnl_amount': round(pnl_amount, 2),
            'exit_reason': exit_reason,
            'hold_time_hours': round(hold_hours, 2),
            'is_win': is_win,
            'is_synthetic': True,
            'data_source': 'RANDOMLY_GENERATED',
            'timeframe': config['timeframe'],
            'created_at': datetime.now().isoformat()
        }
        
        trades.append(trade)
    
    # Sort by entry time
    trades.sort(key=lambda x: x['entry_time'])
    
    return trades

# =============================================================================
# OUTPUT GENERATION
# =============================================================================

def save_csv(trades, filename):
    """Save trades to CSV for audit."""
    if not trades:
        return
    
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=trades[0].keys())
        writer.writeheader()
        writer.writerows(trades)
    
    print(f"  [OK] CSV saved: {filename}")

def save_json(trades, filename):
    """Save trades to JSON."""
    with open(filename, 'w') as f:
        json.dump(trades, f, indent=2)
    
    print(f"  [OK] JSON saved: {filename}")

def generate_sql_inserts(trades, strategy_name):
    """Generate SQL INSERT statements."""
    sql = []
    sql.append(f"-- Trade log for {strategy_name}")
    sql.append(f"-- Generated: {datetime.now().isoformat()}")
    sql.append(f"-- Total trades: {len(trades)}")
    sql.append("")
    
    for trade in trades:
        sql.append(f"""
INSERT INTO at_signal_outcomes (
    trade_id, strategy_name, symbol, direction,
    entry_time, exit_time, entry_price, exit_price,
    stop_loss, take_profit, position_size_pct,
    pnl_pct, pnl_amount, exit_reason, hold_time_hours,
    is_win, is_synthetic, data_source, timeframe, created_at
) VALUES (
    '{trade['trade_id']}', '{trade['strategy']}', '{trade['symbol']}', '{trade['direction']}',
    '{trade['entry_time']}', '{trade['exit_time']}', {trade['entry_price']}, {trade['exit_price']},
    {trade['stop_loss']}, {trade['take_profit']}, {trade['position_size_pct']},
    {trade['pnl_pct']}, {trade['pnl_amount']}, '{trade['exit_reason']}', {trade['hold_time_hours']},
    {1 if trade['is_win'] else 0}, 1, 'RANDOMLY_GENERATED', '{trade['timeframe']}', '{trade['created_at']}'
) ON DUPLICATE KEY UPDATE
    pnl_pct = {trade['pnl_pct']},
    pnl_amount = {trade['pnl_amount']},
    exit_reason = '{trade['exit_reason']}';""")
    
    return '\n'.join(sql)

def generate_summary_stats(trades, strategy_name):
    """Generate summary statistics for verification."""
    total_trades = len(trades)
    wins = [t for t in trades if t['is_win']]
    losses = [t for t in trades if not t['is_win']]
    
    win_rate = len(wins) / total_trades if total_trades else 0
    total_pnl = sum(t['pnl_amount'] for t in trades)
    gross_profit = sum(t['pnl_amount'] for t in wins)
    gross_loss = abs(sum(t['pnl_amount'] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss else 0
    
    avg_win = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0
    
    return {
        'strategy': strategy_name,
        'total_trades': total_trades,
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': round(win_rate, 4),
        'profit_factor': round(profit_factor, 2),
        'total_pnl': round(total_pnl, 2),
        'avg_win_pct': round(avg_win, 4),
        'avg_loss_pct': round(avg_loss, 4),
        'gross_profit': round(gross_profit, 2),
        'gross_loss': round(gross_loss, 2)
    }

# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate SYNTHETIC trade logs for testing/development only.'
    )
    parser.add_argument(
        '--synthetic', action='store_true', required=True,
        help='Required flag acknowledging all generated data is synthetic/fabricated'
    )
    parser.parse_args()

    print("=" * 70)
    print("GENERATING SYNTHETIC TRADE LOGS (NOT REAL TRADES)")
    print("WARNING: All data is randomly generated and labeled is_synthetic=True")
    print("=" * 70)
    print()
    
    all_summaries = []
    
    for strategy_name, config in STRATEGIES.items():
        print(f"Processing: {strategy_name}")
        
        # Generate trades
        trades = generate_trades(strategy_name, config)
        
        # Save CSV
        csv_file = f'backtest_results/futures_comparison/trade_logs/{strategy_name}_trades.csv'
        save_csv(trades, csv_file)
        
        # Save JSON
        json_file = f'backtest_results/futures_comparison/trade_logs/{strategy_name}_trades.json'
        save_json(trades, json_file)
        
        # Generate SQL
        sql = generate_sql_inserts(trades, strategy_name)
        sql_file = f'backtest_results/futures_comparison/trade_logs/{strategy_name}_inserts.sql'
        with open(sql_file, 'w') as f:
            f.write(sql)
        print(f"  [OK] SQL saved: {sql_file}")
        
        # Generate summary
        summary = generate_summary_stats(trades, strategy_name)
        all_summaries.append(summary)
        
        print(f"  Stats: {summary['wins']}W/{summary['losses']}L | WR: {summary['win_rate']:.1%} | PF: {summary['profit_factor']:.2f} | PnL: ${summary['total_pnl']:.2f}")
        print()
    
    # Save combined summary
    summary_file = 'backtest_results/futures_comparison/trade_logs/TRADE_LOG_SUMMARY.json'
    with open(summary_file, 'w') as f:
        json.dump(all_summaries, f, indent=2)
    
    # Generate combined SQL
    combined_sql = []
    combined_sql.append("-- COMBINED TRADE LOG INSERTS")
    combined_sql.append(f"-- Generated: {datetime.now().isoformat()}")
    combined_sql.append(f"-- Strategies: {len(STRATEGIES)}")
    combined_sql.append(f"-- Total Trades: {sum(s['total_trades'] for s in all_summaries)}")
    combined_sql.append("")
    combined_sql.append("USE ejaguiar1_stocks;")
    combined_sql.append("")
    
    for strategy_name in STRATEGIES.keys():
        sql_file = f'backtest_results/futures_comparison/trade_logs/{strategy_name}_inserts.sql'
        with open(sql_file, 'r') as f:
            combined_sql.append(f.read())
        combined_sql.append("")
    
    combined_sql_file = 'backtest_results/futures_comparison/trade_logs/ALL_TRADES_INSERTS.sql'
    with open(combined_sql_file, 'w') as f:
        f.write('\n'.join(combined_sql))
    
    print("=" * 70)
    print("TRADE LOG GENERATION COMPLETE")
    print("=" * 70)
    print()
    print(f"Total strategies processed: {len(STRATEGIES)}")
    print(f"Total trades generated: {sum(s['total_trades'] for s in all_summaries)}")
    print()
    print("Files generated:")
    print(f"  - Individual CSV files: {len(STRATEGIES)}")
    print(f"  - Individual JSON files: {len(STRATEGIES)}")
    print(f"  - Individual SQL files: {len(STRATEGIES)}")
    print(f"  - Combined SQL: {combined_sql_file}")
    print(f"  - Summary JSON: {summary_file}")
    print()
    print("Verification:")
    for summary in all_summaries:
        print(f"  {summary['strategy']}: {summary['total_trades']} trades, {summary['win_rate']:.1%} WR, PF {summary['profit_factor']:.2f}")
    print()

if __name__ == "__main__":
    main()
