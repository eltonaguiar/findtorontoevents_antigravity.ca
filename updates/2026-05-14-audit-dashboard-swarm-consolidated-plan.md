# Audit Dashboard ÔÇö Swarm-Consolidated Gate-to-Money Plan

**Date:** 2026-05-14  
**Foundation:** Mercury2 truth-layer plan  
**Source plan:** `updates/2026-05-14-audit-dashboard-kimi-protocol-operationalization.md`  
**Swarm reviewers:** Backend Engineer, Frontend Engineer, Protocol Auditor, Safety/Risk Engineer  
**Status:** CONSOLIDATED ÔÇö red flags addressed, timeline revised, prerequisites added

---

## Peer Insights & Revision Notes

**Revision date:** 2026-05-15
**Peer reviewer:** `claude-desktop-081g9oh` (cross-PC broadcast `08ca1bb7-09d0-4cd5-9e16-6df72a67bbd0`)
**Status:** REVISED per swarm consensus and live audit findings.

### Key peer findings incorporated

| Finding | Impact on this plan | Action taken |
|---------|---------------------|--------------|
| **PR #1017-1020 CLOSED** by 3-engine swarm consensus (Wire-Up violation / Stage H breach) | Mega-PR approach rejected; sub-PR split required | Phase A rewritten; all merge assumptions replaced with sub-PR openings |
| **PR #1021 MERGED** -- drift auto-pause gate + crypto-short test fixes | P0 infra partially shipped | Removed redundant drift-gate planning; canonical config = `hf_quality_gates.json` |
| **PR #1030 OPEN** -- Mercury2 P0.1+P0.2+P0.3 | `money_ready_filter.js` deployed; `per_asset_thresholds.json` orphan | Updated deployment status; added orphan deprecation note |
| **581 JSON data files in PR #1017 diff** | Data-wise dangerous; blocks mega-merge | Added data-validation gate to Phase A0; each sub-PR must pass JSON schema check |
| **Resolver backfill = 2-week task** (not 3-day) | All timelines underestimated | Shifted backfill to parallel track; Phase A extended from 3 -> 7 days |
| **Frontend direct-Binance price queries banned** | Architecture violation | Added compliance gate to Phase B; prices must route through `alpha_engine/price_feed.py` |
| **Kill-switch RED -> BLACK requires physical halt** | Software-only flag insufficient | Updated Phase C spec: physical halt (exchange API or manual) required |
| **`claude_gainer` sparkline contradiction** (+1006% vs +80%) | Payload coherence defect | Added to Phase J+ anomaly detector; auto-file issue on >500pp divergence |
| **Drift KS_D = 0.0498** vs critical 0.0460 | Marginal, not catastrophic | Revised Phase A0 risk language; monitoring not emergency halt |

### Revised PR disposition

| PR | Original plan | Revised plan | Rationale |
|----|---------------|--------------|-----------|
| #1017 | Merge as state-machine mega-PR | **5 sub-PRs**: (a) resolver v2 table, (b) kill_switch_ladder hierarchy doc, (c) position_sizer_v2, (d) real_money_state_machine staging, (e) daily_edge_report | Swarm: Wire-Up violation + 581 JSON files |
| #1018 | Merge as CRYPTO mutations mega-PR | **4 sub-PRs**: (a) MEME split schema, (b) signal_quality_ml wire, (c) funding_arb backtest, (d) quarantine automation | Swarm: payload-contract risk |
| #1019 | Merge as EQUITY/FOREX/BOND mega-PR | **3 sub-PRs**: (a) factor sleeves, (b) G10 carry, (c) yield curve | Swarm: BOND floor-change without investigation gate |
| #1020 | Merge as COMMODITY/FUTURES/OPTIONS/CEF mega-PR | **3 sub-PRs**: (a) FUTURES Donchian, (b) OPTIONS defined-risk, (c) CEF NAV discount | Swarm: Stage H violation |

---

## 1. Swarm Consensus Summary

Four specialist agents reviewed the source plan in parallel. Areas of **unanimous agreement**:

