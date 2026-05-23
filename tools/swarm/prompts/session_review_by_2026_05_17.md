# Session BY Review — 2026-05-17

## Context
This session built PATH_TO_PROVEN_EDGE Step 1 (walk-forward eff-stability harness) and
performed a strategy-level edge analysis. It also synthesized findings from a 4-model
cloud brainstorm (NO_EDGE_BRAINSTORM_CLOUD.MD) that was pushed to GitHub during the session.

## Session deliverables

### 1. tools/walk_forward_eff_harness.py (PATH_TO_PROVEN_EDGE Step 1)
Walk-forward eff-stability harness. A score is gate-admissible ONLY if:
- Cohen's d eff >= 0.30
- Same sign (direction stable)
- Across >= 3 consecutive 14-day rolling windows

Live result on n=8422 closed picks:
- elite_score: WEAK (eff≈0.005 = NOISE — current primary ranker is random)
- method_a_score: UNSTABLE (sign flips: eff=1.14 window 0, inverted window 1)
- ml_score: WEAK
- confidence: WEAK
- risk_reward: WEAK
- ml_composite_score: WEAK
- forward_wr: INSUFFICIENT_DATA
**0/7 scores are admissible. The system has no proven discriminating signal.**

### 2. tests/test_walk_forward_eff_harness.py
42 tests covering _eff, _is_win, _parse_dt, admissibility_verdict, run_harness.
All 42 pass.

### 3. reports/edge_analysis_by_strategy_2026-05-17.md
Strategy-level WR table (n=8422 total closed picks):
- PROVEN EDGE: cot_positioning (WR=78.4%, n=134) + cftc_cot_commercial_signal (WR=74.8%, n=131)
- DESTROYING: futures_momentum (WR=2.0%, n=202), forex_carry_momentum (WR=5.1%, n=178)
- HIGH-VOLUME DRAG: quan_engine_scalp (n=5293, WR=29.9%, avg_pnl=-0.1814)
- COT edge stable across 2 windows: cot_positioning 77%/81%, cftc_cot_commercial_signal 72%/84%

### 4. MASTER_ACTION_PLAN Section 29 added
Synthesized 4-model cloud brainstorm (NO_EDGE_BRAINSTORM_CLOUD.MD):
- UNANIMOUS: stop FOREX, kill ml_enhanced sprawl, remove kill-threshold ratchet
- Top EV moves: EQUITY PEAD, ETF 12-1 momentum, COMMODITY inventory-surprise roll yield
- New: M-107 pre-registration gate filed

## Questions for review

1. Is the eff-stability harness implementation (Cohen's d, window logic, admissibility verdict) correct?
2. Is the 0/7 scores result consistent with the broader system picture (no proven discriminating signal)?
3. Are the strategy-level WR findings trustworthy given the limitations (2 windows only for COT)?
4. Is M-107 (pre-registration gate) the right next step vs other pending items?
5. Any concerns about the operator-decision items (futures_momentum block, quan_engine_scalp volume)?

## Operator-pending decisions (cannot implement without user approval)
- Block futures_momentum (WR=2.0%, n=202) from FUTURES class
- Reduce quan_engine_scalp volume share (n=5293, WR=29.9%, avg_pnl=-0.1814)
- Block cta_replicator COMMODITY (WR=12%, n=83) — previous session decision pending

## Commit
d9bc76f596 — feat(edge): walk-forward eff-stability harness (PATH_TO_PROVEN_EDGE step 1) + edge analysis by strategy
