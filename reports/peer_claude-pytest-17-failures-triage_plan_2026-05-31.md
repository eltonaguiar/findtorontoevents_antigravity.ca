# Plan — INCIDENT_OVERALL #34 (P1): CI pytest 17 failures triage

**Date:** 2026-05-31
**Incident:** INCIDENT_OVERALL #34 (P1)
**Agent:** peer_claude
**AI provider to consult:** Mimo (Xiaomi token-plan, OpenAI-compatible)

## Live state read

- `gh run list --workflow=ci-tests.yml --limit 5` — latest 4 runs on main FAIL (most recent run 26703676949, 2026-05-31T05:02Z, duration 4m6s).
- Full failed log captured at `/tmp/ci_failures.txt` (6,288 lines).
- Short test summary block has exactly **17 FAILED lines**, matching the incident title.

### Failure inventory (17)

| # | Test | Error |
|---|---|---|
| 1 | `tests/test_audit_hyrotrader_payload.py::test_no_orphan_hyro_files` | undocumented hyro json artifact `hyrotrader_closed_picks.json` |
| 2 | `tests/test_m096_ctf_concentration_cap.py::test_ctf_passes_when_below_cap` | CT=F at 30% should pass 35% cap; got False |
| 3 | `tests/test_m096_ctf_concentration_cap.py::test_non_ctf_symbol_unaffected` | HG=F blocked (M-096 leaking outside CT=F) |
| 4 | `tests/test_m096_ctf_concentration_cap.py::test_fail_open_when_no_data` | CT=F blocked when no active_picks data |
| 5 | `tests/test_m096_ctf_concentration_cap.py::test_skip_when_fewer_than_5_commodity_picks` | gate doesn't skip on n<5 |
| 6 | `tests/test_m098_etf_vix_gate.py::test_shadow_stamps_when_vix_above_threshold` | Shadow mode blocked pick |
| 7 | `tests/test_m098_etf_vix_gate.py::test_custom_threshold` | assert False is True |
| 8 | `tests/test_m098_etf_vix_gate.py::test_disabled_gate_skips_check` | Disabled gate blocked pick |
| 9 | `tests/test_m098_etf_vix_gate.py::test_e006_exception_log_written` | E-006 log file not created |
| 10 | `tests/test_outcome_resolver_noncrypto.py::test_long_time_exit_resolves_at_last_close` | got 'EXPIRED', expected 'WON' |
| 11 | `tests/test_outcome_resolver_noncrypto.py::test_short_time_exit_loss` | got 'EXPIRED', expected 'LOST' |
| 12 | `tests/test_pr10_ab_gate.py::test_ab_router_constant_defaults_false` | AB_ENABLED is True, expected False |
| 13 | `tests/test_pr10_ab_gate.py::test_gatekeeper_reexports_ab_enabled` | AB_ENABLED is True, expected False |
| 14 | `tests/test_quality_gates.py::test_smart_gate_rejects_source_less_pick` | source-less pick passed (should reject) |
| 15 | `tests/test_quality_gates.py::test_active_gate_rejects_exempt_safety_mode` | baseline ml_enhanced pick blocked |
| 16 | `tests/test_quality_gates.py::test_smart_gate_uses_concentration_adjusted_score_floor` | gate returned False unexpectedly |
| 17 | `tests/test_quality_gates.py::test_smart_gate_blocks_highly_concentrated_non_verified_strategy` | gate didn't block concentrated strategy |

No `test_confluence.py` failures despite incident note — likely fixed by PR #115 (merge `fa2be8f6d` "fix(config): map forex_carry_ppp to carry family"). Open PRs touching test files: #126 (P0 batch), #132 (P0 followups), #134 (PnL convention), #143 (PnL reconciliation) — none yet merged.

## File paths in scope (read-only inputs to Mimo)

- `tests/test_m096_ctf_concentration_cap.py`
- `tests/test_m098_etf_vix_gate.py`
- `tests/test_outcome_resolver_noncrypto.py`
- `tests/test_pr10_ab_gate.py`
- `tests/test_quality_gates.py`
- `tests/test_audit_hyrotrader_payload.py`
- Production callees (NOT to be edited blindly): `audit_trail/quality_gates.py`, `audit_trail/vix_regime_gate.py`, `alpha_engine/outcome_resolver.py`, `ml_gatekeeper/ab_router.py`, `ml_gatekeeper/gatekeeper.py`

## Proposed approach

1. Verify live failures — DONE.
2. Send Mimo (Xiaomi) the failure inventory + relevant test-file excerpts + ask for:
   (a) per-failure classification: production-logic regression vs test-data drift vs flaky vs missing-artifact
   (b) suggested surgical fixes for the safe ones (test_data, KNOWN_HYRO_FILES list, ENV setup)
   (c) explicit flag on the risky ones — ab_router default, crypto_not_liquid_core gate, FOREX outcome resolver — that need operator review
3. Save full Mimo response verbatim at `reports/peer_claude-pytest-17-failures-triage_mimo_consult_2026-05-31.md`.
4. Author docs-only PR `reports/peer_claude-pytest-17-failures-triage_2026-05-31.md` with Mimo's classification + my verification + recommended order-of-fix. NO test or production fixes shipped.

## Risk

- Risk of misclassification: low — every failure has an explicit `AssertionError` message; nothing flaky-looking.
- Risk of leaking AI hallucinations into recommended fix order: medium — mitigated by clearly separating "Mimo says" from "verified by me reading the test file."
- Per SESSION RULES + incident note: do NOT ship test fixes blindly. Production-logic items (#12, #13 ab_router default; #14-17 quality_gates; #10, #11 outcome resolver time-exit) get explicit "needs human OK" flag.

## Decision

PROCEED — docs-only PR. Single file: `reports/peer_claude-pytest-17-failures-triage_2026-05-31.md`. Server-side `gh api` PUT off origin/main.
