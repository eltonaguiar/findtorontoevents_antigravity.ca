# Main-Branch Test Debt — Root Cause + Remediation Plan (2026-05-15)

## Headline

`python -m pytest tests/test_quality_gates.py tests/test_hf_quality_gate_wire.py tests/test_jpy_cross_buy_block.py tests/test_bond_agent_workflow.py tests/test_classify_pick_quality_v2.py tests/test_commodity_cot_contrarian.py tests/test_etf_iwm_gld_kill.py tests/test_hf_gate_default_on_safety.py` on origin/main HEAD returns **36 failed / 90 passed**. These failures are NOT caused by any open PR — they are pre-existing test debt on main.

## Provenance

Findings consolidated from 4 parallel agents + 1 swarm engine + direct test runs.

| Source | Output |
|---|---|
| Investigator (PR #1026 root cause) | Initially attributed failures to PR #1026 churn — INCORRECT. Failures persist when PR #1026 is fully reverted. |
| Investigator (bisect) | Identified `c2c072c0123` (2026-05-14 19:37, Hermes Agent) as the largest single jump (11→14 fails in test_quality_gates.py). |
| Reviewer (PR #1026 Wire-Up audit) | PR #1026 commit d3995f5ac4d is itself clean code-wise; 3 new safety modules are pure orphans per Wire-Up Rule. |
| Investigator (PR #1026 docs phantom-work) | Zero phantom-work in d3995f5ac4d; bloat is from earlier branch commits. |
| Swarm DeepSeek | High-confidence verdict on root cause + recommendation (below). |
| Swarm xAI | Failed to return JSON (transport 400). |
| Swarm Kilo | No output. |
| Direct cherry-pick test | Cherry-picking d3995f5ac4d alone to clean origin/main reproduces 36 failures. Confirms PR-innocence. |
| Direct env-flag test | Setting `DRIFT_AUTO_PAUSE_DISABLED=1` in conftest.py had ZERO impact on failure count. Drift gate is not the cause. |

## Root cause (high confidence)

**Multi-agent code-test drift.** Over ~14 days, autonomous commits from Hermes, Cursor, Roocode, Copilot SWE, and Kimi modified `audit_trail/quality_gates.py` (~8000 LOC) WITHOUT running the local test suite. Specifically:

- New env-gated gates added (drift-auto-pause, FOREX SHORT-only, JPY cross block, ETF kill, transaction-cost, HF threshold-A, PCG-5 shadow, anti-overfit validator). Each gate short-circuits `passes_smart_gate` / `passes_active_gate` before the assertions the tests pin.
- Blocked-source-system + blocked-asset-strategy-pair dictionaries expanded. Tests that fixture a "low_trust FOREX EURUSD trend_follow" pick now hit a hard block before any score logic runs.
- Strategy-score-override + per-asset-quality permissive gates changed semantics. Tests asserting old behavior fail.
- Test mocks weren't updated alongside production code.

Identifying ANY single commit is impossible because the drift is cumulative across ~40 commits in the period.

## What I tried

1. **Cherry-picked d3995f5ac4d** to a clean branch off origin/main. Tests still 36-fail.
2. **Set `DRIFT_AUTO_PAUSE_DISABLED=1` in tests/conftest.py.** No impact (drift state in `dashboard_data.json` is unset; gate already fail-opens).
3. **Inspected first failure traceback.** `test_active_gate_blocks_low_trust_non_crypto_rows`: pick blocked by `_hf_quality_gate_reason='transaction_cost_gate'`. So even the drift fix wouldn't unblock — different gate.
4. **Enumerated env-gated flags in quality_gates.py.** 27 env flags found. Disabling all in conftest would mask real bugs — rejected.

Conclusion: there is no single-knob fix. Remediation requires per-test triage.

## Swarm consensus (DeepSeek, high confidence)

> "Multi-agent autonomous commits over the last 14 days have been making aggressive refactors to quality_gates.py without corresponding test updates. The 36 failures are the cumulative result of code-test drift where production paths were deleted or renamed but the tests still pin assertions on the old behavior."

Recommendation: **Path (c) — identify dead tests (testing removed features) + delete them; fix the rest.**
- (a) Revert specific commits — undoes legitimate production work
- (b) Fix-forward by updating tests to match new behavior — risks locking in bugs, violates mutate-before-kill protocol
- (c) **Triage per-test: dead → delete, real → fix code OR fix test** ← recommended
- (d) Quarantine in pytest config — lets problem fester

First 5 tests to fix per DeepSeek:
1. `smart_gate_uses_concentration_adjusted_score_floor`
2. `hf_threshold_a_blocks_smart_gate_when_fwd_lags_bt`
3. `smart_gate_blocks_highly_concentrated_non_verified_strategy`
4. `smart_gate_forex_uses_forward_wr_alias_fields`
5. `active_gate_blocks_low_trust_non_crypto_rows`

## Implications for PR #1026

DeepSeek says: PR #1026 should NOT merge while main is broken. Standard: main must be green before any merge, even for additive changes.

Wire-Up audit also flagged that PR #1026 ships 3 orphan safety modules. Author must either:
- Add a `## Wiring Plan` section to PR body naming target callers + ETA
- OR remove the 3 orphans before merge

## Recommended next steps for operator

1. **Hold PR #1026 + PR #1045** until main is green.
2. **Allocate a focused session** (or assign a dedicated subagent batch) to triage the 36 fails. Plan:
   - For each failing test, capture (a) the assertion it makes, (b) the gate that's blocking, (c) verdict: dead-feature-test / outdated-mock / legit-regression
   - Group into 3 buckets:
     - DELETE — tests that pin removed features (likely 5-10)
     - UPDATE — tests where the new gate behavior is correct + assertion needs revision (likely 15-20)
     - REVERT — tests that catch a real regression in a recent commit (likely 3-8)
   - Ship per-bucket PR.
3. **Lock down CI**: enable required status checks on main so future Hermes/Kimi/Copilot commits cannot land without green tests. Currently the lack of branch protection is what allowed the drift.
4. **Multi-agent coordination memory entry**: append rule to `CLAUDE.md`: "Before pushing changes to `audit_trail/quality_gates.py`, run `pytest tests/test_quality_gates.py tests/test_hf_quality_gate_wire.py`. If fails increase, fix tests in the same PR or open a follow-up issue."

## Risks (DeepSeek)

- Deleting tests for removed features may hide regressions if features re-added later
- Fix-forward locks in potentially incorrect behavior, violates `docs/MUTATION_THREE_AXIS_PROTOCOL.md` mutate-before-kill
- Multi-agent uncoordinated commits will continue producing this pattern unless CI gates added

## Evidence gathered

- `git log --since=2026-05-01 origin/main -- audit_trail/quality_gates.py` shows ~25 commits from Hermes alone in 14 days
- `audit_trail/quality_gates.py` is 8000+ LOC, contains 27 env-gated flags
- `audit_dashboard/data/dashboard_data.json` has no drift state set; drift gate fail-opens
- First failure `test_active_gate_blocks_low_trust_non_crypto_rows` blocked by `transaction_cost_gate`, not drift

## Provenance trail

| File | Purpose |
|---|---|
| `reports/external_eval_validation_2026-05-15.md` (PR #1044) | Validation of external eval that triggered this investigation |
| `reports/bond_regression_deep_dive_2026-05-15.md` (PR #1046) | Adjacent investigation: BOND regression validation |
| `swarm_runs/test-debt-20260515T063210Z/deepseek.json` | DeepSeek's full JSON response with verdict + risks |
| `tests/conftest.py` | Tested + reverted env-flag patch (DRIFT_AUTO_PAUSE_DISABLED — no impact) |

## Status

**No code changes shipped.** This is a verification + planning doc. Operator decision required before remediation begins.
