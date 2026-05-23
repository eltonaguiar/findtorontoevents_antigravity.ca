"""
Deep Asset Class Analysis

Analyzes picks by asset class to identify:
1. Scoring accuracy per asset class
2. Edge opportunities
3. Scoring system flaws
4. Optimization recommendations
"""

import csv
import json
import statistics
from collections import defaultdict, Counter
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


def analyze_by_asset_class():
    """Main analysis function."""
    
    import os
    possible_paths = [
        r'C:\Users\zerou\Downloads\antigravity_closed_picks_2026-03-27 (6).csv',
        r'antigravity_closed_picks_2026-03-27.csv',
    ]
    
    closed = None
    for path in possible_paths:
        if os.path.exists(path):
            closed = load_csv(path)
            print(f"Loaded: {path} ({len(closed)} records)")
            break
    
    if not closed:
        print("CSV not found, generating synthetic analysis...")
        return generate_synthetic_analysis()
    
    # Parse all trades
    parsed_trades = []
    for r in closed:
        pnl = parse_float(r.get('PnL%', r.get('pnl_pct', r.get('pnl', ''))))
        score = parse_float(r.get('Score', r.get('score', '')))
        trust = parse_float(r.get('Trust Score (0-10)', r.get('trust', '')))
        fwd_wr = parse_float(r.get('Forward WR', r.get('fwd_wr', '')))
        
        asset_class = parse_str(r.get('Asset Class', 'UNKNOWN')).upper()
        if not asset_class or asset_class in ('', 'N/A'):
            # Infer from symbol
            symbol = parse_str(r.get('Symbol', ''))
            if any(x in symbol for x in ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']):
                asset_class = 'CRYPTO'
            elif any(x in symbol for x in ['EUR', 'USD', 'GBP', 'JPY']):
                asset_class = 'FOREX'
            elif any(x in symbol for x in ['GC', 'CL', 'NG', 'SI']):
                asset_class = 'COMMODITY'
            elif any(x in symbol for x in ['AAPL', 'TSLA', 'SPY', 'QQQ']):
                asset_class = 'EQUITY'
        
        if pnl is not None:
            parsed_trades.append({
                'pnl': pnl,
                'score': score,
                'trust': trust,
                'fwd_wr': fwd_wr,
                'asset_class': asset_class if asset_class else 'UNKNOWN',
                'symbol': parse_str(r.get('Symbol', 'UNKNOWN')),
                'direction': parse_str(r.get('Direction', 'LONG')).upper(),
                'system': parse_str(r.get('System', 'unknown')),
                'strategy': parse_str(r.get('Strategy', 'unknown')),
                'grade': parse_str(r.get('Grade', '')),
            })
    
    print(f"Successfully parsed {len(parsed_trades)} trades")
    return perform_deep_analysis(parsed_trades)


def perform_deep_analysis(trades: List[Dict]) -> Dict:
    """Perform comprehensive asset class analysis."""
    
    results = {
        'total_trades': len(trades),
        'by_asset_class': {},
        'scoring_analysis': {},
        'edges': [],
        'flaws': [],
        'recommendations': []
    }
    
    # Group by asset class
    by_asset = defaultdict(list)
    for t in trades:
        by_asset[t['asset_class']].append(t)
    
    # Analyze each asset class
    for asset, asset_trades in by_asset.items():
        if len(asset_trades) < 5:
            continue
        
        pnls = [t['pnl'] for t in asset_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        # Basic metrics
        metrics = {
            'count': len(asset_trades),
            'avg_pnl': statistics.mean(pnls),
            'median_pnl': statistics.median(pnls),
            'win_rate': len(wins) / len(pnls) * 100 if pnls else 0,
            'profit_factor': abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf'),
            'total_pnl': sum(pnls),
            'std_dev': statistics.stdev(pnls) if len(pnls) > 1 else 0,
            'max_win': max(pnls) if pnls else 0,
            'max_loss': min(pnls) if pnls else 0,
            'avg_win': statistics.mean(wins) if wins else 0,
            'avg_loss': statistics.mean(losses) if losses else 0,
        }
        
        # Direction breakdown
        longs = [t for t in asset_trades if t['direction'] == 'LONG']
        shorts = [t for t in asset_trades if t['direction'] == 'SHORT']
        
        if longs:
            long_pnls = [t['pnl'] for t in longs]
            metrics['long_wr'] = sum(1 for p in long_pnls if p > 0) / len(long_pnls) * 100
            metrics['long_avg'] = statistics.mean(long_pnls)
        
        if shorts:
            short_pnls = [t['pnl'] for t in shorts]
            metrics['short_wr'] = sum(1 for p in short_pnls if p > 0) / len(short_pnls) * 100
            metrics['short_avg'] = statistics.mean(short_pnls)
        
        # Scoring analysis
        scored_trades = [t for t in asset_trades if t['score'] is not None]
        if scored_trades:
            score_buckets = defaultdict(list)
            for t in scored_trades:
                s = t['score']
                if s >= 80:
                    bucket = '80-100'
                elif s >= 60:
                    bucket = '60-79'
                elif s >= 40:
                    bucket = '40-59'
                else:
                    bucket = '0-39'
                score_buckets[bucket].append(t['pnl'])
            
            metrics['score_correlation'] = {}
            for bucket, bucket_pnls in score_buckets.items():
                if bucket_pnls:
                    metrics['score_correlation'][bucket] = {
                        'count': len(bucket_pnls),
                        'avg_pnl': statistics.mean(bucket_pnls),
                        'wr': sum(1 for p in bucket_pnls if p > 0) / len(bucket_pnls) * 100
                    }
        
        # Trust score analysis
        trusted_trades = [t for t in asset_trades if t['trust'] is not None]
        if trusted_trades:
            high_trust = [t['pnl'] for t in trusted_trades if t['trust'] >= 7]
            low_trust = [t['pnl'] for t in trusted_trades if t['trust'] < 5]
            
            if high_trust:
                metrics['high_trust_avg'] = statistics.mean(high_trust)
                metrics['high_trust_wr'] = sum(1 for p in high_trust if p > 0) / len(high_trust) * 100
            if low_trust:
                metrics['low_trust_avg'] = statistics.mean(low_trust)
                metrics['low_trust_wr'] = sum(1 for p in low_trust if p > 0) / len(low_trust) * 100
        
        results['by_asset_class'][asset] = metrics
    
    # Identify edges
    results['edges'] = identify_edges(results['by_asset_class'])
    
    # Identify flaws
    results['flaws'] = identify_flaws(results['by_asset_class'])
    
    # Generate recommendations
    results['recommendations'] = generate_recommendations(results)
    
    return results


def identify_edges(by_asset: Dict) -> List[Dict]:
    """Identify edge opportunities."""
    edges = []
    
    for asset, metrics in by_asset.items():
        # Edge: High win rate asset class
        if metrics['win_rate'] > 55:
            edges.append({
                'type': 'asset_class_performance',
                'asset': asset,
                'edge': f"{metrics['win_rate']:.1f}% win rate",
                'avg_pnl': f"{metrics['avg_pnl']:+.2f}%",
                'action': f"Increase {asset} allocation"
            })
        
        # Edge: Short bias in asset
        if 'short_wr' in metrics and metrics['short_wr'] > 60:
            edges.append({
                'type': 'direction_bias',
                'asset': asset,
                'edge': f"SHORT {metrics['short_wr']:.1f}% WR vs LONG {metrics.get('long_wr', 0):.1f}%",
                'action': f"Favor SHORT in {asset}"
            })
        
        # Edge: Score correlation
        if 'score_correlation' in metrics:
            sc = metrics['score_correlation']
            if '80-100' in sc and '60-79' in sc:
                if sc['60-79']['avg_pnl'] > sc['80-100']['avg_pnl']:
                    edges.append({
                        'type': 'scoring_inversion',
                        'asset': asset,
                        'edge': f"Score 60-79 outperforms 80+ ({sc['60-79']['avg_pnl']:+.2f}% vs {sc['80-100']['avg_pnl']:+.2f}%)",
                        'action': f"Recalibrate {asset} scoring weights"
                    })
        
        # Edge: High trust performance
        if 'high_trust_avg' in metrics and metrics['high_trust_avg'] > metrics['avg_pnl']:
            edges.append({
                'type': 'trust_validation',
                'asset': asset,
                'edge': f"High trust outperforms: {metrics['high_trust_avg']:+.2f}% vs {metrics['avg_pnl']:+.2f}%",
                'action': f"Trust scores WORK for {asset} - maintain system"
            })
    
    return edges


def identify_flaws(by_asset: Dict) -> List[Dict]:
    """Identify scoring system flaws."""
    flaws = []
    
    for asset, metrics in by_asset.items():
        # Flaw: Poor overall performance
        if metrics['win_rate'] < 45:
            flaws.append({
                'type': 'asset_underperformance',
                'asset': asset,
                'flaw': f"{metrics['win_rate']:.1f}% WR, {metrics['avg_pnl']:+.2f}% avg",
                'severity': 'HIGH',
                'action': f"Reduce {asset} exposure or improve filtering"
            })
        
        # Flaw: Inverted score correlation
        if 'score_correlation' in metrics:
            sc = metrics['score_correlation']
            if '80-100' in sc and sc['80-100']['avg_pnl'] < 0:
                flaws.append({
                    'type': 'score_miscalibration',
                    'asset': asset,
                    'flaw': f"Score 80+ showing {sc['80-100']['avg_pnl']:+.2f}% (should be positive)",
                    'severity': 'CRITICAL',
                    'action': f"Emergency recalibration for {asset}"
                })
        
        # Flaw: Long bias failing
        if 'long_wr' in metrics and metrics['long_wr'] < 40 and metrics.get('short_wr', 0) > 50:
            flaws.append({
                'type': 'direction_mismatch',
                'asset': asset,
                'flaw': f"LONG {metrics['long_wr']:.1f}% WR vs SHORT {metrics['short_wr']:.1f}% WR",
                'severity': 'HIGH',
                'action': f"Invert {asset} direction bias to SHORT"
            })
        
        # Flaw: Trust scores not predictive
        if 'high_trust_avg' in metrics and 'low_trust_avg' in metrics:
            if metrics['high_trust_avg'] <= metrics['low_trust_avg']:
                flaws.append({
                    'type': 'trust_failure',
                    'asset': asset,
                    'flaw': f"High trust {metrics['high_trust_avg']:+.2f}% <= Low trust {metrics['low_trust_avg']:+.2f}%",
                    'severity': 'MEDIUM',
                    'action': f"Recalibrate trust scoring for {asset}"
                })
    
    return flaws


def generate_recommendations(results: Dict) -> List[Dict]:
    """Generate optimization recommendations."""
    recommendations = []
    
    by_asset = results['by_asset_class']
    
    # Rank asset classes
    ranked = sorted(by_asset.items(), key=lambda x: x[1]['avg_pnl'], reverse=True)
    
    recommendations.append({
        'priority': 'P0',
        'category': 'asset_allocation',
        'recommendation': f"Increase {ranked[0][0]} to 60% of portfolio (best performer: {ranked[0][1]['avg_pnl']:+.2f}%)",
        'rationale': f"Top asset class outperforms by {ranked[0][1]['avg_pnl'] - ranked[-1][1]['avg_pnl']:+.2f}%"
    })
    
    if len(ranked) > 1 and ranked[-1][1]['avg_pnl'] < -2:
        recommendations.append({
            'priority': 'P0',
            'category': 'asset_blacklist',
            'recommendation': f"Reduce {ranked[-1][0]} to <10% or blacklist",
            'rationale': f"Severe underperformance: {ranked[-1][1]['avg_pnl']:+.2f}% avg, {ranked[-1][1]['win_rate']:.1f}% WR"
        })
    
    # Score calibration recommendations
    for asset, metrics in by_asset.items():
        if 'score_correlation' in metrics:
            sc = metrics['score_correlation']
            if '80-100' in sc and '60-79' in sc:
                if sc['60-79']['avg_pnl'] > sc['80-100']['avg_pnl']:
                    recommendations.append({
                        'priority': 'P1',
                        'category': 'scoring_calibration',
                        'recommendation': f"Reduce {asset} score weights by 20%",
                        'rationale': f"Scores overvaluing picks: 60-79 band beats 80+ band"
                    })
    
    return recommendations


def generate_synthetic_analysis() -> Dict:
    """Generate synthetic data for demonstration."""
    import random
    random.seed(42)
    
    trades = []
    
    # CRYPTO: Mixed, slight positive, SHORT bias
    for i in range(800):
        direction = random.choice(['LONG', 'SHORT'])
        base_pnl = random.gauss(0.5, 4) if direction == 'SHORT' else random.gauss(-0.8, 3.5)
        trades.append({
            'pnl': base_pnl,
            'score': random.randint(40, 100),
            'trust': random.uniform(3, 9),
            'asset_class': 'CRYPTO',
            'direction': direction,
            'system': random.choice(['alpha', 'battleground', 'mercury']),
        })
    
    # EQUITY: Poor performance
    for i in range(200):
        direction = random.choice(['LONG', 'SHORT'])
        base_pnl = random.gauss(-3.5, 5) if direction == 'LONG' else random.gauss(-1, 4)
        trades.append({
            'pnl': base_pnl,
            'score': random.randint(50, 95),
            'trust': random.uniform(4, 8),
            'asset_class': 'EQUITY',
            'direction': direction,
            'system': random.choice(['alpha', 'pm_kalshi']),
        })
    
    # FOREX: Neutral
    for i in range(150):
        direction = random.choice(['LONG', 'SHORT'])
        base_pnl = random.gauss(-0.2, 2.5)
        trades.append({
            'pnl': base_pnl,
            'score': random.randint(45, 90),
            'trust': random.uniform(3, 8),
            'asset_class': 'FOREX',
            'direction': direction,
            'system': random.choice(['alpha', 'multi_asset']),
        })
    
    return perform_deep_analysis(trades)


def print_detailed_report(results: Dict):
    """Print comprehensive report."""
    print("\n" + "=" * 100)
    print("DEEP ASSET CLASS ANALYSIS")
    print("=" * 100)
    print(f"Total Trades Analyzed: {results['total_trades']}\n")
    
    # Asset class comparison
    print("ASSET CLASS PERFORMANCE COMPARISON")
    print("-" * 100)
    print(f"{'Asset':<15} {'Count':>7} {'Avg PnL':>10} {'WR':>8} {'PF':>6} {'Total':>12} {'Sharpe':>8}")
    print("-" * 100)
    
    for asset, metrics in sorted(results['by_asset_class'].items(), 
                                  key=lambda x: x[1]['avg_pnl'], reverse=True):
        sharpe = metrics['avg_pnl'] / metrics['std_dev'] if metrics['std_dev'] > 0 else 0
        print(f"{asset:<15} {metrics['count']:>7} {metrics['avg_pnl']:>+9.2f}% "
              f"{metrics['win_rate']:>7.1f}% {metrics['profit_factor']:>6.2f} "
              f"{metrics['total_pnl']:>+11.2f}% {sharpe:>8.2f}")
    
    # Direction breakdown
    print("\n" + "-" * 100)
    print("DIRECTION BREAKDOWN BY ASSET")
    print("-" * 100)
    print(f"{'Asset':<15} {'LONG WR':>10} {'LONG Avg':>12} {'SHORT WR':>10} {'SHORT Avg':>12}")
    print("-" * 100)
    
    for asset, metrics in results['by_asset_class'].items():
        long_wr = metrics.get('long_wr', 0)
        long_avg = metrics.get('long_avg', 0)
        short_wr = metrics.get('short_wr', 0)
        short_avg = metrics.get('short_avg', 0)
        print(f"{asset:<15} {long_wr:>9.1f}% {long_avg:>+11.2f}% {short_wr:>9.1f}% {short_avg:>+11.2f}%")
    
    # Score correlation
    print("\n" + "-" * 100)
    print("SCORE CORRELATION ANALYSIS")
    print("-" * 100)
    
    for asset, metrics in results['by_asset_class'].items():
        if 'score_correlation' in metrics:
            print(f"\n{asset}:")
            for bucket, data in sorted(metrics['score_correlation'].items()):
                print(f"  Score {bucket}: {data['count']:>4} trades, {data['avg_pnl']:>+7.2f}% avg, {data['wr']:>5.1f}% WR")
    
    # Edges
    print("\n" + "=" * 100)
    print("IDENTIFIED EDGES")
    print("=" * 100)
    
    for edge in results['edges']:
        emoji = "[+]" if edge['type'] == 'asset_class_performance' else "[*]"
        print(f"{emoji} {edge['asset']} - {edge['edge']}")
        print(f"   Action: {edge['action']}")
    
    # Flaws
    print("\n" + "=" * 100)
    print("IDENTIFIED FLAWS")
    print("=" * 100)
    
    for flaw in sorted(results['flaws'], key=lambda x: x['severity']):
        emoji = "[CRIT]" if flaw['severity'] == 'CRITICAL' else "[HIGH]" if flaw['severity'] == 'HIGH' else "[MED]"
        print(f"{emoji} [{flaw['severity']}] {flaw['asset']} - {flaw['type']}")
        print(f"   Issue: {flaw['flaw']}")
        print(f"   Fix: {flaw['action']}")
    
    # Recommendations
    print("\n" + "=" * 100)
    print("RECOMMENDATIONS")
    print("=" * 100)
    
    for rec in sorted(results['recommendations'], key=lambda x: x['priority']):
        emoji = "[P0]" if rec['priority'] == 'P0' else "[P1]" if rec['priority'] == 'P1' else "[P2]"
        print(f"{emoji} [{rec['priority']}] {rec['category'].upper()}")
        print(f"   {rec['recommendation']}")
        print(f"   Why: {rec['rationale']}")
    
    print("=" * 100)
    
    return results


if __name__ == '__main__':
    results = analyze_by_asset_class()
    print_detailed_report(results)
    
    # Save to JSON
    with open('asset_class_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print("\nResults saved to: asset_class_analysis_results.json")
