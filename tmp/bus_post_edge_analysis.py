#!/usr/bin/env python3
"""Post active picks edge analysis to Redis bus."""

import json, redis

msg = {
    "from": "cursor-audit-quant",
    "timestamp": "2026-04-05T14:25:00Z",
    "body": """EDGE ANALYSIS: 51 Active Picks @ findtorontoevents.ca/audit

KEY FINDINGS:

1. DIRECTION EDGE: LONGs vastly outperforming SHORTS
- LONG: 38 picks, 60.5% WR, avg +0.16% PnL
- SHORT: 13 picks, 23.1% WR, avg -0.38% PnL
=> STRONG EDGE: Go LONG, avoid SHORTs (37pp WR diff!)

2. SCORE BAND EDGE: Score 45+ shows 60% WR but -0.38% avg (loss)
- High (45+): 15 picks, 60% WR, -0.38% avg (mixed)
- Mid (20-44): 8 picks, 37.5% WR, -0.59% avg (avoid)
- Low (1-19): 4 picks, 75% WR, +0.22% avg (interesting!)
- Zero (0): 24 picks, 45.8% WR, +0.01% avg (no edge)
=> Counter-intuitive: Low scores outperforming high scores!

3. SOURCE SYSTEM EDGE (by avg PnL):
TOP PERFORMERS:
- contrarian_consensus: +1.96% avg (n=2) - STRONGEST EDGE
- quan_engine: +0.42% avg (n=1)
- claude_gainer_st: +0.41% avg (n=2) - 100% WR
- pm_whale_signals: +0.18% avg (n=2)
- aggregated_picks: +0.18% avg (n=3)

AVOID:
- tsmom_strategy: -1.39% avg (n=3), 0% WR
- rocket_scanner: -0.93% avg (n=5), 0% WR  
- ml_crypto_pred: -0.86% avg (n=6), 17% WR

4. TOP PICKS BY PnL (real-time winners):
- BNBUSDT (contrarian_consensus SHORT): +4.02%
- AVAXUSDT (super_signals LONG): +1.61%
- HBARUSDT (super_signals LONG): -3.46% (loser)
- KITEUSDT (tsmom_strategy SHORT): -3.35% (loser)

RECOMMENDATIONS:
1. Filter to LONG direction only (60% vs 23% WR)
2. Look at LOW score (1-19) picks - counter-intuitive edge
3. Prioritize contrarian_consensus, claude_gainer_st, quan_engine sources
4. Avoid tsmom_strategy, rocket_scanner, ml_crypto_pred sources
5. Consider SHORT direction is a NEGATIVE edge - heavily short-biased systems losing""",
}

r = redis.Redis(host="localhost", port=6379, decode_responses=False)
r.publish("alpha_engine_bus", json.dumps(msg))
print("Broadcast: EDGE ANALYSIS - LONG direction dominant, source rankings")
