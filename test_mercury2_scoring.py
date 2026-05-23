"""Quick test of Mercury 2 scoring enhancements"""

from audit_trail.mercury2_scoring import (
    compute_blended_score,
    apply_liquidity_penalty,
    apply_time_decay,
    flag_low_confidence_picks,
)

# Test 1: Blended Score
print("=" * 60)
print("TEST 1: Blended Score (Tech 70% + PnL 30%)")
print("=" * 60)

cases = [
    (85, 12.5, "High tech score + positive PnL (good signal)"),
    (85, -8.0, "High tech score + negative PnL (bad signal)"),
    (45, 20.0, "Low tech score + high PnL (unexpected winner)"),
    (80, 0.0, "Good tech score + neutral PnL"),
]

for tech, pnl, desc in cases:
    blended = compute_blended_score(tech, pnl)
    print(f"  {desc}")
    print(f"    Tech={tech}, PnL={pnl}% | Blended={blended}\n")

# Test 2: Liquidity Penalty
print("=" * 60)
print("TEST 2: Liquidity Penalty")
print("=" * 60)

liquidity_cases = [
    (75, 5_000_000, 0.08, "High volume, tight spread"),
    (75, 50_000, 1.5, "Low volume, wide spread"),
    (60, 1_000_000, 0.5, "Medium volume, tight spread"),
]

for score, volume, spread, desc in liquidity_cases:
    penalized, penalty = apply_liquidity_penalty(score, volume_24h=volume, bid_ask_spread_pct=spread)
    print(f"  {desc}")
    print(f"    Score={score}, Volume=${volume:,.0f}, Spread={spread}%")
    print(f"    -> Penalized={penalized}, Penalty={penalty}\n")

# Test 3: Confidence Flags
print("=" * 60)
print("TEST 3: Confidence Flags (Score/PnL Divergence)")
print("=" * 60)

flag_cases = [
    (85, -15.0, "High score but negative PnL"),
    (45, 20.0, "Low score but positive PnL"),
    (80, 12.0, "Aligned score and PnL"),
    (70, -8.0, "Slight divergence"),
]

for score, pnl, desc in flag_cases:
    is_flag, reason, penalty = flag_low_confidence_picks(score, pnl)
    print(f"  {desc}")
    print(f"    Score={score}, PnL={pnl}%")
    print(f"    -> Flagged={is_flag}, Reason={reason}\n")

print("=" * 60)
print("[OK] All tests completed successfully")
print("=" * 60)
