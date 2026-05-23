"""
Analyze picks database from SQL extract
"""
import re
import json
from collections import defaultdict
from typing import Dict, List

SQL_FILE = r'C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql'

def extract_inserts(sql_file: str, table_name: str) -> List[Dict]:
    """Extract INSERT statements for a specific table."""
    records = []
    
    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find all INSERT statements for this table
    pattern = rf"INSERT INTO `{table_name}` \([^)]+\) VALUES"
    inserts = re.split(pattern, content)
    
    for insert in inserts[1:]:  # Skip first split
        # Extract values
        values_match = re.search(r'\((.+?)\);', insert, re.DOTALL)
        if values_match:
            values_str = values_match.group(1)
            # Parse the values tuple
            try:
                # Simple parsing for now - split by comma but handle quoted strings
                values = parse_values(values_str)
                records.append(values)
            except:
                pass
    
    return records


def parse_values(values_str: str) -> List:
    """Parse SQL values tuple."""
    values = []
    current = ''
    in_quotes = False
    
    for char in values_str:
        if char == "'" and (not current or current[-1] != '\\'):
            in_quotes = not in_quotes
            current += char
        elif char == ',' and not in_quotes:
            values.append(current.strip())
            current = ''
        else:
            current += char
    
    if current:
        values.append(current.strip())
    
    return values


def sample_picks_data(sql_file: str, sample_size: int = 1000) -> List[Dict]:
    """Sample picks data from the SQL file."""
    picks = []
    count = 0
    
    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if 'INSERT INTO `alpha_picks`' in line or 'INSERT INTO `picks`' in line.lower():
                # Parse this pick
                pick = parse_pick_line(line)
                if pick:
                    picks.append(pick)
                    count += 1
                    if count >= sample_size:
                        break
    
    return picks


def parse_pick_line(line: str) -> Dict:
    """Parse a pick INSERT line."""
    try:
        # Extract values between VALUES(...);
        match = re.search(r'VALUES \((.+)\);', line)
        if not match:
            return None
        
        values_str = match.group(1)
        values = parse_values(values_str)
        
        # alpha_picks has: id, ticker, strategy, pick_date, entry_price, score, conviction, ...
        if len(values) >= 7:
            return {
                'id': values[0],
                'ticker': values[1].strip("'"),
                'strategy': values[2].strip("'"),
                'pick_date': values[3].strip("'"),
                'entry_price': values[4],
                'score': values[5],
                'conviction': values[6].strip("'") if len(values) > 6 else None,
                'horizon': values[7].strip("'") if len(values) > 7 else None,
            }
    except:
        pass
    return None


def analyze_algorithm_performance():
    """Analyze algorithm_performance table."""
    print("Reading algorithm performance data...")
    
    algorithms = []
    
    with open(SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find algorithm_performance INSERTs
    perf_section = re.search(r'INSERT INTO `algorithm_performance`.*?(?=CREATE TABLE|INSERT INTO)', 
                              content, re.DOTALL)
    
    if perf_section:
        section = perf_section.group(0)
        # Find all value tuples
        values_pattern = r'\((\d+),\s*\'([^\']+)\',\s*\'([^\']*)\',\s*(\d+),\s*(\d+),\s*([\d.]+),\s*([\-\d.]+)'
        matches = re.findall(values_pattern, section)
        
        for match in matches[:50]:  # First 50 algorithms
            alg_id, name, strat_type, total_picks, total_trades, win_rate, avg_return = match
            algorithms.append({
                'id': int(alg_id),
                'name': name,
                'type': strat_type,
                'total_picks': int(total_picks),
                'total_trades': int(total_trades),
                'win_rate': float(win_rate),
                'avg_return': float(avg_return)
            })
    
    return algorithms


def analyze_picks_sample():
    """Sample and analyze picks."""
    print("Sampling picks data...")
    
    picks = sample_picks_data(SQL_FILE, 500)
    
    # Group by strategy
    by_strategy = defaultdict(list)
    for pick in picks:
        by_strategy[pick.get('strategy', 'unknown')].append(pick)
    
    print(f"\nSampled {len(picks)} picks across {len(by_strategy)} strategies")
    
    for strategy, strategy_picks in sorted(by_strategy.items(), 
                                            key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"  {strategy}: {len(strategy_picks)} picks")
    
    return by_strategy


def analyze_database_structure():
    """Analyze the overall database structure."""
    print("Analyzing database structure...")
    
    with open(SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find all table names
    tables = re.findall(r'CREATE TABLE `([^`]+)`', content)
    
    # Count records per table
    table_stats = {}
    for table in tables:
        count = content.count(f'INSERT INTO `{table}`')
        table_stats[table] = count
    
    return table_stats


def main():
    print("=" * 80)
    print("PICKS DATABASE ANALYSIS")
    print("=" * 80)
    print(f"Source: {SQL_FILE}")
    print()
    
    # Analyze structure
    table_stats = analyze_database_structure()
    print("DATABASE TABLES:")
    print("-" * 80)
    for table, count in sorted(table_stats.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {table:<40} {count:>8} records")
    
    print()
    
    # Analyze algorithm performance
    algorithms = analyze_algorithm_performance()
    print("TOP ALGORITHMS BY PERFORMANCE:")
    print("-" * 80)
    
    # Sort by various metrics
    by_return = sorted(algorithms, key=lambda x: x['avg_return'], reverse=True)[:10]
    print("\nBy Average Return:")
    for alg in by_return:
        print(f"  {alg['name'][:40]:<40} {alg['avg_return']:>+7.2f}%  WR: {alg['win_rate']:>5.1f}%  Picks: {alg['total_picks']}")
    
    by_winrate = sorted(algorithms, key=lambda x: x['win_rate'], reverse=True)[:10]
    print("\nBy Win Rate:")
    for alg in by_winrate:
        print(f"  {alg['name'][:40]:<40} {alg['win_rate']:>5.1f}%  Return: {alg['avg_return']:>+7.2f}%  Picks: {alg['total_picks']}")
    
    by_volume = sorted(algorithms, key=lambda x: x['total_picks'], reverse=True)[:10]
    print("\nBy Volume (Most Picks):")
    for alg in by_volume:
        print(f"  {alg['name'][:40]:<40} {alg['total_picks']:>5} picks  WR: {alg['win_rate']:>5.1f}%  Return: {alg['avg_return']:>+7.2f}%")
    
    print()
    
    # Sample picks
    by_strategy = analyze_picks_sample()
    
    # Save results
    results = {
        'algorithms': algorithms,
        'table_stats': table_stats,
        'sample_strategies': list(by_strategy.keys())
    }
    
    with open('sql_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\nResults saved to: sql_analysis_results.json")
    
    return algorithms, table_stats


if __name__ == '__main__':
    main()