- **Phase J (ML Calibration Banner)** ÔÇö Ship immediately. Zero risk, high safety value.
- **Feature flags** ÔÇö `PROTOCOL_UI_ENABLED` default-OFF is mandatory.
- **Auto-generated `real_money.html`** ÔÇö Correct architecture; prevents doc drift.
- **Payload splitting** ÔÇö New blocks must NOT inflate the 16.78 MB monolithic `dashboard_data.json`.
- **Resolver gap (0/3,500)** ÔÇö Is a **hard blocker** for real-money progression, not a table row.
- **Monkey Test compute cost** ÔÇö Infeasible inline; must be a nightly cached batch job.

**Critical conflicts surfaced:**
- Backend says PR #1017 merge is "clean code-wise" but "dangerous data-wise" (581 JSON data files in diff).
- Frontend says CTAs ("Initiate Micro Live") are fine **only if** auth/mutation specs exist; Safety says they are **unacceptable without** two-person rule.
- Protocol reviewer says 6 levels are well-mapped; Safety says the 10-step readiness gate is **unenforced static HTML**, not a guard.
- Backend says 14-day kill-switch shadow is reasonable; Safety says it must be **30 days or 3 distinct trigger observations**.

---

## 2. Revised Phase Structure

Phases are reordered by **safety precedence**, not logical dependency. Phases with ­ƒö┤ swarm-red flags are blocked until prerequisites clear.

| Phase | Name | Original Days | Revised Days | Swarm Verdict |
|-------|------|---------------|--------------|---------------|
| **J** | ML Calibration Banner | 1 | **Ship today** | ­ƒƒó Unanimous go |
| **A0** | Prerequisite Cleanup | ÔÇö | **Days 1ÔÇô3** | ­ƒƒí Required before A |
| **A** | Merge PR #1017 + Staging | 1ÔÇô3 | **Days 4ÔÇô10** | ­ƒö┤ Revised (was underestimated) |
| **B** | State Machine Surface | 4ÔÇô7 | **Days 11ÔÇô14** | ­ƒƒí Conditional go |
| **C** | Kill Switch Widget | 5ÔÇô8 | **Days 11ÔÇô14** (parallel) | ­ƒƒí Conditional go |
| **J+** | Auto-Quarantine + Incident Mode | ÔÇö | **Days 12ÔÇô13** | ­ƒƒí New (safety mandate) |
| **D** | 6-Level Progress Tracker | 6ÔÇô10 | **Days 15ÔÇô18** | ­ƒƒí Conditional go |
| **E** | Per-Asset Action Cards | 8ÔÇô12 | **Days 15ÔÇô18** (parallel) | ­ƒƒí Conditional go |
| **F** | 5-AI Consensus Gate | 10ÔÇô14 | **Days 19ÔÇô21** | ­ƒƒí Conditional go |
| **G** | Shadow Paper Expansion | 12ÔÇô18 | **Days 19ÔÇô24** | ­ƒƒí Conditional go |
| **H** | Monkey Test + Slippage | 15ÔÇô21 | **Days 22ÔÇô26** | ­ƒö┤ Revised (nightly cache) |
| **I** | Auto-generated real_money.html | 18ÔÇô24 | **Days 22ÔÇô26** (parallel) | ­ƒƒó Go |
| **K** | Safety Hardening + Chaos Dry-Run | ÔÇö | **Days 27ÔÇô30** | ­ƒö┤ New (safety mandate) |

---

## 3. Phase Details (Revised)

### Phase J ÔÇö ML Calibration Banner + Auto-Quarantine
**Ship: Today**  
**Files:** `audit_dashboard/dashboard_enhancements.js`, `audit_dashboard/template.html`, `audit_trail/quality_gates.py`  
**Swarm override:** Original plan had only a banner. Safety reviewer mandated **hard quarantine**.

1. **Sticky dismissible banner** on `/audit` and `/audit/real_money.html`:
   - Text: "ÔÜá´©Å ML confidence is inverted: confÔëÑ0.9 bucket WR 14.4%; conf 0.5ÔÇô0.6 bucket WR 60.3%. `_normalize_confidence` defense active. Do NOT size by raw confidence."
2. **Auto-quarantine in `quality_gates.py`:**
   - Any pick with `raw_confidence >= 0.9` is excluded from `passes_smart_gate` and `passes_active_gate`.
   - Log: `QUARANTINE_HIGH_RAW_CONF: {symbol} excluded from promotion pipeline`.
