#!/usr/bin/env python3
"""
Investigate TP/SL resolution bug v3.
Focused on: recent high TP rate, PnL mismatches, OHLCV time filtering.
"""

import os
import pymysql
import json
from datetime import datetime, timezone
from collections import defaultdict

DB_HOST = 'mysql.50webs.com'
DB_USER = 'ejaguiar1_stocks'
DB_NAME = 'ejaguiar1_stocks'


def connect():
    from tools.db_env import get_stocks_creds
    return pymysql.connect(
        **get_stocks_creds(),
        charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
    )

def check_recent_high_tp_rate():
    """Investigate the 75-92% TP rate on recent dates."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            print("=== RECENT HIGH TP RATE INVESTIGATION (2026-06-04 to 2026-06-05) ===")
            print()
            
            # Get all picks resolved on 2026-06-04 and 2026-06-05
            cur.execute("""
                SELECT 
                    o.pick_id, o.symbol, o.strategy, o.asset_class,
                    o.resolution_method, o.pnl_pct, o.resolved_at, o.resolver_version,
                    r.entry_price, r.take_profit, r.stop_loss, r.direction,
                    r.signal_timestamp, r.source_system
                FROM at_pick_outcomes o
                INNER JOIN at_raw_picks r 
                    ON o.symbol = r.symbol 
                    AND o.strategy = r.strategy
                    AND ABS(TIMESTAMPDIFF(MINUTE, o.resolved_at, r.signal_timestamp)) < 120
                WHERE o.resolution_method IN ('TP_HIT','SL_HIT')
                  AND DATE(o.resolved_at) IN ('2026-06-04', '2026-06-05')
                ORDER BY o.resolved_at DESC
            """)
            picks = cur.fetchall()
            
            tp_picks = [p for p in picks if p['resolution_method'] == 'TP_HIT']
            sl_picks = [p for p in picks if p['resolution_method'] == 'SL_HIT']
            
            print(f"Total picks on 2026-06-04/05: {len(picks)}")
            print(f"TP_HIT: {len(tp_picks)} ({len(tp_picks)/len(picks)*100:.1f}%)")
            print(f"SL_HIT: {len(sl_picks)} ({len(sl_picks)/len(picks)*100:.1f}%)")
            print()
            
            # Check R:R for these
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
            
            avg_rr_tp = sum(calc_rr(p)[0] for p in tp_picks if calc_rr(p)) / len([p for p in tp_picks if calc_rr(p)])
            avg_rr_sl = sum(calc_rr(p)[0] for p in sl_picks if calc_rr(p)) / len([p for p in sl_picks if calc_rr(p)])
            print(f"Average R:R for TP_HIT picks: {avg_rr_tp:.2f}")
            print(f"Average R:R for SL_HIT picks: {avg_rr_sl:.2f}")
            print()
            
            # Show specific examples of TP_HIT picks
            print("=== SPECIFIC TP_HIT EXAMPLES (2026-06-04/05) ===")
            for p in tp_picks[:20]:
                rr = calc_rr(p)
                print(f"  {p['symbol']} {p['direction']} {p['strategy']}")
                print(f"    entry={p['entry_price']:.6f} TP={p['take_profit']:.6f} SL={p['stop_loss']:.6f}")
                if rr:
                    print(f"    R:R={rr[0]:.2f} TP_dist={rr[1]:.2f}% SL_dist={rr[2]:.2f}%")
                print(f"    pnl={p['pnl_pct']:.2f}% resolved_at={p['resolved_at']} resolver={p['resolver_version']}")
            print()
            
            # Show SL_HIT picks
            print("=== SPECIFIC SL_HIT EXAMPLES (2026-06-04/05) ===")
            for p in sl_picks[:20]:
                rr = calc_rr(p)
                print(f"  {p['symbol']} {p['direction']} {p['strategy']}")
                print(f"    entry={p['entry_price']:.6f} TP={p['take_profit']:.6f} SL={p['stop_loss']:.6f}")
                if rr:
                    print(f"    R:R={rr[0]:.2f} TP_dist={rr[1]:.2f}% SL_dist={rr[2]:.2f}%")
                print(f"    pnl={p['pnl_pct']:.2f}% resolved_at={p['resolved_at']} resolver={p['resolver_version']}")
            print()
            
            return picks
    finally:
        conn.close()

def check_pnl_mismatch_root_cause():
    """Check if resolver is using clamped TP/SL instead of original values."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            print("=== PNL MISMATCH ROOT CAUSE ===")
            print()
            
            # The resolver code does TP/SL clamping:
            #   TP: 2-4% range
            #   SL: 1-2.5% range
            # Let's see if the at_pick_outcomes PnL matches clamped values
            
            cur.execute("""
                SELECT 
                    o.pick_id, o.symbol, o.strategy, o.resolution_method, o.pnl_pct,
                    r.entry_price, r.take_profit, r.stop_loss, r.direction
                FROM at_pick_outcomes o
                INNER JOIN at_raw_picks r 
                    ON o.symbol = r.symbol 
                    AND o.strategy = r.strategy
                    AND ABS(TIMESTAMPDIFF(MINUTE, o.resolved_at, r.signal_timestamp)) < 120
                WHERE o.resolution_method IN ('TP_HIT','SL_HIT')
                  AND o.resolved_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY RAND()
                LIMIT 200
            """)
            picks = cur.fetchall()
            
            clamped_matches = 0
            original_matches = 0
            neither_matches = 0
            
            for p in picks:
                entry = float(p['entry_price'] or 0)
                tp = float(p['take_profit'] or 0)
                sl = float(p['stop_loss'] or 0)
                pnl = float(p['pnl_pct'] or 0)
                direction = p['direction']
                
                if entry <= 0 or not tp or not sl:
                    continue
                
                # Compute expected PnL from original TP/SL
                if direction == 'LONG':
                    orig_tp_pnl = (tp - entry) / entry * 100
                    orig_sl_pnl = (sl - entry) / entry * 100
                else:
                    orig_tp_pnl = (entry - tp) / entry * 100
                    orig_sl_pnl = (entry - sl) / entry * 100
                
                # Compute clamped TP/SL (resolver logic)
                tp_pct = abs(tp - entry) / entry * 100
                sl_pct = abs(sl - entry) / entry * 100
                
                clamped_tp = tp
                clamped_sl = sl
                
                # Clamp TP to 2-4%
                if tp_pct < 2.0:
                    if direction == 'LONG':
                        clamped_tp = round(entry * 1.025, 8)
                    else:
                        clamped_tp = round(entry * 0.975, 8)
                elif tp_pct > 4.0:
                    if direction == 'LONG':
                        clamped_tp = round(entry * 1.035, 8)
                    else:
                        clamped_tp = round(entry * 0.965, 8)
                
                # Clamp SL to 1-2.5%
                if sl_pct < 1.0:
                    if direction == 'LONG':
                        clamped_sl = round(entry * 0.99, 8)
                    else:
                        clamped_sl = round(entry * 1.01, 8)
                elif sl_pct > 2.5:
                    if direction == 'LONG':
                        clamped_sl = round(entry * 0.98, 8)
                    else:
                        clamped_sl = round(entry * 1.02, 8)
                
                # Compute expected PnL from clamped values
                if direction == 'LONG':
                    clamped_tp_pnl = (clamped_tp - entry) / entry * 100
                    clamped_sl_pnl = (clamped_sl - entry) / entry * 100
                else:
                    clamped_tp_pnl = (entry - clamped_tp) / entry * 100
                    clamped_sl_pnl = (entry - clamped_sl) / entry * 100
                
                if p['resolution_method'] == 'TP_HIT':
                    orig_diff = abs(pnl - orig_tp_pnl)
                    clamped_diff = abs(pnl - clamped_tp_pnl)
                else:
                    orig_diff = abs(pnl - orig_sl_pnl)
                    clamped_diff = abs(pnl - clamped_sl_pnl)
                
                if clamped_diff < 0.1:
                    clamped_matches += 1
                elif orig_diff < 0.1:
                    original_matches += 1
                else:
                    neither_matches += 1
            
            print(f"PnL matches CLAMPED TP/SL: {clamped_matches}")
            print(f"PnL matches ORIGINAL TP/SL: {original_matches}")
            print(f"PnL matches NEITHER: {neither_matches}")
            print()
            
            if clamped_matches > original_matches:
                print("VERDICT: Resolver is applying TP/SL CLAMPING before resolution!")
                print("This means original TP/SL from at_raw_picks are being overwritten.")
            else:
                print("VERDICT: PnL mostly matches original TP/SL (clamping may not be the main issue)")
            print()
            
    finally:
        conn.close()

