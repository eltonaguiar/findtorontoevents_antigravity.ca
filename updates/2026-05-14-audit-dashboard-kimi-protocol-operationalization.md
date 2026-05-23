# Audit Dashboard ÔÇö Gate-to-Money Protocol Operationalization Plan

**Date:** 2026-05-14  
**Scope:** `findtorontoevents.ca/audit` + backend protocol branches  
**Foundation:** Mercury2 truth-layer plan (`updates/2026-05-14-audit-enhancement-plan-mercury2.md`)  
**Protocol source:** Kimi Code "Backtesting to Live Trading Protocol" deliverables (PR #1017ÔÇô#1022, `PROTOCOL_GATE_TO_MONEY.md`, `ENHANCEMENTS_PER_ASSET_CLASS.md`)

---

## Peer Insights & Revision Notes

**Revision date:** 2026-05-15
**Peer reviewer:** `claude-desktop-081g9oh` (cross-PC broadcast `08ca1bb7-09d0-4cd5-9e16-6df72a67bbd0`)
**Status:** REVISED per swarm consensus and live audit findings.

### Key peer findings incorporated

| Finding | Impact on this plan | Action taken |
|---------|---------------------|--------------|
| **PR #1017-1020 CLOSED** by 3-engine swarm consensus (Wire-Up violation / Stage H breach) | Mega-PR approach rejected; sub-PR split required | Phase A rewritten; backend state machine to be introduced via 5 sub-PRs, not monolith |
| **PR #1021 MERGED** -- drift auto-pause gate + crypto-short test fixes | P0 infra partially shipped | Removed redundant drift-gate planning; referenced new canonical config `hf_quality_gates.json` |
| **PR #1030 OPEN** -- Mercury2 P0.1+P0.2+P0.3 | `money_ready_filter.js` now deployed; `per_asset_thresholds.json` marked orphan | Updated deployment status; deprecated `per_asset_thresholds.json` |
| **581 JSON data files in PR #1017 diff** | Data-wise dangerous; staging required | Added data-validation gate before any sub-PR merge |
| **Resolver backfill = 2-week task** (not 3-day) | All downstream dates underestimated | Shifted backfill milestone to Day 10; added parallel-track recommendation |
| **Frontend direct-Binance price queries banned** | Architecture violation; must route through `alpha_engine/price_feed.py` | Added compliance check to Phase B wire specs |
| **Kill-switch RED -> BLACK requires physical halt** | Not just software flag; needs exchange API halt or manual intervention | Updated Phase C kill-switch spec with physical-halt requirement |
| **`claude_gainer` sparkline contradiction** | Dashboard payload coherence issue | Added to Phase J+ anomaly detector scope |
| **Drift KS_D = 0.0498** vs critical 0.0460 | Marginal drift, not catastrophic | Revised risk language; monitoring not emergency |

### Revised PR disposition

| PR | Original | Revised | Rationale |
|----|----------|---------|-----------|
| #1017 | Merge as mega-PR | **5 sub-PRs**: resolver v2 table, kill_switch_ladder doc, position_sizer_v2, state_machine staging, daily_edge_report | Wire-Up violation + 581 JSON files |
| #1018 | Merge as mega-PR | **4 sub-PRs**: MEME split schema, signal_quality_ml wire, funding_arb backtest, quarantine automation | Payload-contract risk |
| #1019 | Merge as mega-PR | **3 sub-PRs**: factor sleeves, G10 carry, yield curve | BOND floor-change without gate |
| #1020 | Merge as mega-PR | **3 sub-PRs**: FUTURES Donchian, OPTIONS defined-risk, CEF NAV discount | Stage H violation |

---

## 1. Executive Summary

The audit dashboard is a **rich data viewer** but not yet a **decision cockpit**. Mercury2 correctly identified that the first priority is truth-layer consistency (missing assets, gate policy drift, circuit-breaker freshness). *This plan assumes Mercury2 P0 items ship first* and layers the **6-Level Gate-to-Money Protocol** on top so the dashboard becomes an operational control surface for real-money progression.

**The core gap:** Backend state-machine code exists on `remotes/origin/pr1-core-real-money-state-machine` (`real_money_state_machine.py`, `kill_switch_ladder.py`, `outcome_resolver_v2.py`) but is **completely invisible** on `/audit`. The only protocol UI today is a static `real_money.html` page and a single COT paper-pilot tracker. The Kimi protocol forces binary decisions at 6 levels (Monkey Test ÔåÆ Slippage ÔåÆ Safety ÔåÆ Shadow ÔåÆ Micro ÔåÆ Scale/Kill); the dashboard must surface these levels per asset class and enforce visibility of blockers.

---

## 2. Current State Assessment

### What works today
| Component | Status | Evidence |
|-----------|--------|----------|
| Active Picks grid + live Binance prices | Live | `audit_dashboard/index.html` |
| 5-AI Battle (Claude vs Antigravity vs Grok vs KIMI vs Mercury) | Live | JS-rendered competition table |
| Score Tracker / What-If Performance | Live | Snapshot history every 15 min |
| DSR Anti-Overfit sidecar | Live | `anti_overfit.html` |
| COT Paper Pilot tracker | Live | `paper_pilot.html` (single asset-class deviant) |
| Static Real Money hub | Live | `real_money.html` (static HTML, not state-machine driven) |
| Codex state machine (backend) | Partial | `REHAB ÔåÆ OOS_READY ÔåÆ SHADOW ÔåÆ LIVE_ELIGIBLE` hardcoded in narrative only |
| Hard-blocks / kill lists | Live | `quality_gates.py` `BLOCKED_*` sets |

### What's missing (the decision-layer gap)
| Missing | Impact | Backend exists? |
|---------|--------|-----------------|
| Per-asset-class protocol level (1ÔÇô6) | Operators cannot see which gate blocks progression | No UI; backend on `pr1-core-real-money-state-machine` |
| Real-time kill-switch ladder status | No visibility into GREENÔåÆYELLOWÔåÆORANGEÔåÆREDÔåÆBLACK | `kill_switch_ladder.py` on remote branch |
| 5-AI Consensus Adherence Rate | Battle is entertainment, not gated decision support | No |
| Shadow-paper tracking beyond COT | Only COT has `paper_pilot.html`; EQUITY/CRYPTO/etc. do not | Partial (`real_money_state_machine.py` supports all classes) |
| Monkey Test / Slippage Reality panels | No UI for Level 1 or Level 2 gates | No |
| Resolver gap visibility | 0/3,500 resolved picks is backend-only; not on dashboard | `outcome_resolver_v2.py` on remote branch |
| Auto-generated `real_money.html` | Page is static; drifts from actual state | No generator |
| ML calibration warning banner | Inverted confidence (confÔëÑ0.9 WR 14.4%) is buried in tooltip | No prominent banner |

---

## 3. Enhancement Plan

### Phase A ÔÇö Prerequisite: Merge PR #1017 (backend state machine)
**Owner:** Quant eng + user sign-off  
**Duration:** Days 1ÔÇô3  
**Blocks everything else.**

1. **Open sub-PRs #1017a-e** from `pr1-core-real-money-state-machine` into `main` (via staging branch).
   - Sub-PR #1017a: `outcome_resolver_v2.py` + `at_pick_outcomes` table schema
   - Sub-PR #1017b: `kill_switch_ladder.py` + hierarchy documentation
   - Sub-PR #1017c: `position_sizer_v2.py` + Kelly-0.25 sizing
   - Sub-PR #1017d: `real_money_state_machine.py` staging (no LIVE transitions)
   - Sub-PR #1017e: `daily_edge_report.py` + auto-generation
   - Verify resolver backfill on the 3,500 orphaned picks (**2-week task, not 3-day**; run parallel to UI phases).
   - Run 96 tests shipped in the PR + validate 581 JSON data files for schema integrity.
2. **Wire state-machine JSON output** into `audit_trail/dashboard_generator.py`.
   - New payload block: `protocol_state.by_asset_class`
   - Keys per class: `current_state`, `current_level` (1ÔÇô6), `next_state`, `blockers[]`, `guard_failures[]`, `manual_approval_required`, `last_transition_at`, `shadow_paper_stats`.
3. **Wire kill-switch ladder JSON** into the payload.
   - New payload block: `kill_switch.status`
   - Keys: `portfolio_level`, `asset_class_levels{}`, `strategy_levels{}`, `active_actions[]`, `triggered_at`.

*Success criteria:* `dashboard_data.json` contains `protocol_state` and `kill_switch` blocks; CI passes; resolver backfill completes.

---

### Phase B ÔÇö Dashboard State Machine Surface
**Owner:** Frontend / dashboard generator  
**Duration:** Days 4ÔÇô7  
**Files:** `audit_dashboard/template.html`, `audit_dashboard/dashboard_enhancements.js`, `audit_trail/dashboard_generator.py`

1. **Asset Class Protocol Cards** (replace or augment existing asset-class health cards).
   - Each card shows:
     - **Current State** badge: `BLOCKED` ­ƒö┤ | `REHAB` ­ƒƒí | `OOS_READY` ­ƒöÁ | `SHADOW` ­ƒƒú | `LIVE_ELIGIBLE` ­ƒƒó | `LIVE` ­ƒÆ░
     - **Protocol Level** (1ÔÇô6) with progress bar
     - **Blocker list** (top 3 guard failures)
     - **Next gate** button (disabled until guards pass)
   - Color coding aligned to Kimi decisions:
     - `SCALE` ÔåÆ green pulse (EQUITY)
     - `MUTATE` ÔåÆ amber pulse (CRYPTO, FOREX, BOND)
     - `KILL & REPLACE` ÔåÆ red strikethrough (COMMODITY `cta_commodity_momentum_term`)
     - `EXPAND NEW` ÔåÆ cyan pulse (OPTIONS, MEME, CEF, FUTURES)
2. **State Transition Log** (new tab or modal).
   - Table: `timestamp | asset_class | from_state | to_state | trigger | guard_results | approved_by`
   - Sourced from `real_money_history.json` (produced by `real_money_state_machine.py`).

*Success criteria:* Load `/audit`; every asset-class card shows state + level; hovering shows blocker tooltips.

---

### Phase C ÔÇö Kill Switch Ladder Widget
**Owner:** Frontend  
**Duration:** Days 5ÔÇô8 (parallel with B)  
**Files:** `audit_dashboard/template.html`, `audit_dashboard/dashboard_enhancements.js`

1. **Sticky Header Kill-Switch Indicator** (always visible).
   - Portfolio-level pill: `GREEN` / `YELLOW` / `ORANGE` / `RED` / `BLACK`
   - On hover: breakdown by asset class and strategy.
   - On `RED` or `BLACK`: full-screen interstitial warning with auto-actions taken (e.g., "HALTED CRYPTO at 10:14 UTC ÔÇö PF 0.78 for 5 days").
2. **Active Actions Panel** (new tab or sidebar).
   - Live list of auto-actions executed by the ladder:
     - `REDUCE_POSITIONS 50%` @ `YELLOW`
     - `HALT_TRADING` @ `ORANGE`
     - `FULL_HALT` @ `RED`
     - `PAPER_ONLY` @ `BLACK`
   - Each row shows: trigger condition, affected symbols, recovery criteria.

*Success criteria:* Change a mock portfolio drawdown to >5%; dashboard shows `YELLOW` within one refresh cycle.

---

### Phase D ÔÇö 6-Level Protocol Progress Tracker
**Owner:** Frontend + backend payload  
**Duration:** Days 6ÔÇô10  
**Files:** `audit_dashboard/template.html`, `audit_trail/dashboard_generator.py`

Implement the Kimi **6-Level Gate-to-Money** as a first-class UI component:

| Level | Name | Dashboard Surface | Gate Criteria |
|-------|------|-------------------|---------------|
| 1 | **Monkey Test** | New panel: "Monkey Test Results" | Beat 95th %ile of 1,000 random strategies; PSR > 0.95 |
| 2 | **Slippage Reality** | New panel: "Net-of-Cost Edge" | Net profit > 50% of gross after all costs |
| 3 | **Safety Architecture** | Kill-switch widget (Phase C) + position-size panel | Kelly├ù0.25, correlation guard, max position limits |
| 4 | **Shadow Paper** | Expanded `paper_pilot.html` for all asset classes | 30 days, live Sharpe > 0.7├ùbacktest |
| 5 | **Micro Real-Money** | New badge on active picks: "MICRO LIVE $500" | <$5k allocation, <5% DD, profitable after 30d |
| 6 | **Scale or Kill** | State machine card shows decision matrix | Either scaled to full allocation or killed |

**UI Component:** A vertical stepper (like a checkout flow) per asset class, showing:
- Ô£à / ÔÅ│ / ÔØî for each level
- Tooltip with exact metric and threshold
- "Advance to Level X" button (auto-disabled until criteria met)

*Success criteria:* Click into any asset class; see 6-level stepper with real data.

---

### Phase E ÔÇö Per-Asset-Class Action Cards
**Owner:** Dashboard generator + frontend  
**Duration:** Days 8ÔÇô12  
**Files:** `audit_dashboard/template.html`, `audit_trail/dashboard_generator.py`

Surface the Kimi per-asset-class decisions as actionable cards:

1. **EQUITY ÔÇö SCALE** ­ƒƒó
   - Show factor-sleeve breakdown (value, momentum, quality, low-vol, dividend)
   - Highlight `elite_score` lowered 30ÔåÆ15 impact
   - CTA: "Initiate Micro Live ($500)" ÔåÆ triggers state transition to `SHADOW`
2. **CRYPTO ÔÇö MUTATE** ­ƒƒí
   - MEME split badge: "MEME class separated from CRYPTO 2026-05-XX"
   - Signal Quality ML integration status: `+5ÔÇô15pp WR expected`
   - Funding rate arb strategy tracker
3. **FOREX ÔÇö MUTATE** ­ƒƒí
   - Carry trade sleeve status (G10 carry, Sharpe 0.86 target)
   - Regime filter overlay
4. **BOND ÔÇö MUTATE** ­ƒƒí
   - Yield curve steepener status
   - `elite_score` 30ÔåÆ15 badge
5. **COMMODITY ÔÇö KILL & REPLACE** ­ƒö┤
   - `cta_commodity_momentum_term` quarantine banner: PF 0.02, 58% flat exits
   - Triple-screen replacement deployment tracker
6. **FUTURES ÔÇö EXPAND** ­ƒöÁ
   - Accumulation mode badge
   - Donchian channel strategy status
7. **OPTIONS ÔÇö EXPAND NEW** ­ƒöÁ
   - Defined-risk only badge (credit spreads, iron condors)
   - 5% cap warning, 90-day paper minimum countdown
8. **MEME ÔÇö EXPAND NEW** ­ƒöÁ
   - Split-from-CRYPTO badge
   - Pump-dump detection overlay
9. **CEF ÔÇö EXPAND NEW** ­ƒöÁ
   - NAV discount tracker
   - Monthly rebalance countdown

*Success criteria:* Each card has a primary metric, a decision badge, and a CTA button tied to the state machine.

---

### Phase F ÔÇö 5-AI Consensus Adherence & Battle Integration
**Owner:** Frontend  
**Duration:** Days 10ÔÇô14  
**Files:** `audit_dashboard/dashboard_enhancements.js`, `audit_trail/dashboard_generator.py`

The 5-AI Battle is currently a competition. It must become a **gated consensus engine**.

1. **Weighted Consensus Score** per pick:
   - `Final Score = w_Alpha * S_AlphaEngine + w_KIMI * S_KIMI + w_Claude * S_Claude + w_Grok * S_Grok + w_Mercury * S_Mercury`
   - Weights tuned by forward WR of each agent (auto-updated weekly).
2. **Consensus Adherence Rate** metric:
   - `% of top battle picks that also pass Level 2+ protocol gates`
   - Shown as a summary badge: "Consensus Adherence: 73% (target ÔëÑ90%)"
3. **Battle ÔåÆ Promotion Gate**:
   - Only picks with consensus score ÔëÑ threshold AND all Level 1ÔÇô3 gates clear appear in the "Promotion Candidates" table.
   - New filter button: `­ƒÄ» Protocol-Ready Picks`

*Success criteria:* A pick can win the battle but be excluded from promotion if it fails the monkey test or kill-switch guard.

---

### Phase G ÔÇö Shadow Paper Expansion (Beyond COT)
**Owner:** Backend + frontend  
**Duration:** Days 12ÔÇô18  
**Files:** `alpha_engine/v2_enhancements/real_money_state_machine.py`, `audit_dashboard/paper_pilot.html` (refactor to template), `audit_trail/dashboard_generator.py`

Today only `cot_positioning + CT=F` has a paper-pilot tracker. The Kimi protocol requires **every asset class entering Level 4** to have a shadow paper tracker.

1. **Generic Paper Pilot Template**:
   - Convert `paper_pilot.html` from a COT-hardcoded page to a parameterized template: `paper_pilot.html?asset_class=EQUITY&strategy=factor_sleeve_value`
   - Data source: `data/paper_pilot_{asset_class}_{strategy}.json`
2. **Auto-provision trackers** when state machine transitions to `SHADOW`:
   - On transition, state machine auto-creates JSON tracker with:
     - `start_date`, `initial_notional`, `expected_per_trade_band`, `graduation_gate` (30 days, Sharpe floor)
3. **Dashboard Integration**:
   - New tab: "Shadow Paper"
   - Table of all active shadow experiments: asset class, strategy, days in shadow, current WR vs backtest WR, Sharpe, graduation verdict.

*Success criteria:* Transition EQUITY to `SHADOW`; a new tracker JSON appears and is visible on `/audit` within one cron cycle.

---

### Phase H ÔÇö Monkey Test & Slippage Reality Panels
**Owner:** Backend + frontend  
**Duration:** Days 15ÔÇô21  
**Files:** New `tools/monkey_test_runner.py`, `tools/slippage_reality_checker.py`, `audit_dashboard/template.html`

These are the Level 1 and Level 2 gates from the Kimi protocol.

1. **Monkey Test Panel** (`Level 1`):
   - Runs 1,000 random strategies (same n-trades, same holding periods) on the asset class's historical data.
   - Shows: distribution of random PF/Sharpe, 95th %ile threshold, candidate strategy's percentile.
   - Gate: candidate must be >95th %ile AND PSR > 0.95.
   - UI: histogram with candidate marked as a vertical line; green if above 95th %ile, red if below.
2. **Slippage Reality Panel** (`Level 2`):
   - Overlay realistic costs per asset class:
     - CRYPTO: 5ÔÇô10 bps taker fee + spread
     - EQUITY: commission + SEC fee + slippage (use `transaction_cost_model.py`)
     - FOREX: spread + rollover
     - FUTURES: commission + tick slippage
   - Shows: Gross PF vs Net PF. Gate: Net PF > 0.5 ├ù Gross PF.
   - UI: side-by-side bar chart (Gross vs Net) per asset class.

*Success criteria:* Run monkey test on EQUITY factor sleeve; dashboard shows histogram + "PASS" badge.

---

### Phase I ÔÇö Auto-Generated `real_money.html`
**Owner:** Backend generator  
**Duration:** Days 18ÔÇô24  
**Files:** `audit_trail/real_money_generator.py` (new), `audit_dashboard/real_money.html` (replace static with generated)

The current `real_money.html` is static and drifts. Replace it with an auto-generated page driven by `real_money_state_machine.py`.

1. **Generator script** (`audit_trail/real_money_generator.py`):
   - Reads `alpha_engine/data/real_money_history.json`
   - Reads `alpha_engine/data/kill_switch_status.json`
   - Reads `alpha_engine/data/outcome_resolver_log.json`
   - Produces `audit_dashboard/real_money.html` (same URL, now dynamic)
2. **Content**:
   - 10-step readiness gate (existing) but with **live checkmarks** pulled from state machine
   - Per-asset-class state cards (from Phase B)
   - Active hard-blocks (existing, but auto-updated from `quality_gates.py`)
   - Queued P0/P1/P2 items (existing, but sourced from a JSON file instead of hardcoded HTML)
3. **Deploy trigger**:
   - Add to `.github/workflows/audit-dashboard.yml` push-trigger paths (per AGENTS.md rule)

*Success criteria:* Commit a state change; `real_money.html` updates within the cron cycle without manual HTML editing.

---

### Phase J ÔÇö ML Calibration Warning Banner (Quick Win)
**Owner:** Frontend  
**Duration:** 1 day (can ship anytime)  
**Files:** `audit_dashboard/dashboard_enhancements.js`, `audit_dashboard/template.html`

The inverted ML confidence is a critical safety issue. Surface it prominently.

1. **Sticky warning banner** (dismissible for 24h):
   - "ÔÜá´©Å ML confidence is inverted: confÔëÑ0.9 bucket WR 14.4%; conf 0.5ÔÇô0.6 bucket WR 60.3%. `_normalize_confidence` defense active. Do NOT size by raw confidence."
   - Shown on `/audit` and `/audit/real_money.html`
2. **Per-pick confidence badge**:
   - If raw confidence ÔëÑ 0.9, show inverted warning tooltip: "High raw confidence historically predicts LOW WR. Verify with forward data."

*Success criteria:* Banner visible on every audit page load until calibration is fixed.

---

## 4. 30-Day Execution Roadmap

Aligned with Kimi Code "30-Day Escape Plan" and Mercury2 14-day sequence.

| Days | Phase | Deliverable | Owner |
|------|-------|-------------|-------|
| 1ÔÇô3 | A | Merge PR #1017, wire state machine + kill switch into dashboard payload | Quant eng |
| 4ÔÇô7 | B + C | Asset class protocol cards + kill-switch sticky header | Frontend |
| 8ÔÇô10 | D | 6-Level Protocol Progress Tracker (MonkeyÔåÆScale) | Frontend + backend |
| 11ÔÇô12 | E | Per-asset-class action cards (SCALE/MUTATE/KILL/EXPAND) | Frontend |
| 13ÔÇô14 | F | 5-AI consensus adherence + promotion gate | Frontend |
| 15ÔÇô18 | G | Shadow paper expansion beyond COT | Backend + frontend |
| 19ÔÇô21 | H | Monkey Test + Slippage Reality panels | Backend + frontend |
| 22ÔÇô24 | I | Auto-generated `real_money.html` | Backend |
| 25ÔÇô28 | J + polish | ML calibration banner, operator presets (Incident/Promotion/Research), Mercury2 P2 UX | Frontend |
| 29ÔÇô30 | Validation | End-to-end protocol test: transition one asset class through all 6 levels on the dashboard | QA |

---

## 5. Files to Create / Modify

### New files
| Path | Purpose |
|------|---------|
| `audit_trail/real_money_generator.py` | Auto-generate `real_money.html` from state machine JSON |
| `tools/monkey_test_runner.py` | Level 1 gate: 1,000 random strategy benchmark |
| `tools/slippage_reality_checker.py` | Level 2 gate: net-of-cost PF calculation per asset class |
| `tests/test_audit_protocol_surface.py` | CI: assert protocol_state block exists and is fresh |
| `tests/test_kill_switch_widget.py` | CI: mock kill-switch escalation and verify dashboard JSON |
| `tests/test_monkey_test_gate.py` | CI: assert monkey test histogram data present for top strategies |
| `audit_dashboard/data/paper_pilot_TEMPLATE.json` | Generic template for shadow paper trackers |

### Modified files
| Path | Change |
|------|--------|
| `audit_trail/dashboard_generator.py` | Ingest `protocol_state`, `kill_switch`, `monkey_test`, `slippage_reality` blocks into payload |
| `audit_dashboard/template.html` | Add protocol cards, kill-switch header, 6-level stepper, consensus adherence, ML banner |
| `audit_dashboard/dashboard_enhancements.js` | Render protocol UI, kill-switch interstitial, operator presets |
| `audit_dashboard/real_money.html` | Replace static with auto-generated (or redirect to generated) |
| `.github/workflows/audit-dashboard.yml` | Add `audit_trail/real_money_generator.py` to push-trigger paths |
| `alpha_engine/v2_enhancements/real_money_state_machine.py` | Add `to_dashboard_json()` helper |
| `alpha_engine/v2_enhancements/kill_switch_ladder.py` | Add `to_dashboard_json()` helper |

---

## 6. Test Plan

1. **`tests/test_audit_protocol_surface.py`**
   - Assert `dashboard_data.json` contains `protocol_state.by_asset_class` with all 9 asset classes.
   - Assert each class has `current_state`, `current_level`, `blockers`.
   - Fail if `kill_switch` block is missing or stale (>5 min).

2. **`tests/test_kill_switch_widget.py`**
   - Mock portfolio drawdown to 6% ÔåÆ expect `YELLOW` in dashboard JSON.
   - Mock asset-class PF 0.75 for 5 days ÔåÆ expect `ORANGE` for that class.
   - Assert active actions include `REDUCE_POSITIONS`.

3. **`tests/test_monkey_test_gate.py`**
   - Run monkey test on a known-good strategy.
   - Assert 95th %ile threshold is computed and candidate percentile is shown.
   - Fail if candidate is below 95th %ile but marked `PASS`.

4. **`tests/test_shadow_paper_auto_provision.py`**
   - Transition a test asset class to `SHADOW`.
   - Assert tracker JSON is created within 60 seconds.
   - Assert dashboard payload includes the new shadow experiment.

5. **`tests/test_real_money_html_freshness.py`**
   - Assert `real_money.html` generated timestamp is within 1 hour of current time.
   - Assert at least one active block and one queued item are rendered.

---

## 7. Dependency on Mercury2 Plan

This plan **builds on top of** Mercury2 P0/P0.5:

| Mercury2 Item | How this plan uses it |
|---------------|----------------------|
| P0.1 Fix missing money-ready script | Kill-switch and protocol cards depend on `money_ready_filter.js`; verify it deploys before adding dependent UI |
| P0.2 Unify gate policy | Protocol Level 3 (Safety) uses unified thresholds; state-machine guards must read canonical config |
| P0.3 Drift freshness | Protocol Level 4 (Shadow) and Level 5 (Micro) require fresh drift metadata; stale drift = auto-block |
| P0.5 Policy-diff panel | Place the policy-diff panel *inside* the Level 3 Safety stepper so operators see config-vs-runtime mismatches at the exact gate they affect |
| P1.6 Class lifecycle states | This plan is the UI surface for Mercury2's backend lifecycle states; Mercury2 defines the transitions, this plan visualizes them |
| P2.8 Operator presets | Extend Mercury2 presets: add "Protocol Mode" preset that shows only Levels, kill switch, and promotion candidates |

---

## 8. Risk & Mitigation

| Risk | Mitigation |
|------|------------|
| PR #1017 merge conflicts | Rebase `pr1-core-real-money-state-machine` onto latest `main` before merge; run full backfill in staging |
| Dashboard payload bloat | Put new blocks behind feature flags (`PROTOCOL_UI_ENABLED`) in `dashboard_generator.py`; default OFF until validated |
| Kill-switch false positives | Shadow mode for kill switch: UI shows level but does NOT auto-execute actions for 14 days |
| Operator overwhelm | Ship Phase J (ML banner) immediately for safety; ship operator presets (Mercury2 P2.8 + Protocol Mode) before Phase D |
| Backend JSON schema drift | Version the `protocol_state` block (`"schema_version": "2026-05-14-v1"`); dashboard JS refuses to render unknown versions |

---

## 9. Success Criteria (30-Day Checkpoint)

- [ ] `/audit` loads with kill-switch header showing `GREEN` and all 9 asset classes showing protocol level badges
- [ ] EQUITY card shows `Level 4 (SHADOW)` or higher with a visible "Initiate Micro Live" CTA
- [ ] COMMODITY card shows `Level 0 (KILL & REPLACE)` with `cta_commodity_momentum_term` quarantine banner
- [ ] 5-AI Battle shows Consensus Adherence Rate ÔëÑ target
- [ ] Monkey Test panel runs and shows histogram for top 3 strategies
- [ ] `real_money.html` is auto-generated and timestamp is <1h old
- [ ] All 6 new tests pass in CI
- [ ] No 404 assets on `/audit/` (Mercury2 P0.1 complete)

---

*Next action:* User approval ÔåÆ begin Phase A (merge PR #1017) and Phase J (ML calibration banner quick win) in parallel.