3. **Per-pick badge:** Hover on high-confidence picks shows: "High raw confidence historically predicts LOW WR."

*Success criteria:* Banner visible; CI test asserts that a mock pick with conf=0.95 is rejected by smart gate.

---

### Phase A0 ÔÇö Prerequisite Cleanup (NEW)
**Duration: Days 1ÔÇô3**  
**Blocks Phase A.**

1. **Deprecate `audit_trail/protocol_state.py`:**
   - Audit all consumers; migrate to `alpha_engine/v2_enhancements/real_money_state_machine.py`.
   - Running two state machines is a red-flagged risk.
2. **Data-file conflict mitigation:**
   - Reset `*/data/*.json` files on `pr1-core-real-money-state-machine` to match `main`.
   - Add `.gitattributes` merge=ours for `*/data/*.json` to prevent future data-file merge conflicts.
3. **Kill-switch hierarchy doc:**
   - Document how `kill_switch_ladder.py` relates to existing `alpha_engine/kill_switch.py`, `fx_kill_switch.py`, `commodity_kill_switch.py`.
   - Publish 1-page hierarchy in `docs/KILL_SWITCH_HIERARCHY.md`.
4. **Performance budget:**
   - Generator must complete in <45 min (current: 30ÔÇô35 min, cron gap: 60 min).
   - Add telemetry to `dashboard_generator.py`: log duration per payload block.

*Success criteria:* No duplicate state machine consumers; `.gitattributes` merged; hierarchy doc published.

---

### Phase A ÔÇö Merge PR #1017 + Staging Validation (REVISED)
**Duration: Days 4ÔÇô10**  
**Files:** `alpha_engine/v2_enhancements/*`, `audit_trail/dashboard_generator.py`  
**Swarm override:** Original 3-day timeline is dangerous. Resolver backfill is a **2-week data migration**.

1. **Rebase branch onto `main`:**
   - Resolve data-file conflicts using `merge=ours` strategy.
2. **Staging branch:** `staging-audit-protocol`
   - Run full `dashboard_generator.py` on `main + pr1-core-real-money-state-machine`.
   - Assert: exit code 0, payload size < 25 MB, generation time < 45 min.
3. **Schema backward-compat test:**
   - CI test asserts all **existing** top-level keys in `dashboard_data.json` are present and correctly typed after merge.
4. **Resolver backfill (2-week sub-project):**
   - Run `outcome_resolver_v2.py` backfill on a **clone of production data**.
   - Checksum audit: compare old vs new outcomes for a 100-pick sample.
   - Require >95% agreement before accepting backfill.
   - Backfill runs in **parallel** with UI phases; do NOT block B/C/D on backfill completion.
5. **`to_dashboard_json()` helpers:**
   - Add `to_dashboard_json()` to `real_money_state_machine.py` and `kill_switch_ladder.py`.
6. **Payload split (mandatory):**
   - New blocks go to **separate JSON files**:
     - `audit_dashboard/data/protocol_state.json`
     - `audit_dashboard/data/kill_switch.json`
     - `audit_dashboard/data/monkey_test_cache.json`
   - `dashboard_data.json` retains a lightweight `refs` block pointing to the satellite files.

*Success criteria:* Staging CI passes; payload split verified; backfill running in parallel; no schema regressions.

---

### Phase B ÔÇö State Machine Surface (REVISED)
**Duration: Days 11ÔÇô14**  
**Files:** `audit_dashboard/template.html`, `audit_dashboard/dashboard_enhancements.js`, `audit_trail/dashboard_generator.py`  
**Swarm override:** Must add terminal `KILLED` state; must publish state-to-level mapping.

1. **Revised state enum (9 states):**
   - `BLOCKED` ÔåÆ `REHAB` ÔåÆ `OOS_READY` ÔåÆ `SHADOW` ÔåÆ `LIVE_ELIGIBLE` ÔåÆ `LIVE`
   - **NEW terminal:** `KILLED` (for permanent quarantine, e.g., COMMODITY `cta_commodity_momentum_term`)
   - **NEW emergency:** `REVERTED` (rollback state requiring manual review)
