#!/usr/bin/env python3
"""
Register Crypto Hybrid Bundle strategies
"""

import json
from pathlib import Path

# Strategy definitions
STRATEGIES = {
    "williams_pr_trend_mr": {
        "class": "WilliamsPRTrendMRStrategy",
        "file": "baby_strategies/williams_pr_trend_mr.py",
        "tier": "TIER_3_TESTING",  # Pending full backtest
        "status": "PENDING_VALIDATION",
        "weight": 0.25,
    },
    "connors_rsi2": {
        "class": "ConnorsRSI2Strategy", 
        "file": "baby_strategies/connors_rsi2.py",
        "tier": "TIER_1_PROVEN",
        "status": "DEPLOYED",
        "weight": 0.25,
    },
    "bollinger_mean_rev": {
        "class": "BollingerMeanReversionStrategy",
        "file": "baby_strategies/bollinger_mean_reversion.py", 
        "tier": "TIER_1_PROVEN",
        "status": "DEPLOYED",
        "weight": 0.25,
    },
    "orb_breakout": {
        "class": "ORBBreakoutStrategy",
        "file": "baby_strategies/orb_breakout.py",
        "tier": "TIER_2_PROVEN",
        "status": "DEPLOYED",
        "weight": 0.25,
    },
}

BUNDLE = {
    "name": "Crypto Hybrid Reversion-Momentum Ensemble",
    "created": "2026-02-28",
    "strategies": list(STRATEGIES.keys()),
    "allocation": {k: v["weight"] for k, v in STRATEGIES.items()},
    "expected_sharpe": "1.4-1.8",
    "expected_wr": "62-65%",
    "status": "PENDING_WILLIAMS_BACKTEST",
}

print("=" * 80)
print("CRYPTO HYBRID BUNDLE - STRATEGY REGISTRATION")
print("=" * 80)

print("\n[Strategies to Register]")
print("-" * 80)
for name, config in STRATEGIES.items():
    print(f"  {name}")
    print(f"    Class: {config['class']}")
    print(f"    File: {config['file']}")
    print(f"    Tier: {config['tier']}")
    print(f"    Status: {config['status']}")
    print(f"    Weight: {config['weight']*100:.0f}%")
    print()

print("=" * 80)
print("[Bundle Configuration]")
print("=" * 80)
print(f"  Name: {BUNDLE['name']}")
print(f"  Expected Sharpe: {BUNDLE['expected_sharpe']}")
print(f"  Expected WR: {BUNDLE['expected_wr']}")
print(f"  Status: {BUNDLE['status']}")

print("\n" + "=" * 80)
print("REGISTRATION INSTRUCTIONS")
print("=" * 80)
print("""
1. Add to incubator/backtest_team/forward_signal_scanner.py:

   from baby_strategies.williams_pr_trend_mr import WilliamsPRTrendMRStrategy
   
   TIER1_STRATEGIES = {
       "connors_rsi2": ConnorsRSI2Strategy,
       "bollinger_mean_rev": BollingerMeanReversionStrategy,
       "orb_breakout": ORBBreakoutStrategy,
       # Add after Williams %R passes full backtest:
       # "williams_pr_trend_mr": WilliamsPRTrendMRStrategy,
   }

2. Run full backtest on Williams %R:
   
   py alpha_engine/survivor_backtest.py \\
     --strategy williams_pr_trend_mr \\
     --symbols 24 \\
     --years 5 \\
     --checks all_8

3. If Williams %R passes 8/8 checks:
   - Uncomment in forward_signal_scanner.py
   - Deploy bundle to paper trading
   - Monitor for 100+ trades

4. Bundle deployment command:
   
   py incubator/bundle_deployer.py \\
     --bundle crypto_hybrid_ensemble \\
     --mode paper
""")

print("=" * 80)

# Save bundle config
bundle_file = Path("bundle_registry/crypto_hybrid_ensemble.json")
bundle_file.parent.mkdir(parents=True, exist_ok=True)
with open(bundle_file, 'w') as f:
    json.dump(BUNDLE, f, indent=2)

print(f"\n[OK] Bundle config saved: {bundle_file}")
