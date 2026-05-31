# INCIDENT_OVERALL #34 (P1) — pytest 17 failures triage

**Date:** 2026-05-31
**Branch:** main (workflow `ci-tests.yml`, latest failing run 26703676949)
**AI consult:** Xiaomi Mimo `mimo-v2.5-pro` — full verbatim response in `reports/peer_claude-pytest-17-failures-triage_mimo_consult_2026-05-31.md`
**Scope:** docs-only triage. **No** test fixes shipped here — production-logic changes require operator review per incident notes.

## TL;DR

17 failures cluster into 5 root-causes. Only **1** is safe to auto-fix (Cluster E). Clusters B and C (outcome resolver, AB router) are HIGH-RISK — **never auto-revert**. Cluster A (rogue upstream gate, 8 tests) is the highest-ROI investigation: a single new gate in `audit_trail/quality_gates.py` is rejecting baseline COMMODITY (CT=F, HG=F) AND baseline ETF (SPY) picks before targeted gates run.

## Failure inventory (verified live 2026-05-31T05:02Z)

Source: `gh run view 26703676949 --log-failed` short-summary block.

| # | Test | Cluster |
|---|---|---|
| 1 | `tests/test_audit_hyrotrader_payload.py::test_no_orphan_hyro_files` | E |
| 2-5 | `tests/test_m096_ctf_concentration_cap.py::*` (4 tests) | A |
| 6-9 | `tests/test_m098_etf_vix_gate.py::*` (4 tests) | A |
| 10-11 | `tests/test_outcome_resolver_noncrypto.py::TestTimeExitV22::*` (2 tests) | B |
| 12-13 | `tests/test_pr10_ab_gate.py::*` (2 tests) | C |
| 14-17 | `tests/test_quality_gates.py::*` (4 tests) | D |

## Mimo's classification (summary; full table in consult MD)

| Cluster | Tests | Class | Verdict |
|---|---|---|---|
| **A — Rogue upstream gate** | 2-9 (8) | P | NEEDS-OPERATOR-REVIEW |
| **B — Outcome resolver time-exit stub** | 10-11 (2) | P (CRITICAL) | NEEDS-OPERATOR-REVIEW. Never auto-fix. |
| **C — AB router default flipped to ON** | 12-13 (2) | P (CRITICAL) | NEEDS-OPERATOR-REVIEW. Never auto-revert. |
| **D — Quality gate logic drift** | 14-17 (4) | P (HIGH) | NEEDS-OPERATOR-REVIEW |
| **E — Missing artifact** | 1 (1) | M | SAFE-FIX |

## My verification of Mimo's load-bearing claims

I independently verified the four claims Mimo's recommendations rest on:

1. **Cluster C (ab_router default).** `ml_gatekeeper/ab_router.py:38`:
   ```
   AB_ENABLED = os.environ.get("ML_GATE_AB_ENABLED", "1") == "1"
   ```
   Spec per `tests/test_pr10_ab_gate.py:12` docstring: default must be `"0"`. **Mimo is correct — default was flipped to `"1"`.** This silently turns ML A/B routing ON globally. **Do NOT auto-revert** without operator + product confirmation.

