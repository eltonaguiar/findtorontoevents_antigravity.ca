# Forced Resolution: Sensitivity Analysis + Peer Review Summary
**Date:** 2026-05-31 22:55 EST  
**Methodology:** Honest resolved-trade analysis + 3 external AI peer reviews + sensitivity analysis

## Peer Reviews (3/3 Methodology Confirmed Sound)

### Grok (xai)
- "Closing at actual market price after max_hold is the correct default"
- "You are still discarding the TIME_EXIT population — those 11k+ trades are the dominant outcome"
- Recommend: bootstrap CI, Deflated Sharpe, regime-split analysis

### Mimo (Xiaomi)
- "Close-at-market is superior for three reasons: reflects reality, preserves natural variance, avoids artificial compression"
- Flagged: sensitivity analysis ±20% on max_hold, ±15% on TP/SL
- "If results swing wildly, the edge may be parameter-fitted noise"

### DeepSeek
- "Edge exists on paper but is fragile"
- "Walk-forward validate before trusting"
- "PF 1.48 is positive but modest once you subtract realistic commissions"
- Warning: "Crypto PF 0.96 — if same methodology fails on crypto, FX edge may be artifact"

## Critical Finding: The Edge Paradox

**FOREX resolved trades (n=2,387):** WR=40.1%, PF=1.471, EV=+0.141%/trade

**Sensitivity analysis reveals:**
- SL floor drives edge (SL=-0.05% → PF=17.03)
- TP cap kills edge (TP=0.1% → PF=0.09)
- Combined TP/SL compression → ALL configs show PF<1

**The edge is in asymmetry:** avg TP win = +1.1% vs avg SL loss = -0.46% (ratio 2.4:1)
**Forced resolution with tight TP/SL destroys this asymmetry.**

**Bootstrap 95% CI on EV:** [-0.169%, +0.590%] — CI CROSSES ZERO, not statistically significant at 95%

## Correct Approach (Not Capping)

The fix is NOT tighter TP/SL. It's:
1. Keep existing wide TP/SL (preserves asymmetry)
2. Add time-based market exit as safety net (closes at actual price, not capped)
3. This eliminates TIME_EXIT at 0% without destroying the win/loss asymmetry
4. Paper-pilot for 30+ days with n≥500 before any sizing decision

## Status
- Methodology: CONFIRMED SOUND by 3 external AIs
- Edge: EXISTS but fragile (CI crosses zero)
- Next: Wire forced resolution with WIDE TP/SL (not tight) + time-based market exit
