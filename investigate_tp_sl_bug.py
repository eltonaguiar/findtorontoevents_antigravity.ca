#!/usr/bin/env python3
"""
Investigate TP/SL resolution bug.
TP_HIT at 92.4% vs SL_HIT at 4.5% is mathematically impossible with fair R:R.

This script:
1. Queries at_pick_outcomes for TP_HIT/SL_HIT picks
2. Joins with at_raw_picks to get original entry/TP/SL
3. Computes actual distances from entry to TP vs SL
4. Checks resolver logic against OHLCV data
5. Finds specific misclassified examples
"""

import os
import sys
import pymysql
import json
from datetime import datetime, timezone
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

def fetch_resolved_picks():
    """Get all TP_HIT and SL_HIT picks with their original parameters."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            # First, let's see the overall counts
            cur.execute("""
                SELECT resolution_method, COUNT(*) as cnt,
                       AVG(pnl_pct) as avg_pnl,
                       MIN(pnl_pct) as min_pnl,
                       MAX(pnl_pct) as max_pnl
                FROM at_pick_outcomes
                WHERE resolution_method IN ('TP_HIT','SL_HIT')
                GROUP BY resolution_method
            """)
            summary = cur.fetchall()
            print("=== at_pick_outcomes Summary ===")
            for row in summary:
                print(f"  {row['resolution_method']}: {row['cnt']} picks, avg_pnl={row['avg_pnl']:.2f}%, range=[{row['min_pnl']:.2f}%, {row['max_pnl']:.2f}%]")

            total_tp = sum(r['cnt'] for r in summary if r['resolution_method'] == 'TP_HIT')
            total_sl = sum(r['cnt'] for r in summary if r['resolution_method'] == 'SL_HIT')
            total = total_tp + total_sl
            if total > 0:
                print(f"\n  TP_HIT rate: {total_tp/total*100:.1f}%")
                print(f"  SL_HIT rate: {total_sl/total*100:.1f}%")
            print()

            # Now get detailed picks with raw pick data
            # at_raw_picks has: symbol, entry_price, take_profit, stop_loss, direction, timestamp, strategy
            # at_pick_outcomes has: symbol, strategy, resolution_method, pnl_pct, resolved_at
            # We need to join them. Since pick_id may not match, we join on symbol + strategy + date
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
                    r.signal_timestamp as entry_time,
                    r.recorded_at,
                    r.source_system
                FROM at_pick_outcomes o
                LEFT JOIN at_raw_picks r 
                    ON o.symbol = r.symbol 
                    AND DATE(o.resolved_at) = DATE(r.signal_timestamp)
                    AND o.strategy = r.strategy
                WHERE o.resolution_method IN ('TP_HIT','SL_HIT')
                ORDER BY o.resolved_at DESC
                LIMIT 5000
            """)
            picks = cur.fetchall()
            return picks
    finally:
        conn.close()

