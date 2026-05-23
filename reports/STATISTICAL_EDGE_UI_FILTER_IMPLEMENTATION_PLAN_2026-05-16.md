# Statistical Edge + UI Filter Implementation Plan
**Date:** 2026-05-16  
**Author:** Grok 4.3 (after money-maker-readyv2 run + full reconciliation of 14+ daily idea files from Antigravity, Kimi CLI, GROK, Cursor, KimiCode, Kilocode, edge-per-class, synthesis, etc.)  
**Status:** Draft for Swarm Peer Review  
**Goal:** Convert the reconciled OOS-validated statistical edge into the highest-impact per-asset-class improvements that a user can reach with 1-2 clicks on `findtorontoevents.ca/audit`.

---

## 1. Executive Summary

We have strong, multi-agent-validated statistical edge in several places (especially `aggregated_picks` + `kimi_signal_tracking` on CRYPTO, post-dedup COMMODITY via `multi_asset_cot`, true EQUITY via elite_score + RSI-2, ETF). However, the live UI filter surface (`money_ready_filter.js`, `hc_filter.js`, index.html buttons) is still partially based on older optimistic numbers and does not yet make the **best OOS-validated filters** trivially accessible.

This plan prioritizes changes that are:
- Highest expected portfolio PnL lift (80/20 statistical levers)
- **Easily filterable** via the existing dashboard UI (no complex manual filtering required)
- Validated against the latest code state (2026-05-16 dashboard_data.json, weekly_filter reports, money_ready_filter.js, hc_filter.js, edge_filter_engine_v3.py)
- Ready for immediate swarm peer review

---

## 2. Current State Verification (Latest Code)

- `audit_dashboard/data/dashboard_data.json`: generated 2026-05-16T09:34Z (0.23h old — fresh)
- `reports/weekly_filter_20260516T065000Z.md` + `.json`: Latest OOS v2 output from `edge_filter_engine_v3.py` (Kimi CLI 05-16)
- `audit_dashboard/money_ready_filter.js`: Still contains older hardcoded `SUPREME_EDGE_REAL` list (cot_positioning 89.8%, specific ml_enhanced 85-100% on n=25-34)
- `audit_dashboard/hc_filter.js`: Partially updated (trust_score preference + confidence 0.80-0.90 danger zone flagged)
- `audit_dashboard/index.html`: Has pulsing **MONEY READY** and **HIGH CONVICTION** hero buttons + `#active-filter-tags` + "Proven Only"
- `tools/edge_filter_engine_v3.py`: Produces machine-readable weekly filter with Kelly sizing
- OOS-validated reports (`statistical_edge_analysis_2026-05-16.md`, etc.): Show drag systems, dedup needs, pipeline gaps for COMMODITY, true equity thinness

**Key Gap:** The "MONEY READY" button (the most prominent "this is the edge" UI element) is not yet aligned with the reconciled 05-16 OOS + dedup reality.

---

## 3. Per-Asset-Class Most Impactful Changes (Statistical + UI Filterability)

| Priority | Asset Class | #1 Statistical Lever (Highest ROI) | UI Filter Method (1-2 clicks) | Expected Impact | Effort | Key Files | Validation Status |
|----------|-------------|------------------------------------|-------------------------------|------------------|--------|-----------|-------------------|
| **P0** | **CRYPTO** | Quarantine 4-5 drag systems (`alpha_engine`, `ml_crypto_pred`, `quan_engine`, `luxalgo`, `dna_winner_picks`) + route through `aggregated_picks` + `kimi_signal_tracking` LONG + RR 1.5-2.0 + conf ≥0.70 | New `CRYPTO_ULTRA` preset (or make it the default behavior of MONEY READY for CRYPTO) | +0.4–0.8 PF on the class (biggest volume lever) | Low-Medium | `quality_gates.py`, `money_ready_filter.js` / new `institutional_presets.js`, payload `source_system` + `trust_score` | Latest OOS + daily ideas (GROK, KIMI, edge_per_class) agree |
| **P0** | **COMMODITY** | Fix pipeline so `multi_asset_cot` + clean post-dedup COT actually lands in `universal_resolved_picks.json` (currently n=0 in validated OOS) + enforce dedup guard | `COMMODITY Post-Dedup COT` preset (shows "Awaiting validated n≥100" until pipeline fixed) | Unlocks best-looking T1 class (PF ~2.57 / 62.6% post-dedup) | Medium | resolver / alpha_engine emission, `verify_system_pf.py`, money_ready_filter.js | All daily ideas + MASTER M-008/M-021 flagged this |
| **P1** | **EQUITY** | True stock symbol validation (strip crypto mislabels from `signal_validation`) + promote `stocks_competition` + elite_score ≥55 + US close hours tilt | `EQUITY Real Stocks` preset | Turns thin promising edge into reliable T2 with 5+ weekly real equity picks | Medium | `dashboard_generator.py`, payload symbol validation, `money_ready_filter.js` | Cursor + Antigravity + edge_per_class consensus |
| **P1** | **ETF** | Expand universe (XLF/XLE/XLK + sector dual momentum) to reach n≥150 resolved | Simple ETF asset filter + "Strong ETF" preset (exclude SLV) | Maintains PF ≥2.0 while doubling volume | Low | universe config, `money_ready_filter.js` | Synthesis + MASTER M-036 |
| **P2** | **FOREX** | Hard block (or force exclusively through `signal_validation` + `kimi_signal_tracking`) | FOREX hidden or clearly marked "Under Mutation — Not Recommended" in all presets | Stops negative expectancy bleeding + frees cycles | Low | `quality_gates.py` + `FOREX_HARD_DISABLE` flag, UI state | Universal agreement across 14 daily idea files + MASTER M-007 |
| **P3** | **BOND / FUTURES** | Accumulate + finish `contract_type` classifier (already started 05-16) | Keep in "Paper / Research" tab only until n≥50 credible | Avoids premature sizing on meaningless samples | Low | `dashboard_generator.py` | GROK 05-16 + MASTER M-020 |

