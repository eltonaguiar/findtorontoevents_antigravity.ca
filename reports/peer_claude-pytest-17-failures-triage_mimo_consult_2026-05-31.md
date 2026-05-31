# Mimo Consult — INCIDENT_OVERALL #34 — pytest 17 failures triage

**Date:** 2026-05-31
**Provider:** Xiaomi Mimo (`mimo-v2.5-pro`)
**Endpoint:** `https://token-plan-sgp.xiaomimimo.com/v1/chat/completions`
**Response ID:** `06a678782f9549f2a3aff5e7c4df5794`
**Temperature:** 0.2 · max_tokens: 4000

---

## PROMPT (system + user)

### System
> You are a senior Python test/CI triage engineer. Output structured markdown only. Be concrete; no fluff. For each failure: classify, propose minimal fix or operator-review flag, cite the risk.

### User
> PYTEST 17 FAILURES on main (CI-Tests workflow, repo eltonaguiar/findtorontoevents_antigravity.ca). Incident #34 P1. Task: classify each failure as (P)roduction-logic regression / (T)est-data-drift / (F)laky / (M)issing-artifact. For each, propose (a) a surgical fix if SAFE, or (b) flag NEEDS-OPERATOR-REVIEW with the specific production code path that would have to change. Per the incident notes these three items are HIGH-RISK and need operator review, never auto-fix: ab_router default (tests 12,13); crypto_not_liquid_core gate / quality_gates (14-17); FOREX outcome resolver time-exit (10,11). Final section: recommended order-of-fix (low-risk first, highest-risk last).
>
> FAILURE INVENTORY:
>
> 1. tests/test_audit_hyrotrader_payload.py::test_no_orphan_hyro_files -- AssertionError: undocumented hyro json artifacts: ['hyrotrader_closed_picks.json'] -- add to KNOWN_HYRO_FILES in test_audit_hyrotrader_payload.py after confirming a reader exists
>
> 2. tests/test_m096_ctf_concentration_cap.py::test_ctf_passes_when_below_cap -- AssertionError: M-096: CT=F at 30% should pass the 35% cap. Got False.
> 3. tests/test_m096_ctf_concentration_cap.py::test_non_ctf_symbol_unaffected -- AssertionError: M-096 must not affect non-CT=F COMMODITY picks. HG=F should pass.
> 4. tests/test_m096_ctf_concentration_cap.py::test_fail_open_when_no_data -- AssertionError: M-096 fail-open: must allow CT=F when no active_picks data available.
> 5. tests/test_m096_ctf_concentration_cap.py::test_skip_when_fewer_than_5_commodity_picks -- AssertionError: M-096: with < 5 COMMODITY picks, gate should skip (insufficient sample).
>    Context: test calls audit_trail.quality_gates.passes_smart_gate(pick). _common_env disables CONCENTRATION_CAP_ENABLED, COT_DEDUP_GATE_ENABLED, COMMODITY_SHORT_ONLY, COMMODITY_CTF_WEEKLY_CAP, MATRIX_SYMBOL_GATES. Some OTHER gate is firing before M-096 has a chance to evaluate. Likely root cause: a new gate added recently (e.g. M-108 magnitude sanity, FOREX_DIRECTIONAL_GATE, or new commodity gate) is rejecting CT=F before M-096 logic runs.
>
> 6. tests/test_m098_etf_vix_gate.py::test_shadow_stamps_when_vix_above_threshold -- AssertionError: Shadow mode must not block pick (ETF_VIX_GATE=0 → should shadow only, but pick was hard-blocked).
> 7. tests/test_m098_etf_vix_gate.py::test_custom_threshold -- assert False is True
> 8. tests/test_m098_etf_vix_gate.py::test_disabled_gate_skips_check -- AssertionError: Disabled gate must not block (ETF_VIX_GATE_DISABLED=1 → some other gate blocks the ETF pick).
> 9. tests/test_m098_etf_vix_gate.py::test_e006_exception_log_written -- AssertionError: E-006 log file must be created. Likely the VIX gate doesn't reach the log-write path because something earlier blocked.
>    Context: tests call audit_trail.quality_gates.passes_active_gate(pick) with a baseline ETF/SPY/sector_rotation pick. _common_env: ETF_VIX_GATE_DISABLED=0, CRYPTO_ML_SCORE_GATE_ENABLED=0, NUPL_GATE_ENFORCE=0, M044_MIN_AGE_SECONDS=0, BOOK_CONFLICT_GATE_DISABLED=1. Some upstream gate blocks ETF picks.
>
> 10. tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::test_long_time_exit_resolves_at_last_close -- AssertionError: assert 'EXPIRED' == 'WON'
> 11. tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::test_short_time_exit_loss -- AssertionError: assert 'EXPIRED' == 'LOST'
>     Context: alpha_engine/outcome_resolver.py v2.2 spec says: pick aged past per-class max_hold window with no TP/SL touch resolves at last bar's close (classify WON/LOST). Currently returns 'EXPIRED'. RESOLVER_VERSION/RESOLVER_SUBVERSION imported. Likely production-logic regression — the time-exit branch reverted to a stub that just stamps EXPIRED. This is a P-class failure: changes affect FOREX/COMMODITY/EQUITY/BOND outcome rates and asset_class_health.
>
> 12. tests/test_pr10_ab_gate.py::test_ab_router_constant_defaults_false -- AssertionError: assert True is False (ab_router.AB_ENABLED is True when ML_GATE_AB_ENABLED is unset; spec says False).
> 13. tests/test_pr10_ab_gate.py::test_gatekeeper_reexports_ab_enabled -- assert True is False (same constant).
>     Context: spec — AB_ENABLED reads ML_GATE_AB_ENABLED env with default '0'. Some recent change flipped default to '1'. HIGH-RISK: this default controls whether the ML A/B router is on in production. Operator must decide; do NOT auto-revert.
>
> 14. tests/test_quality_gates.py::test_smart_gate_rejects_source_less_pick -- AssertionError: assert False is True (gate did NOT reject a source-less pick; should reject).
> 15. tests/test_quality_gates.py::test_active_gate_rejects_exempt_safety_mode -- AssertionError: baseline ml_enhanced pick should pass (sanity). A NEW gate is rejecting a known-good ml_enhanced baseline pick.
> 16. tests/test_quality_gates.py::test_smart_gate_uses_concentration_adjusted_score_floor -- assert False is True.
> 17. tests/test_quality_gates.py::test_smart_gate_blocks_highly_concentrated_non_verified_strategy -- assert False is True (highly-concentrated strategy was NOT blocked, but should be).
>     Context: HIGH-RISK. These tests directly probe production-grade gate logic (smart-pick gate, concentration-adjusted score floor, source-required check). Changes affect /audit's Smart Picks list. Operator review required.
>
> Production files (do NOT edit blindly): audit_trail/quality_gates.py, audit_trail/vix_regime_gate.py, alpha_engine/outcome_resolver.py, ml_gatekeeper/ab_router.py, ml_gatekeeper/gatekeeper.py.
>
> Deliver: a table with columns [#, Test, Classification (P/T/F/M), Proposed Fix or NEEDS-OPERATOR-REVIEW, Production-code path touched]. Then recommended order-of-fix.

---

## RESPONSE (verbatim)

# Incident #34 — 17 PYTEST FAILURES — Triage Report

## Classification Table

| # | Test | Class | Proposed Fix / Flag | Production Path Touched |
|---|------|-------|---------------------|------------------------|
| 1 | `test_no_orphan_hyro_files` | **M** (Missing artifact) | **SAFE-FIX.** Add `'hyrotrader_closed_picks.json'` to `KNOWN_HYRO_FILES` in `test_audit_hyrotrader_payload.py` after confirming a reader/writer exists for that file in `hyrotrader/` package. One-line constant update. | `tests/test_audit_hyrotrader_payload.py` only |
| 2 | `test_ctf_passes_when_below_cap` | **P** (Production-logic regression) | **NEEDS-OPERATOR-REVIEW.** A new or reordered gate inside `audit_trail/quality_gates.py` (`passes_smart_gate` / `passes_active_gate`) is rejecting the CT=F pick *before* M-096 CTF cap ever evaluates. The gate that fires needs identification — likely M-108 magnitude sanity, a FOREX directional gate, or a commodity gate. Fix must come from gate-ordering or gate-condition scoping in production code. | `audit_trail/quality_gates.py` — gate evaluation order / gating conditions |
| 3 | `test_non_ctf_symbol_unaffected` | **P** | Same root cause as #2. **NEEDS-OPERATOR-REVIEW.** HG=F (non-CTF commodity) is being rejected by the same rogue gate. | `audit_trail/quality_gates.py` |
| 4 | `test_fail_open_when_no_data` | **P** | Same root cause as #2. **NEEDS-OPERATOR-REVIEW.** Fail-open path unreachable because an earlier gate blocks the pick. | `audit_trail/quality_gates.py` |
| 5 | `test_skip_when_fewer_than_5_commodity_picks` | **P** | Same root cause as #2. **NEEDS-OPERATOR-REVIEW.** | `audit_trail/quality_gates.py` |
| 6 | `test_shadow_stamps_when_vix_above_threshold` | **P** (Production-logic regression) | **NEEDS-OPERATOR-REVIEW.** An upstream gate (not VIX) is hard-blocking the ETF/SPY/sector_rotation pick before the VIX gate even runs. `_common_env` already disables CRYPTO_ML, NUPL, M044, BOOK_CONFLICT — a newer gate (possibly the same gate blocking M-096 tests) is the culprit. Must identify which gate in `quality_gates.py` or `gatekeeper.py` now rejects baseline ETF picks. | `audit_trail/quality_gates.py`, `audit_trail/vix_regime_gate.py`, `ml_gatekeeper/gatekeeper.py` |
| 7 | `test_custom_threshold` | **P** | Same root cause as #6. Pick hard-blocked upstream before custom VIX threshold is tested. **NEEDS-OPERATOR-REVIEW.** | `audit_trail/quality_gates.py` |
| 8 | `test_disabled_gate_skips_check` | **P** | Same root cause as #6. Even with `ETF_VIX_GATE_DISABLED=1`, another gate blocks the pick. **NEEDS-OPERATOR-REVIEW.** | `audit_trail/quality_gates.py` |
| 9 | `test_e006_exception_log_written` | **P** | Same root cause as #6. Gate never reaches VIX log-write path. **NEEDS-OPERATOR-REVIEW.** | `audit_trail/quality_gates.py`, `audit_trail/vix_regime_gate.py` |
| 10 | `test_long_time_exit_resolves_at_last_close` | **P** (HIGH-RISK Production-logic regression) | **NEEDS-OPERATOR-REVIEW ⚠️.** `alpha_engine/outcome_resolver.py` v2.2 time-exit branch is returning `'EXPIRED'` instead of classifying WON/LOST at last-bar close. This is a stub-or-revert in the resolver: the per-class max-hold → last-close classification logic is missing or bypassed. Affects all FOREX/COMMODITY/EQUITY/BOND outcome rates and `asset_class_health`. **Do NOT auto-fix.** | `alpha_engine/outcome_resolver.py` — `resolve_time_exit()` / time-exit branch |
| 11 | `test_short_time_exit_loss` | **P** (HIGH-RISK Production-logic regression) | Same root cause as #10. **NEEDS-OPERATOR-REVIEW ⚠️.** Short-side time-exit also resolves EXPIRED instead of LOST. | `alpha_engine/outcome_resolver.py` |
| 12 | `test_ab_router_constant_defaults_false` | **P** (HIGH-RISK Production-logic regression) | **NEEDS-OPERATOR-REVIEW ⚠️.** `ml_gatekeeper/ab_router.py` — `AB_ENABLED` defaults to `True` (reads `ML_GATE_AB_ENABLED` with default `'1'`). Spec says default `'0'`. This silently enables the ML A/B router in production for all environments. **Do NOT auto-revert** — operator must confirm intent (may be an intentional cutover). | `ml_gatekeeper/ab_router.py` — `AB_ENABLED` constant / env default |
| 13 | `test_gatekeeper_reexports_ab_enabled` | **P** (HIGH-RISK Production-logic regression) | Same root cause as #12. **NEEDS-OPERATOR-REVIEW ⚠️.** `ml_gatekeeper/gatekeeper.py` re-exports the flipped default. | `ml_gatekeeper/ab_router.py`, `ml_gatekeeper/gatekeeper.py` |
| 14 | `test_smart_gate_rejects_source_less_pick` | **P** (HIGH-RISK Production-logic regression) | **NEEDS-OPERATOR-REVIEW ⚠️.** `smart_gate` is *not* rejecting a source-less pick. Either the source-required check was removed/bypassed, or a new gate is failing fast before source validation runs, returning a misleading pass. Changes affect `/audit` Smart Picks list. | `audit_trail/quality_gates.py` — `passes_smart_gate()` source check |
| 15 | `test_active_gate_rejects_exempt_safety_mode` | **P** (HIGH-RISK Production-logic regression) | **NEEDS-OPERATOR-REVIEW ⚠️.** A known-good `ml_enhanced` baseline pick is being rejected by a gate that should not affect it. A new gate with an overly broad condition is firing on standard `ml_enhanced` picks. Must identify which gate. | `audit_trail/quality_gates.py` — gate conditions |
| 16 | `test_smart_gate_uses_concentration_adjusted_score_floor` | **P** (HIGH-RISK Production-logic regression) | **NEEDS-OPERATOR-REVIEW ⚠️.** Concentration-adjusted score floor logic is not rejecting as expected. Either the floor calculation changed or a gate ordering issue causes early rejection/acceptance. | `audit_trail/quality_gates.py` — score floor logic |
| 17 | `test_smart_gate_blocks_highly_concentrated_non_verified_strategy` | **P** (HIGH-RISK Production-logic regression) | **NEEDS-OPERATOR-REVIEW ⚠️.** Highly-concentrated strategy passes when it should be blocked. Concentration gate either removed, bypassed, or threshold changed. | `audit_trail/quality_gates.py` — concentration cap logic |

---

## Root-Cause Clustering

| Cluster | Tests | Shared Root Cause |
|---------|-------|-------------------|
| **A — Rogue upstream gate** | 2, 3, 4, 5, 6, 7, 8, 9 | A single recently-added or recently-modified gate in `quality_gates.py` (or `gatekeeper.py`) is rejecting baseline commodity picks AND baseline ETF picks before targeted gates (M-096, VIX) evaluate. Two `_common_env` fixtures insufficiently disable it. This is **the most likely single root cause** — fixing the offending gate condition or adding its disable-env-var to both test fixtures could unblock **8 tests at once**. |
| **B — Outcome resolver time-exit stub** | 10, 11 | `outcome_resolver.py` time-exit branch returns `EXPIRED` instead of WON/LOST. Single code path. |
| **C — AB router default flip** | 12, 13 | `ab_router.py` default changed from `'0'` to `'1'`. Single constant. |
| **D — Quality gate logic drift** | 14, 15, 16, 17 | Multiple gate behaviors in `quality_gates.py` changed (source check, concentration floor, strategy concentration cap). May all stem from a single refactor of `passes_smart_gate()`. |
| **E — Missing artifact** | 1 | Standalone. Test constant update. |

---

## Recommended Order-of-Fix

| Priority | What | Why | Risk |
|----------|------|-----|------|
| **1 (lowest risk)** | **#1** — Add `hyrotrader_closed_picks.json` to `KNOWN_HYRO_FILES` | Pure test-data constant. No production code touched. Unblocks 1 test immediately. | None |
| **2** | **Cluster A (#2–9)** — Identify and fix/disable the rogue upstream gate | Highest ROI: unblocks **8 tests**. Operator must identify the new gate (inspect `git log` on `quality_gates.py` / `gatekeeper.py` for last merge). If it's a gate with an env-flag, add that flag to `_common_env` fixtures. If it's a logic error in gate scoping, fix the gate condition. **Operator review required** — cannot auto-fix because the gate may be intentionally production-active. | Medium — gate ordering in production is sensitive |
| **3** | **Cluster D (#14–17)** — Quality gate logic drift in `passes_smart_gate()` | Probes core production gate logic. Operator must diff `quality_gates.py` against last passing commit to find what changed in source-check, concentration-floor, and strategy-concentration paths. | High — affects Smart Picks list |
| **4** | **Cluster B (#10–11)** — Outcome resolver time-exit | Directly affects WIN/LOSS rates for FOREX/COMMODITY/EQUITY/BOND. Operator must verify whether the EXPIRED stub was intentional (migration?) or a revert. **Never auto-fix** — incorrect outcome classification corrupts `asset_class_health` and downstream dashboards. | **Critical** — financial outcome data |
| **5 (highest risk)** | **Cluster C (#12–13)** — AB router default | Controls whether ML A/B routing is active globally. Flipping this default without operator sign-off could silently change which model serves picks in production. **Never auto-fix.** | **Critical** — production serving behavior |

---

**Immediate operator action:** Run `git diff HEAD~5 -- audit_trail/quality_gates.py ml_gatekeeper/gatekeeper.py` to identify the rogue gate causing Cluster A. That single investigation likely resolves the majority of failures.
