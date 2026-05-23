# Bisect Reconciliation — Copilot Agent vs Local Bisect (2026-05-15)

## Headline

Copilot SWE Agent independently audited the bisect handoff and **corrected one factual error in my local bisect agent's attribution**. Both agents reached the same remediation recommendation (Path B / env-flag mocking). My shipped fix (PR #1050) was already aligned with Copilot's recommendation.

## Copilot's corrections to local bisect

| Claim | Local bisect agent | Copilot verdict | Impact |
|---|---|---|---|
| Drift gate introduced by `c2c072c0123` | YES | **WRONG.** Drift gate `_passes_drift_auto_pause_gate` was added in `ed6b3f6b` (2026-05-14 18:03 EDT) and parallel-landed via PR #1021 squash `60c83c0a` (22:09 EDT). `c2c072c0123` only changed score floors + VIX default + quan_engine cap. | Attribution corrected — `c2c072c0123` is innocent of drift gate. |
| Mechanism: drift gate short-circuits `passes_smart_gate` before score checks | YES | **PARTIAL.** ~13/16 failures actually trip in `passes_active_gate` (called BEFORE smart-gate body). Drift gate accounts for only ~2-3 fails. Real mix: UTC death-zone, transaction-cost, VIX regime, source-staleness, drift. | Path C (reorder smart gate) wouldn't fix most fails. |
| Baseline date `9d26f13280d` = 2026-05-13 21:50 | YES | **WRONG.** Actual `2026-05-14 17:00:43 -0400`. Suspected timezone bug in bisect tooling. | ~20hr offset; doesn't change conclusions. |

## Why my PR #1050 still works

My PR shipped 7 env-flag setdefaults in conftest + a transaction-cost gate scope fix. Result: **36 → 4 fails**. Empirically validates Copilot's Step 2 recommendation:

> "Apply path B style mocking, but to the whole new-gate cluster, not just drift"

The reason I succeeded despite the bisect's wrong attribution: I disabled the actual gates (TRANSACTION_COST_GATE, FOREX_SHORT_ONLY, CRYPTO_HIGH_CONF_GUARD, DRIFT_PAUSE_GATE, BTC_BEAR_LONG, ML_CRYPTO_PRED_LONG, CRYPTO_UTC_HOUR_FILTER) by reading the actual `_hf_quality_gate_reason` field on each failing pick — not by trusting the bisect's mechanism claim.

Copilot's recommended env vars vs what I set:

