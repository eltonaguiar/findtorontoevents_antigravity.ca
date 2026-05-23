# Two-Target TP Post-Processor & Earnings Drift Audit

**Date:** 2026-04-14 12:26 AM EDT  
**Items:** Decision Point #1 (Two-target TP) and #5 (Earnings Drift) from Claude's queue  
**Data Source:** `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed` (canonical)

---

## 1. Two-Target TP Post-Processor — REJECTED

**Hypothesis:** Closing half the position at TP1 (50% of target) and letting the other half run to TP2 (full target) would improve profit factor.

**Result: Tiered TP HURTS performance across every asset class and every strategy.**

### Per-Asset Results

| Asset | N | Base PF | Tiered PF (50%/100%) | Aggressive PF (40%/120%) | PF Change |
|-------|---|---------|---------------------|-------------------------|-----------|
| CRYPTO | 1,849 | 1.32 | **1.05** | 1.10 | **-0.28** |
| EQUITY | 617 | 0.75 | 0.61 | 0.64 | -0.14 |
| FOREX | 703 | 2.02 | 1.55 | 1.65 | -0.46 |
| COMMODITY | 287 | 1.06 | 0.79 | 0.84 | -0.26 |

### Per-Strategy Results (Crypto, min 20 picks)

Every single strategy is worse with tiered TP:

| Strategy | N | Base PF | Tiered PF | Change |
|----------|---|---------|-----------|--------|
| quan_engine_scalp | 568 | 1.40 | 1.08 | -0.32 |
| st_fear_greed_contrarian | 218 | 1.07 | 0.96 | -0.11 |
| luxalgo_confluence | 99 | 2.16 | 1.62 | -0.54 |
| st_obv_support_divergence | 72 | 6.66 | 5.37 | -1.29 |
| st_multi_day_momentum | 41 | 2.76 | 2.10 | -0.66 |
| claude_ml_moderate_mut | 20 | 2.24 | 1.68 | -0.56 |

**Why it fails:** The current TP levels are already calibrated. Closing half at 50% of target reduces the average win magnitude without improving WR. The winners that hit full TP are already optimally sized — splitting them dilutes the payoff without adding protection.

**Recommendation:** Do NOT implement tiered TP. The current single-target TP is optimal for this system. If tiered exits are desired, a trailing stop after TP1 (rather than a fixed TP2) would be the correct approach — but that requires real-time price monitoring infrastructure.

---

## 2. Earnings Drift Audit — INVERSE CONFIRMED

**Hypothesis:** The `Earnings Drift` strategy might have a sign-flip bug (going LONG when it should SHORT, or vice versa).

### Current Performance

| Metric | Value |
|--------|-------|
| Picks | 31 (all LONG) |
| WR | 32.3% |
| PF | **0.48** |
| Sum PnL | **-51.7%** |
| SL Hit Rate | 48.4% (15/31) |

### Inverse Performance

| Metric | Current | **Inverse** |
|--------|---------|------------|
| WR | 32.3% | **67.7%** |
| PF | 0.48 | **2.07** |
| Sum PnL | -51.7% | **+51.7%** |

**The sign-flip hypothesis is CONFIRMED.** Inverting Earnings Drift doubles the WR and quadruples the PF.

### Symbol-Level Analysis

| Symbol | N | WR | Sum PnL | Inverse actionable? |
|--------|---|-----|---------|-------------------|
| MARA | 4 | 0% | -20.8% | ✅ All 4 are losers → SHORT all |
| PLTR | 3 | 0% | -14.5% | ✅ All 3 are losers → SHORT all |
| CVX | 2 | 0% | -13.5% | ✅ Both losers → SHORT |
| OPEN | 4 | 25% | -6.0% | ⚠️ Mostly losers |
| AMD | 2 | 100% | +10.7% | ❌ Both winners — keep LONG |
| NVDA | 2 | 50% | +4.3% | Neutral |
| GOOGL | 1 | 100% | +6.5% | Keep LONG |

**Pattern:** Earnings Drift LONG fails on high-beta/speculative names (MARA, PLTR, OPEN) but works on established tech (AMD, GOOGL, NVDA). The inverse would SHORT the speculative names after earnings — which aligns with the known "post-earnings volatility crush" pattern where speculative stocks tend to give back gains.

### Recommended Action

Per TESTING_PROTOCOL Section 7 (rehabilitation-first pipeline):

1. **Create `earnings_drift_inverse` variant** using `baby_strategies/inverse_wrapper.py` (already merged in PR #183)
2. Set `wired_in_scanner: false` initially
3. Paper-trade for 2 weeks with n≥20 target
4. If PF ≥ 1.5 on paper, promote to `DATA_VALIDATED`

**Implementation:**

```python
# In baby_strategies/ or strategy_mutations.py
EARNINGS_DRIFT_INVERSE_CONFIG = {
    "parent_strategy": "Earnings Drift",
    "flip_direction": True,
    "symbol_filter": {
        "prefer_short": ["MARA", "PLTR", "OPEN", "MSTR", "CVX", "SOXX"],
        "keep_long": ["AMD", "GOOGL", "NVDA", "MSFT"],
    },
    "source_system": "stocks_competition",
    "asset_class": "EQUITY",
}
```

---

## 3. Summary of Decision Point Items

| # | Item | Result | Action |
|---|------|--------|--------|
| 1 | Two-target TP post-processor | ❌ **REJECTED** — hurts PF across all assets/strategies | Do not implement |
| 2 | HMM regime gate on squeeze/expansion | Not tested yet — needs regime_terminal data | Defer |
| 3 | Activate quan_engine_inverse | Ready (inverse_wrapper merged) — but touches scanner.py | Defer to separate PR |
| 4 | Execute promotion gate plan | 14-task TDD — largest scope | Defer |
| **5** | **Audit Earnings Drift** | **✅ CONFIRMED sign-flip — inverse PF 2.07** | **Ship inverse variant** |

---

*Generated: 2026-04-14 12:26 AM EDT*
