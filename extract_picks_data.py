#!/usr/bin/env python3
"""
Extract picks data for deeper analysis
"""
import re
import json
from collections import defaultdict

SQL_FILE = r'C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql'

def extract_picks_sample(sample_size=2000):
    """Extract a sample of picks data."""
    picks = []
    
    print(f"Extracting {sample_size} picks sample...")
    
    with open(SQL_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        chunk_size = 50 * 1024 * 1024  # 50MB chunks
        buffer = ""
        total_read = 0
        
        while total_read < 2000 * 1024 * 1024 and len(picks) < sample_size:  # Stop after 2GB or enough picks
            chunk = f.read(chunk_size)
            if not chunk:
                break
            
            total_read += len(chunk)
            buffer += chunk
            
            # Find INSERT statements for alpha_picks
            pattern = r'INSERT INTO `alpha_picks`[^;]+VALUES\s+(.+?);'
            matches = re.findall(pattern, buffer, re.DOTALL)
            
            for match in matches:
                # Parse individual rows
                # Row: (id, 'ticker', 'strategy', 'date', price, score, 'conviction', ...)
                rows = re.findall(
                    r"\((\d+),\s*'([^']+)',\s*'([^']*)',\s*'([^']+)',\s*([\d.]+),\s*(\d+),\s*'([^']*)'",
                    match
                )
                
                for row in rows:
                    pick_id, ticker, strategy, date, price, score, conviction = row
                    picks.append({
                        'id': int(pick_id),
                        'ticker': ticker,
                        'strategy': strategy,
                        'date': date,
                        'entry_price': float(price),
                        'score': int(score),
                        'conviction': conviction
                    })
                    
                    if len(picks) >= sample_size:
                        break
                
                if len(picks) >= sample_size:
                    break
            
            buffer = buffer[-512*1024:] if len(buffer) > 512*1024 else buffer
            
            if total_read % (200 * 1024 * 1024) == 0:
                print(f"  Processed {total_read/1024/1024:.0f}MB, found {len(picks)} picks...")
    
    print(f"\nExtracted {len(picks)} picks")
    return picks


def analyze_picks(picks):
    """Analyze picks sample."""
    
    print("\n" + "=" * 80)
    print("PICKS SAMPLE ANALYSIS")
    print("=" * 80)
    
    # By strategy
    by_strategy = defaultdict(list)
    for p in picks:
        by_strategy[p['strategy']].append(p)
    
    print(f"\nPicks by Strategy:")
    print("-" * 80)
    for strat, strat_picks in sorted(by_strategy.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
        avg_score = sum(p['score'] for p in strat_picks) / len(strat_picks)
        print(f"  {strat[:40]:<40} Count:{len(strat_picks):>5}  AvgScore:{avg_score:>5.1f}")
    
    # Score distribution
    print("\nScore Distribution:")
    print("-" * 80)
    score_buckets = {'90-100': 0, '80-89': 0, '70-79': 0, '60-69': 0, '50-59': 0, '<50': 0}
    for p in picks:
        s = p['score']
        if s >= 90: score_buckets['90-100'] += 1
        elif s >= 80: score_buckets['80-89'] += 1
        elif s >= 70: score_buckets['70-79'] += 1
        elif s >= 60: score_buckets['60-69'] += 1
        elif s >= 50: score_buckets['50-59'] += 1
        else: score_buckets['<50'] += 1
    
    for bucket, count in score_buckets.items():
        pct = count / len(picks) * 100
        bar = '█' * int(pct / 2)
        print(f"  {bucket:<10} {count:>5} picks ({pct:>5.1f}%) {bar}")
    
    # By ticker
    by_ticker = defaultdict(int)
    for p in picks:
        by_ticker[p['ticker']] += 1
    
    print("\nMost Picked Tickers:")
    print("-" * 80)
    for ticker, count in sorted(by_ticker.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {ticker:<10} {count:>4} picks")
    
    # Conviction analysis
    by_conviction = defaultdict(list)
    for p in picks:
        by_conviction[p['conviction']].append(p)
    
    print("\nBy Conviction Level:")
    print("-" * 80)
    for conv, conv_picks in sorted(by_conviction.items(), key=lambda x: len(x[1]), reverse=True):
        avg_score = sum(p['score'] for p in conv_picks) / len(conv_picks)
        print(f"  {conv:<15} Count:{len(conv_picks):>5}  AvgScore:{avg_score:>5.1f}")
    
    return {
        'total_picks': len(picks),
        'by_strategy': {k: len(v) for k, v in by_strategy.items()},
        'by_ticker': dict(by_ticker),
        'score_distribution': score_buckets
    }


def main():
    picks = extract_picks_sample(2000)
    results = analyze_picks(picks)
    
    with open('picks_sample_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\n\nResults saved to: picks_sample_analysis.json")
    
    return results


if __name__ == '__main__':
    main()
