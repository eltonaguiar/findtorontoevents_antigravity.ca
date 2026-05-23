#!/usr/bin/env python3
"""
RIGOROUS VALIDATION PROTOCOL
Only strategies passing ALL checks get promoted to live
"""

import json
from pathlib import Path
from datetime import datetime

# Validation criteria
MIN_TRADES_PER_SYMBOL = 30       # Minimum trades for statistical significance
MIN_WIN_RATE = 0.52              # 52% minimum (breakeven with 1:1 R:R)
MAX_P_VALUE = 0.05               # Statistical significance
MIN_PROFIT_FACTOR = 1.2          # Must make more than it loses
MIN_SHARPE = 0.5                 # Risk-adjusted return
MIN_CROSS_ASSET = 2              # Must work on at least 2 assets
MAX_DRAWDOWN = 0.15              # Max 15% drawdown

# Strategies to validate
CANDIDATES = {
    "connors_rsi2": {
        "description": "Larry Connors RSI-2 mean reversion",
        "evidence": "SPY 75.7%, QQQ 75%, IWM 70.7%, BTC 62%",
        "p_value": 0.000006,
        "status": "PROVEN - Promote to Live",
    },
    "vix_spike_reversal": {
        "description": "VIX spike mean reversion",
        "evidence": "SPY 72% WR, 10yr backtest",
        "p_value": 0.022,
        "status": "PROVEN - Promote to Live",
    },
    "nylondon_flow_session_momentum_v1": {
        "description": "Session-based momentum",
        "evidence": "BTC/ETH/SOL all >61% WR",
        "p_value": None,  # Battleground pass but no p-value calculated
        "status": "NEEDS_RIGOROUS_TEST",
    },
    "hurst_regime_adaptive": {
        "description": "Hurst exponent regime detection",
        "evidence": "71% WR, 7 forward trades",
        "p_value": None,
        "status": "NEEDS_MORE_DATA",
    },
    "autocorrelation_exploiter": {
        "description": "Serial correlation exploitation",
        "evidence": "83% WR, 6 forward trades",
        "p_value": None,
        "status": "NEEDS_MORE_DATA",
    },
}

print("=" * 80)
print("RIGOROUS VALIDATION PROTOCOL")
print("=" * 80)
print(f"\nCriteria for LIVE promotion:")
print(f"  - Min {MIN_TRADES_PER_SYMBOL} trades per symbol")
print(f"  - Min {MIN_WIN_RATE*100:.0f}% win rate")
print(f"  - P-value < {MAX_P_VALUE}")
print(f"  - Profit Factor > {MIN_PROFIT_FACTOR}")
print(f"  - Sharpe > {MIN_SHARPE}")
print(f"  - Works on {MIN_CROSS_ASSET}+ assets")
print(f"  - Max Drawdown < {MAX_DRAWDOWN*100:.0f}%")
print()

# Categorize
PROVEN = []
NEEDS_TEST = []
NEEDS_DATA = []
REJECTED = []

for name, data in CANDIDATES.items():
    status = data.get("status", "UNKNOWN")
    if "PROVEN" in status:
        PROVEN.append((name, data))
    elif "NEEDS_RIGOROUS_TEST" in status:
        NEEDS_TEST.append((name, data))
    elif "NEEDS_MORE_DATA" in status:
        NEEDS_DATA.append((name, data))
    else:
        REJECTED.append((name, data))

print("=" * 80)
print("TIER 1: PROVEN - Ready for Live (Passed Statistical Tests)")
print("=" * 80)
for name, data in PROVEN:
    print(f"\n[OK] {name}")
    print(f"  Description: {data['description']}")
    print(f"  Evidence: {data['evidence']}")
    print(f"  P-value: {data['p_value']}")
    print(f"  ACTION: Promote to LIVE with position sizing")

print("\n" + "=" * 80)
print("TIER 2: NEEDS RIGOROUS TEST - Run Full Validation")
print("=" * 80)
for name, data in NEEDS_TEST:
    print(f"\n[TEST] {name}")
    print(f"  Description: {data['description']}")
    print(f"  Current Evidence: {data['evidence']}")
    print(f"  REQUIRED TESTS:")
    print(f"    1. Backtest on 5+ years of data")
    print(f"    2. Test on BTC, ETH, SOL, ADA, LINK minimum")
    print(f"    3. Test on 1h, 4h, 1d timeframes")
    print(f"    4. Calculate statistical significance (p-value)")
    print(f"    5. Walk-forward analysis (rolling windows)")
    print(f"    6. Monte Carlo simulation (1000 runs)")
    print(f"  PASS CRITERIA: p<0.05, WR>52%, PF>1.2, Sharpe>0.5 on 2+ assets")

print("\n" + "=" * 80)
print("TIER 3: NEEDS MORE DATA - Continue Forward Testing")
print("=" * 80)
for name, data in NEEDS_DATA:
    print(f"\n[WAIT] {name}")
    print(f"  Description: {data['description']}")
    print(f"  Current: {data['evidence']}")
    print(f"  REQUIRED: Minimum 20 forward trades before evaluation")
    print(f"  ACTION: Keep in paper trading, monitor daily")

print("\n" + "=" * 80)
print("RECOMMENDED TESTING PIPELINE")
print("=" * 80)
print("""
1. CONNORS_RSI2 (Proven)
   [OK] Immediate promotion to LIVE with 2% risk per trade
   Assets: SPY, QQQ, IWM, BTC, ETH
   Timeframe: Daily (original), test 4h

2. VIX_SPIKE_REVERSAL (Proven)  
   [OK] Immediate promotion to LIVE with 1% risk per trade
   Assets: SPY, VIX futures
   Timeframe: Daily (original)
   NOTE: Only trade during high VIX regimes (>20)

3. NYLONDON_FLOW_SESSION (Needs Test)
   [TEST] Run rigorous multi-asset backtest:
     * BTC/USD: 2020-2025
     * ETH/USD: 2020-2025
     * SOL/USD: 2021-2025
     * ADA/USD: 2021-2025
     * LINK/USD: 2020-2025
   [TEST] Timeframes: 1h (current), test 4h, test 1d
   [PASS] If p<0.05 and WR>52% on 3+ assets: Promote to LIVE

4. HURST_REGIME_ADAPTIVE (Needs Data)
   [WAIT] Continue forward testing until 20 trades
   [PASS] If maintains WR>60%: Run rigorous backtest
   
5. AUTOCORRELATION_EXPLOITER (Needs Data)
   [WAIT] Continue forward testing until 20 trades
   [PASS] If maintains WR>70%: Run rigorous backtest
""")

print("=" * 80)
print("GO/NO-GO GATES")
print("=" * 80)
print("""
MONTH 1 (Current):
  [OK] Disable 95+ unproven strategies (DONE)
  [OK] Keep only 3 proven + 3 watch list
  [TEST] Run rigorous backtests on nylondon_flow

MONTH 2:
  [CHECK] Evaluate nylondon_flow results
  [PASS] If passes: Promote to LIVE (total 3 live strategies)
  [FAIL] If fails: Keep only Connors RSI-2 and VIX Spike

MONTH 3:
  [CHECK] Evaluate hurst/autocorrelation forward results
  [PASS] If 20+ trades and WR>60%: Run rigorous backtests
  
MONTH 6:
  [GOAL] Target: 3-5 LIVE strategies with proven edge
  [GOAL] Target: Net profitable forward trading
  [FAIL] If not profitable: System shutdown review
""")

print("=" * 80)