2. **State-to-Level mapping (published in UI):**
   - Level 1 (Monkey Test): `BLOCKED` Ôåö `REHAB`
   - Level 2 (Slippage): `REHAB` Ôåö `OOS_READY`
   - Level 3 (Safety): `OOS_READY`
   - Level 4 (Shadow): `SHADOW`
   - Level 5 (Micro): `LIVE_ELIGIBLE`
   - Level 6 (Scale/Kill): `LIVE` or `KILLED`
3. **Asset Class Protocol Cards:**
   - Each card shows: state badge, protocol level progress bar (1ÔÇô6), top 3 blockers.
   - **FUTURES** decision badge corrected to `EXPAND` (not `EXPAND NEW`).
   - **COMMODITY** shows `KILLED` terminal state with quarantine banner.
4. **State Transition Log:**
   - New tab: "Transition Log"
   - Columns: timestamp, asset class, fromÔåÆto, trigger, guard results, approved_by.

*Success criteria:* All 9 asset classes show correct state + level; transition log renders; `KILLED` state is reachable.

---

### Phase C ÔÇö Kill Switch Widget (REVISED)
**Duration: Days 11ÔÇô14 (parallel with B)**  
**Files:** `audit_dashboard/template.html`, `audit_dashboard/dashboard_enhancements.js`  
**Swarm override:** 14-day shadow ÔåÆ 30 days; YELLOW must be warning-only; RED needs physical halt.

1. **Sticky header pill:**
   - Portfolio-level: `GREEN` / `YELLOW` / `ORANGE` / `RED` / `BLACK`
   - 15-second polling of lightweight `/audit/data/kill_switch.json` (not full payload).
2. **Revised escalation rules:**
   - `GREEN` ÔåÆ `YELLOW`: warning only, heightened monitoring (NO position reduction).
   - `YELLOW` ÔåÆ `ORANGE`: reduce positions 50%, halt affected asset class.
   - `ORANGE` ÔåÆ `RED`: **physical halt** (API key suspension, not CSS overlay).
   - `RED` ÔåÆ `BLACK`: paper-only, zero-size. Override requires code deploy.
3. **30-day shadow mode:**
   - New kill-switch levels show in UI for 30 days before auto-actions arm.
   - Requires 3 distinct trigger-type observations before auto-actions execute.
4. **Active Actions Panel:**
   - Read-only list of auto-actions. **No UI override button.**
   - Actions: `REDUCE_POSITIONS`, `HALT_TRADING`, `PAPER_ONLY`, `MANUAL_REVIEW_REQUIRED`.
5. **WORM audit log:**
   - Append-only `audit_trail/kill_switch_log.jsonl` (write-once, read-many).
   - Every ladder transition logged with timestamp, trigger, actions taken.

*Success criteria:* Mock 6% drawdown ÔåÆ `YELLOW` within 15s; mock 12% drawdown ÔåÆ `RED` with physical halt verified; no UI path to bypass `BLACK`.

---

### Phase J+ ÔÇö Safety Hardening (NEW)
**Duration: Days 12ÔÇô13**  
**Mandated by Safety reviewer.**

1. **Incident Mode preset (Mercury2 P2.8 extension):**
   - New button: "­ƒÜ¿ Incident Mode"
   - Hides all CTAs ("Initiate Micro Live", "Advance to Level X").
   - Shows only: kill-switch status, blockers, stale feeds, drift alerts.
2. **Resolver Gap Widget (BLACK gate):**
   - Permanent sticky widget: "Outcome Resolution: X% (target: ÔëÑ95% before Level 4)".
   - Color: `BLACK` until >80%, `RED` until >95%, `GREEN` at ÔëÑ95%.
   - This is the #1 real-money readiness metric.
3. **Auto-quarantine hard gate (extends Phase J):**
   - Already implemented in Phase J; verify in CI.
4. **Emergency revert path:**
   - `real_money_state_machine.py` supports `EMERGENCY_REVERT` event.
   - Requires two signed approvals; logs reason immutably.

*Success criteria:* Incident Mode hides CTAs; resolver widget visible; emergency revert tested in staging.

---

### Phase D ÔÇö 6-Level Progress Tracker (REVISED)
**Duration: Days 15ÔÇô18**  
**Files:** `audit_dashboard/template.html`, `audit_dashboard/dashboard_enhancements.js`  
**Swarm override:** Must use accordion (lazy-render) per asset class; must have mobile compact mode.

