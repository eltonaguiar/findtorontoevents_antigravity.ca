#!/usr/bin/env python3
"""
================================================================================
MEME COIN PERFORMANCE INVESTIGATION
================================================================================
Deep dive into existing meme coin data to verify the 5% win rate claim
================================================================================
"""

from multi_db_manager import manager

print("=" * 70)
print("MEME COIN PERFORMANCE INVESTIGATION")
print("=" * 70)

# =============================================================================
# 1. CHECK mc_scan_log (Meme Coin Scan Log - 1,749 rows)
# =============================================================================
print("\n[1] INVESTIGATING: mc_scan_log (1,749 rows)")
print("-" * 70)

try:
    # Get column info
    schema = manager.execute('memecoin', "DESCRIBE mc_scan_log")
    print("Columns:")
    for col in schema:
        print(f"  - {col['Field']}: {col['Type']}")
    
    # Get sample data
    sample = manager.execute('memecoin', "SELECT * FROM mc_scan_log LIMIT 3")
    print("\nSample records:")
    for row in sample:
        print(f"  {row}")
    
    # Check for performance data
    perf_check = manager.execute('memecoin', """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN win_loss = 'WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN win_loss = 'LOSS' THEN 1 ELSE 0 END) as losses
        FROM mc_scan_log
        WHERE win_loss IS NOT NULL
    """)
    
    if perf_check and perf_check[0]:
        row = perf_check[0]
        total = row.get('total', 0) or 0
        wins = row.get('wins', 0) or 0
        losses = row.get('losses', 0) or 0
        
        print(f"\nPerformance Data Found:")
        print(f"  Total with results: {total}")
        print(f"  Wins: {wins}")
        print(f"  Losses: {losses}")
        
        if total > 0:
            win_rate = (wins / total) * 100
            print(f"  >>> WIN RATE: {win_rate:.1f}% <<<")
            
            if win_rate < 10:
                print(f"  [CRITICAL] Win rate is {win_rate:.1f}% - Audit claim of 5% IS VALIDATED")
            elif win_rate < 20:
                print(f"  [WARNING] Win rate is very low ({win_rate:.1f}%)")
            else:
                print(f"  [INFO] Win rate: {win_rate:.1f}%")
        else:
            print("  No performance data found in this table")
            
except Exception as e:
    print(f"  Error: {e}")

# =============================================================================
# 2. CHECK mc_winners (29 rows)
# =============================================================================
print("\n[2] INVESTIGATING: mc_winners (29 rows)")
print("-" * 70)

try:
    schema = manager.execute('memecoin', "DESCRIBE mc_winners")
    print("Columns:")
    for col in schema:
        print(f"  - {col['Field']}: {col['Type']}")
    
    sample = manager.execute('memecoin', "SELECT * FROM mc_winners LIMIT 5")
    print("\nSample records:")
    for row in sample:
        print(f"  {row}")
        
except Exception as e:
    print(f"  Error: {e}")

# =============================================================================
# 3. CHECK kraken_meme_scans
# =============================================================================
print("\n[3] INVESTIGATING: kraken_meme_scans")
print("-" * 70)

try:
    schema = manager.execute('memecoin', "DESCRIBE kraken_meme_scans")
    print("Columns:")
    for col in schema:
        print(f"  - {col['Field']}: {col['Type']}")
    
    count = manager.execute('memecoin', "SELECT COUNT(*) as cnt FROM kraken_meme_scans")
    print(f"\nTotal rows: {count[0]['cnt']}")
    
    sample = manager.execute('memecoin', "SELECT * FROM kraken_meme_scans LIMIT 3")
    print("Sample records:")
    for row in sample:
        print(f"  {row}")
        
except Exception as e:
    print(f"  Error: {e}")

# =============================================================================
# 4. CHECK meme_ml_predictions
# =============================================================================
print("\n[4] INVESTIGATING: meme_ml_predictions")
print("-" * 70)

try:
    schema = manager.execute('memecoin', "DESCRIBE meme_ml_predictions")
    print("Columns:")
    for col in schema:
        print(f"  - {col['Field']}: {col['Type']}")
    
    count = manager.execute('memecoin', "SELECT COUNT(*) as cnt FROM meme_ml_predictions")
    print(f"\nTotal rows: {count[0]['cnt']}")
    
    # Check for accuracy data
    acc_check = manager.execute('memecoin', """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct,
            SUM(CASE WHEN was_correct = 0 THEN 1 ELSE 0 END) as wrong
        FROM meme_ml_predictions
        WHERE was_correct IS NOT NULL
    """)
    
    if acc_check and acc_check[0]:
        row = acc_check[0]
        total = row.get('total', 0) or 0
        correct = row.get('correct', 0) or 0
        
        print(f"\nML Prediction Accuracy:")
        print(f"  Total evaluated: {total}")
        print(f"  Correct: {correct}")
        if total > 0:
            acc_rate = (correct / total) * 100
            print(f"  >>> ML ACCURACY: {acc_rate:.1f}% <<<")
            
    sample = manager.execute('memecoin', "SELECT * FROM meme_ml_predictions LIMIT 3")
    print("Sample records:")
    for row in sample:
        print(f"  {row}")
        
except Exception as e:
    print(f"  Error: {e}")

# =============================================================================
# 5. CHECK tv_signals (TradingView signals - 51 rows)
# =============================================================================
print("\n[5] INVESTIGATING: tv_signals (TradingView signals)")
print("-" * 70)

try:
    schema = manager.execute('memecoin', "DESCRIBE tv_signals")
    print("Columns:")
    for col in schema[:10]:  # First 10 columns
        print(f"  - {col['Field']}: {col['Type']}")
    
    # Check for meme coins
    meme_signals = manager.execute('memecoin', """
        SELECT * FROM tv_signals 
        WHERE symbol IN ('DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'BOME')
        LIMIT 10
    """)
    
    print(f"\nMeme coin signals found: {len(meme_signals)}")
    for row in meme_signals:
        print(f"  {row.get('symbol', 'N/A')}: {row.get('signal', 'N/A')} @ {row.get('price', 'N/A')}")
        
except Exception as e:
    print(f"  Error: {e}")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("INVESTIGATION SUMMARY")
print("=" * 70)
print("""
FINDINGS:
- mc_scan_log: 1,749 meme coin scans logged
- mc_winners: 29 winning trades tracked
- kraken_meme_scans: Meme coin scan data
- meme_ml_predictions: ML prediction tracking
- tv_signals: 51 TradingView signals (some meme coins)

ACTION REQUIRED:
Query these tables for win_loss or was_correct fields to calculate
actual win rate and validate the 5% claim.
""")
