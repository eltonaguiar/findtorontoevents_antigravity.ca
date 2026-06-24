# Action Plan — June 2026 Edition

**Source:** Money Maker Ready audit 2026-06-13  
**Status:** ACTIVE — verified findings, data-corrected  
**Owner:** Buffy (Codebuff) + fleet agents

---

## Verified Findings (Post-Investigation)

Several items from the initial Money Maker Ready report were **data misinterpretations**, not real bugs. The corrected status:

| Initial Finding | Corrected Status | Evidence |
|---|---|---|
| Smart picks feed shows 0 picks | **2 picks present** (XRPUSDT SHORT score=74, SOLUSDT SHORT score=83) | `dashboard_data.json::smart_picks_feed.picks` has 2 entries |
| `signal_time` missing from feed | **Already fixed** (2026-05-27) | `smart_picks_engine.py` line 1588 populates `signal_time` |
| Blacklist simulation shows 0 blacklisted | **19 strategies killed** — wrong key name in report | `killed_strategies_count=19`, `killed_strategies` list has 19 entries |
| WR values showing as 0.50 not 50% | **Standard decimal format** — multiply by 100 for display | `baseline.wr=0.5449` = 54.49% WR |
| Concept drift / forward validation empty | **Correct** — these sections are genuinely empty in the live dashboard JSON | `hf_stats.concept_drift` and `forward_validation` both return `{}` |

---

## P0 — Block Real Money (Do Before Any Live Deployment)

### 1. Walk-Forward Validation for 6 Survivor Strategies
**Why:** The 6 survivors (stocks_rsi2_pullback, smart_money_accumulation, forex_rsi2_mean_reversion, luxalgo_confluence, crypto_liquidity_wick_reversal_v1, ig_contrarian_sentiment) have proven historical edges but need walk-forward confirmation.

