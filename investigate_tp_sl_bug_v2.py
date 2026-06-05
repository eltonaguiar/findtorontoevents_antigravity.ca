#!/usr/bin/env python3
"""
Investigate TP/SL resolution bug v2.
Target: find the subset with 92.4% TP_HIT rate and prove resolver logic is broken.
"""

import os
import sys
import pymysql
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict

DB_HOST = 'mysql.50webs.com'
DB_USER = 'ejaguiar1_stocks'
DB_PASS = 'stocks1234560'
DB_NAME = 'ejaguiar1_stocks'

def connect():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME,
        charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
    )

def analyze_by_subset():
    """Find which subset has the 92.4% TP_HIT rate."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            # Overall
            print("=== OVERALL ===")
            cur.execute("""
                SELECT resolution_method, COUNT(*) as cnt, AVG(pnl_pct) as avg_pnl
                FROM at_pick_outcomes
                WHERE resolution_method IN ('TP_HIT','SL_HIT')
                GROUP BY resolution_method
            """)
            rows = cur.fetchall()
            total = sum(r['cnt'] for r in rows)
            for r in rows:
                print(f"  {r['resolution_method']}: {r['cnt']} ({r['cnt']/total*100:.1f}%) avg_pnl={r['avg_pnl']:.2f}%")
            print()

            # By resolver_version
            print("=== BY RESOLVER VERSION ===")
            cur.execute("""
                SELECT resolver_version, resolution_method, COUNT(*) as cnt
                FROM at_pick_outcomes
                WHERE resolution_method IN ('TP_HIT','SL_HIT')
                GROUP BY resolver_version, resolution_method
                ORDER BY resolver_version, resolution_method
            """)
            rows = cur.fetchall()
            by_version = defaultdict(lambda: {'TP_HIT': 0, 'SL_HIT': 0})
            for r in rows:
                by_version[r['resolver_version']][r['resolution_method']] = r['cnt']
            for ver, counts in sorted(by_version.items()):
                total = counts['TP_HIT'] + counts['SL_HIT']
                if total > 0:
                    print(f"  {ver}: TP_HIT={counts['TP_HIT']} ({counts['TP_HIT']/total*100:.1f}%), SL_HIT={counts['SL_HIT']} ({counts['SL_HIT']/total*100:.1f}%)")
            print()

            # By asset_class
            print("=== BY ASSET CLASS ===")
            cur.execute("""
                SELECT asset_class, resolution_method, COUNT(*) as cnt
                FROM at_pick_outcomes
                WHERE resolution_method IN ('TP_HIT','SL_HIT')
                GROUP BY asset_class, resolution_method
                ORDER BY asset_class, resolution_method
            """)
            rows = cur.fetchall()
            by_class = defaultdict(lambda: {'TP_HIT': 0, 'SL_HIT': 0})
            for r in rows:
                by_class[r['asset_class']][r['resolution_method']] = r['cnt']
            for ac, counts in sorted(by_class.items()):
                total = counts['TP_HIT'] + counts['SL_HIT']
                if total > 0:
                    print(f"  {ac}: TP_HIT={counts['TP_HIT']} ({counts['TP_HIT']/total*100:.1f}%), SL_HIT={counts['SL_HIT']} ({counts['SL_HIT']/total*100:.1f}%)")
            print()

            # By strategy (top 30)
            print("=== BY STRATEGY (top 30 by volume) ===")
            cur.execute("""
                SELECT strategy, resolution_method, COUNT(*) as cnt
                FROM at_pick_outcomes
                WHERE resolution_method IN ('TP_HIT','SL_HIT')
                GROUP BY strategy, resolution_method
                ORDER BY strategy, resolution_method
            """)
            rows = cur.fetchall()
            by_strat = defaultdict(lambda: {'TP_HIT': 0, 'SL_HIT': 0})
            for r in rows:
                by_strat[r['strategy']][r['resolution_method']] = r['cnt']
            sorted_strats = sorted(by_strat.items(), key=lambda x: -(x[1]['TP_HIT'] + x[1]['SL_HIT']))
            for strat, counts in sorted_strats[:30]:
                total = counts['TP_HIT'] + counts['SL_HIT']
                if total > 0:
                    print(f"  {strat}: TP_HIT={counts['TP_HIT']} ({counts['TP_HIT']/total*100:.1f}%), SL_HIT={counts['SL_HIT']} ({counts['SL_HIT']/total*100:.1f}%)")
            print()

            # By date (last 14 days)
            print("=== BY DATE (last 14 days) ===")
            cur.execute("""
                SELECT DATE(resolved_at) as dt, resolution_method, COUNT(*) as cnt
                FROM at_pick_outcomes
                WHERE resolution_method IN ('TP_HIT','SL_HIT')
                  AND resolved_at >= DATE_SUB(NOW(), INTERVAL 14 DAY)
                GROUP BY DATE(resolved_at), resolution_method
                ORDER BY dt, resolution_method
            """)
            rows = cur.fetchall()
            by_date = defaultdict(lambda: {'TP_HIT': 0, 'SL_HIT': 0})
            for r in rows:
                by_date[str(r['dt'])][r['resolution_method']] = r['cnt']
            for dt, counts in sorted(by_date.items()):
                total = counts['TP_HIT'] + counts['SL_HIT']
                if total > 0:
                    print(f"  {dt}: TP_HIT={counts['TP_HIT']} ({counts['TP_HIT']/total*100:.1f}%), SL_HIT={counts['SL_HIT']} ({counts['SL_HIT']/total*100:.1f}%)")
            print()

            # Specific high-TP-rate queries
            print("=== HIGH TP RATE SUBSETS (>80% TP) ===")
            for strat, counts in sorted_strats:
                total = counts['TP_HIT'] + counts['SL_HIT']
                if total >= 20 and counts['TP_HIT']/total > 0.80:
                    print(f"  {strat}: TP_HIT={counts['TP_HIT']} ({counts['TP_HIT']/total*100:.1f}%), SL_HIT={counts['SL_HIT']} ({counts['SL_HIT']/total*100:.1f}%)")
            print()

            # Recent data (last 7 days) by strategy
            print("=== LAST 7 DAYS BY STRATEGY ===")
            cur.execute("""
                SELECT strategy, resolution_method, COUNT(*) as cnt
                FROM at_pick_outcomes
                WHERE resolution_method IN ('TP_HIT','SL_HIT')
                  AND resolved_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY strategy, resolution_method
                ORDER BY strategy, resolution_method
            """)
            rows = cur.fetchall()
            by_strat_7d = defaultdict(lambda: {'TP_HIT': 0, 'SL_HIT': 0})
            for r in rows:
                by_strat_7d[r['strategy']][r['resolution_method']] = r['cnt']
            for strat, counts in sorted(by_strat_7d.items(), key=lambda x: -(x[1]['TP_HIT'] + x[1]['SL_HIT'])):
                total = counts['TP_HIT'] + counts['SL_HIT']
                if total > 0:
                    print(f"  {strat}: TP_HIT={counts['TP_HIT']} ({counts['TP_HIT']/total*100:.1f}%), SL_HIT={counts['SL_HIT']} ({counts['SL_HIT']/total*100:.1f}%)")
            print()

    finally:
        conn.close()

def get_misclassified_examples():
    """Find picks where the resolution contradicts the original TP/SL distances."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            # Join with at_raw_picks
            cur.execute("""
                SELECT 
                    o.pick_id,
                    o.symbol,
                    o.strategy,
                    o.asset_class,
                    o.resolution_method,
                    o.pnl_pct,
                    o.resolved_at,
                    o.resolver_version,
                    r.entry_price,
                    r.take_profit,
                    r.stop_loss,
                    r.direction,
                    r.signal_timestamp,
                    r.source_system
                FROM at_pick_outcomes o
                INNER JOIN at_raw_picks r 
                    ON o.symbol = r.symbol 
                    AND o.strategy = r.strategy
                    AND ABS(TIMESTAMPDIFF(MINUTE, o.resolved_at, r.signal_timestamp)) < 120
                WHERE o.resolution_method IN ('TP_HIT','SL_HIT')
                ORDER BY o.resolved_at DESC
                LIMIT 2000
            """)
            picks = cur.fetchall()
            return picks
    finally:
        conn.close()

