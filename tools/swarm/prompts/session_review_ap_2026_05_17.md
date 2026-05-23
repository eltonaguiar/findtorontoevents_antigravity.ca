# Session AP — Swarm Review Request
# Date: 2026-05-17
# Session: AP (following AO — APPROVE)

## Context

Session AP: diagnostic session focusing on shadow tracker findings, EQUITY data path
investigation, and gate calibration analysis. No code changes made.

## Session AP Findings

### 1. WINNER_FILTER: cross_sectional_reversal Blocked by confidence_max=0.85

**Finding:** 7 `cross_sectional_reversal` picks blocked by WINNER_FILTER, 5 resolved:
- All blocked because `confidence=0.902` > `WINNER_FILTER_CONFIG["confidence_max"]=0.85`
- RR=2.00 on all picks (within `rr_min=1.5, rr_max=3.0`)
- 5 resolved outcomes: 5 KILLED_ALPHA, 0 SAVED

| Symbol | Strategy | Confidence | RR | Outcome | PnL if traded |
|--------|----------|------------|-----|---------|--------------|
| GIGGLEUSDT | cross_sectional_reversal | 0.902 | 2.00 | UNRESOLVABLE | N/A |
| GIGGLEUSDT | cross_sectional_reversal | 0.902 | 2.00 | UNRESOLVABLE | N/A |
| AAVEUSDT | cross_sectional_reversal | 0.86 | 2.00 | KILLED_ALPHA | +0.85% |
| AAVEUSDT | cross_sectional_reversal | 0.902 | 2.00 | KILLED_ALPHA | +1.91% |
| NEIROUSDT | cross_sectional_reversal | 0.902 | 2.00 | KILLED_ALPHA | +11.58% |
| AAVEUSDT | cross_sectional_reversal | 0.902 | 2.00 | KILLED_ALPHA | +2.61% |
| NEIROUSDT | cross_sectional_reversal | 0.902 | 2.00 | KILLED_ALPHA | +12.45% |

**Statistics:** 5/5 resolved picks would have won. Avg PnL = +5.88%.

**Root cause:** `cross_sectional_reversal` always outputs confidence ≥ 0.86, which exceeds the
confidence ceiling. The original `confidence_max=0.85` was calibrated on broader data showing
>0.85 = 9.1% WR (overfit). But `cross_sectional_reversal`'s high-confidence picks appear to be
legitimate (NEIROUSDT +11.58/+12.45 hit TP).

**Concern:** Sample n=5 is too small to override the global threshold. But all 5 were winners —
this warrants monitoring.

### 2. Gate Shadow Stats (full picture)

| Gate | Total Blocks | Resolved | Save Rate | Avg PnL if Traded |
|------|-------------|----------|-----------|-------------------|
| QUALITY_GATE | 420 | 202 | 44.1% | -0.38% |
| RR_GATE | 63 | 46 | 50.0% | +0.47% |
| WINNER_FILTER | 7 | 5 | 0.0% | +5.88% |
| FOREX_GATE | 10 | 0 | N/A | N/A |

**Interpretations:**
- QUALITY_GATE: working correctly (avg PnL -0.38% if traded = gate is blocking losers)
- RR_GATE: borderline (50% save rate, +0.47% avg = slightly profitable if unblocked)
- WINNER_FILTER: potentially over-blocking for cross_sectional_reversal specifically (n=5)

### 3. EQUITY Data Path Investigation

`money_ready_verdict.py` reads from `alpha_engine/data/closed_picks.json` only.
`audit_trail/data/universal_resolved_picks.json` has 162 EQUITY picks but ALL have
status=`CLOSED` (not `WON`/`LOST`) and many are mislabeled (DOGE-USD tagged as EQUITY).
Not a clean source — the EQUITY dashboard n=240 comes from MySQL (not accessible locally).

EQUITY verdict WATCH with dashboard_fallback n=240 WR=54.2% is the best available picture.
Adding universal_resolved_picks as source would not improve data quality.

### 4. Pending User Approvals from Session AO

Both still pending:
1. Block `cta_cross_asset_tsmom` for COMMODITY (WR=12.7% n=71)
2. Add `CONCENTRATION_CAP_BY_CLASS = {"COMMODITY": 0.85}` (CT=F at 81.6% when tsmom blocked)

### 5. CI Status

- 0 stale failures, no open PRs
- All FOOLPROOF items remain externally blocked or monitoring-only

## Questions for Swarm

1. **WINNER_FILTER threshold review**: With n=5 KILLED_ALPHA and avg +5.88% for
   `cross_sectional_reversal` (confidence=0.902), should we:
   a) Wait for n≥20 before considering threshold change (conservative)
   b) Whitelist `cross_sectional_reversal` from confidence_max restriction (surgical)
   c) Raise confidence_max from 0.85 to 0.90 globally (risk: might reintroduce overfit)
   d) Add a per-strategy confidence_max override in WINNER_FILTER_CONFIG

2. **RR_GATE calibration**: save_rate=50% with +0.47% avg PnL if traded — is this a
   signal that RR_GATE should be relaxed? Or is 50% save rate still valuable at the
   marginal pick level?

3. **cross_sectional_reversal promotion**: This strategy has n≥5 forward test data, all
   wins. The shadow tracker in M-075 uses n≥10/WR≥50%/PF≥1.5 for promotion. With 5/5
   wins but n<10, should we promote early (wait for n=10) or document as WATCH?

4. **Overall verdict**: Is Session AP APPROVE? No code changes made — diagnostic only.

## Verification

- CI: 0 failures
- Shadow tracker: 500 entries, 4 gate types analyzed
- Commits: none this session
- Prior commits: M-080 + M-081 (Session AN), diagnostic sessions AO + AP
