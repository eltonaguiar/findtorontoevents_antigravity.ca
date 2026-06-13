# Peer Review Plan — June 2026 Action Plan

**Reviewer target:** 5-20 independent AI models  
**Subject:** Action plan for making the trading system real-money ready  
**Files to review:**
- `reports/ACTION_PLAN_JUNE_2026.md` (the plan)
- `reports/MONEY_MAKER_READY_JUNE_2026_EDITION.md` (the audit)
- `alpha_engine/honest_kill_switch.py` (the kill switch with per-class thresholds)
- `tools/blacklist_impact_simulation.py` (the simulation)

---

## Review Questions

### Q1: Threshold Appropriateness
The per-asset-class WR/PF thresholds are:
- CRYPTO/ETF/BOND: 45% WR / 1.0 PF
- EQUITY: 45% WR / 0.8 PF
- FOREX/COMMODITY/FUTURES: 50% WR / 1.2 PF

**Question:** Are these thresholds too lenient, too strict, or appropriate for each asset class? What would you change?

### Q2: Walk-Forward Validation Rigor
The plan requires 3 windows × 30+ trades each with efficiency ≥ 0.30.

**Question:** Is this sufficient statistical rigor? Should we require more windows, more trades per window, or a higher efficiency threshold? What are the risks of false positives at these levels?

### Q3: Kill Switch Design
The kill switch kills strategies below per-class WR/PF thresholds after 30+ trades. It preserves originals via `_ORIGINAL_THRESHOLDS` and propagates CLI overrides safely.

**Question:** Are there any edge cases or failure modes in the kill switch design? Should it consider additional factors (e.g., drawdown, Sharpe, regime)?

### Q4: Missing P0 Items
The plan identifies 3 P0 items: walk-forward validation, concept drift fix, and slippage tracking.

**Question:** Are there any critical missing P0 items that should block real-money deployment? What's the single most important thing we're NOT doing?

### Q5: Strategy Concentration Risk
CRYPTO has 2 surviving strategies (luxalgo_confluence n=133, crypto_liquidity_wick_reversal_v1 n=4904). EQUITY has 2 (stocks_rsi2_pullback n=79, smart_money_accumulation n=50).

**Question:** Is this too concentrated? What's the minimum number of independent strategies per asset class for real-money deployment?

### Q6: Blacklist Simulation Validity
The simulation shows +5.21pp WR lift and 326% PnL damage removed after blacklisting 19 strategies. But the WR values are stored as decimals (0.5449 = 54.49%).

**Question:** Is the simulation methodology sound? Are there any biases in how the "before" vs "after" comparison is constructed?

### Q7: Regime Detection
The concept drift detector is empty in the live dashboard. Previous reports cite KS_D=0.313 vs critical 0.047.

**Question:** Should regime detection be a P0 blocker? If KS_D is truly 0.313, that's massive distributional shift — should we halt all live trading until this is resolved?

### Q8: Smart Picks Coverage
Only 2 picks in the smart picks feed (XRPUSDT SHORT, SOLUSDT SHORT). The scoring pipeline has 15+ filters.

**Question:** Is 2 picks sufficient for a real-money system? What's the minimum smart picks count for deployment? Should we relax filters?

---

## Review Format

Please respond in this format:

```
## Review by [Model Name]

### Q1: Threshold Appropriateness
[Your answer]

### Q2: Walk-Forward Validation Rigor
[Your answer]

...

### Overall Verdict
[PASS / CONDITIONAL PASS / FAIL / NEEDS MORE INFO]

### Top 3 Recommendations
1. [Most important change]
2. [Second most important]
3. [Third most important]
```

---

*Submitted for review: 2026-06-13*