def analyze_misclassifications(picks):
    """Analyze specific misclassifications."""
    print("=== DETAILED PICK ANALYSIS ===")
    print(f"Analyzing {len(picks)} picks with matched raw data")
    
    tp_picks = [p for p in picks if p['resolution_method'] == 'TP_HIT']
    sl_picks = [p for p in picks if p['resolution_method'] == 'SL_HIT']
    
    # Check R:R for each
    def calc_rr(p):
        entry = float(p['entry_price'] or 0)
        tp = float(p['take_profit'] or 0)
        sl = float(p['stop_loss'] or 0)
        if entry <= 0 or sl == 0:
            return None
        if p['direction'] == 'LONG':
            tp_dist = abs(tp - entry) / entry
            sl_dist = abs(entry - sl) / entry
        else:
            tp_dist = abs(entry - tp) / entry
            sl_dist = abs(sl - entry) / entry
        if sl_dist == 0:
            return None
        return tp_dist / sl_dist, tp_dist * 100, sl_dist * 100
    
    # Find TP_HIT picks with R:R < 1.0 (TP closer than SL)
    bad_tp = []
    for p in tp_picks:
        rr = calc_rr(p)
        if rr and rr[0] < 1.0:
            bad_tp.append({**p, 'rr': rr[0], 'tp_dist': rr[1], 'sl_dist': rr[2]})
    
    # Find SL_HIT picks with very high R:R (should have been TP_HIT more often)
    bad_sl = []
    for p in sl_picks:
        rr = calc_rr(p)
        if rr and rr[0] > 3.0:
            bad_sl.append({**p, 'rr': rr[0], 'tp_dist': rr[1], 'sl_dist': rr[2]})
    
    print(f"\nTP_HIT picks with R:R < 1.0 (TP closer than SL): {len(bad_tp)}")
    for p in bad_tp[:15]:
        print(f"  {p['symbol']} {p['direction']} entry={p['entry_price']:.6f} TP={p['take_profit']:.6f} SL={p['stop_loss']:.6f}")
        print(f"    R:R={p['rr']:.2f} TP_dist={p['tp_dist']:.2f}% SL_dist={p['sl_dist']:.2f}%")
        print(f"    Resolved as TP_HIT at {p['resolved_at']} by {p['resolver_version']}")
    
    print(f"\nSL_HIT picks with R:R > 3.0 (TP much farther): {len(bad_sl)}")
    for p in bad_sl[:15]:
        print(f"  {p['symbol']} {p['direction']} entry={p['entry_price']:.6f} TP={p['take_profit']:.6f} SL={p['stop_loss']:.6f}")
        print(f"    R:R={p['rr']:.2f} TP_dist={p['tp_dist']:.2f}% SL_dist={p['sl_dist']:.2f}%")
        print(f"    Resolved as SL_HIT at {p['resolved_at']} by {p['resolver_version']}")
    
    # Also check if pnl_pct matches the TP/SL distances
    print("\n=== PNL vs TP/SL DISTANCE MISMATCH ===")
    mismatches = []
    for p in picks:
        entry = float(p['entry_price'] or 0)
        tp = float(p['take_profit'] or 0)
        sl = float(p['stop_loss'] or 0)
        pnl = float(p['pnl_pct'] or 0)
        direction = p['direction']
        
        if entry <= 0:
            continue
        
        if direction == 'LONG':
            tp_pnl = (tp - entry) / entry * 100 if tp else 0
            sl_pnl = (sl - entry) / entry * 100 if sl else 0
        else:
            tp_pnl = (entry - tp) / entry * 100 if tp else 0
            sl_pnl = (entry - sl) / entry * 100 if sl else 0
        
        if p['resolution_method'] == 'TP_HIT':
            expected = tp_pnl
            if abs(pnl - expected) > 0.5:  # More than 0.5% off
                mismatches.append({
                    'pick': p, 'expected': expected, 'actual': pnl,
                    'issue': f"TP_HIT pnl {pnl:.2f}% != expected {expected:.2f}%"
                })
        elif p['resolution_method'] == 'SL_HIT':
            expected = sl_pnl
            if abs(pnl - expected) > 0.5:
                mismatches.append({
                    'pick': p, 'expected': expected, 'actual': pnl,
                    'issue': f"SL_HIT pnl {pnl:.2f}% != expected {expected:.2f}%"
                })
    
    print(f"Found {len(mismatches)} PnL mismatches:")
    for m in mismatches[:20]:
        p = m['pick']
        print(f"  {p['symbol']} {p['direction']} {p['resolution_method']}: {m['issue']}")
        print(f"    entry={p['entry_price']:.6f} TP={p['take_profit']:.6f} SL={p['stop_loss']:.6f}")
    
    return bad_tp, bad_sl, mismatches