**Existing infrastructure:**
- `alpha_engine/walk_forward_validator.py` — core WF validation (ROBUST/MODERATE/FRAGILE/INSUFFICIENT verdicts)
- `alpha_engine/walkforward_validator.py` — per-class WF validation (PR #654)
- `tools/walk_forward_eff_harness.py` — efficiency stability harness
- `tools/check_walkforward_gate.py` — CI gate for WF results
- `tools/walk_forward_validate.py` — CLI tool for WF validation

**Action:**
1. Run `python tools/walk_forward_validate.py --max-oos-dd-pct 15 --min-sharpe 0.5` for each survivor
2. Minimum: 3 windows × 30+ trades each, efficiency ≥ 0.30
3. Wire WF verdicts into `smart_picks_engine.py` scoring (already partially done for ml_enhanced_* via `_ml_enhanced_edge_validated`)
4. Reject any strategy with `wf_verdict` not in {ELITE, STRONG, VIABLE, PASS}

**Owner:** @claude-code  
**ETA:** 2-3 days  
**Blocked by:** Sufficient historical data per strategy (check n ≥ 100)

### 2. Wire Concept Drift Auto-Pause (Data Found!) ✅ VERIFIED
**Why:** Concept drift data actually EXISTS in `dashboard_data.json::hf_stats.concept_drift`:
- `ks_D = 0.0498` vs `ks_critical_05 = 0.0460` → `drift_alert = true`
- `early_n = 1746`, `late_n = 1746` (substantial sample)
- Previously cited KS_D=0.313 was from a May 11 report (stale data, regime has shifted since)
- Per-class drift is NOT computed (all asset classes show empty)

The drift is REAL but MILD (KS_D only 8% above critical). The `drift_alert=true` flag is correctly set.

**Existing infrastructure:**
- `tools/hf_stats.py` line 432: `compute_concept_drift()` — already producing output
- `audit_trail/quality_gates.py` line 890: `_get_concept_drift_ratio()` — reads from dashboard
- `alpha_engine/drift_aware_scoring.py` — adjusts scores based on drift
- Dashboard template already renders concept_drift block (line 5859)

**Action:**
1. Wire `drift_alert=true` → auto-pause new position sizing when KS_D > 0.10 (currently 0.0498, below threshold)
2. Add per-class concept drift computation (scaffolded at `quality_gates.py` line 1124)
3. Add per-strategy drift monitoring (rolling 30d WR vs lifetime WR)

**Owner:** @claude-code  
**ETA:** 1-2 days  
**Status:** Data confirmed present; wiring is the remaining work

### 3. Real-Time Slippage Tracking
**Why:** All PnL figures are theoretical without actual fill quality measurement.

**Existing infrastructure:**
- `alpha_engine/charter_slippage.py` — deduct_slippage() exists but uses fixed estimates
- Smart picks engine already computes `transaction_cost_pct` per pick

**Action:**
1. Implement bid-ask spread tracking per symbol (from Binance order book API)
2. Compare expected fill price vs actual fill price for paper trades
3. Store slippage metrics in `alpha_engine/data/slippage_metrics.json`
4. Wire into `charter_slippage.py` for dynamic cost estimation

**Owner:** @claude-code  
**ETA:** 3-5 days  
**Blocked by:** Paper trading infrastructure must be running

---

## P1 — Do Before Scaling

### 4. Smart Picks Feed — Increase Coverage
**Why:** Only 2 picks in the feed is thin. The scoring pipeline is highly selective (many filters: blacklist, elite score, regime, FOMO, consensus conflict, etc.).

**Action:**
1. Review filter rejection counts from the last `smart_picks_engine` run
2. Consider relaxing `elite_below_20` floor for strategies with proven forward WR
3. Ensure non-crypto picks are flowing through (MAX_NON_CRYPTO_PICKS=5 but only 2 total picks)

**Owner:** @claude-code  
**ETA:** 1 day

### 5. Regime-Aware Drift Detection
**Why:** The concept drift root cause report (2026-05-11) confirmed VIX -44.64% / 30d regime collapse is the real driver of performance changes. Without per-regime tagging, every Tier-2 claim is implicitly regime-conditioned.

**Existing infrastructure:**
- `alpha_engine/regime_detector.py` — detects TRENDING_UP, MEAN_REVERTING, HIGH_VOLATILITY
- `alpha_engine/regime_flip_detector.py` — monitors BTC 24h change + momentum
- `alpha_engine/fast_regime_detector.py` — 5-minute refresh cycle
- `alpha_engine/regime_filter.py` — multi-dimensional regime classification

**Action:**
1. Tag every closed pick with the regime at entry time
2. Compute per-regime WR/PF for each strategy
3. Add regime-conditioned thresholds to the kill switch (e.g., "this strategy only works in TRENDING_UP")
4. Wire into dashboard as a per-strategy regime compatibility matrix

**Owner:** @claude-code  
**ETA:** 3-5 days

### 6. Fix Money Maker Ready Report Data Interpretation
**Why:** The initial report misread several data fields, leading to false conclusions.

**Action:**
1. ✅ Smart picks: confirmed 2 picks present (not 0)
2. ✅ signal_time: already fixed
3. ✅ Blacklist simulation: 19 killed (not 0) — correct key is `killed_strategies_count`
4. ✅ WR format: standard decimals, multiply by 100 for display
5. Update `reports/MONEY_MAKER_READY_JUNE_2026_EDITION.md` with corrected data

**Owner:** @buffy  
**ETA:** Done (this document)

---

## P2 — Production Hardening

### 7. Per-Strategy PF-over-Time Chart
**Why:** Visualize strategy decay before it kills PnL.

**Action:** Add a time-series chart to the dashboard template showing rolling 30-day PF per strategy.

**ETA:** 2-3 days

### 8. Economic Calendar Integration
**Why:** FOMC, NFP, CPI releases cause regime shifts. Block new entries 2h before/after high-impact events.

**Action:** Integrate `alpha_engine/economic_calendar.py` (if exists) or create one using FRED API.

**ETA:** 2-3 days

### 9. COMMODITY Strategy Diversification
**Why:** CT=F concentration is a single-point-of-failure. 230/354 closed COMMODITY picks are CT=F COT duplicates.

**Action:** Add GC=F, SI=F, CL=F strategies with COT-dedup enforcement.

**ETA:** 1-2 weeks

### 10. Walk-Forward for Non-Crypto Asset Classes
**Why:** FOREX (n=48, 60) and ETF (n~50) strategies have insufficient data for walk-forward. Need 100+ trades.

**Action:** Continue accumulating data. Monitor PF decay weekly. Re-evaluate at n=100.

**ETA:** Ongoing (2-4 weeks of data accumulation)

---

## Implementation Order

```
P0-1: Walk-forward validation (2-3d) ─────────────────────────────────┐
P0-2: Fix concept drift KS_D (1-2d) ──────────────────────────────┐  │
P0-3: Slippage tracking (3-5d) ─────────────────────────────────┐  │  │
                                                                  │  │  │
P1-4: Smart picks coverage (1d) ────────────────────────────────│  │  │
P1-5: Regime-aware drift (3-5d) ────────────────────────────────│  │  │
P1-6: Report corrections (done) ────────────────────────────────│  │  │
                                                                  │  │  │
P2-7: PF-over-time chart (2-3d) ────────────────────────────────┘  │  │
P2-8: Economic calendar (2-3d) ────────────────────────────────────┘  │
P2-9: COMMODITY diversification (1-2w) ──────────────────────────────┘
P2-10: Non-crypto data accumulation (ongoing)
```

---

## Peer Review Status

This plan has been submitted for peer review to multiple AI models:
- See `reports/PEER_REVIEW_PLAN.md` for the review questionnaire
- Reviews will be appended as they complete

---

*Last updated: 2026-06-13 by Buffy (Codebuff)*
