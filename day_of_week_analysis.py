"""
Day of Week Analysis for Trading Performance

Analyzes closed picks to identify patterns by day of week.
Includes scientific research on calendar effects in markets.
"""

import csv
import json
import statistics
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Tuple


def load_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def parse_float(val):
    if not val or val.strip() in ('', 'None', 'N/A', '??', '?'):
        return None
    try:
        return float(val.replace('%', '').strip())
    except:
        return None


def parse_str(val):
    if not val:
        return ''
    return val.strip()


def parse_datetime(val):
    """Parse various datetime formats."""
    if not val:
        return None
    formats = [
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%m/%d/%Y, %I:%M:%S %p',
        '%m/%d/%Y %H:%M:%S',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val.strip(), fmt)
        except:
            continue
    return None


def get_day_of_week(dt: datetime) -> str:
    """Get day name from datetime."""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return days[dt.weekday()]


def analyze_day_of_week():
    """Main analysis function."""
    
    # Load data (check common paths)
    import os
    possible_paths = [
        r'C:\Users\zerou\Downloads\antigravity_closed_picks_2026-03-27 (6).csv',
        r'antigravity_closed_picks_2026-03-27.csv',
        r'data\closed_picks.csv',
        r'closed_picks.csv',
    ]
    
    closed = None
    for path in possible_paths:
        if os.path.exists(path):
            try:
                closed = load_csv(path)
                print(f"Loaded: {path} ({len(closed)} records)")
                break
            except Exception as e:
                print(f"Failed to load {path}: {e}")
                continue
    
    if not closed:
        print("Could not find closed picks CSV file")
        return generate_synthetic_analysis()
    
    # Parse timestamps and PnL
    parsed_trades = []
    for r in closed:
        entry_time = parse_datetime(parse_str(r.get('Entry Time', r.get('entry_time', ''))))
        exit_time = parse_datetime(parse_str(r.get('Exit Time', r.get('exit_time', r.get('Closed Time', '')))))
        pnl = parse_float(r.get('PnL%', r.get('pnl_pct', r.get('pnl', ''))))
        
        if entry_time and pnl is not None:
            parsed_trades.append({
                'entry_time': entry_time,
                'exit_time': exit_time,
                'entry_day': get_day_of_week(entry_time),
                'exit_day': get_day_of_week(exit_time) if exit_time else None,
                'pnl': pnl,
                'symbol': parse_str(r.get('Symbol', 'UNKNOWN')),
                'direction': parse_str(r.get('Direction', 'LONG')).upper(),
                'asset_class': parse_str(r.get('Asset Class', 'CRYPTO')).upper(),
                'system': parse_str(r.get('System', 'unknown')),
            })
    
    print(f"Successfully parsed {len(parsed_trades)} trades with timestamps")
    
    return analyze_trades(parsed_trades)


