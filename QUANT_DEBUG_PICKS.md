# QUANT DEBUG PICKS — Initial Diagnosis
*Generated: 2026-04-07 | Analyst: Antigravity Quant Review*

---

## Executive Summary

**System-wide Profit Factor: 0.56** (needs > 1.0 to be profitable)  
**Win Rate: 29.6%** on 3,340 closed picks  
**Gross Profit: 690%** vs **Gross Loss: 1,231%**

This is not a bad-luck streak. These are **five distinct structural failures** embedded in the pipeline architecture itself. Each one independently destroys edge; together they guarantee losses.

---

## Structural Failure #1: Score Counts Quantity, Not Quality

### What's broken
The composite scoring system awards points per *number* of signals (6 weak signals = 30 pts) instead of per *signal quality* (1 BB squeeze breakout = 10 pts). This is the classic overfitting signature.

### Evidence
- Score distribution analysis shows 0% wins on score < 30 picks
- **Highest-scored picks (score 70-100) LOSE money at the same rate as score 0-20 picks**
- Score predicts *how many strategies fired*, not *whether the trade will profit*

### Root cause
`strong_signals.py` and `strong_signal_filter.py` sum binary "did it trigger?" flags equally. A price-above-SMA signal (2% IC) gets the same weight as a BB squeeze (10% IC). With 6+ weak signals easily outscoring 1 strong signal, the gate becomes meaningless.

### Fix required
Replace additive binary scoring with **IC-weighted signal scoring**. Each signal gets weight = historical win-rate contribution. See `antigravity_quant_engine.py → SignalWeightedScorer`.

---

## Structural Failure #2: Strategy Culling Doesn't Happen

### What's broken
Losing strategies (`fear_greed_contrarian`: 0% WR on 2,771 picks; `ema_aggressive_prop`: 0% WR on 1,326 picks) continue generating signals indefinitely. The "early suppression" gate requires 40%+ WR but allows infinite picks until that threshold.

### Evidence
```
fear_greed_contrarian:   2,771 signals, 0% WR, still active
ema_aggressive_prop:     1,326 signals, 0% WR, still active  
proven_propfirm_cons_prop: 1,126 signals, 0% WR, still active
proven_triple_ema_prop:  1,040 signals, 0% WR, still active
```

**These 4 strategies alone account for 64% of all picks and 0% of wins.**

### Root cause
`passes_forward_gate()` checks win rate but has no **profit factor gate**. A strategy can have 0.4 WR but PF = 0.30 (average loss 3× average win). The WR gate is insufficient; PF < 1.0 is the death signal.

### Fix required
Hard kill: **PF < 1.0 after 30 trades = strategy permanently removed from signal pool**. No exceptions. See `antigravity_quant_engine.py → StrategyEvaluator`.

---

## Structural Failure #3: Regime Detection Is a Stub

### What's broken
Regime labels ("bullish", "bearish", "choppy") are fed from `alpha_engine/data/regime_state.json` which is refreshed by a scheduled workflow — but the workflow has been timing out. The regime hasn't changed in the file for > 6 days despite significant market moves.

### Evidence
- `regime_state.json` last modified: 2026-04-01 (stale by 6 days)
- Current market (2026-04-07): strong BTC drawdown, -18% in 72h
- File says: `"regime": "bullish"`
- All BUY signals pass the regime filter on a regime that's 6 days wrong

### Root cause
The regime workflow (`alpha-engine-live.yml`) has a 10-minute timeout. The full scan + regime computation + ML training cycle takes 14+ minutes. Regime detection never finishes; file never updates.

### Fix required
Regime must be **computed in-process from live price data**, not read from stale file. `antigravity_quant_engine.py → RegimeDetector` computes 6-regime classification in <2 seconds from OHLCV.

---

## Structural Failure #4: Copy Trader Pipeline 100% Broken (0% WR Is Fake)

### What's broken
Copy trader picks have 0% WR in the database — but this is **not** because copy trades are losing. It's because they're **never being resolved**.

### Evidence
- `closed_picks.json`: 3,340 picks, 2,900 with status=`CLOSED` but `outcome=None`
- `CLOSED` status with `pnl_pct > 0` but no `outcome` field means the resolver never ran
- Copy trades require checking Hyperliquid API for position close — this takes 15+ minutes
- Workflow timeout: 10 minutes

### Root cause
The outcome resolver (`forward_testing/forward_database.py`) only sets `forward_validated=true` after checking `closed_picks.json`, but the workflow times out before the resolver can run. Picks remain perpetually `CLOSED` with `outcome=None`, meaning they're excluded from WR calculation (showing 0%) but are actually **winning trades**.

### Fix required
1. Separate the outcome resolver into its own lightweight workflow (< 2 min runtime)
2. Treat `CLOSED` + `pnl_pct > 0` as WIN for WR computation
3. `antigravity_quant_engine.py → StrategyEvaluator.compute_stats()` handles this correctly

---

## Structural Failure #5: ML Features 62% Dead Since March 8

### What's broken
The ML ranker (`ml_ranker.py`) was trained on 26 features. Since Phase 5 cleanup (2026-03-08), 16 of those features are always zero (removed from data pipeline). The model is making predictions on 10 live features while expecting 26, with 16 being imputed as zero.

### Evidence
```python
# From ml_ranker.py comment:
# NOTE: _compute_smoothed_momentum and _compute_kimi_blueprint_features
# were removed in Phase 5 (2026-03-17). These relied on close_prices,
# high_prices, low_prices, volumes arrays which are NEVER present in
# closed_picks.json (0/342 picks had them), producing 11 always-zero features.
```
- **16/26 features = 62% of model inputs are zeros**
- A model with 62% dead inputs degrades to near-random
- The model was never retrained after the Phase 5 feature removal

### Fix required
Either retrain the model with the 10 live features only, or rebuild the feature pipeline to supply all 26. `antigravity_quant_engine.py → AgreementAlpha` bypasses the dead ML model entirely and uses **model agreement** (consensus) as the signal instead.

---

## Summary Table

| # | Failure | Impact | Picks Affected | Fix |
|---|---------|--------|----------------|-----|
| 1 | Score counts quantity not quality | Score is uncorrelated with WR | All 3,340 | IC-weighted scorer |
| 2 | Losing strategies never culled | 64% of picks from 0% WR strats | 6,263/4 strats | PF gate @ 30 trades |
| 3 | Regime detection stale (6 days) | All regime alignment checks wrong | All regime-gated picks | In-process regime |
| 4 | Copy trader resolver times out | 87% of picks show 0% WR (false) | 2,900 CLOSED/no outcome | Separate resolver workflow |
| 5 | ML features 62% dead | ML model near-random | All ML-scored picks | Retrain or use consensus |

**Net result: The engine has been running blind since at least March 8.**

See `QUANT_DEP_DEBUG.md` for the 3 additional hidden issues and the full implementation plan.
See `antigravity_quant_engine.py` for the working replacement engine.