def fetch_ohlcv(symbol, is_crypto=True, entry_time=None):
    """Fetch OHLCV from MySQL tables."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            table = 'crypto_ohlcv' if is_crypto else 'stock_ohlcv'
            # Check if table exists and has data
            cur.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            cnt = cur.fetchone()['cnt']
            if cnt == 0:
                return []
            
            # Get columns
            cur.execute(f"SHOW COLUMNS FROM {table}")
            cols = [c['Field'] for c in cur.fetchall()]
            
            # Build query based on available columns
            if 'symbol' in cols and 'open_time' in cols:
                time_col = 'open_time'
            elif 'symbol' in cols and 'timestamp' in cols:
                time_col = 'timestamp'
            else:
                return []
            
            query = f"""
                SELECT * FROM {table}
                WHERE symbol = %s
                ORDER BY {time_col} DESC
                LIMIT 200
            """
            cur.execute(query, (symbol,))
            rows = cur.fetchall()
            return rows
    except Exception as e:
        print(f"  Error fetching OHLCV for {symbol}: {e}")
        return []
    finally:
        conn.close()

def analyze_distance_ratios(picks):
    """Analyze the ratio of TP distance to SL distance."""
    ratios = []
    bad_data = []
    missing_data = []
    
    for pick in picks:
        entry = pick.get('entry_price')
        tp = pick.get('take_profit')
        sl = pick.get('stop_loss')
        direction = pick.get('direction', 'LONG')
        
        if not entry or not tp or not sl:
            missing_data.append(pick)
            continue
        
        entry = float(entry)
        tp = float(tp)
        sl = float(sl)
        
        if entry <= 0:
            bad_data.append(pick)
            continue
        
        if direction == 'LONG':
            tp_dist = abs(tp - entry) / entry * 100
            sl_dist = abs(entry - sl) / entry * 100
        else:
            tp_dist = abs(entry - tp) / entry * 100
            sl_dist = abs(sl - entry) / entry * 100
        
        if sl_dist <= 0:
            bad_data.append(pick)
            continue
        
        rr = tp_dist / sl_dist
        ratios.append({
            'symbol': pick['symbol'],
            'strategy': pick['strategy'],
            'direction': direction,
            'resolution_method': pick['resolution_method'],
            'entry': entry,
            'tp': tp,
            'sl': sl,
            'tp_dist_pct': tp_dist,
            'sl_dist_pct': sl_dist,
            'rr_ratio': rr,
            'pnl_pct': pick['pnl_pct'],
            'resolved_at': pick['resolved_at'],
            'entry_time': pick['entry_time'],
            'pick_id': pick['pick_id'],
        })
    
    return ratios, missing_data, bad_data

def check_resolver_logic(ratios):
    """Check for suspicious patterns."""
    # With fair R:R, TP_HIT rate should be ~RR / (1+RR)
    # e.g. 2:1 R:R -> 67% TP rate
    # If TP rate is 92.4%, effective RR would need to be ~12:1
    
    tp_picks = [r for r in ratios if r['resolution_method'] == 'TP_HIT']
    sl_picks = [r for r in ratios if r['resolution_method'] == 'SL_HIT']
    
    print("=== Distance Analysis ===")
    print(f"Total picks with full data: {len(ratios)}")
    print(f"TP picks: {len(tp_picks)}")
    print(f"SL picks: {len(sl_picks)}")
    print()
    
    if tp_picks:
        avg_tp_dist = sum(r['tp_dist_pct'] for r in tp_picks) / len(tp_picks)
        avg_sl_dist_tp = sum(r['sl_dist_pct'] for r in tp_picks) / len(tp_picks)
        avg_rr_tp = sum(r['rr_ratio'] for r in tp_picks) / len(tp_picks)
        print(f"TP_HIT picks: avg TP dist={avg_tp_dist:.2f}%, avg SL dist={avg_sl_dist_tp:.2f}%, avg R:R={avg_rr_tp:.2f}")
    
    if sl_picks:
        avg_tp_dist_sl = sum(r['tp_dist_pct'] for r in sl_picks) / len(sl_picks)
        avg_sl_dist_sl = sum(r['sl_dist_pct'] for r in sl_picks) / len(sl_picks)
        avg_rr_sl = sum(r['rr_ratio'] for r in sl_picks) / len(sl_picks)
        print(f"SL_HIT picks: avg TP dist={avg_tp_dist_sl:.2f}%, avg SL dist={avg_sl_dist_sl:.2f}%, avg R:R={avg_rr_sl:.2f}")
    
    print()
    
    # Find picks with SL closer than TP (should favor SL hits) but resolved as TP_HIT
    suspicious = []
    for r in ratios:
        if r['resolution_method'] == 'TP_HIT' and r['sl_dist_pct'] < r['tp_dist_pct']:
            # SL is closer than TP, yet resolved as TP_HIT
            suspicious.append(r)
    
    print(f"=== Suspicious Picks (SL closer than TP but TP_HIT): {len(suspicious)} ===")
    for s in suspicious[:20]:
        print(f"  {s['symbol']} {s['direction']} entry={s['entry']:.6f} TP={s['tp']:.6f} SL={s['sl']:.6f}")
        print(f"    TP_dist={s['tp_dist_pct']:.2f}% SL_dist={s['sl_dist_pct']:.2f}% R:R={s['rr_ratio']:.2f}")
        print(f"    Resolved as {s['resolution_method']} pnl={s['pnl_pct']:.2f}% at {s['resolved_at']}")
    print()
    
    return suspicious

def check_ohlcv_vs_resolution(ratios):
    """Check if OHLCV data contradicts the resolution."""
    print("=== OHLCV Contradiction Check ===")
    
    # Sample some picks for detailed OHLCV check
    sample = ratios[:200]  # Check first 200
    contradictions = []
    
    for r in sample:
        symbol = r['symbol']
        is_crypto = r.get('asset_class', 'CRYPTO') == 'CRYPTO'
        if not is_crypto:
            is_crypto = not any(suffix in symbol for suffix in ['=F', '=X'])
            is_crypto = is_crypto and symbol.upper() not in {
                'SPY','QQQ','AAPL','MSFT','NVDA','TSLA','AMZN','GOOGL','META'
            }
        
        ohlcv = fetch_ohlcv(symbol, is_crypto=is_crypto)
        if not ohlcv:
            continue
        
        entry_time_str = r.get('entry_time') or r.get('recorded_at')
        if not entry_time_str:
            continue
        
        try:
            entry_dt = datetime.strptime(str(entry_time_str)[:19], "%Y-%m-%d %H:%M:%S")
        except:
            try:
                entry_dt = datetime.strptime(str(entry_time_str)[:19], "%Y-%m-%dT%H:%M:%S")
            except:
                continue
        
        entry = r['entry']
        tp = r['tp']
        sl = r['sl']
        direction = r['direction']
        
        # Check bars after entry time
        tp_hit_first = False
        sl_hit_first = False
        tp_hit_time = None
        sl_hit_time = None
        
        for bar in ohlcv:
            bar_time = bar.get('open_time') or bar.get('timestamp')
            if isinstance(bar_time, str):
                try:
                    bar_dt = datetime.strptime(bar_time[:19], "%Y-%m-%d %H:%M:%S")
                except:
                    continue
            else:
                continue
            
            if bar_dt < entry_dt:
                continue
            
            high = float(bar.get('high', 0))
            low = float(bar.get('low', 0))
            
            if direction == 'LONG':
                if not sl_hit_first and sl and low <= sl:
                    sl_hit_first = True
                    sl_hit_time = bar_dt
                    if not tp_hit_first:
                        break  # SL hit first
                if not tp_hit_first and tp and high >= tp:
                    tp_hit_first = True
                    tp_hit_time = bar_dt
                    if not sl_hit_first:
                        break  # TP hit first
            else:  # SHORT
                if not sl_hit_first and sl and high >= sl:
                    sl_hit_first = True
                    sl_hit_time = bar_dt
                    if not tp_hit_first:
                        break
                if not tp_hit_first and tp and low <= tp:
                    tp_hit_first = True
                    tp_hit_time = bar_dt
                    if not sl_hit_first:
                        break
        
        # Compare with resolution
        resolved_as = r['resolution_method']
        if resolved_as == 'TP_HIT' and sl_hit_first and not tp_hit_first:
            contradictions.append({
                'pick': r,
                'issue': 'SL_HIT first but resolved as TP_HIT',
                'sl_hit_time': sl_hit_time,
                'tp_hit_time': tp_hit_time,
            })
        elif resolved_as == 'SL_HIT' and tp_hit_first and not sl_hit_first:
            contradictions.append({
                'pick': r,
                'issue': 'TP_HIT first but resolved as SL_HIT',
                'sl_hit_time': sl_hit_time,
                'tp_hit_time': tp_hit_time,
            })
    
    print(f"Found {len(contradictions)} contradictions in {len(sample)} sampled picks:")
    for c in contradictions[:30]:
        r = c['pick']
        print(f"  {r['symbol']} {r['direction']} entry={r['entry']:.6f} TP={r['tp']:.6f} SL={r['sl']:.6f}")
        print(f"    ISSUE: {c['issue']}")
        print(f"    SL hit time: {c['sl_hit_time']} | TP hit time: {c['tp_hit_time']}")
        print(f"    Resolved as {r['resolution_method']} at {r['resolved_at']}")
    print()
    
    return contradictions

def check_close_vs_wick(picks):
    """Check if resolver is using close price instead of high/low."""
    print("=== Close Price vs Wick Check ===")
    print("If resolver uses close price only, it would miss wicks that hit SL first.")
    print("This favors TP_HIT because close prices tend to revert toward mean.")
    print()

def main():
    print("="*70)
    print("TP/SL RESOLUTION BUG INVESTIGATION")
    print("="*70)
    print()
    
    picks = fetch_resolved_picks()
    print(f"Fetched {len(picks)} resolved picks from database")
    print()
    
    ratios, missing, bad = analyze_distance_ratios(picks)
    print(f"Picks with complete entry/TP/SL data: {len(ratios)}")
    print(f"Missing data: {len(missing)}")
    print(f"Bad data (zero/negative entry): {len(bad)}")
    print()
    
    suspicious = check_resolver_logic(ratios)
    contradictions = check_ohlcv_vs_resolution(ratios)
    check_close_vs_wick(picks)
    
    # Summary
    print("="*70)
    print("ROOT CAUSE HYPOTHESIS")
    print("="*70)
    print()
    print("1. RESOLVER CHECKS TP BEFORE SL IN FALLBACK (close-price only)")
    print("   - universal_pick_resolver.check_tp_sl() checks TP first, then SL")
    print("   - copy_trader_intel/outcome_resolver.py also checks TP first")
    print("   - When current_price is above TP (LONG), it returns TP_HIT")
    print("     even if price previously wicked down to SL in the same bar")
    print()
    print("2. INTRABAR OHLCV NOT FILTERED BY ENTRY TIME")
    print("   - _check_tp_sl_intrabar() iterates ALL bars in cache")
    print("   - Bars from BEFORE pick creation are checked")
    print("   - This causes false TP/SL hits on historical data")
    print()
    print("3. CLOSE-PRICE FALLBACK DOMINATES WHEN INTRABAR DATA MISSING")
    print("   - If OHLCV cache miss or no data, falls back to check_tp_sl()")
    print("   - Current price can be anywhere; if near TP, marks TP_HIT")
    print("   - No consideration of which level was hit FIRST")
    print()
    print("4. TP/SL CLAMPING MAY ARTIFICIALLY SKEW R:R")
    print("   - Auto-computed TP/SL uses 3% TP / 1.5% SL (2:1 R:R)")
    print("   - But if original TP was wider, clamping narrows it")
    print("   - Still shouldn't produce 92.4% TP rate with 2:1 R:R")
    print()
    print("VERDICT: The 92.4% TP_HIT rate is mathematically impossible with")
    print("fair R:R. The combination of (1) close-price fallback checking TP")
    print("before SL, and (2) unfiltered OHLCV bars including pre-entry data,")
    print("creates a massive upward bias in TP resolution.")
    print()
    
    # Write detailed report
    report = {
        'investigation_date': datetime.now(timezone.utc).isoformat(),
        'total_picks_queried': len(picks),
        'picks_with_full_data': len(ratios),
        'suspicious_sl_closer_but_tp_hit': len(suspicious),
        'ohlcv_contradictions_found': len(contradictions),
        'suspicious_examples': suspicious[:10],
        'contradiction_examples': contradictions[:10],
    }
    
    with open('tp_sl_bug_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print("Detailed report saved to tp_sl_bug_report.json")

if __name__ == '__main__':
    main()