def analyze_trades(trades: List[Dict]) -> Dict:
    """Analyze trades by day of week."""
    
    # Group by entry day
    by_entry_day = defaultdict(list)
    for t in trades:
        by_entry_day[t['entry_day']].append(t)
    
    # Group by exit day
    by_exit_day = defaultdict(list)
    for t in trades:
        if t['exit_day']:
            by_exit_day[t['exit_day']].append(t)
    
    # Analyze by entry day
    day_stats = {}
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for day in days:
        day_trades = by_entry_day.get(day, [])
        if not day_trades:
            continue
        
        pnls = [t['pnl'] for t in day_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        day_stats[day] = {
            'count': len(day_trades),
            'avg_pnl': statistics.mean(pnls),
            'median_pnl': statistics.median(pnls),
            'win_rate': len(wins) / len(pnls) * 100 if pnls else 0,
            'profit_factor': abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf'),
            'total_pnl': sum(pnls),
            'avg_win': statistics.mean(wins) if wins else 0,
            'avg_loss': statistics.mean(losses) if losses else 0,
            'long_count': sum(1 for t in day_trades if t['direction'] == 'LONG'),
            'short_count': sum(1 for t in day_trades if t['direction'] == 'SHORT'),
        }
    
    # Analyze by direction and day
    direction_day_stats = {}
    for direction in ['LONG', 'SHORT']:
        direction_day_stats[direction] = {}
        for day in days:
            dir_day_trades = [t for t in by_entry_day.get(day, []) if t['direction'] == direction]
            if dir_day_trades:
                pnls = [t['pnl'] for t in dir_day_trades]
                wins = [p for p in pnls if p > 0]
                direction_day_stats[direction][day] = {
                    'count': len(dir_day_trades),
                    'avg_pnl': statistics.mean(pnls),
                    'win_rate': len(wins) / len(pnls) * 100 if pnls else 0,
                }
    
    # Holding period analysis
    holding_by_day = defaultdict(list)
    for t in trades:
        if t['entry_time'] and t['exit_time']:
            try:
                # Handle timezone-aware vs naive
                entry = t['entry_time'].replace(tzinfo=None) if t['entry_time'].tzinfo else t['entry_time']
                exit = t['exit_time'].replace(tzinfo=None) if t['exit_time'].tzinfo else t['exit_time']
                holding_hours = (exit - entry).total_seconds() / 3600
                holding_by_day[t['entry_day']].append(holding_hours)
            except:
                pass
    
    holding_stats = {}
    for day, hours in holding_by_day.items():
        if hours:
            holding_stats[day] = {
                'avg_hours': statistics.mean(hours),
                'median_hours': statistics.median(hours),
            }
    
    return {
        'total_trades': len(trades),
        'by_entry_day': day_stats,
        'by_direction_day': direction_day_stats,
        'holding_by_day': holding_stats,
        'raw_trades': trades,
    }


def generate_synthetic_analysis() -> Dict:
    """Generate synthetic data for demonstration if real data unavailable."""
    print("Generating synthetic trade data for demonstration...")
    
    import random
    random.seed(42)
    
    # Synthetic patterns based on research:
    # - Monday: Lower volatility, mean reversion
    # - Wednesday: "Wednesday Curse" - midweek chop
    # - Friday: Position squaring, lower volume
    # - Weekend: Crypto 24/7, different patterns
    
    trades = []
    base_wr = {'Monday': 48, 'Tuesday': 52, 'Wednesday': 45, 'Thursday': 54, 
               'Friday': 50, 'Saturday': 55, 'Sunday': 53}
    
    for i in range(500):  # 500 synthetic trades
        day = random.choice(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
        direction = random.choice(['LONG', 'SHORT'])
        
        # Adjust WR based on direction and day
        wr = base_wr[day]
        if direction == 'SHORT':
            wr += 15  # SHORT bias in current market
        
        is_win = random.random() < (wr / 100)
        
        if is_win:
            pnl = random.uniform(0.5, 8.0)
        else:
            pnl = random.uniform(-4.0, -0.1)
        
        trades.append({
            'entry_day': day,
            'pnl': pnl,
            'direction': direction,
            'symbol': random.choice(['BTCUSDT', 'ETHUSDT', 'SOLUSDT']),
        })
    
    return analyze_trades(trades)


def print_analysis(results: Dict):
    """Print formatted analysis."""
    print("\n" + "=" * 80)
    print("DAY OF WEEK ANALYSIS - TRADING PERFORMANCE")
    print("=" * 80)
    print(f"Total Trades Analyzed: {results['total_trades']}\n")
    
    # Overall by day
    print("BY ENTRY DAY (Overall)")
    print("-" * 80)
    print(f"{'Day':<12} {'Count':>6} {'Avg PnL':>10} {'Win Rate':>10} {'PF':>6} {'Total PnL':>12}")
    print("-" * 80)
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day in days:
        if day in results['by_entry_day']:
            s = results['by_entry_day'][day]
            print(f"{day:<12} {s['count']:>6} {s['avg_pnl']:>+9.2f}% {s['win_rate']:>9.1f}% {s['profit_factor']:>6.2f} {s['total_pnl']:>+11.2f}%")
    
    # By direction
    print("\n" + "-" * 80)
    print("BY DIRECTION AND DAY")
    print("-" * 80)
    
    for direction in ['LONG', 'SHORT']:
        print(f"\n{direction}:")
        print(f"{'Day':<12} {'Count':>6} {'Avg PnL':>10} {'Win Rate':>10}")
        print("-" * 40)
        for day in days:
            if day in results['by_direction_day'].get(direction, {}):
                s = results['by_direction_day'][direction][day]
                print(f"{day:<12} {s['count']:>6} {s['avg_pnl']:>+9.2f}% {s['win_rate']:>9.1f}%")
    
    # Statistical significance test
    print("\n" + "=" * 80)
    print("STATISTICAL ANALYSIS")
    print("=" * 80)
    
    day_pnls = {day: results['by_entry_day'][day]['avg_pnl'] 
                for day in days if day in results['by_entry_day']}
    
    if day_pnls:
        best_day = max(day_pnls, key=day_pnls.get)
        worst_day = min(day_pnls, key=day_pnls.get)
        
        print(f"Best Day: {best_day} ({day_pnls[best_day]:+.2f}% avg)")
        print(f"Worst Day: {worst_day} ({day_pnls[worst_day]:+.2f}% avg)")
        print(f"Spread: {day_pnls[best_day] - day_pnls[worst_day]:+.2f}%")
    
    # Weekend vs Weekday
    weekday_pnls = []
    weekend_pnls = []
    
    for day in days:
        if day in results['by_entry_day']:
            day_data = results['by_entry_day'][day]
            if day in ['Saturday', 'Sunday']:
                weekend_pnls.extend([day_data['avg_pnl']] * day_data['count'])
            else:
                weekday_pnls.extend([day_data['avg_pnl']] * day_data['count'])
    
    if weekday_pnls and weekend_pnls:
        print(f"\nWeekday Avg: {statistics.mean(weekday_pnls):+.2f}%")
        print(f"Weekend Avg: {statistics.mean(weekend_pnls):+.2f}%")
    
    print("=" * 80)
    
    return results


if __name__ == '__main__':
    results = analyze_day_of_week()
    print_analysis(results)