1. **Vertical stepper per asset class:**
   - Levels 1ÔÇô6 with Ô£à / ÔÅ│ / ÔØî status.
   - **Accordion:** Only expanded asset class mounts its stepper DOM.
   - **Mobile:** Collapses to horizontal 6-dot bar with expand chevron.
2. **Level criteria tooltips:**
   - Exact metric and threshold on hover.
3. **Level 4 entry criteria (was missing):**
   - Show why an asset entered `SHADOW`: DSRÔëÑ0.95, PBO<0.05, nÔëÑ100.
   - Gate checklist visible before transition button is enabled.

*Success criteria:* Stepper renders for all 9 classes; mobile view tested; Level 4 entry criteria visible.

---

### Phase E ÔÇö Per-Asset Action Cards (REVISED)
**Duration: Days 15ÔÇô18 (parallel with D)**  
**Files:** `audit_dashboard/template.html`, `audit_dashboard/dashboard_enhancements.js`  
**Swarm override:** CTAs must require typed confirmation + secondary approval for Level 5.

1. **Decision cards per asset class:**
   - EQUITY ÔÇö `SCALE` ­ƒƒó | factor-sleeve breakdown | CTA: "Request Micro Live Review"
   - CRYPTO ÔÇö `MUTATE` ­ƒƒí | MEME split + Signal Quality ML
   - FOREX ÔÇö `MUTATE` ­ƒƒí | carry sleeve + regime filter
   - BOND ÔÇö `MUTATE` ­ƒƒí | yield curve + elite_score badge
   - COMMODITY ÔÇö `KILLED` ­ƒö┤ | quarantine banner (terminal)
   - FUTURES ÔÇö `EXPAND` ­ƒöÁ | accumulation + Donchian (corrected from EXPAND NEW)
   - OPTIONS ÔÇö `EXPAND NEW` ­ƒöÁ | defined-risk badge + 90-day countdown
   - MEME ÔÇö `EXPAND NEW` ­ƒöÁ | split-from-CRYPTO + pump detection
   - CEF ÔÇö `EXPAND NEW` ­ƒöÁ | NAV discount + rebalance countdown
2. **CTA safety:**
   - "Request Micro Live Review" requires:
     - Typed confirmation (type asset class name).
     - Secondary approval (two-operator rule or hardware token).
     - Resolver coverage ÔëÑ95%.
     - All Level 1ÔÇô4 gates clear.
   - CTA is **hidden in Incident Mode**.

*Success criteria:* All 9 cards render; CTA requires dual approval; COMMODITY shows `KILLED` terminal state.

---

### Phase F ÔÇö 5-AI Consensus Gate (REVISED)
**Duration: Days 19ÔÇô21**  
**Files:** `audit_trail/dashboard_generator.py`, `audit_dashboard/dashboard_enhancements.js`  
**Swarm override:** Consensus math MUST move to Python generator; frontend render-only.

1. **Pre-computed consensus scores:**
   - `dashboard_generator.py` computes weighted score per pick.
   - Weights: tuned by forward WR of each agent (auto-updated weekly via new `tools/agent_weight_calibrator.py`).
   - Emits `consensus_score` and `consensus_adherence_rate` in payload.
2. **Promotion Candidates filter:**
   - New filter button: `­ƒÄ» Protocol-Ready Picks`
   - Only picks with consensus ÔëÑ threshold AND Level 1ÔÇô3 gates clear.
3. **Adherence rate badge:**
   - "Consensus Adherence: 73% (target ÔëÑ90%)"

*Success criteria:* Frontend does zero math; adherence rate visible; promotion filter works.

---

### Phase G ÔÇö Shadow Paper Expansion (REVISED)
**Duration: Days 19ÔÇô24**  
**Files:** `alpha_engine/v2_enhancements/real_money_state_machine.py`, `audit_dashboard/paper_pilot.html`  
**Swarm override:** Must use atomic writes / SQLite for tracker provisioning to avoid race conditions.

1. **Generic parameterized template:**
   - `paper_pilot.html?asset_class=EQUITY&strategy=factor_sleeve_value`
   - Reads `data/paper_pilot_{asset_class}_{strategy}.json`
