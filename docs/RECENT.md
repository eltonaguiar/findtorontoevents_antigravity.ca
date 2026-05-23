# Recent Changes (2026-04-09)

## High Conviction Pick Quality Fixes

This document tracks the recent changes made to fix the "coin-toss" performance issue in high-conviction picks.

**Canonical plan / tooling index:** `docs/MERCURY2_HC_VALIDATION_PIPELINE.md` (kept in sync with `audit_dashboard/hc_filter.js`).

---

## Changes Made

### 1. Scoring Metadata Preservation Fix
**File:** `audit_trail/universal_pick_resolver.py`

**Problem:** The resolver was stripping quality/scoring fields when resolving picks to closed. `elite_score`, `trust_score`, forward stats, etc. were not always available for HC filtering and analytics.

**Solution:** `_SCORING_FIELDS` lists 25+ metrics; `_extract_pick_fields()` preserves them during resolution.

---

### 2. Dashboard High Conviction Filter (hc_filter.js + config)
**Files:** `audit_dashboard/hc_filter.js`, `config/hc_gate_params.json`, `tools/dashboard_hc_rules.py`

**Problem:** The HC preset was letting through too much unvalidated noise relative to proven PROVEN / high-grade rows.

**Solution:** Config-driven **hard gates** (see pipeline doc for the exact current list), including:

- **Grade:** `max(score, elite) >= gradeEffectiveMin` (default 50) — avoids killing strong **elite** or **tier** paths when raw `score` is only ~50.
- Trust tier blocklist, minimum forward trades + forward WR%%, trust score floor, overconfidence rule, regime×direction flags, optional `wf_verdict` FAILING reject, optional **independent signal-group** consensus when `independentGroupsMin > 0`.

Then HF tier paths (S/A/B) and asset-class heuristics (crypto, equity, forex, etc.).

**Note:** An older write-up mentioned extra blocks (graduated confidence 0.60–0.85, tier-B-only score floor, 6-state regime taxonomy) **inside** the same function. Those are **not** in the current `hc_filter.js`; do not document them as shipped unless they appear in the file.

---

### 3. Conviction Stack Backend
**Files:** `alpha_engine/conviction_stack.py`, `alpha_engine/conviction_stack_patch.py`

**Problem:** Backend tiering could diverge from dashboard quality expectations.

**Solution:** Stricter alignment with forward/trust/elite checks on tier paths (details in git history / stack module). Patch file relaxed harmful fallbacks where applicable.

---

## Expected Impact

| Metric | Before (typical) | After (directional) |
|--------|------------------|----------------------|
| HC pass rate | High % of unvalidated rows | Lower %; dominated by gated + tier/heuristic passes |
| Trust / forward hygiene | Many low-trust / thin-forward rows | Driven toward PROVEN + validated forward stats |
| Dashboard WR on filtered set | Near coin-flip on broad book | Higher on **filtered** subset (validate with backtests) |

Run `python tools/backtest_hc_filter.py` on fresh `dashboard_data.json` for current numbers.

---

## Key Insight

Genuinely proven rows (PROVEN, strong forward, sane confidence) already showed strong WR in research; the fix is **stopping the HC preset from advertising weak rows as “high conviction.”**

---

## Related Files

- `audit_trail/universal_pick_resolver.py` — scoring preservation
- `audit_dashboard/hc_filter.js` — dashboard filter
- `config/hc_gate_params.json` — tunable thresholds
- `tools/dashboard_hc_rules.py` — Python mirror + parity tests
- `alpha_engine/conviction_stack.py` — backend tiers
- `docs/MERCURY2_HC_VALIDATION_PIPELINE.md` — **master plan / commands**
- `docs/QUANT_AUDIT_v2.md` — calibration source hygiene
- External: `docs/HC_PICKS_OPTIMIZATION_PLAN.md` if present

---

## Next Steps (updated)

| Step | Status |
|------|--------|
| Regime / direction tuning | Partial — flags in `hc_gate_params.json` |
| Per-portfolio mandates | `config/portfolio_mandate.json`; wire to TV/bus |
| Monitoring / edge decay | `tools/edge_decay_monitor.py` + workflow |
| Correlation at placement | `tools/portfolio_correlation_gate.js` |
| Backtests before deploy | `tools/backtest_hc_filter.py`, `hc_filter_backtest.py`, `hc_csv_backtest.js` |
| Hyrotrader / confidence recalibration | Open — use non–paper-trading data per `QUANT_AUDIT_v2.md` |
| Kill-switch v2 (ATR / grace) | Open — risk engine / separate PR |
