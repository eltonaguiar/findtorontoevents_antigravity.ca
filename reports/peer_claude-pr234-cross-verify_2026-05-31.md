# PR #234 Cross-Verification (Meta Red-Team)

**Date:** 2026-05-31
**Reviewer:** claude-opus-4-7 (cross-verify subagent)
**Subject:** PR #234 (`docs/pr232-red-team-2026-05-31`) — the red-team report of PR #232's 5 operator-ready diffs.
**Task framing:** independently verify that PR #234's *own* claims (symbol existence, DB counts, scope citations) are real and not hallucinated.

## Premise note

The orchestrator brief described PR #234 as a "corrections PR" addressing PR #232's fabrications. PR #234 is in fact the red-team **report** of PR #232 (verdict: 3 FABRICATED, 2 NEEDS_CORRECTION, 0 VERIFIED). No corrective diffs were proposed in code; PR #234 recommends revoking PR #232. This meta-verification therefore checks whether PR #234's red-team findings are themselves trustworthy.

## Independent verification

### Item 1 — confidence 0.8-bucket dampener

- `_compute_ml_composite` at `alpha_engine/smart_picks_engine.py:82` — VERIFIED (grep hit).
- `_calibrate_confidence` (import alias line 45 / fallback line 47), `_effective_confidence_for_ranking` (line 23), `_trusted_forward_wr` (line 431) — all VERIFIED.
- PR #227 body cites `asset_class == CRYPTO` scope explicitly — VERIFIED via `gh pr view 227`.
- Confidence-bucket WR table in PR #227: 0.7→42.3%, 0.8→22.0%, 0.9→37.5%, 1.0→52.1%. PR #234's "0.9 actually 37.5% not 39-43%" call-out — VERIFIED.

**Verdict: REALLY_VERIFIED.** PR #234's NEEDS_CORRECTION judgment for Item 1 is accurate.

### Item 2 — FOREX kill list + dxy_trend_filter

DB query against `ejaguiar1_stocks.trading_picks`:

| Strategy | Rows | Source |
|---|---|---|
| `dxy_trend_filter` | 0 | PR #234 claim CONFIRMED |
| `cross_momentum_dxy` | 1 | PR #234 claim CONFIRMED |
| `dxy_correlation_regime` | 1 | PR #234 claim CONFIRMED |
| `cta_cross_asset_tsmom` | 2015 | PR #234 claim CONFIRMED |
| `forex_carry` (exact) | 0 | PR #234 claim CONFIRMED |
| `forex_carry_momentum` | 1182 | PR #234 claim CONFIRMED |
| `BLACKLISTED_STRATEGIES` at `config.py:257` | symbol exists | CONFIRMED |

**Verdict: REALLY_VERIFIED.** PR #234's FABRICATED judgment for Item 2 is accurate — `dxy_trend_filter` truly does not exist.

### Item 3 — COMMODITY COT quarantine

DB query against `ejaguiar1_stocks.trading_picks`:

| Strategy | Rows |
|---|---|
| `cot_commercial_extreme` | 0 |
| `cot_speculator_reversal` | 0 |
| `cot_managed_money_flip` | 0 |
| `cot_positioning` | 59 |
| `cftc_cot_commercial_signal` | 41 |

PR #234 numbers (n=59, n=41) for the real COT emitters — EXACT MATCH.

**Verdict: REALLY_VERIFIED.** PR #234's FABRICATED judgment for Item 3 is accurate.

### Item 4 — EQUITY `stocks_rsi2_pullback` un-kill

- `stocks_rsi2_pullback` at `config.py:270` inside `BLACKLISTED_STRATEGIES` — CONFIRMED via grep, including the comment "10 EQUITY trades, WR 30%, PF 0.032" matching the historical kill rationale.
- DB row count for `stocks_rsi2_pullback`: 1421 — EXACT MATCH with PR #234.
- `NON_CRYPTO_STRATEGY_POLICY` (singular) at `alpha_engine/non_crypto_policy.py:182` — CONFIRMED.
- `NON_CRYPTO_STRATEGY_POLICIES` (plural, as PR #232 used) — does NOT exist in repo (grep -n returns no hits in `alpha_engine/`).

**Verdict: REALLY_VERIFIED.** PR #234's NEEDS_CORRECTION judgment + the singular/plural dict-name catch are accurate.

### Item 5 — PENNY+MEMECOIN score floor

- `MIN_SCORE_FLOORS_BY_CLASS` — NOT present in `audit_trail/quality_gates.py` (grep returns 0 hits).
- `ASSET_CLASS_SMART_THRESHOLDS` at line 488 — CONFIRMED.
- `get_effective_min_score` at line 545 — CONFIRMED.
- `passes_penny_meme_class_gate` at line 6306 — CONFIRMED (PR #234 implies the function exists and is called; line 6742 shows the call site).

**Verdict: REALLY_VERIFIED.** PR #234's FABRICATED judgment for Item 5 is accurate.

## Summary

| # | PR #234 verdict | Cross-verify result |
|---|---|---|
| 1 | NEEDS_CORRECTION | REALLY_VERIFIED |
| 2 | FABRICATED | REALLY_VERIFIED |
| 3 | FABRICATED | REALLY_VERIFIED |
| 4 | NEEDS_CORRECTION | REALLY_VERIFIED |
| 5 | FABRICATED | REALLY_VERIFIED |

**Score: REALLY_VERIFIED=5, STILL_FABRICATED=0, PARTIAL=0**

## Escalation recommendation

**No escalation required.** PR #234's red-team findings are independently confirmed against real source and live DB. The fabrications in PR #232 are real fabrications, the symbol-name corrections (singular `NON_CRYPTO_STRATEGY_POLICY`, real dict `ASSET_CLASS_SMART_THRESHOLDS`) are correct, and the live-data citations match the trading_picks DB to the row.

Operator action: per PR #234's recommendation, the *next* PR should ship corrected diffs (CRYPTO-only scope for Item 1, real strategy names for Items 2/3, correct dict identifiers for Items 4/5). The red-team layer (PR #234) is trustworthy and can be relied on as the gate before any code-touching PR #232 successor is merged.