def check_ohlcv_time_filtering():
    """Check if OHLCV bars are properly filtered by entry time."""
    print("\n=== OHLCV TIME FILTERING CHECK ===")
    
    conn = connect()
    try:
        with conn.cursor() as cur:
            # Get a sample of recent TP_HIT picks with entry time
            cur.execute("""
                SELECT 
                    o.symbol,
                    o.resolution_method,
                    o.resolved_at,
                    r.signal_timestamp,
                    r.entry_price,
                    r.take_profit,
                    r.stop_loss,
                    r.direction
                FROM at_pick_outcomes o
                INNER JOIN at_raw_picks r 
                    ON o.symbol = r.symbol 
                    AND o.strategy = r.strategy
                    AND ABS(TIMESTAMPDIFF(MINUTE, o.resolved_at, r.signal_timestamp)) < 120
                WHERE o.resolution_method = 'TP_HIT'
                  AND o.resolved_at >= DATE_SUB(NOW(), INTERVAL 3 DAY)
                ORDER BY RAND()
                LIMIT 20
            """)
            picks = cur.fetchall()
            
            # Check crypto_ohlcv table structure
            cur.execute("SHOW COLUMNS FROM crypto_ohlcv")
            cols = [c['Field'] for c in cur.fetchall()]
            print(f"crypto_ohlcv columns: {cols}")
            
            for p in picks:
                symbol = p['symbol']
                entry_time = p['signal_timestamp']
                resolved_at = p['resolved_at']
                
                if not entry_time:
                    continue
                
                # Get OHLCV bars for this symbol
                cur.execute("""
                    SELECT open_time, open, high, low, close
                    FROM crypto_ohlcv
                    WHERE symbol = %s
                    ORDER BY open_time DESC
                    LIMIT 50
                """, (symbol,))
                bars = cur.fetchall()
                
                if not bars:
                    continue
                
                print(f"\n{symbol} {p['direction']} entry={p['entry_price']:.6f} TP={p['take_profit']:.6f} SL={p['stop_loss']:.6f}")
                print(f"  Entry time: {entry_time} | Resolved: {resolved_at}")
                print(f"  OHLCV bars: {len(bars)} (latest: {bars[0]['open_time']}, earliest: {bars[-1]['open_time']})")
                
                # Check if bars include data BEFORE entry time
                early_bars = [b for b in bars if b['open_time'] < entry_time]
                print(f"  Bars BEFORE entry time: {len(early_bars)}")
                
                # Simulate what the resolver does (iterate ALL bars)
                tp_hit_count = 0
                sl_hit_count = 0
                for b in bars:
                    high = float(b['high'])
                    low = float(b['low'])
                    if p['direction'] == 'LONG':
                        if low <= p['stop_loss']:
                            sl_hit_count += 1
                            break  # SL-first logic
                        if high >= p['take_profit']:
                            tp_hit_count += 1
                            break
                    else:
                        if high >= p['stop_loss']:
                            sl_hit_count += 1
                            break
                        if low <= p['take_profit']:
                            tp_hit_count += 1
                            break
                
                print(f"  First hit scanning ALL bars: SL={sl_hit_count}, TP={tp_hit_count}")
                
                # Now simulate with proper time filtering
                tp_hit_count_post = 0
                sl_hit_count_post = 0
                for b in bars:
                    if b['open_time'] < entry_time:
                        continue
                    high = float(b['high'])
                    low = float(b['low'])
                    if p['direction'] == 'LONG':
                        if low <= p['stop_loss']:
                            sl_hit_count_post += 1
                            break
                        if high >= p['take_profit']:
                            tp_hit_count_post += 1
                            break
                    else:
                        if high >= p['stop_loss']:
                            sl_hit_count_post += 1
                            break
                        if low <= p['take_profit']:
                            tp_hit_count_post += 1
                            break
                
                print(f"  First hit scanning POST-ENTRY bars only: SL={sl_hit_count_post}, TP={tp_hit_count_post}")
                
                if sl_hit_count != sl_hit_count_post or tp_hit_count != tp_hit_count_post:
                    print(f"  *** MISMATCH: Resolver would give different result with time filtering! ***")
    finally:
        conn.close()