def check_ohlcv_time_filtering():
    """Check if OHLCV bars are properly filtered by entry time."""
    print("=== OHLCV TIME FILTERING BUG CHECK ===")
    print()
    
    conn = connect()
    try:
        with conn.cursor() as cur:
            # Get a sample of recent TP_HIT picks with entry time
            cur.execute("""
                SELECT 
                    o.symbol, o.resolution_method, o.resolved_at,
                    r.signal_timestamp, r.entry_price, r.take_profit, r.stop_loss, r.direction
                FROM at_pick_outcomes o
                INNER JOIN at_raw_picks r 
                    ON o.symbol = r.symbol 
                    AND o.strategy = r.strategy
                    AND ABS(TIMESTAMPDIFF(MINUTE, o.resolved_at, r.signal_timestamp)) < 120
                WHERE o.resolution_method = 'TP_HIT'
                  AND o.resolved_at >= DATE_SUB(NOW(), INTERVAL 3 DAY)
                ORDER BY RAND()
                LIMIT 10
            """)
            picks = cur.fetchall()
            
            for p in picks:
                symbol = p['symbol']
                entry_time = p['signal_timestamp']
                
                if not entry_time:
                    continue
                
                # Get OHLCV bars for this symbol
                cur.execute("""
                    SELECT timestamp, open, high, low, close
                    FROM crypto_ohlcv
                    WHERE symbol = %s
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (symbol,))
                bars = cur.fetchall()
                
                if not bars:
                    continue
                
                print(f"\n{symbol} {p['direction']} entry={p['entry_price']:.6f} TP={p['take_profit']:.6f} SL={p['stop_loss']:.6f}")
                print(f"  Entry time: {entry_time} | Resolved: {p['resolved_at']}")
                print(f"  OHLCV bars: {len(bars)} (latest: {bars[0]['timestamp']}, earliest: {bars[-1]['timestamp']})")
                
                # Convert entry_time to timestamp for comparison
                entry_ts = entry_time.timestamp() if hasattr(entry_time, 'timestamp') else entry_time
                
                # Check if bars include data BEFORE entry time
                early_bars = [b for b in bars if b['timestamp'] < entry_ts]
                post_entry_bars = [b for b in bars if b['timestamp'] >= entry_ts]
                print(f"  Bars BEFORE entry time: {len(early_bars)}")
                print(f"  Bars AFTER entry time: {len(post_entry_bars)}")
                
                # Simulate what the resolver does (iterate ALL bars)
                tp_hit_all = False
                sl_hit_all = False
                for b in bars:
                    high = float(b['high'])
                    low = float(b['low'])
                    if p['direction'] == 'LONG':
                        if low <= p['stop_loss']:
                            sl_hit_all = True
                            break
                        if high >= p['take_profit']:
                            tp_hit_all = True
                            break
                    else:
                        if high >= p['stop_loss']:
                            sl_hit_all = True
                            break
                        if low <= p['take_profit']:
                            tp_hit_all = True
                            break
                
                print(f"  Scanning ALL bars: TP_HIT={tp_hit_all}, SL_HIT={sl_hit_all}")
                
                # Now simulate with proper time filtering
                tp_hit_post = False
                sl_hit_post = False
                for b in bars:
                    if b['timestamp'] < entry_ts:
                        continue
                    high = float(b['high'])
                    low = float(b['low'])
                    if p['direction'] == 'LONG':
                        if low <= p['stop_loss']:
                            sl_hit_post = True
                            break
                        if high >= p['take_profit']:
                            tp_hit_post = True
                            break
                    else:
                        if high >= p['stop_loss']:
                            sl_hit_post = True
                            break
                        if low <= p['take_profit']:
                            tp_hit_post = True
                            break
                
                print(f"  Scanning POST-ENTRY bars only: TP_HIT={tp_hit_post}, SL_HIT={sl_hit_post}")
                
                if sl_hit_all and not sl_hit_post:
                    print(f"  *** FALSE SL: Historical data shows SL hit, but not after entry! ***")
                if tp_hit_all and not tp_hit_post:
                    print(f"  *** FALSE TP: Historical data shows TP hit, but not after entry! ***")
                if (tp_hit_all != tp_hit_post) or (sl_hit_all != sl_hit_post):
                    print(f"  *** MISMATCH: Resolver gives different result with time filtering! ***")
    finally:
        conn.close()

def check_resolver_code_bug():
    """Document the exact code bugs found."""
    print("=== RESOLVER CODE BUGS ===")
    print()
    print("Bug 1: check_tp_sl() checks TP BEFORE SL (close-price fallback)")
    print("  File: audit_trail/universal_pick_resolver.py, lines 757-781")
    print("  Code:")
    print("    if direction == 'LONG':")
    print("        if tp and current_price >= tp:  # <-- TP checked FIRST")
    print("            return ('TP_HIT', tp, pnl)")
    print("        if sl and current_price <= sl:  # <-- SL checked SECOND")
    print("            return ('SL_HIT', sl, pnl)")
    print("  Impact: If both TP and SL levels are crossed (e.g., volatile bar),")
    print("          resolver returns TP_HIT even if SL was hit first.")
    print()
    print("Bug 2: _check_tp_sl_intrabar() does NOT filter bars by entry time")
    print("  File: audit_trail/universal_pick_resolver.py, lines 554-591")
    print("  The function receives ohlcv_bars from cache, which contains")
    print("  ALL recent bars (up to 48 hours for crypto, 5 days for stocks).")
    print("  It iterates ALL bars without checking if bar_time >= pick_timestamp.")
    print("  Impact: Historical bars from BEFORE pick creation can trigger false hits.")
    print()
    print("Bug 3: copy_trader_intel/outcome_resolver.py has same TP-first bug")
    print("  File: copy_trader_intel/outcome_resolver.py, lines 240-263")
    print("  Uses current price only (no OHLCV), checks TP before SL.")
    print()
    print("Bug 4: TP/SL CLAMPING modifies original levels before resolution")
    print("  File: audit_trail/universal_pick_resolver.py, lines 1218-1249")
    print("  Original TP/SL from pick are clamped to 2-4% TP / 1-2.5% SL.")
    print("  If original SL was wider (>2.5%), it gets narrowed, making SL hits MORE likely.")
    print("  This explains why PnL often doesn't match original TP/SL distances.")
    print()

def main():
    print("="*70)
    print("TP/SL RESOLUTION BUG INVESTIGATION v3")
    print("="*70)
    print()
    
    check_recent_high_tp_rate()
    check_pnl_mismatch_root_cause()
    check_ohlcv_time_filtering()
    check_resolver_code_bug()
    
    print("="*70)
    print("FINAL VERDICT")
    print("="*70)
    print()
    print("ROOT CAUSE HYPOTHESIS:")
    print()
    print("The user's reported 92.4% TP_HIT rate may be from a specific subset")
    print("(e.g., a single strategy with small sample size, or a specific date range).")
    print("However, the resolver code contains MULTIPLE bugs that create upward")
    print("bias in TP resolution:")
    print()
    print("1. CLOSE-PRICE FALLBACK CHECKS TP BEFORE SL")
    print("   - When intrabar OHLCV doesn't show a hit, fallback uses current close")
    print("   - If close >= TP (LONG), returns TP_HIT regardless of prior SL wick")
    print("   - This is the PRIMARY driver of TP bias when OHLCV cache misses")
    print()
    print("2. OHLCV BARS NOT FILTERED BY ENTRY TIME")
    print("   - _check_tp_sl_intrabar() scans ALL cached bars (up to 48h/5d)")
    print("   - Bars from BEFORE pick creation can trigger false TP/SL hits")
    print("   - If price hit TP in the past 48h, a new pick may instantly resolve as TP_HIT")
    print()
    print("3. TP/SL CLAMPING NARROWS ORIGINAL LEVELS")
    print("   - Original SL > 2.5% gets clamped down to 2.0-2.5%")
    print("   - Original TP < 2% gets widened to 2.5%")
    print("   - This changes the actual R:R from what the strategy intended")
    print("   - PnL mismatches prove clamping is active")
    print()
    print("4. COPY_TRADER RESOLVER HAS SAME TP-FIRST BUG")
    print("   - No OHLCV at all, only current price")
    print("   - TP checked before SL in all cases")
    print()
    print("RECOMMENDED FIXES:")
    print("A. In _check_tp_sl_intrabar(): filter bars where bar_time >= pick_timestamp")
    print("B. In check_tp_sl(): check SL BEFORE TP (conservative ordering)")
    print("C. Remove or make optional the TP/SL clamping (it distorts strategy intent)")
    print("D. In copy_trader resolver: check SL before TP, or add OHLCV support")
    print()

if __name__ == '__main__':
    main()