| Env flag | Copilot recommends | PR #1050 sets | Status |
|---|---|---|---|
| `DRIFT_AUTO_PAUSE_DISABLED` / `DRIFT_PAUSE_GATE_ENABLED=0` | yes | yes (DRIFT_PAUSE_GATE_ENABLED=0) | ✓ |
| `VIX_REGIME_GATE_ENABLED=0` | yes | no (default already OFF per code) | safe — default OFF, no override needed |
| `PCG5_ENFORCE=0` | yes | no (default already OFF per Copilot's read) | safe — confirmed shadow-mode default |
| `JPY_CROSS_BUY_KILL_DISABLED=1` | yes | no | TBD if any remaining FOREX fixture trips it |
| `UTC_DEATH_ZONE_DISABLED` | proposed if exists | partially via CRYPTO_UTC_HOUR_FILTER=0 | ✓ same code path |
| `TRANSACTION_COST_GATE_DISABLED` | yes | yes (added env flag + code fix) | ✓ |
| `FOREX_SHORT_ONLY_GATE_DISABLED` | not in list | yes | additional coverage |
| `CRYPTO_HIGH_CONF_GUARD_ENABLED=0` | not in list | yes | additional coverage |
| `BTC_BEAR_LONG_REJECT=0` | not in list | yes | additional coverage |
| `ML_CRYPTO_PRED_LONG_REJECT=0` | not in list | yes | additional coverage |

## Where Copilot's analysis is stronger than mine

1. **Defense-in-depth justification for NOT reordering smart_gate.** Copilot explicitly rejects Path C with the correct semantic argument: "drift pause appearing before score floor is a feature: a class with KS_D > 2×critical should fail Smart admission regardless of how high the individual pick scores." This is a better defense than my "would lock in bugs" framing.
2. **Failure pattern bucketing.** Copilot's 5-pattern decomposition (A-E) is cleaner than the agent triage's 4-bucket scheme. Pattern A (most fails are in `passes_active_gate`, upstream of smart_gate) explains why reorder doesn't help.
3. **Production gate ladder enumeration** with timestamps + commit refs. Useful future-reference for any test author writing a fixture that needs to navigate the post-2026-05-14 ladder.

## Where my work is stronger than Copilot's

1. **Empirical validation.** I shipped + measured (36→4). Copilot's analysis is verification-only — recommends acceptance criteria (0 fails in test_quality_gates.py) but doesn't validate.
2. **Cross-module scope.** Copilot focused on `tests/test_quality_gates.py` (16 fails). I tested all 8 affected modules (36 fails total). The conftest setdefault approach generalizes; the test-quality-gates-only scope wouldn't.
3. **Transaction-cost code fix.** Copilot's open-question 2 ("should the gate itself read a `TRANSACTION_COST_GATE_DISABLED` env var?") — I implemented exactly that, plus the additional fix to skip the gate when pick has no realized pnl (a real production bug, not just a test issue).

## Remaining 4 fails — out of scope for both reports

These weren't in Copilot's 16-test scope (test_quality_gates.py only):
- `tests/test_bond_agent_workflow.py::*` (2 fails) — `bond_yield_curve_slope` missing from `.github/workflows/bond-agent.yml`. FIX_CODE bucket. Separate PR.
- `tests/test_commodity_cot_contrarian.py::*` (2 fails) — COT module intentionally gated 2026-05-14 (look-ahead bias). Tests should be `@pytest.mark.skip`d. DELETE bucket. Separate PR.

## Follow-ups Copilot suggests + my response

| Copilot proposal | Local response |
|---|---|
| Add `TESTING_PROTOCOL.MD` section listing env vars new fixtures must disable when predating 2026-05-14 | **AGREE.** Will append once test-debt PR #1050 merges. |
| Confirm PR #1021 (`60c83c0a`) parallel-landing of drift gate didn't leave duplicate definitions | Verified by Copilot: `grep -c "_smart_drift_reason"` shows 1. Closed. |
| Surgical fixture refresh for score-floor-tuned tests (3 tests) | Already neutralized by env setdefault. If specific tests still want to pin a floor, monkeypatch `alpha_engine.config.SCORE_FLOOR_BY_CLASS` in setUp. |
| Add UTC death-zone kill-switch env if not present | Already exists as `CRYPTO_UTC_HOUR_FILTER` (set to "0" in PR #1050). |

## Decision

PR #1050 stays. Acknowledge Copilot's bisect correction in this doc. Operator decides whether to also merge Copilot's analysis PR (it's a verification-only doc, no code).

Copilot's doc would land at `updates/2026-05-15-test-quality-gates-bisect-analysis.md`. Recommended: merge it alongside PR #1050 as the canonical record. Two-document trail (test_debt_analysis from PR #1049 → this reconciliation → Copilot's analysis) preserves the full investigation.

## Provenance

- Copilot session: https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/sessions/96149cec-e6ba-4514-84fe-0d51d82dcff8
- Copilot PR branch: `copilot/analyze-test-failures` (commit `ba06471065c`)
- Local bisect agent: `a58eb3b839f899154` (incorrect attribution corrected)
- Local triage agent: `a482f15bd758714e1` (correct buckets, validated empirically)
- Local fix PR: #1050 (32 of 36 unblocked)
- Local doc PR: #1049 (test-debt analysis)
