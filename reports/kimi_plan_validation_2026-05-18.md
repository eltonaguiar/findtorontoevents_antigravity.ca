# Kimi Plan Validation Report — 2026-05-18

**Validated by:** claude-sonnet-4-6-desktop (swarm critique)  
**Source:** `reports/MASTER_ACTION_PLAN_kimi_2026-05-18.md` + `audit_infrastructure_technical_brief_kimi_2026-05-18.md`  
**Method:** Read-only codebase verification against actual files

---

## VERDICT SUMMARY

| # | Kimi Claim | Status | Evidence |
|---|---|---|---|
| CRYPTO = MONEY_READY (PF=2.54, n=195) | **WRONG** (already corrected) | pf_registry canonical: PF=1.275721, n=1942 |
| COMMODITY PF=2.15, WR=60.2%, n=89 | **WRONG** | pf_registry canonical: PF=1.173605, n=160 |
| ETF VIX gate "needs wiring" (E-005) | **RESOLVED** — already wired | `audit_trail/vix_regime_gate.py` active; VIX>30 ETF veto at quality_gates.py:4154 |
| COT 3-day lag correction (M-001, PR #941) | **IN-PROGRESS** under PR #1058 | Commit `cb4a9b257f`: COT lag corrector + MATCH gate |
| Pick traceability gaps (5 items) | **CONFIRMED REAL** | All 5 gaps verified in pick_feature_store.py + quality_gates.py |
| CT=F hard 40% concentration cap (M-002) | **NOT IMPLEMENTED** | M-046 has soft 30% cap (env-gated); no hard 40% CT=F block exists |

---

## 1. PF REGISTRY CORRECTIONS

Kimi's Section 1 dashboard table uses stale/wrong values. Canonical source: `audit_dashboard/data/pf_registry.json::by_asset_class_policy_clean_net`

| Class | Kimi WR | Kimi PF | Kimi n | Canonical PF | Canonical n | Delta |
|-------|---------|---------|--------|--------------|-------------|-------|
| CRYPTO | 66.4% | 2.54 | 195 | 1.275721 | 1942 | PF -49.8%, n 10x higher |
| COMMODITY | 60.2% | 2.15 | 89 | 1.173605 | 160 | PF -45.4% |
| FOREX | 33.3% | 0.48 | 45 | ~0.33 | ~392 | WR roughly correct, n underestimated |
| EQUITY | — | — | 31 | ~0.72 | ~31 | n matches |

**Root cause:** Kimi likely used the money_ready_verdict() filter output (n=195 CRYPTO "clean" picks) rather than pf_registry canonical. The filter result is inflated because 97.7% of it is ml_enhanced sprawl.

---

## 2. VIX GATE — ALREADY WIRED

Kimi's E-005 action item ("Wire VIX<25 gate") and PR-2026-0518-4 are **not needed** — the gate already exists:

- `audit_trail/vix_regime_gate.py` — full VIX regime gate implementation
- `audit_trail/quality_gates.py:4133-4147` — VIX<22 bonus (+3 score) for EQUITY
- `audit_trail/quality_gates.py:4154-4172` — VIX>30 macro veto for ETF (score penalty)
- `tests/test_vix_regime_gate.py` — tests exist

The threshold in the existing gate is VIX>30 (not VIX>=25 as Kimi specifies). If the 25 threshold is intentional, this is a calibration change, not a new wiring. **Effort estimate: 1 hour, not a full PR.**

---

## 3. COT LAG — SUBSTANTIALLY DONE (WRONG PR#)

Kimi references "PR #941 in-flight" for COT lag. The actual PR is **#1058** (commit `cb4a9b257f`):
- `feat(M-008/M-021): COT 3-day pub-lag + MATCH gate + friction-adjusted DSR`
- COT lag guard is inline in `alpha_engine/cot_positioning.py` (not a separate `filters/cot_staleness.py`)
- `commodity_limits.yaml` does not exist — config is inline in Python

**Action:** Update M-001 reference from PR #941 to PR #1058. Mark M-001 as substantially complete pending verification.

---

## 4. PICK TRACEABILITY GAPS — ALL CONFIRMED

Kimi's `audit_infrastructure_technical_brief_kimi_2026-05-18.md` (Section 8.2) is accurate:

| Gap | Confirmed? | Notes |
|-----|-----------|-------|
| No pick_id for rejected picks | YES | ID assigned after gate pass, not before |
| No pick_gate_decisions table | YES | Not in pick_feature_store.py (only at_pick_features, at_symbol_strategy_stats, raw_picks_weekly) |
| No score penalty chain trace | YES | Penalties applied but not logged per-pick |
| No what-if replay capability | YES | No gate bypass simulation exists |
| filter_log SQLite-only | YES | No MySQL replication of filter events |

**Kimi's proposed SQL schemas** (pick_gate_decisions, pick_lifecycle_events, gate_impact_attribution) are well-designed and non-conflicting with existing schema. The PR-T5 core logger is the right foundation.

---

## 5. CT=F CONCENTRATION CAP — NOT IMPLEMENTED

Kimi's M-002 (hard 40% CT=F cap) is genuinely missing:

- **What exists:** M-046 source concentration soft cap (30%, env-gated `CONCENTRATION_GATE_ENABLED`)
- **What exists:** Dedup guard reducing CT=F over-emission (1 pick/symbol/72h)
- **What's missing:** Hard percentage block: "if CT=F > 40% of weekly signals → block new CT=F signals"
- `commodity_limits.yaml` does not exist (Kimi's target config file)
- `filters/concentration_cap.py` does not exist (Kimi's target)

**Recommended approach:** Add CT=F concentration check inside `passes_active_gate()` using rolling count from `closed_picks.json`, similar to how `BLOCKED_DIRECTION_TRIPLES` works. Config inline, no new YAML file needed.

---

## REVISED ACTION PRIORITY

Based on validation:

| ID | Action | Status | Real Priority |
|----|--------|--------|--------------|
| M-105 | Quarantine ml_enhanced family in money_ready_verdict CRYPTO filter | NOT DONE | **P0 — blocks all CRYPTO sizing** |
| M-002 | CT=F hard concentration cap (<40%) | NOT DONE | **P0 — blocks COMMODITY PBO** |
| PR-T5 | Pick lifecycle logger (core) | NOT DONE | **P0 — enables traceability** |
| E-005 | VIX gate threshold calibration (25 vs 30) | PARTIAL | P1 — threshold tweak only |
| M-001 | COT lag correction (verify PR #1058 merged) | MOSTLY DONE | P1 — verify + test |
| PR-T1 | Active/closed picks dashboard | NOT DONE | P1 — depends on PR-T5 |
| Q-001 | MySQL ghost-row purge + EQUITY sync | BLOCKED | P1 — PA console action 2026-05-24 |

---

## WHAT KIMI GOT RIGHT

- `audit_infrastructure_technical_brief_kimi_2026-05-18.md` is **excellent** — most accurate codebase map produced by any agent this session. The pick lifecycle flow diagram, gate function inventory, BLOCKED_* set analysis, and filter_log schema are all verified correct.
- FOREX HARD_DISABLED rationale is correct (WR=33%)
- BOND accumulation path is correct (scanner live, n=1 first pick confirmed)
- FUTURES blocked/deprioritized is correct
- Pick Traceability PR-T5 → PR-T1 → PR-T2 → PR-T3 → PR-T4 dependency order is correct
- Post-cost expectancy formula and slippage breakdown are reasonable (COMMODITY 0.02% commission etc.)

---

*Generated: 2026-05-18 | Validated by claude-sonnet-4-6-desktop swarm critique*
