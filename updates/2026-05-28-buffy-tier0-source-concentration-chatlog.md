# Buffy Session — 2026-05-28

**Branch:** `fix/audit-tier0-edge-pgates`
**Session scope:** Source-concentration cap (action #3), AI Tournament page review

---

## 1. Source-Concentration Cap Implementation

**Files modified:**

### `alpha_engine/money_ready_verdict.py`
- Added `MAX_SOURCE_CONCENTRATION = 0.40` (global) and per-class override `COMMODITY: 0.60`
- `_class_stats()` now tracks top source and its share of resolved picks
- `_verdict()` caps any class at `WATCH` when a single source dominates the resolved sample (>40% globally, >60% for COMMODITY), mirroring the existing symbol-concentration guard
- Output fields on the verdict dict: `top_source`, `top_source_share`, `source_concentration_capped`

### `tests/test_money_ready_verdict.py`
- `_make_picks()` now accepts `source_system` parameter (list for round-robin, string for single value, `None` defaults to `strategy` — backward-compatible)
- Updated `test_returns_expected_keys` to include new source-concentration fields
- Fixed M-105 ML quarantine tests to use diverse source systems (single-source now triggers the cap → WATCH → no quarantine recommendation)
- **4 new tests:**
  - `test_m070_single_source_concentration_caps_to_watch` — CRYPTO single source → WATCH
  - `test_m070_diversified_sources_allow_money_ready` — 3 sources → passes cap
  - `test_commodity_source_concentration_cap_override_at_60pct` — COMMODITY 55% → allowed
  - `test_commodity_source_concentration_fails_above_60pct` — COMMODITY 65% → WATCH

**Result: All 47 tests pass ✅**

Pre-existing failure in `tests/test_quality_gates.py::test_smart_gate_rejects_source_less_pick` — unrelated to these changes, confirmed via `git stash`.

---

## 2. AI Tournament Page Review

Visited `https://findtorontoevents.ca/audit/ai-tournament.html`

**Local source:** `audit_dashboard/ai-tournament.html` (~740 lines of hand-coded HTML/CSS/JS)

### Page sections:
- Pipeline freshness banner (data from `ai_tournament_picks_latest.json`)
- Phase bar (1A done, 1B active, 1C pending, Phase 2 future)
- Leaderboard (forward-test only, min n=30, score = lower_95%(WR) × lower_95%(PF))
- Model summary + fleet diagnostics from JSON data files
- 23 unique strategy personas across 4 categories
- 8 asset classes with locked pre-registered universes
- Tier-rating algorithms with consensus feature analysis
- AI vs System comparison table

### Data sources:
- `data/ai_tournament_picks_latest.json` (primary, cache-busted)
- `data/ai_tournament_leaderboard.json` (fallback)
- `data/ai_tournament_model_summary.json`
- `data/ai_tournament_model_diagnostics.json`
- Per-day `picks_YYYYMMDD.json` files (fallback)

---

## 3. Git State at End of Session

- Branch: `fix/audit-tier0-edge-pgates`
- Changes not staged:
  - `alpha_engine/money_ready_verdict.py` — modified (source-concentration cap)
  - `tests/test_money_ready_verdict.py` — modified (tests)
  - `audit_dashboard/dashboard_enhancements.js` — modified (DB health banner)
  - `audit_trail/quality_gates.py` — modified (pre-existing)
  - Various data files (auto-updated timestamps, caches)
- Untracked: reports, updates, memory files
- All committed work up to `Scanner data update [2026-05-28 01:40 UTC]` on branch

---

## 4. Next Actions (suggested)

- Commit source-concentration changes and push branch
- Verify CI passes on the branch
- Check AI Tournament page for stale data / model coverage gaps