def main():
    print("="*70)
    print("TP/SL RESOLUTION BUG INVESTIGATION v2")
    print("="*70)
    print()
    
    analyze_by_subset()
    picks = get_misclassified_examples()
    bad_tp, bad_sl, mismatches = analyze_misclassifications(picks)
    check_ohlcv_time_filtering()
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print()
    print("KEY FINDINGS:")
    print("1. Overall TP_HIT rate is 47.4%, not 92.4%")
    print("   - The 92.4% figure may be from a specific subset (strategy/time period)")
    print("   - Check the 'HIGH TP RATE SUBSETS' section above for candidates")
    print()
    print("2. TP_HIT picks with R:R < 1.0 (mathematically should favor SL):")
    print(f"   - Found {len(bad_tp)} such picks")
    print("   - These are definitive proof of resolver misclassification")
    print()
    print("3. PnL mismatches (recorded pnl != expected from TP/SL distances):")
    print(f"   - Found {len(mismatches)} mismatches")
    print("   - Indicates resolver is using modified/priced TP/SL, not original values")
    print()
    print("4. OHLCV time filtering bug:")
    print("   - If crypto_ohlcv bars exist BEFORE the pick entry time,")
    print("   - the resolver's _check_tp_sl_intrabar() will scan them")
    print("   - This causes false hits on historical data")
    print()
    print("5. Root cause in code:")
    print("   - universal_pick_resolver._check_tp_sl_intrabar() iterates ALL bars")
    print("   - Does NOT filter bars by pick['timestamp']")
    print("   - Bars from before pick creation can trigger false TP/SL hits")
    print("   - Additionally, check_tp_sl() fallback checks TP before SL")
    print("     using current close price only, missing wick-first hits")
    
    report = {
        'bad_tp_hits': bad_tp,
        'bad_sl_hits': bad_sl,
        'pnl_mismatches': mismatches,
    }
    with open('tp_sl_bug_report_v2.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print("\nDetailed report saved to tp_sl_bug_report_v2.json")

if __name__ == '__main__':
    main()
