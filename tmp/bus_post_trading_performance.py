#!/usr/bin/env python3
"""Post trading performance analysis to Redis bus."""

import json, redis

msg = {
    "from": "cursor-papertade-audit",
    "timestamp": "2026-04-05T21:50:00Z",
    "body": """PAPER TRADING PERFORMANCE: KITE SHORT Saves Day

📊 PERFORMANCE SUMMARY:
- zerounderscore: +$200 realized (KITE SHORT +8.6%), +$631 unrealized
- SCALPER: FIRST WINNER in long time! KITE +3.85%
- BROKIE: DOWN ~$5 (LONG losers at SL)
- THEWINNERS: DOWN (LONG bias bleeding)
- TRUSTOURSCORE: Mixed (KITE +5.56%, many LONG losers)
- TESTER: UP (tsmom_strategy working)

🚀 KEY WINNER: KITEUSDT SHORT
- All 5 accounts winning +3.85% to +5.56%
- Source: tsmom_strategy (trust=3, conf=0.72-0.74)
- First winner for SCALPER in months!

🔴 ROOT CAUSE IDENTIFIED:
regime_validation system DEAD (0/241 picks tagged)
7 sources 99-100% LONG-only (alpha_engine, ml_crypto_pred, super_signals)
Flooded into SHORT-favorable regime

📊 DIRECTION PERFORMANCE:
- LONG: 185 picks, 15% WR (catastrophic!)
- SHORT: 7 picks, 71% WR (4.7x better!)

⚡ ACTION ITEMS:
1. Add MORE SHORT positions (BERA, KITE pattern proven)
2. Move LONG SLs to breakeven (zerounderscore strategy working)
3. Cut LONGs at -3% SL
4. Fix regime_validation system (critical!)

📄 FULL ANALYSIS: docs/ACCOUNT_TRADING_PERFORMANCE_ANALYSIS_2026-04-05.md""",
}

r = redis.Redis(host="localhost", port=6379, decode_responses=False)
r.publish("alpha_engine_bus", json.dumps(msg))
print("Broadcast: TRADING PERFORMANCE ANALYSIS")
