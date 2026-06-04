#!/usr/bin/env python3
"""
Edge Analysis - Find patterns in active, closed, and smart picks
"""
import json
import statistics
from collections import defaultdict
from datetime import datetime

def load_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return []

def analyze_edge():
    # Load all data
    active = load_json('alpha_engine/data/active_picks.json')
    closed = load_json('alpha_engine/data/closed_picks.json')
    smart = load_json('alpha_engine/data/smart_picks.json')
    resolved = load_json('audit_trail/data/universal_resolved_picks.json')
    
    print("=" * 100)
    print("EDGE ANALYSIS - PATTERN DISCOVERY")
    print("=" * 100)
    
    # Smart picks analysis
    print("\n[1] SMART PICKS ANALYSIS")
    print("-" * 100)
    if isinstance(smart, dict) and 'picks' in smart:
        smart_picks = smart['picks']
        print(f"Total Smart Picks: {len(smart_picks)}")
        for pick in smart_picks:
            print(f"  {pick['symbol']} ({pick['direction']}): Elite={pick.get('elite_score', 'N/A')}, "
                  f"PnL={pick.get('pnl_pct', 'N/A'):+.2f}%, Trust={pick.get('trust_tier', 'N/A')}, "
                  f"Age={pick.get('age_hours', 'N/A'):.1f}h")
    
    # Active picks by asset class
    print("\n[2] ACTIVE PICKS BY ASSET CLASS")
    print("-" * 100)
    by_asset_active = defaultdict(list)
    for pick in active:
        asset = pick.get('asset_class', pick.get('category', 'UNKNOWN')).upper()
        by_asset_active[asset].append(pick)
    
    for asset, picks in sorted(by_asset_active.items(), key=lambda x: len(x[1]), reverse=True):
        avg_elite = statistics.mean([p.get('elite_score', 0) for p in picks]) if picks else 0
        avg_conf = statistics.mean([p.get('confidence', 0) for p in picks]) if picks else 0
        print(f"\n  {asset}: {len(picks)} picks")
        print(f"    Avg Elite Score: {avg_elite:.1f}")
        print(f"    Avg Confidence: {avg_conf:.2f}")
        
        # Direction breakdown
        longs = [p for p in picks if p.get('direction') == 'LONG']
        shorts = [p for p in picks if p.get('direction') == 'SHORT']
        print(f"    Direction: {len(longs)} LONG, {len(shorts)} SHORT")
        
        # Top picks
        print(f"    Top by Elite Score:")
        for p in sorted(picks, key=lambda x: x.get('elite_score', 0), reverse=True)[:3]:
            print(f"      {p.get('symbol', 'N/A')}: {p.get('elite_score', 0):.0f} ({p.get('elite_grade', 'N/A')}) - {p.get('direction', 'N/A')}")
    
    # Closed picks deep analysis
    print("\n[3] CLOSED PICKS - EDGE DISCOVERY")
    print("-" * 100)
    print(f"Total Closed Picks: {len(closed)}")
    
    # By exit reason
    by_exit = defaultdict(list)
    for pick in closed:
        reason = pick.get('exit_reason', 'UNKNOWN')
        by_exit[reason].append(pick)
    
    print("\n  Performance by Exit Reason:")
    for reason, picks in sorted(by_exit.items(), key=lambda x: len(x[1]), reverse=True):
        avg_pnl = statistics.mean([p.get('pnl_pct', 0) for p in picks]) if picks else 0
        win_rate = sum(1 for p in picks if (p.get('pnl_pct') or 0) > 0) / len(picks) * 100 if picks else 0
        print(f"    {reason}: {len(picks)} picks, Avg PnL={avg_pnl:+.3f}%, WR={win_rate:.1f}%")
    
    # By asset class
    print("\n  Performance by Asset Class (Closed Picks):")
    by_asset_closed = defaultdict(list)
    for pick in closed:
        asset = pick.get('asset_class', pick.get('category', 'UNKNOWN')).upper()
        by_asset_closed[asset].append(pick)
    
    for asset, picks in sorted(by_asset_closed.items(), key=lambda x: len(x[1]), reverse=True):
        if len(picks) < 5:
            continue
        pnls = [p.get('pnl_pct', 0) for p in picks]
        avg_pnl = statistics.mean(pnls)
        win_rate = sum(1 for p in pnls if p > 0) / len(pnls) * 100
        profit_factor = abs(sum(p for p in pnls if p > 0) / sum(p for p in pnls if p < 0)) if any(p < 0 for p in pnls) else float('inf')
        
        # Direction breakdown
        longs = [p for p in picks if p.get('direction', '').upper() == 'LONG' or p.get('signal_type', '').upper() == 'LONG']
        shorts = [p for p in picks if p.get('direction', '').upper() == 'SHORT' or p.get('signal_type', '').upper() == 'SHORT']
        
        long_wr = sum(1 for p in longs if (p.get('pnl_pct') or 0) > 0) / len(longs) * 100 if longs else 0
        short_wr = sum(1 for p in shorts if (p.get('pnl_pct') or 0) > 0) / len(shorts) * 100 if shorts else 0
        
        print(f"\n    {asset}: {len(picks)} picks")
        print(f"      Avg PnL: {avg_pnl:+.3f}%")
        print(f"      Win Rate: {win_rate:.1f}%")
        print(f"      Profit Factor: {profit_factor:.2f}")
        print(f"      LONG WR: {long_wr:.1f}% ({len(longs)} picks)")
        print(f"      SHORT WR: {short_wr:.1f}% ({len(shorts)} picks)")
        
        # Mode analysis
        by_mode = defaultdict(list)
        for p in picks:
            mode = p.get('mode', 'UNKNOWN')
            by_mode[mode].append(p)
        print(f"      By Mode:")
        for mode, mode_picks in sorted(by_mode.items(), key=lambda x: len(x[1]), reverse=True):
            mode_pnl = statistics.mean([p.get('pnl_pct', 0) for p in mode_picks])
            mode_wr = sum(1 for p in mode_picks if (p.get('pnl_pct') or 0) > 0) / len(mode_picks) * 100
            print(f"        {mode}: {len(mode_picks)} picks, {mode_pnl:+.3f}%, WR={mode_wr:.1f}%")
    
    # By source system
    print("\n  Performance by Source System:")
    by_source = defaultdict(list)
    for pick in closed + resolved[:500]:  # Include resolved picks too
        source = pick.get('source_system', pick.get('source', 'UNKNOWN'))
        by_source[source].append(pick)
    
    source_stats = []
    for source, picks in by_source.items():
        if len(picks) < 5:
            continue
        pnls = [p.get('pnl_pct', 0) for p in picks]
        avg_pnl = statistics.mean(pnls)
        win_rate = sum(1 for p in pnls if p > 0) / len(pnls) * 100
        source_stats.append((source, len(picks), avg_pnl, win_rate))
    
    source_stats.sort(key=lambda x: x[2], reverse=True)
    for source, count, avg_pnl, wr in source_stats[:15]:
        print(f"    {source[:40]:<40} {count:>4} picks  {avg_pnl:>+7.3f}%  WR={wr:>5.1f}%")
    
    # By strategy
    print("\n  Performance by Strategy:")
    by_strategy = defaultdict(list)
    for pick in closed:
        strategy = pick.get('strategy', 'UNKNOWN')
        by_strategy[strategy].append(pick)
    
    strat_stats = []
    for strategy, picks in by_strategy.items():
        if len(picks) < 5:
            continue
        pnls = [p.get('pnl_pct', 0) for p in picks]
        avg_pnl = statistics.mean(pnls)
        win_rate = sum(1 for p in pnls if p > 0) / len(pnls) * 100
        strat_stats.append((strategy, len(picks), avg_pnl, win_rate))
    
    strat_stats.sort(key=lambda x: x[2], reverse=True)
    print("    Top 10 Strategies:")
    for strategy, count, avg_pnl, wr in strat_stats[:10]:
        print(f"      {strategy[:38]:<38} {count:>4} picks  {avg_pnl:>+7.3f}%  WR={wr:>5.1f}%")
    print("\n    Worst 5 Strategies:")
    for strategy, count, avg_pnl, wr in strat_stats[-5:]:
        print(f"      {strategy[:38]:<38} {count:>4} picks  {avg_pnl:>+7.3f}%  WR={wr:>5.1f}%")
    
    # Score correlation
    print("\n  Elite Score Correlation (Closed Picks):")
    score_buckets = {'A (80-100)': [], 'B (60-79)': [], 'C (40-59)': [], 'D (20-39)': [], 'F (0-19)': []}
    for pick in closed:
        score = pick.get('elite_score', 0)
        if score >= 80:
            score_buckets['A (80-100)'].append(pick.get('pnl_pct', 0))
        elif score >= 60:
            score_buckets['B (60-79)'].append(pick)
        elif score >= 40:
            score_buckets['C (40-59)'].append(pick.get('pnl_pct', 0))
        elif score >= 20:
            score_buckets['D (20-39)'].append(pick.get('pnl_pct', 0))
        else:
            score_buckets['F (0-19)'].append(pick.get('pnl_pct', 0))
    
    for bucket, pnls in score_buckets.items():
        if pnls:
            avg = statistics.mean(pnls) if isinstance(pnls[0], (int, float)) else statistics.mean([p.get('pnl_pct', 0) for p in pnls])
            wr = sum(1 for p in pnls if (p if isinstance(p, (int, float)) else p.get('pnl_pct', 0)) > 0) / len(pnls) * 100
            print(f"    {bucket}: {len(pnls)} picks, Avg={avg:+.3f}%, WR={wr:.1f}%")
    
    # Hold time analysis
    print("\n  Hold Time Analysis (Closed Picks):")
    hold_times = [p.get('hold_bars', 0) for p in closed if p.get('hold_bars')]
    if hold_times:
        print(f"    Avg Hold (bars): {statistics.mean(hold_times):.1f}")
        print(f"    Median Hold: {statistics.median(hold_times):.1f}")
        print(f"    Max Hold: {max(hold_times)}")
    
    # Best and worst individual picks
    print("\n  Best Closed Picks:")
    best_picks = sorted(closed, key=lambda x: x.get('pnl_pct', 0), reverse=True)[:10]
    for p in best_picks:
        print(f"    {p.get('symbol', 'N/A'):<12} {p.get('pnl_pct', 0):>+7.2f}%  {p.get('exit_reason', 'N/A'):<15} "
              f"{p.get('strategy', 'N/A')[:25]:<25} {p.get('source_system', 'N/A')[:20]}")
    
    print("\n  Worst Closed Picks:")
    worst_picks = sorted(closed, key=lambda x: x.get('pnl_pct', 0))[:10]
    for p in worst_picks:
        print(f"    {p.get('symbol', 'N/A'):<12} {p.get('pnl_pct', 0):>+7.2f}%  {p.get('exit_reason', 'N/A'):<15} "
              f"{p.get('strategy', 'N/A')[:25]:<25} {p.get('source_system', 'N/A')[:20]}")
    
    # Edge summary
    print("\n" + "=" * 100)
    print("[4] EDGE SUMMARY")
    print("=" * 100)
    
    edges = []
    
    # Asset class edge
    for asset, picks in by_asset_closed.items():
        if len(picks) >= 10:
            pnls = [p.get('pnl_pct', 0) for p in picks]
            avg = statistics.mean(pnls)
            if avg > 0.1:
                edges.append(f"{asset} shows positive expectancy: {avg:+.3f}% avg")
    
    # Direction edge
    all_longs = [p for p in closed if p.get('direction', '').upper() == 'LONG' or p.get('signal_type', '').upper() == 'LONG']
    all_shorts = [p for p in closed if p.get('direction', '').upper() == 'SHORT' or p.get('signal_type', '').upper() == 'SHORT']
    
    if all_longs and all_shorts:
        long_pnl = statistics.mean([p.get('pnl_pct', 0) for p in all_longs])
        short_pnl = statistics.mean([p.get('pnl_pct', 0) for p in all_shorts])
        if short_pnl > long_pnl:
            edges.append(f"SHORT bias edge: SHORT={short_pnl:+.3f}% vs LONG={long_pnl:+.3f}%")
    
    # Exit reason edge
    tp_exits = by_exit.get('TP', []) + by_exit.get('TP_HIT', [])
    sl_exits = by_exit.get('SL', []) + by_exit.get('SL_HIT', [])
    if tp_exits and sl_exits:
        tp_avg = statistics.mean([p.get('pnl_pct', 0) for p in tp_exits])
        sl_avg = statistics.mean([p.get('pnl_pct', 0) for p in sl_exits])
        edges.append(f"TP exits avg {tp_avg:+.3f}% vs SL exits avg {sl_avg:+.3f}%")
    
    # Mode edge
    if 'SCALP' in by_mode and 'POSITION' in by_mode:
        scalp_pnl = statistics.mean([p.get('pnl_pct', 0) for p in by_mode['SCALP']])
        pos_pnl = statistics.mean([p.get('pnl_pct', 0) for p in by_mode['POSITION']])
        if scalp_pnl > pos_pnl:
            edges.append(f"SCALP mode outperforms POSITION: {scalp_pnl:+.3f}% vs {pos_pnl:+.3f}%")
    
    print("\n  Identified Edges:")
    for edge in edges:
        print(f"    + {edge}")
    
    return {
        'by_asset_active': dict(by_asset_active),
        'by_asset_closed': dict(by_asset_closed),
        'by_source': dict(by_source),
        'by_strategy': dict(by_strategy),
        'edges': edges
    }

if __name__ == '__main__':
    results = analyze_edge()
    
    # Save results
    with open('edge_analysis_results.json', 'w') as f:
        json.dump({k: str(v) for k, v in results.items()}, f, indent=2)
    print("\n\nResults saved to: edge_analysis_results.json")