2. **Cluster E (#1 hyrotrader_closed_picks.json).** Verified both reader and writer exist:
   - Writer: `tools/hyrotrader_closed_picks_emitter.py` (line 42, `OUTPUT_PATH = ... hyrotrader_closed_picks.json`)
   - Reader: `tools/build_pf_registry.py:593-619` (consumes the JSON for pf registry)
   - Therefore adding `'hyrotrader_closed_picks.json'` to `KNOWN_HYRO_FILES` is safe — the artifact has a real production read/write path.

3. **Cluster A (rogue upstream gate).** Recent `audit_trail/quality_gates.py` commits include:
   - `d52793902` "feat(quant-edge): per-class gates — EQUITY/ETF VIX regime + CRYPTO liquid-core + BOND NSS yield curve"
   - `a043dc575` "fix(audit): Tier 0 P0 — kill falsified COT DSR=1.0, propagate CRYPTO DISPUTED, freeze FOREX, **add source-concentration gate**"
   The "source-concentration gate" (M-013 / Tier-0 P0) is the prime suspect: it is class-wide, was added 2026-05-17, has no per-class env disable in M-096/M-098 test fixtures, and rejecting both baseline CT=F (multi_asset_cot) and SPY (sector_rotation) is consistent with a concentration gate firing on single-source patterns. Operator should diff this commit's gate addition first.

4. **Cluster B (outcome resolver time-exit).** Test asserts `classify_outcome(...) == "WON"` for a `compute_pnl(100.0, 102.0, "LONG")` LONG profit. Live output is `'EXPIRED'` for the time-exit branch. This is a regression of v2.2's last-bar-close classification logic — affects every non-crypto asset class's WR/PF reporting. **Critical — never auto-fix.**

## Recommended order-of-fix (with operator gates)

| Priority | Cluster | Action | Operator gate |
|---|---|---|---|
| **1** | E (#1) | One-line edit: add `'hyrotrader_closed_picks.json'` to `KNOWN_HYRO_FILES` set in `tests/test_audit_hyrotrader_payload.py`. | None — pure test artifact. Can ship as part of any pytest fix PR. |
| **2** | A (#2-9) | Investigate `git diff a043dc575~1..a043dc575 -- audit_trail/quality_gates.py` to find the source-concentration gate. If it's an intentional production gate, add `CONCENTRATION_CAP_ENABLED` or new env-var to `_common_env` in `tests/test_m096_ctf_concentration_cap.py` and `tests/test_m098_etf_vix_gate.py`. If it's leaking outside its intended scope (firing on commodity + ETF baselines that should be in-scope but pass), fix the gate condition. | Operator must confirm scope of the source-concentration gate before any test-fixture env-var change. |
| **3** | D (#14-17) | `git diff` `audit_trail/quality_gates.py` since last all-passing commit. Likely a refactor of `passes_smart_gate()` changed source-required check, concentration-adjusted score floor, or concentration cap threshold. | Operator must compare current Smart Picks production behavior to what tests expect — DO NOT assume tests are stale. |
| **4** | B (#10-11) | Re-implement the time-exit last-bar-close classification in `alpha_engine/outcome_resolver.py`. The function currently returns `'EXPIRED'` instead of `compute_pnl(entry, last_close, direction)` → `classify_outcome(...)`. | **Critical operator gate.** This change recalculates WR/PF for every non-crypto asset class. Plan a one-shot recompute of `asset_class_health` immediately after merge and watch for jumps >5pp in FOREX/COMMODITY/EQUITY/BOND. |
| **5** | C (#12-13) | Either: (a) change `ML_GATE_AB_ENABLED` default back to `"0"` to match spec, OR (b) update the test to reflect intentional cutover with audit-page disclosure. | **Critical operator gate.** This default controls whether ML A/B routing is on for production picks. Need product + engineering sign-off on which way to resolve. Live A/B traffic since the flip is unaudited. |

## What this PR does NOT do

- Does not modify any test files.
- Does not modify `audit_trail/quality_gates.py`, `audit_trail/vix_regime_gate.py`, `alpha_engine/outcome_resolver.py`, `ml_gatekeeper/ab_router.py`, or `ml_gatekeeper/gatekeeper.py`.
- Does not ship the safe Cluster E one-line fix — bundling it with this triage doc would let it slip in unreviewed; the operator should ship it (or any subset of fixes) explicitly via a separate PR.

## Open PR context (no merge conflicts expected)

These open PRs touch overlapping files; the operator should sequence resolution carefully:

- #126 `fix/incidents-p0-batch-2026-05-31` — P0 batch incl. data integrity / FOREX consolidation
- #132 `fix/incidents-p0-followups-2026-05-31` — P0 followups: ghost dedup, trust_score, HC parity, sync hook
- #134 `fix/incidents-batch-resolve-2026-05-31` — PnL decimal/percent convention
- #143 `fix/pnl-percentage-reconciliation-isolated` — PnL reconciliation

None of the above explicitly claim to fix the 5 clusters above, but #126 + #143 may move surface area in `quality_gates.py` / outcome resolver paths. Re-run pytest on each affected PR after Cluster A is resolved to detect cross-PR regressions.

## Reproducer

```bash
# Live failure inventory
gh run view 26703676949 --log-failed | grep "^FAILED\|short test summary" | head -30

# Local repro (no production code touch)
pytest tests/test_m096_ctf_concentration_cap.py tests/test_m098_etf_vix_gate.py \
       tests/test_outcome_resolver_noncrypto.py tests/test_pr10_ab_gate.py \
       tests/test_quality_gates.py tests/test_audit_hyrotrader_payload.py \
       -v --tb=short 2>&1 | tail -50

# Cluster A investigation
git log --oneline -10 -- audit_trail/quality_gates.py
git diff a043dc575~1..a043dc575 -- audit_trail/quality_gates.py
```

## Provenance

- Plan: `reports/peer_claude-pytest-17-failures-triage_plan_2026-05-31.md`
- AI consult (verbatim): `reports/peer_claude-pytest-17-failures-triage_mimo_consult_2026-05-31.md`
- Result: `reports/peer_claude-pytest-17-failures-triage_result_2026-05-31.md`