2. **Auto-provision on `SHADOW` transition:**
   - State machine creates tracker JSON with atomic write (`temp` ÔåÆ `rename`).
   - Use SQLite for provisioning ledger to avoid file-locking issues.
3. **Dashboard "Shadow Paper" tab:**
   - Table: asset class, strategy, days in shadow, WR vs backtest, Sharpe, graduation verdict.

*Success criteria:* Transition EQUITY to `SHADOW`; tracker appears within one cron cycle; table renders.

---

### Phase H ÔÇö Monkey Test + Slippage Reality (REVISED)
**Duration: Days 22ÔÇô26**  
**Files:** `tools/monkey_test_runner.py`, `tools/slippage_reality_checker.py`, `audit_dashboard/template.html`  
**Swarm override:** Monkey Test MUST be nightly cached; inline computation is infeasible.

1. **Monkey Test Cache (`tools/monkey_test_runner.py`):**
   - Runs nightly at 04:00 UTC (`cron: '0 4 * * *'`).
   - 1,000 random strategies per asset class.
   - Writes `audit_dashboard/data/monkey_test_cache.json` with TTL.
   - Dashboard reads cached histograms, never computes.
2. **Slippage Reality Panel:**
   - Reuses `transaction_cost_model.py`.
   - Gross vs Net PF per asset class.
   - Gate: Net PF > 0.5 ├ù Gross PF.
   - Side-by-side bar chart in UI.

*Success criteria:* Nightly cron runs <2 hours; dashboard shows histogram for top 3 strategies; slippage panel renders.

---

### Phase I ÔÇö Auto-Generated real_money.html
**Duration: Days 22ÔÇô26 (parallel with H)**  
**Files:** `audit_trail/real_money_generator.py`, `audit_dashboard/real_money.html`  
**Swarm override:** Do NOT add generated HTML to workflow push-trigger paths.

1. **Generator script:**
   - Reads `real_money_history.json`, `kill_switch_status.json`, `outcome_resolver_log.json`.
   - Produces `audit_dashboard/real_money.html`.
2. **Deploy safety:**
   - Add `audit_trail/real_money_generator.py` to `.github/workflows/audit-dashboard.yml` paths.
   - **Do NOT** add `audit_dashboard/real_money.html` to paths (prevents self-trigger loop).

*Success criteria:* `real_money.html` timestamp <1h old; 10-step gate shows live checkmarks from state machine.

---

### Phase K ÔÇö Safety Hardening + Chaos Dry-Run (NEW)
**Duration: Days 27ÔÇô30**  
**Mandated by Safety reviewer.**

1. **Chaos engineering session:**
   - Simulate 6% portfolio drawdown ÔåÆ verify `YELLOW` triggers.
   - Simulate 12% drawdown ÔåÆ verify `RED` physical halt.
   - Simulate strategy PF 0.75 for 5 days ÔåÆ verify `ORANGE` asset-class halt.
   - Document pass/fail for each scenario.
2. **Two-person rule enforcement:**
   - Level 5+ transitions require dual approval in state machine.
   - CI test: assert single-operator `SHADOWÔåÆLIVE_ELIGIBLE` transition fails.
3. **Rollback procedure runbook:**
   - `docs/PROTOCOL_ROLLBACK_RUNBOOK.md`
   - Covers: `LIVE_ELIGIBLEÔåÆSHADOW`, `SHADOWÔåÆREHAB`, `REHABÔåÆBLOCKED`, `ANYÔåÆREVERTED`.
4. **Pre-deployment dry-run protocol:**
   - Entire ladder (GREENÔåÆBLACK) exercised in synthetic mode.
   - Require sign-off before any asset class reaches Level 5.

*Success criteria:* Chaos session passes; dual approval CI passes; rollback runbook published; synthetic ladder exercised.

---

## 4. New Files (Revised)

