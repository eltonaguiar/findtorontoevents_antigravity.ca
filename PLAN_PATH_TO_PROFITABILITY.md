# Path to True Profitability — Action Plan
**Date:** 2026-11-14
**Status:** P0 Implementation In Progress

## The Core Problem

Our prediction system has **verified profitable edges** that are being **actively blocked** by outdated kill lists. The strategies labeled "WORST in entire system" in May 2026 are now the **best performers** in November 2026.

| Strategy | May 2026 Label | Nov 2026 Reality | Status |
|----------|---------------|------------------|--------|
| `quan_engine` | "0% WR, blocked" | **95.8% WR, +669% PnL, 284 trades** | HARD BLOCKED |
| `st_rsi_momentum_confluence` | "WORST in system, -296% PnL" | **65.1% WR, PF 2.53, 258 trades** | HARD BLOCKED |
| SHORT direction | Treated equally | **72.0% WR vs LONG 20.3%** | NOT EXPLOITED |
| Score 40-59 | No special treatment | **60.8% WR, +0.056% avg PnL** | NOT EXPLOITED |

## Root Cause: Regime Change Without Adaptation

The kill lists in `quality_gates.py` and `source_quality_filter_v1.py` were built from **May 2026 data** when the market regime was different. Since then:
- Crypto entered a new volatility regime
- `quan_engine`'s mean-reversion signals started working
- `st_rsi_momentum_confluence`'s RSI-50/70 confluence caught momentum shifts
- SHORT became the dominant winning direction

**The system never re-evaluated.** Static kill lists + regime change = profitable edges blocked.

## What TradingView Contest Winners Do Differently

From research on 59K–107K contestant leaderboards:

1. **Specialize in ONE pattern per asset class** — don't run 100+ strategies
2. **Use 1-3% position sizing for real money** (not 10-20% like contests)
3. **Technical SLs** (swing low, order block invalidation) — not fixed percentages
4. **Daily loss cap -5%, monthly -20%** — hard stops
5. **3 losses in a row → stop for the session** — regime is unfavorable
6. **Two archetypes:** High-WR Grinders (83-95% WR, 1.5:1 R:R) OR High-R:R Snipers (45-55% WR, 3:1+ R:R)

## Immediate Actions (P0 — This Session)

### 1. Create Pilot Pipeline for Verified Edges

Create `alpha_engine/pilot_verified_edges.py` that:
- Bypasses `PERMANENTLY_KILLED_STRATEGIES` for the 3 verified edges
- Emits ONLY `quan_engine`, `st_rsi_momentum_confluence`, and SHORT-bias signals
- Runs in shadow mode (logs picks, does not emit to dashboard)
- Uses 1% position sizing
- Uses ATR-based technical stops (not fixed percentages)
- Tags all picks with `pilot_verified_edge` for tracking

### 2. Unblock `quan_engine` in Source Quality Filter

Move `quan_engine` from `penalized_sources` (0.8x) to `amplified_sources` (1.5x) in `strategies/source_quality_filter_v1.py`. Add comment explaining the regime change.

### 3. Implement SHORT-Bias Gate

Create a direction-aware gate that:
- For CRYPTO: boosts SHORT signals by +20% score, penalizes LONG by -20%
- Tracks separate PF/WR for LONG vs SHORT
- Only emits LONG if it independently passes all gates

### 4. Implement 40-59 Score Bucket Gate

Create a score-aware gate that:
- Blocks scores < 40 (losing)
- Allows scores 40-59 (proven positive expectancy)
- Blocks scores > 59 (too few trades, unverified)

### 5. Add Regime Detection

Use `alpha_engine/regime_router.py` to detect WHEN the verified edges work:
- High volatility → `quan_engine` mean-reversion works
- Trending market → `st_rsi_momentum_confluence` works
- Flat/choppy → both work

## Medium-Term Actions (P1 — Next 48h)

### 6. Implement Statistical Scoring Framework

Use the framework from the subagent research:
- Gate 0: Data Quality (n >= 30)
- Gate 1: Bootstrap CI (10K resamples, 95% CI)
- Gate 2: Walk-Forward (10 folds, >= 60% profitable)
- Gate 3: Gross Profitability (PF > 1.5, Sharpe > 1.0)
- Gate 4: Money-Ready (Net PF > 1.2, DSR > 0.95)
- Gate 5: Direction Validation (both sides pass or explicit single-direction)

### 7. Run Bootstrap Validation on 3 Verified Edges

Generate bootstrap distributions for:
- `quan_engine`: n=284, WR=95.8%, PF=?
- `st_rsi_momentum_confluence`: n=258, WR=65.1%, PF=2.53
- SHORT bias: n=?, WR=72.0%, PF=?

### 8. Implement Dynamic Kill List

Replace static `PERMANENTLY_KILLED_STRATEGIES` with a regime-aware system:
- Re-evaluate every strategy every 7 days
- Use rolling 30-day window for kill/amplify decisions
- Regime-specific: a strategy killed in high-vol may be amplified in low-vol

## Success Metrics

| Metric | Current | Target (30 days) |
|--------|---------|------------------|
| Verified edges emitted | 0 | 50-100 picks/week |
| Pilot PF | N/A | > 1.2 net |
| Pilot WR | N/A | > 55% |
| Score-PnL correlation | +0.008 | > +0.3 |
| Static kill list size | 40+ | Dynamic, regime-aware |

## Risks

| Risk | Mitigation |
|------|------------|
| Verified edges were lucky (not real) | Bootstrap CI + walk-forward validation before live emission |
| Regime changes again | Rolling 7-day re-evaluation + regime router |
| Overfitting to 3 strategies | Still run 100+ strategies in background; only promote validated ones |
| User sees fewer picks | Quality > quantity; transparent about filtering |

## Implementation Order

1. **Now:** Create pilot pipeline (shadow mode)
2. **Next 2h:** Unblock in source filter, implement SHORT bias + score gates
3. **Next 24h:** Bootstrap validation on verified edges
4. **Next 48h:** If validation passes, promote to live emission with 1% sizing
5. **Next 7 days:** Implement dynamic kill list + regime-aware routing

---
**Prepared by:** Kilo (finpredict-v4)
**Based on:** Peer audit round 2, TradingView contest research, statistical scoring framework