---

## 4. Cross-Cutting Highest-Leverage Changes (UI + Statistical)

### 4.1 Evolve "MONEY READY" into Data-Driven Institutional Edge Presets (Highest UI Impact)
- Replace or augment the hardcoded `SUPREME_EDGE_REAL` in `money_ready_filter.js` with logic that consumes the latest `reports/weekly_filter_*.json` (or a compiled `institutional_edge_presets.json`).
- Add a **"Proven Edge Presets" dropdown** (or dedicated chips next to the hero buttons) with one-click options:
  - CRYPTO_ULTRA (OOS Verified)
  - Institutional Core (T1 + T2 across classes)
  - COMMODITY Clean COT
  - EQUITY Real Stocks
  - ETF Strong
- Update the pulsing **MONEY READY** button to apply the strictest superset (all Tier 1 OOS-validated filters).
- Active filter tags must clearly show "OOS Verified • DSR ≥0.95 • Dedup Safe" etc.

**Files:**
- `audit_dashboard/money_ready_filter.js` (major refactor)
- `audit_dashboard/index.html` (new preset dropdown + chips)
- New or extended `audit_dashboard/institutional_presets.js`
- `tools/edge_filter_engine_v3.py` → emit a clean `presets` section in the weekly JSON

### 4.2 Payload Field Hygiene (Required for Reliable UI Filtering)
Ensure the following fields are reliably present and normalized on every pick in `dashboard_data.json`:
- `source_system` (or `agreeing_sources`)
- `trust_score` (preferred over raw `confidence` for CRYPTO — already partially in hc_filter.js)
- `elite_score`
- `risk_reward`
- `is_post_dedup_safe` (boolean, especially for COMMODITY)
- `oos_verified` / `validated_n`
- Strategy family tags (for CRYPTO drag quarantine)

**Files:** `audit_trail/dashboard_generator.py`, `alpha_engine/score_booster.py`, quality gates.

### 4.3 Align "HIGH CONVICTION" with Latest Anti-Edge Findings
- `hc_filter.js` already has good recent updates (trust_score, 0.80-0.90 confidence danger zone). Make sure it also respects the drag system quarantine list from P0 CRYPTO work.

### 4.4 Weekly Filter → UI Sync (Single Source of Truth)
- The `edge_filter_engine_v3.py` (or a thin wrapper) should output both the human `weekly_filter_*.md` **and** a machine `institutional_presets.json` that directly drives the UI buttons.
- This prevents the "statistical work lives in reports, UI is stale" problem we currently have.

---

## 5. Phased Rollout

**Phase 0 — Quick Wins (Today / Tomorrow)**
- Quarantine the 4-5 CRYPTO drag systems in `quality_gates.py` + probation JSON.
- Hard-disable FOREX emissions (or force through elite systems only).
- Minor update to `money_ready_filter.js` to at least block the known drag systems and bad confidence bands on CRYPTO.

**Phase 1 — UI Surface Alignment (3-7 days)**
- Refactor `money_ready_filter.js` + add presets dropdown.
- Wire `weekly_filter_*.json` as the driver for presets.
- Expose `trust_score`, `is_post_dedup_safe`, `elite_score` reliably.
- Update hero button titles/tooltips with OOS numbers from 05-16 reports.

**Phase 2 — Structural Statistical Work (7-21 days)**
- COMMODITY pipeline fix + dedup guard (unlocks P0 edge).
- True EQUITY symbol validation + stocks_competition promotion.
- ETF universe expansion.
- Full data-driven institutional presets (no more hardcoded lists).

---

## 6. Success Criteria (Measurable)

- A user can reach the best OOS-validated edge for any asset class with **≤2 clicks** (one preset button + optional asset chip).
- "MONEY READY" / new Institutional button reflects the latest reconciled OOS + dedup numbers (not the older 89.8%/100% claims).
- CRYPTO class PF on filtered active picks improves measurably within 7-14 days of drag quarantine.
- COMMODITY shows validated n≥50-100 in `universal_resolved_picks.json` within 2-3 weeks.
- Active filter tags clearly communicate "OOS Verified", "Dedup Safe", "DSR ≥0.95".

---

## 7. Risks & Dependencies

- COMMODITY pipeline fix is a dependency for the biggest unlocked edge.
- Payload changes require coordination with `dashboard_generator.py` (risk of breaking other consumers).
- Over-aggressive quarantine on CRYPTO could temporarily reduce pick volume (mitigate with shadow mode first).
- UI changes must not regress existing "High Conviction" or "Smart Picks" flows.

---

## 8. Request for Swarm Peer Review

This plan has been created after:
- Full `money-maker-readyv2` execution
- Reconciliation against all listed daily idea files (GROK_05-16, KIMI_CLI_05-16, Antigravity, Cursor, KimiCode, edge_per_class, synthesis, etc.)
- Direct inspection of latest `dashboard_data.json`, `money_ready_filter.js`, `hc_filter.js`, `index.html`, `edge_filter_engine_v3.py`, and OOS reports

**Please review for:**
- Statistical validity of the per-class levers
- Realism of the UI filter proposals against current code
- Missing high-impact items
- Correct prioritization
- Any contradictions with latest agent work or code

---

**Next Action After Swarm Feedback:** Incorporate consensus, produce final v1.1 of this plan, then execute Phase 0 + Phase 1 in a focused branch/PR.

---

*End of Draft Plan — Ready for Swarm Review*