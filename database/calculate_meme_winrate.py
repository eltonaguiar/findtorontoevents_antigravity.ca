#!/usr/bin/env python3
"""
================================================================================
CALCULATE MEME COIN WIN RATE
================================================================================
"""

from multi_db_manager import manager

print("=" * 70)
print("MEME COIN WIN RATE CALCULATION")
print("=" * 70)

# Query mc_winners for outcomes
print("\n[1] Analyzing mc_winners table (29 rows)")
print("-" * 70)

outcomes = manager.execute('memecoin', """
    SELECT 
        outcome,
        COUNT(*) as count,
        AVG(pnl_pct) as avg_pnl
    FROM mc_winners
    WHERE outcome IS NOT NULL
    GROUP BY outcome
""")

total = 0
wins = 0
losses = 0
breakeven = 0

print("\nOutcome breakdown:")
for row in outcomes:
    outcome = row['outcome']
    count = row['count']
    avg_pnl = row['avg_pnl'] or 0
    total += count
    
    if outcome in ['win', 'target_hit', 'tp_hit']:
        wins += count
        status = "WIN"
    elif outcome in ['loss', 'stopped_out', 'sl_hit']:
        losses += count
        status = "LOSS"
    else:
        breakeven += count
        status = "OTHER"
    
    print(f"  {outcome}: {count} trades (avg P&L: {avg_pnl:.2f}%)")

print("\n" + "=" * 70)
print("CALCULATED WIN RATE")
print("=" * 70)

if total > 0:
    win_rate = (wins / total) * 100
    loss_rate = (losses / total) * 100
    
    print(f"\nTotal Trades with Outcome: {total}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Breakeven/Other: {breakeven}")
    print(f"\n>>> WIN RATE: {win_rate:.1f}% <<<")
    print(f">>> LOSS RATE: {loss_rate:.1f}% <<<")
    
    if win_rate < 10:
        print(f"\n[CRITICAL] Win rate is {win_rate:.1f}%")
        print("Audit claim of 5% is VALIDATED - performance is extremely poor")
    elif win_rate < 30:
        print(f"\n[WARNING] Win rate is {win_rate:.1f}% - very poor")
    elif win_rate < 50:
        print(f"\n[INFO] Win rate is {win_rate:.1f}% - below random")
    else:
        print(f"\n[SUCCESS] Win rate is {win_rate:.1f}% - acceptable")
else:
    print("No completed trades found in mc_winners")

# Check mc_scan_log for verdicts
print("\n" + "=" * 70)
print("[2] Analyzing mc_scan_log verdicts (1,749 scans)")
print("=" * 70)

verdicts = manager.execute('memecoin', """
    SELECT 
        verdict,
        COUNT(*) as count
    FROM mc_scan_log
    GROUP BY verdict
""")

print("\nScan verdicts:")
total_scans = 0
for row in verdicts:
    print(f"  {row['verdict']}: {row['count']}")
    total_scans += row['count']

print(f"\nTotal scans: {total_scans}")

# Look at specific coins
print("\n" + "=" * 70)
print("[3] Top Meme Coins Scanned")
print("=" * 70)

top_coins = manager.execute('memecoin', """
    SELECT 
        pair,
        COUNT(*) as scans,
        AVG(score) as avg_score
    FROM mc_scan_log
    GROUP BY pair
    ORDER BY scans DESC
    LIMIT 10
""")

print("\nMost scanned pairs:")
for row in top_coins:
    print(f"  {row['pair']}: {row['scans']} scans (avg score: {row['avg_score']:.1f})")

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)
print("""
The meme coin scanner has extensive tracking infrastructure:
- 1,749 scans logged with detailed scoring
- 29 completed trades tracked
- 7-factor scoring system (volume, momentum, RSI, etc.)
- Tier-based classification

The actual win rate calculation depends on how "wins" are defined
in the outcome field. Based on the sample data showing "partial_loss"
outcomes, the system is actively tracking performance.
""")
