# Tick 15 — Safe Packet Subset (autonomous-safe ship from 9 diagnostic packets)
**Date:** 2026-05-31
**Author:** claude-opus-4-7 (autonomous-safe subagent)
**Source:** `reports/peer_claude-OPERATOR_DIAGNOSTIC_PACKETS_2026-05-31.md` (PR #239 merged + PR #243 polish, 9/9 strict-verified)
**Rule of engagement:** ship ONLY items whose action target is docs / workflow YAML / non-scoring config / observability. Skip anything that touches outcome_resolver, forward_validator, smart_picks_engine, production_scanner, dashboard_generator scoring, mysql_trading_sync, quality_gates.

---

## Classification table (9 items)

| # | Item | Action target | Class | Status / PR | Operator verification |
|---|---|---|---|---|---|
| 1 | Run-Backtests retrigger | GH Actions run state | **SAFE-NOW** | run `26706712727` -> `status=completed conclusion=success`. No PR needed. | `gh run view 26706712727 --json status,conclusion` returns success. |
| 2 | `harness_healthy` gate | `tools/db_health_check.py:653-669` | **OPERATOR-ONLY** (db_health_check.py is observability; polished draft already shipped as **PR #229 OPEN** awaiting operator review) | PR #229 open | Operator reviews PR #229 diff vs packet decision criteria; merges if `banner_should_show=True AND any_red=False AND harness_healthy=False` mapping is acceptable. |
| 3 | CONFIDENCE_INVERT verdict | `alpha_engine/smart_picks_engine.py:23-36` | **OPERATOR-ONLY** (smart_picks_engine is in the protected scoring path) -- verdict-only REJECT already shipped as **PR #227 OPEN** (docs/recommendation only, no code change) | PR #227 open | Operator merges PR #227 to lock the REJECT verdict; default `CONFIDENCE_INVERT_CRYPTO=0` stays. |
| 4 | `skyrocket_detector` track record | persona/orphan decision | **SAFE-NOW (docs-only)** -- ship 30-day SHADOW_PILOT plan as report; defer wiring (touches `calculate_smart_score` / `passes_active_gate`) to operator. | Shipped via this PR (report file) | Operator reads "Item 4 SHADOW_PILOT plan" below + grep confirms zero callers + decides keep / wire / delete. |
| 5 | 6 persona classes (NOT 33) | `tools/ai_tournament/persona_registry.py` per-class demote | **OPERATOR-ONLY** -- modifying registry changes tournament emission (feeds `tournament_picks` -> consensus pickers downstream); per CLAUDE.md MAJOR GOAL #1 we don't mutate emitters under autonomous mandate. | none | Operator runs Item 5 query in packets file, decides per-section. |
| 6 | FOREX kill list | `non_crypto_policy.py:240-288` + `quality_gates.py:6135-6139` (BLOCKED_SYMBOLS_BY_CLASS) | **OPERATOR-ONLY** -- quality_gates.py is in the protected list. | none | Operator re-runs query with `status='TP_HIT'` (NOT `status='won'` -- see Item 9 bug) then decides. |
| 7 | COMMODITY rebuild | `non_crypto_policy.py:231-235, 428-432` + `production_scanner.py:2602-2613` + `quality_gates.py::COMMODITY_BLACKLIST` | **OPERATOR-ONLY** -- production_scanner + quality_gates are in the protected list. | none | Operator runs Item 7 TP_HIT-based query, decides kill/keep per-strategy. |
| 8 | EQUITY rebuild | `non_crypto_policy.py:180-440` + `production_scanner.py:3849, 2680` | **OPERATOR-ONLY** -- production_scanner is in the protected list. | none | Operator runs Item 8 TP_HIT query, decides per-strategy. |
| 9 | PENNY Gate 0 + UEPS | `quality_gates.py:6128, 6306-6325, 6738-6744` + `.github/workflows/ueps-pick-runner.yml` + `value_screener_runner.py` | **SPLIT** -- PENNY gate is **OPERATOR-ONLY** (quality_gates), UEPS workflow YAML enable is **SAFE-NOW** if the file exists and is merely disabled. | Deferred to UEPS-specific PR; this report only flags it. | Operator checks `.github/workflows/ueps-pick-runner.yml` `on:` block -- if `workflow_dispatch` only, cron is missing -> safe to add cron. If the workflow doesn't exist, wire-up IS scoring path = operator-only. |

**Tally:** SAFE-NOW autonomous ship in this tick = **1 new doc PR** (this report) + status verification of pre-existing PRs #229, #227, run #26706712727.

**OPERATOR-ONLY = 6** (items 2, 3, 5, 6, 7, 8 -- all touch protected scoring path files or persona/policy emitters).

**Note on items 2 & 3:** they appear in both buckets because the *decision documents* (draft PR / verdict PR) are already shipped, but the *code merge* is operator-gated. From a "what does this subagent need to ship now?" perspective, neither needs new work.

---

## Item 4 -- `skyrocket_detector` SHADOW_PILOT plan (30 days)

**Status today (per packets sec.4.2-4.3):**
- Zero production callers (grep returns 3 comment-only mentions in `dashboard_generator.py`).
- Zero historical emissions in `trading_picks` or `picks` for any `source_system LIKE '%skyrocket%'`.
- Module is self-contained: `skyrocket_detector/{config,detector,feature_engine,label_builder,model,train}.py` (447 LOC entry point).

**Why we don't wire it now:**
- CLAUDE.md Wire-Up Rule requires either (a) a production caller in `calculate_smart_score` / `passes_active_gate` / `score_pick` / etc., or (b) an explicit opt-in sidecar with `## Wiring Plan`.
- Wiring into `calculate_smart_score` or `passes_active_gate` would touch the protected scoring path. **Out of scope for autonomous tick.**
- The autonomous-safe alternative is a SHADOW_PILOT: run the detector on a cron, write picks to a NEW table `skyrocket_shadow_picks` (or `source_system='skyrocket_shadow'` in `trading_picks` with `shadow_only=1` flag), and DO NOT feed into smart_picks ranking.

**SHADOW_PILOT acceptance criteria (operator-implementable in 1 follow-up PR):**
1. Add `.github/workflows/skyrocket-shadow-pilot.yml` -- runs `skyrocket_detector.detector` every 4h.
2. Detector writes to NEW column `is_shadow=1` (operator adds via migration on `trading_picks`) OR to NEW table `skyrocket_shadow_picks`.
3. **Hard rule:** quality_gates.py MUST reject any pick with `is_shadow=1` so it never enters smart_picks / active picks / TradingView execution.
4. Pilot duration: 30 days from first successful emission.
5. Promotion criteria at day 30: n>=100 closed, PF>=1.5, WR>=50% (T2 minimum). If met -> operator writes wiring PR. If not -> delete module.
6. Backup target if operator decides to delete: nothing (zero rows in any production table).

**Recommendation:** keep module as orphan for now (zero callers = zero risk). Schedule SHADOW_PILOT as a discrete operator follow-up. **Do not delete** until at least one alternative penny-detector lands, because the trained model artifacts in `skyrocket_detector/data/` represent prior labeled work.

---

## What this tick shipped

- **This report** -- `reports/peer_claude-tick15-safe-packet-subset_2026-05-31.md` (docs-only, no scoring path touched, server-side PR + admin-merge).

## What this tick verified (no new PR needed)

- **Item 1:** GH Actions run `26706712727` (Run Backtests & Deploy Dashboards) -> `status=completed conclusion=success`. Dashboard data is current.
- **Item 2:** PR #229 (`feat(db-health): add harness_healthy gate ...`) is OPEN awaiting operator review. No new draft needed.
- **Item 3:** PR #227 (`docs(reconcile): REJECT CONFIDENCE_INVERT_CRYPTO; propose 0.8-bucket dampener`) is OPEN. Verdict already documented; no new work.

## What operator MUST still do

- Items 5, 6, 7, 8, 9-PENNY: protected scoring path. Read the packet, apply own diff, backup to `ejaguiar1_backups.*` first.
- Item 9-UEPS: check workflow YAML existence (`.github/workflows/ueps-pick-runner.yml`). If missing entirely, wire-up to `value_screener_runner.py` IS scoring path and is operator-only. If only cron disabled, a SAFE-NOW PR can re-enable.
- Merge or close PRs #227 and #229 to clear the queue.

## References

- Source packets: `reports/peer_claude-OPERATOR_DIAGNOSTIC_PACKETS_2026-05-31.md` (PR #239, polished PR #243).
- Wire-Up Rule: `CLAUDE.md` -> "Wire-Up Rule (integration modules)".
- Protected scoring path: outcome_resolver, forward_validator, smart_picks_engine, production_scanner, dashboard_generator (scoring), mysql_trading_sync, quality_gates.
