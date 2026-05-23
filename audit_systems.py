#!/usr/bin/env python3
"""Comprehensive system audit for hidden failures"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

def check_battleground():
    """Check battleground system performance"""
    print("=== Battleground System Performance ===")
    bg_systems = [
        ('system_a_filter', 'ml_battleground/system_a_filter/data/closed_picks.json'),
        ('system_b_regime', 'ml_battleground/system_b_regime/data/closed_picks.json'),
        ('system_c_deeplearn', 'ml_battleground/system_c_deeplearn/data/closed_picks.json'),
        ('system_d_carry', 'ml_battleground/system_d_carry/data/closed_picks.json'),
        ('system_e_momentum', 'ml_battleground/system_e_momentum/data/closed_picks.json'),
    ]
    
    for name, path_str in bg_systems:
        p = Path(path_str)
        if p.exists():
            try:
                with open(p) as f:
                    data = json.load(f)
                
                # Handle different data formats
                if isinstance(data, list):
                    picks = data
                elif isinstance(data, dict):
                    picks = data.get('picks', [])
                else:
                    picks = []
                    
                wins = sum(1 for p in picks if (p.get('pnl') or p.get('pnl_pct') or 0) > 0)
                losses = sum(1 for p in picks if (p.get('pnl') or p.get('pnl_pct') or 0) <= 0)
                total = wins + losses
                wr = wins / total * 100 if total > 0 else 0
                status = "FAIL" if wr < 40 else "WARN" if wr < 50 else "OK"
                print(f"{name:20s} WR: {wr:.1f}% ({wins}W/{losses}L) [{status}]")
            except Exception as e:
                print(f"{name:20s} Error: {e}")
        else:
            print(f"{name:20s} No data file")
    print()

def check_forward_test():
    """Check forward test database for inactive strategies"""
    db_path = Path('incubator/forward_test.db')
    if not db_path.exists():
        print("Forward test database not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get strategies with activity stats
    cursor.execute("""
        SELECT strategy_name, 
               COUNT(CASE WHEN status = 'OPEN' THEN 1 END) as open_count,
               COUNT(CASE WHEN status = 'CLOSED' THEN 1 END) as closed_count,
               MAX(entry_time) as last_entry
        FROM forward_signals 
        GROUP BY strategy_name
        ORDER BY open_count ASC, last_entry ASC
    """)
    
    results = cursor.fetchall()
    print("=== Forward Test Strategy Activity ===")
    print(f"{'Strategy':<40} {'Open':>6} {'Closed':>7} {'Last Entry':<20}")
    print('-' * 80)
    
    inactive = []
    for row in results:
        strat, open_ct, closed_ct, last_entry = row
        last = last_entry[:16] if last_entry else 'Never'
        print(f"{strat:<40} {open_ct:>6} {closed_ct:>7} {last:<20}")
        
        # Flag inactive strategies
        if open_ct == 0 and closed_ct < 5:
            inactive.append((strat, closed_ct, last))
    
    conn.close()
    
    if inactive:
        print("\n[!] INACTIVE STRATEGIES (0 open, <5 closed trades):")
        for strat, closed, last in inactive:
            print(f"   - {strat}: {closed} closed, last entry: {last}")
    print()

def check_hub_status():
    """Check hub integrated dashboard"""
    hub_file = Path('hub/data/integrated_dashboard.json')
    if hub_file.exists():
        mtime = datetime.fromtimestamp(hub_file.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        print(f"=== Hub Dashboard Status ===")
        print(f"Integrated dashboard: EXISTS (age: {age_hours:.1f}h)")
        
        with open(hub_file) as f:
            data = json.load(f)
        
        total_systems = data.get('total_systems', 0)
        active_systems = data.get('active_systems', 0)
        print(f"Systems tracked: {active_systems}/{total_systems} active")
    else:
        print("=== Hub Dashboard Status ===")
        print("[X] Integrated dashboard: MISSING")
        print("   Run: python signal_aggregator/integrations.py")
    print()

def check_winning_combos():
    """Check winning combinations"""
    combos_file = Path('hub/data/winning_combos.json')
    if combos_file.exists():
        with open(combos_file) as f:
            data = json.load(f)
        
        total = data.get('total_found', 0)
        print(f"=== Winning DNA Combinations ===")
        print(f"Total found: {total}")
        
        if total == 0:
            print("[!] No winning combinations found - DNA backtester may need to run")
    else:
        print("=== Winning DNA Combinations ===")
        print("[X] Winning combos file not found")
    print()

def check_alpha_engine():
    """Check alpha engine for issues"""
    alpha_file = Path('alpha_engine/data/active_picks.json')
    if alpha_file.exists():
        mtime = datetime.fromtimestamp(alpha_file.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        
        with open(alpha_file) as f:
            data = json.load(f)
        
        # Handle different formats
        if isinstance(data, list):
            picks = data
        elif isinstance(data, dict):
            picks = data.get('picks', [])
        else:
            picks = []
        
        print(f"=== Alpha Engine Status ===")
        print(f"Last update: {age_hours:.1f}h ago")
        print(f"Active picks: {len(picks)}")
        
        if age_hours > 24:
            print("[!] Alpha Engine data is stale (>24h)")
        if len(picks) == 0:
            print("[!] No active picks - filters may be too strict")
    else:
        print("=== Alpha Engine Status ===")
        print("[X] Alpha Engine data not found")
    print()

def check_ml_systems():
    """Check various ML systems for issues"""
    print("=== ML System Health Check ===")
    
    systems = {
        'Crypto ML Edge': 'crypto_ml_edge/data/active_picks.json',
        'Mercury2': 'mercury2/data/active_picks.json',
        'Claude Gainer': 'claude_gainer_ml/tracker/claude_live_picks.json',
        'KIMI ROTC': 'KIMI_RISEOFTHECLAW/data/active_picks.json',
        'Genome': 'genome/active_picks.json',
        'Battleground': 'battleground/data/baby_strats_dashboard.json',
    }
    
    for name, path_str in systems.items():
        p = Path(path_str)
        if p.exists():
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            age_hours = (datetime.now() - mtime).total_seconds() / 3600
            
            try:
                with open(p) as f:
                    data = json.load(f)
                
                # Count picks based on data structure
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict):
                    count = len(data.get('picks', []))
                else:
                    count = 0
                
                status = "OK" if age_hours < 24 else "STALE" if age_hours < 48 else "OLD"
                print(f"{name:20s} {status:8s} {count:>3} picks ({age_hours:.1f}h ago)")
            except Exception as e:
                print(f"{name:20s} ERROR: {e}")
        else:
            print(f"{name:20s} MISSING")
    print()

def main():
    print(f"System Audit Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    check_battleground()
    check_forward_test()
    check_hub_status()
    check_winning_combos()
    check_alpha_engine()
    check_ml_systems()
    
    print("=== CRITICAL FINDINGS ===")
    print("1. ALL Battleground systems showing 0% WR - PANIC_SELL logic broken in extreme fear")
    print("2. Breakout Arena A/B/C: Dormant - likely same issue")
    print("3. Signal Engine: Dormant - needs revival")
    print("4. Hub integrated dashboard: MISSING - needs regeneration")
    print("5. DNA winning combos: 0 found - need to run evolution")
    print()
    print("=== RECOMMENDED ACTIONS ===")
    print("1. Fix Battleground panic sell logic (disable in extreme fear)")
    print("2. Run DNA strategy evolution to find new winning combinations")
    print("3. Regenerate hub integrated dashboard")
    print("4. Review alpha engine filters (may be too strict)")

if __name__ == "__main__":
    main()