| Path | Purpose | Swarm Note |
|------|---------|------------|
| `audit_trail/real_money_generator.py` | Auto-gen `real_money.html` | Go; add generator to paths, NOT output |
| `tools/monkey_test_runner.py` | Nightly random-strategy benchmark | Go; MUST be nightly, not inline |
| `tools/monkey_test_cache.py` | TTL cache manager for monkey results | New (backend yellow flag mitigation) |
| `tools/slippage_reality_checker.py` | Net-of-cost PF per asset class | Go; reuse `transaction_cost_model.py` |
| `tools/agent_weight_calibrator.py` | Weekly consensus weight tuning | New (frontend yellow flag mitigation) |
| `docs/KILL_SWITCH_HIERARCHY.md` | Hierarchy doc for existing + v2 kill switches | New (A0 prerequisite) |
| `docs/PROTOCOL_ROLLBACK_RUNBOOK.md` | Emergency rollback procedures | New (Phase K safety mandate) |
| `tests/test_audit_protocol_surface.py` | CI: protocol_state block present & fresh | Go |
| `tests/test_kill_switch_widget.py` | CI: mock escalation ÔåÆ dashboard JSON | Go; test physical halt signal |
| `tests/test_monkey_test_gate.py` | CI: cached histogram data present | Go; assert cache, not compute |
| `tests/test_shadow_paper_auto_provision.py` | CI: SHADOW transition ÔåÆ tracker JSON | Go; test SQLite atomicity |
| `tests/test_real_money_html_freshness.py` | CI: generated timestamp <1h | Go |
| `tests/test_schema_backward_compat.py` | CI: existing payload keys intact after merge | New (A red flag mitigation) |
| `tests/test_dual_approval.py` | CI: single-operator Level 5 transition fails | New (K safety mandate) |
| `tests/test_resolver_coverage_widget.py` | CI: resolver widget BLACK until >80% | New (J+ safety mandate) |

---

## 5. Modified Files (Revised)

| Path | Change | Swarm Note |
|------|--------|------------|
| `audit_trail/dashboard_generator.py` | Ingest protocol_state, kill_switch refs; compute consensus; emit satellite JSON files | Split payload into `protocol_state.json`, `kill_switch.json` |
| `audit_dashboard/template.html` | Add protocol cards, kill-switch header, 6-level accordion, consensus banner, ML banner, resolver widget | Use `<template>` fragments or JS renderer; do not inline 18 card variations |
| `audit_dashboard/dashboard_enhancements.js` | Render protocol UI, kill-switch polling, operator presets | Split into modules: `protocol_renderer.js`, `kill_switch_widget.js`, `consensus_gate.js`, `operator_presets.js` |
| `audit_dashboard/real_money.html` | Replace static with auto-generated | Go |
| `.github/workflows/audit-dashboard.yml` | Add `audit_trail/real_money_generator.py` to paths; **exclude** generated HTML outputs | Critical safety fix |
| `alpha_engine/v2_enhancements/real_money_state_machine.py` | Add `to_dashboard_json()`, `EMERGENCY_REVERT`, `KILLED` state, dual approval | Required for protocol alignment |
| `alpha_engine/v2_enhancements/kill_switch_ladder.py` | Add `to_dashboard_json()`, WORM logging, 30-day shadow, revised YELLOW rules | Required for safety |
| `audit_trail/quality_gates.py` | Auto-quarantine raw_conf ÔëÑ0.9 picks | Phase J safety mandate |

---

## 6. Dependency Chain

```
Phase J ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Ship today
   Ôöé
   Ôû╝
Phase A0 (cleanup) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Days 1ÔÇô3
   Ôöé
   Ôû╝
Phase A (merge + staging) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Days 4ÔÇô10
   Ôöé
   Ôö£ÔöÇÔöÇÔû║ Phase B (state surface) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Days 11ÔÇô14
   Ôöé      ÔööÔöÇÔöÇÔû║ Phase D (stepper) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Days 15ÔÇô18
   Ôöé      ÔööÔöÇÔöÇÔû║ Phase E (action cards) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Days 15ÔÇô18
   Ôöé
   Ôö£ÔöÇÔöÇÔû║ Phase C (kill switch) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Days 11ÔÇô14
   Ôöé      ÔööÔöÇÔöÇÔû║ Phase J+ (safety hardening) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Days 12ÔÇô13
   Ôöé
   Ôö£ÔöÇÔöÇÔû║ Phase F (consensus) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Days 19ÔÇô21
   Ôöé
   Ôö£ÔöÇÔöÇÔû║ Phase G (shadow paper) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Days 19ÔÇô24
   Ôöé
   Ôö£ÔöÇÔöÇÔû║ Phase H (monkey + slippage) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Days 22ÔÇô26
   Ôöé      ÔööÔöÇÔöÇÔû║ Phase I (auto real_money.html) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Days 22ÔÇô26
   Ôöé
   ÔööÔöÇÔöÇÔû║ Phase K (chaos dry-run + rollback) ÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔöÇÔû║ Days 27ÔÇô30
```

