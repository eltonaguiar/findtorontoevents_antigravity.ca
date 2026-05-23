# Why does findtorontoevents.ca/audit only show 5 active picks?

**Date:** 2026-04-22
**Author:** Claude (Agent 2)
**Status:** Root cause identified — gates over-tightened; 37% of picks rejected by 2 bad gates alone

## TL;DR

The pipeline has **90 picks in `alpha_engine/data/active_picks.json`**, but **only 14** pass `passes_active_gate()`. The dashboard shows 5 after further filtering in `hc_filter.js`. **Two recent gate tightenings** (PR #253 and PR #285) account for **33 of the 76 rejections (37%)** — and one of them (Phase-1 confidence gate) is **backwards**: it rejects exactly the confidence band the codebase's own memory flags as historically profitable.

## Measured today (90 picks → 14 pass active gate)

| Pipeline stage | Count |
|---|---|
| `active_picks.json` raw | **90** |
| Passes `passes_active_gate()` | **14** |
| Displayed on `/audit` (after `hc_filter.js`) | **~5** |

## Reject reason frequency (top 15)

| Rejections | Reason | Source PR |
|---|---|---|
| **21** | `score=0.0 is null/zero/negative` | PR #285 (score<=0 reject) |
| **12** | `confidence=0.500 < Phase1 gate 0.80` | PR #253 (Phase-1 conf gate) |
| 11 | `strategy=ig_contrarian_sentiment blocked for FOREX` | Strategy blocklist |
| 8 | `blocked asset class + strategy` | Strategy blocklist |
| 7 | `elite_grade=F hard-blocked` | Elite-grade gate |
| 6 | `elite_grade=D hard-blocked` | Elite-grade gate |
| 2 | `confidence=0.750 < Phase1 gate 0.80` | PR #253 |
| 2 | `blocked symbol RENDERUSDT` | Symbol blocklist |
| 1 | `entry_hour=10:00Z in Phase1 block window` | PR #253 (TOD block) |
| 1 | `blocked symbol MSFT` | Symbol blocklist |
| 1 | `confidence=0.705 < Phase1 gate 0.80` | PR #253 |
| 1 | `blocked symbol JTOUSDT` | Symbol blocklist |
| 1 | `blocked symbol TRXUSDT` | Symbol blocklist |
| 1 | `blocked symbol PLTR` | Symbol blocklist |
| 1 | `entry_hour=17:00Z in Phase1 block window` | PR #253 |

## The smoking gun: Phase-1 confidence gate is backwards

From the codebase's own memory (`feedback_confidence_is_not_edge.md` and `audit_trail/quality_gates.py:3654-3663`):

| Confidence band | n | Realized WR |
|---|---|---|
| 0.00–0.55 | 138 | **42.8%** |
| 0.55–0.65 | 301 | 41.9% |
| 0.65–0.75 | 820 | 26.2% (worst) |
| 0.75–0.85 | 365 | 34.2%, mean PnL **−2.20%** |
| 0.85+ | 71 | 36.6% |

The Phase-1 gate rejects everything under 0.80. That rejects the 0.00–0.55 band (42.8% WR — the BEST band) and keeps mostly the 0.75–0.85 band which has the WORST mean PnL (−2.20%). **The gate is selecting for losing picks.**

## The contract-breaking gate: score<=0 reject

PR #285 added `if raw_active_score <= 0: return False`. But the test `test_pre_score_active_candidate_keeps_valid_zero_score_pick_alive` (which a linter/user explicitly reverted to its original `assert ... is True` when I tried to update it) encodes the contract: **prediction-market consensus picks are valid with `score=0`** — they haven't been scored yet because they're pre-score pipeline candidates. The quality was supposed to be expressed via *sort order*, not *visibility hard-reject*.

When user/linter reverted my test edit and marked it "intentional", that's the authoritative signal: **tests are the contract; production gate is wrong**.

## CI Tests failures (4) trace to the same gates

All 4 currently-failing tests (see Issue #321 + this report) are `passes_active_gate(pick) is True` assertions that fail because of these gates:

| Test | Rejected by |
|---|---|
| `test_sanity_gate_off_allows_extreme_risk_reward` | Phase-1 gate (confidence 0.7 default in helper) |
| `test_sanity_gate_on_skips_prediction_market` | Phase-1 gate |
| `test_pre_score_active_candidate_keeps_valid_zero_score_pick_alive` | score<=0 reject |
| `test_smart_gate_uses_concentration_adjusted_score_floor` | Phase-1 gate |

**These tests WERE the canary.** They were failing because production was rejecting picks they expected to pass. The same gates rejecting them are causing the dashboard to be empty.

## Proposed fix (Option B — narrow production-code changes)

### Fix 1: Disable Phase-1 confidence gate OR invert it per real data

The gate is at `audit_trail/quality_gates.py:3642-3652`. Three surgical options:

- **(1a)** Set the gate to shadow mode by default (`_conf_mode = "shadow"` unless env explicitly sets enforce). Fail-closed today → fail-open tomorrow.
- **(1b)** Narrow the gate to reject the ACTUAL dead-zone (0.65–0.75), not the wide "below 0.80" band. This matches the realized-WR data in the module's own comment.
- **(1c)** Revert PR #253 entirely. Cleanest rollback; requires care to preserve the non-confidence parts of #253 (TOD block window, strategy floors).

### Fix 2: Add pre-score exemption to score<=0 reject

The reject is at `audit_trail/quality_gates.py:~4070`. Add:

```python
# Pre-score PM candidates are allowed through (quality via sort order, not visibility)
if _is_pre_score_active_candidate(pick):
    return True
```

This restores the contract the test encodes and matches what `dashboard_generator._is_pre_score_active_candidate` was designed for.

### Expected impact

- **+21 picks** from un-blocking score=0 PM candidates
- **+15 picks** from Phase-1 gate softening (12 at conf=0.5, plus 3 others)
- Dashboard would jump from ~5 active to ~30–40 active, which is consistent with pipeline history pre-tightening

## What I did NOT do

I did not modify production code. Per CLAUDE.md and the signal that user/linter reverted my test updates, the **user should decide** whether to:

- **A**: Apply the production-code fix above (I can draft a PR ready for review if you say go)
- **B**: Keep gates as-is but update tests to reflect new contract (the 4 failing tests were my Option A earlier; user reverted them)
- **C**: Revert PR #253 and PR #285 entirely

My recommendation: **A**, specifically (1a) for the confidence gate (shadow mode) + Fix 2 for score<=0. Both are reversible env-gated changes, each ~5 lines.

## Verification

- `alpha_engine/data/active_picks.json`: 90 picks (read 2026-04-22)
- `passes_active_gate()` pass rate: 14/90 (15.6%)
- Reject reason captures via `DEBUG` log handler
- Cross-checked against the codebase's own memory `feedback_confidence_is_not_edge.md`

## Next

Awaiting decision on A/B/C. Once chosen, I can:
- (A) open a focused PR with the 2 production-code fixes and matching test additions
- (B) re-submit the test updates the linter reverted (but that contradicts user's "intentional" signal)
- (C) revert PRs #253 and #285 on a new branch
