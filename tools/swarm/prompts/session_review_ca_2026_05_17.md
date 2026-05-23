# Session CA Review — 2026-05-17/18

## Context
Continuation of PATH_TO_PROVEN_EDGE across sessions BY→BZ→CA (same day, multiple context-window resets).
Goal: complete all MASTER_ACTION_PLAN todos and feed transcripts to swarm for review.

## Session deliverables

### 1. walk-forward eff-stability harness (PATH_TO_PROVEN_EDGE Step 1)
- File: `tools/walk_forward_eff_harness.py` (committed d9bc76f596)
- Result: **0/7 scores admissible** — `elite_score` Cohen's d eff≈0.005 = NOISE
- All score fields tested: elite_score, ml_score, ml_composite_score, confidence, method_a_score, risk_reward, forward_wr
- Only `cot_positioning` and `cftc_cot_commercial_signal` show WR>70% but these are STRATEGY-level signals, not score fields
- **Implication: current pick ranker (elite_score) is random. We are NOT sorting picks by quality.**

### 2. M-039 Cross-commodity spread momentum (OPT-IN sidecar)
- File: `tools/research/commodity_spread_momentum.py` (committed 6c1b854871)
- Live results: CL/NG spread_pnl=+0.0138 PROMISING, CT/KC spread_pnl=+0.0475 PROMISING, GC/SI FLAT
- 8 tests passing. Wiring plan: opt-in env var COMMODITY_SPREAD_MOMENTUM_ENABLED=1

### 3. M-060 Monthly calibrator refit cron
- File: `.github/workflows/monthly-calibrator-refit.yml` (committed fa1c621e77)
- Runs 1st of each month 07:00 UTC; commits confidence_calibrators.json + dated report

### 4. M-107 Hypothesis pre-registration gate (DONE)
- File: `reports/hypothesis_registry.json` (committed 894f678ba3)
- H-001: COT (LIVE_TESTING, WR=78.4% 2 windows, needs 3rd)
- H-002: EQUITY PEAD (PENDING_IMPLEMENTATION — needs SUE earnings data)
- H-003: ETF 12-1 momentum (PENDING_IMPLEMENTATION — needs historical ETF returns)
- H-004: COMMODITY inventory-surprise roll yield (PENDING_IMPLEMENTATION — needs EIA/USDA)
- H-005: futures_momentum inversion — TESTED, REFUTED, ARCHIVED

### 5. futures_momentum anti-signal investigation (H-005 REFUTED)
- LONG picks: avg_pnl=-0.0274, WR=2.0% (n=148)
- SHORT picks: avg_pnl=-0.0276, WR=1.9% (n=54)
- Conclusion: SYMMETRIC FAILURE. Not an inversion bug. Both directions equally broken.
- **Operator must approve block before implementation**

### 6. dropchat-multipc
- Session BZ: gateway DOWN → CHATBIBLE_FAILURE.MD appended, events.jsonl fallback
- Session CA: gateway UP → SESSION_SUMMARY broadcast sent (message_id=e317b5e4), inbox empty

## Open operator decisions (CANNOT implement without user approval)
1. Block futures_momentum (WR=2%, n=202) — confirmed NOT anti-signal, truly broken
2. Reduce quan_engine_scalp volume share (n=5293, WR=29.9%)
3. Block cta_replicator COMMODITY (WR=12%, n=83)

## Key finding requiring strategic response
**elite_score eff=0.005 means we are NOT differentiating pick quality.** 
The correct next steps per PATH_TO_PROVEN_EDGE:
- Step 2: Identify what dimension DOES separate winners from losers (strategy-level WR is the best current signal)
- Step 3: Wire strategy-level WR as the primary ranking signal instead of elite_score
- Step 4: Implement H-002/H-003/H-004 once data sources are identified

## Review questions
1. Is the walk-forward eff harness correctly rejecting all 7 score fields? Is Cohen's d the right test statistic, or should we use AUC-ROC or rank-biserial correlation instead?
2. Given elite_score is NOISE, should we immediately replace it with strategy-level WR as primary ranker? What are the risks?
3. For H-001 COT: WR=78.4% (n=134) across 2 windows — does this require a 3rd window, or is n=134 sufficient evidence with p<0.001?
4. Should we accelerate H-002 PEAD using free earnings data (Yahoo Finance earnings calendar + historical SUE from Zacks/Estimize)?
5. Are the 3 pending operator decisions (futures_momentum, quan_engine_scalp, cta_replicator) safe to implement based on the evidence, and what would be the net PF impact?

## Commits this session
- d9bc76f596: feat(edge): walk-forward eff-stability harness (PATH_TO_PROVEN_EDGE step 1)
- fa1c621e77: feat(M-060): monthly calibrator refit workflow + stale PENDING corrections
- b09cdf004f: docs: MASTER_ACTION_PLAN stale corrections (M-018, M-039, M-107)
- 6c1b854871: feat(M-039): cross-commodity spread momentum research module + 8 tests
- 894f678ba3: feat(edge): M-107 hypothesis pre-registration registry + futures_momentum REFUTED