**Critical path:** A0 ÔåÆ A ÔåÆ B/C/J+ ÔåÆ D/E ÔåÆ K  
**Parallel tracks:** F, G, H/I can run in parallel with critical path once A completes.

---

## 7. Swarm Red Flags ÔåÆ Required Actions

| Red Flag | Source | Resolution in this plan |
|----------|--------|------------------------|
| Resolver backfill in 3 days | Backend | Revised to 2-week sub-project; runs parallel with UI phases; does NOT block BÔÇôE |
| 0/3,500 picks = hard blocker | Safety | Phase J+ adds permanent resolver coverage widget (BLACK until >80%); backfill is P0 parallel track |
| No rollback procedures | Safety | Phase K mandates rollback runbook + `EMERGENCY_REVERT` event + CI tests |
| No two-person rule | Safety | Phase E CTAs require typed confirmation + dual approval; Phase K CI enforces it |
| Kill-switch CSS overlay only | Safety | Phase C: RED triggers physical halt (API suspension); BLACK requires code deploy to override |
| Monkey test inline compute | Backend | Phase H: moved to nightly cache (`tools/monkey_test_runner.py` cron at 04:00 UTC) |
| Payload bloat (16.78 MB ÔåÆ 20 MB) | Backend | Phase A: split into satellite JSON files (`protocol_state.json`, `kill_switch.json`) |
| Direct Binance API from frontend | Frontend | Forbidden by spec; all kill-switch state server-computed, polled from JSON |
| CTA buttons without auth | Frontend + Safety | Phase E: CTAs require dual approval + typed confirmation; hidden in Incident Mode |
| Template generator fragility | Frontend | Use JS renderer or `<template>` fragments; do not inline 18 card variations |
| "Level 0" does not exist | Protocol | Removed; COMMODITY shows `KILLED` terminal state at Level 6 |
| FUTURES under EXPAND NEW | Protocol | Corrected to `EXPAND` (FUTURES) vs `EXPAND NEW` (OPTIONS, MEME, CEF) |

---

## 8. 30-Day Success Criteria (Revised)

- [ ] Phase J shipped: ML banner visible + auto-quarantine CI passes
- [ ] Phase A0 complete: no duplicate state machines; `.gitattributes` merged; hierarchy doc published
- [ ] Phase A complete: staging branch passes; payload split verified; resolver backfill running (may be <100%)
- [ ] Kill-switch widget: mock 6% DD ÔåÆ `YELLOW` in <15s; mock 12% DD ÔåÆ `RED` with physical halt
- [ ] Dual approval: CI asserts single-operator Level 5 transition fails
- [ ] Resolver widget: visible on every page; BLACK until coverage >80%
- [ ] All 9 asset classes show correct state + level; COMMODITY shows `KILLED` terminal
- [ ] `real_money.html` auto-generated; timestamp <1h old
- [ ] Monkey test cache: nightly cron runs; dashboard reads histograms
- [ ] Chaos dry-run: YELLOW, ORANGE, RED scenarios pass; documented
- [ ] Rollback runbook published and tested
- [ ] No 404 assets on `/audit/`

---

## 9. Immediate Next Actions (Today)

1. **Ship Phase J** ÔÇö ML calibration banner + auto-quarantine in `quality_gates.py`.
2. **Begin Phase A0** ÔÇö Audit `audit_trail/protocol_state.py` consumers; prepare deprecation PR.
3. **Create staging branch** ÔÇö `staging-audit-protocol` from `main + pr1-core-real-money-state-machine`.
4. **Add `.gitattributes`** ÔÇö `*/data/*.json merge=ours` on `main`.
5. **Write `docs/KILL_SWITCH_HIERARCHY.md`** ÔÇö Map existing kill switches vs v2 ladder.

---

*Consolidated by swarm review. Original plan: `updates/2026-05-14-audit-dashboard-kimi-protocol-operationalization.md`. Foundation plan: `updates/2026-05-14-audit-enhancement-plan-mercury2.md`.*
