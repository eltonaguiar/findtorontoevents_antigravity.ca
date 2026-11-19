# 2026-11-19 audit3 TODO sweep — T4/T5/T6/T7/T8/T9/T10/T11/T12/T13/T15/T16/T17/T19/T20/T21

## What was broken

The audit3 P0/P1 correctness branch (`feat/audit3-p0-p1-correctness`, PR #965) landed the core tribunal fixes, but 17 TODO items from Buffy's ledger and the COMS findings drop remained open. This session closed the open items:

- **T4** — `volume_ratio_at_entry` was nested inside `ml_features_at_entry` on closed picks but missing at top level, so volume A/B research couldn't join entry volume to realized outcome.
- **T5** — `dashboard_data.json` summary reported three PnL figures (`total_pnl_pct` rolling-100, `total_pnl_pct_sum_raw` raw additive, `total_pnl_pct_compounded_ew` full-ledger EW) that legitimately disagree (-11.96% vs +1653.11% vs +2643.01%) but were displayed without explanation.
- **T6** — `required_n` (pre-declared MDE sample size) was `None` on all 7 class rows in the audit3 ledger.
- **T7** — G8 selection-alpha rendered as "not computed" when unavailable; should say "not evaluated".
- **T8** — 56 WEAK cells had empty `reasons[]` because no specific sub-reason matched.
- **T9** — FORCE_CLOSED (597 rows, mean +0.33% vs median -2.17%) was an unclassified bucket polluting WR/PF/CI with an unknown exit rule.
- **T10** — `value_screener_picks.json` did not exist (dashboard 404ed on the missing artifact).
- **T11** — `scored_share_of_valid_pct` could exceed 100% when `scored > valid`.
- **T12** — `audit2_pods.json` did not exist; audit2 PODS were locked in a JS literal in `audit2.js`.
- **T13** — `reports/backtesting_methodology_audit_2026-06-02.md` was absent on disk, breaking citations in `docs/BACKTEST_ADMISSIBILITY_STANDARD.md` and several EAGLE reports.
- **T15** — Risk-parity pod was not pre-registered in `reports/hypothesis_registry.json`.
- **T16** — 12-month top-3 sector-rotation pod was not pre-registered (distinct from H-040's long-short 21-day momentum).
- **T17** — `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md` claimed Sharpe 0.88 / MaxDD −19%, which the TAA settlement sweep (576 cells) did not reproduce.
- **T19** — ETF slippage figure (8bps in `audit3_tribunal.py`) was not derived/documented anywhere.
- **T20** — Materiality cost fraction was 0.5x (edge only needed to exceed half of round-trip cost), far too permissive.
- **T21** — Forward-observations ingestion routed CRYPTO/COMMODITY picks into the ledger despite both classes being net-negative after cost.

## What changed

### `alpha_engine/audit3_tribunal.py`
- **T6**: Added `required_n` to every class row via `power_analysis()` (pre-declared MDE sample size, per-class).
- **T7**: Changed G8 selection-alpha rendering fallback from "not computed" to "not evaluated" (audit3.html).
- **T8**: Added catch-all reason `"no promotion gate passed..."` for WEAK cells with no specific sub-reason.
- **T9**: Added `force_closed_breakdown` to summary classifying FORCE_CLOSED rows into TP-like/SL-like/time-like buckets by pnl sign.
- **T11**: Capped `scored_share_of_total_pct` and `scored_share_of_valid_pct` at 100.0%.
- **T19**: Documented ETF slippage derivation (8bps per-pick vs 5bps per-turnover for monthly rotation) in TAA_SETTLE_2026-11-19.md.
- **T20**: Changed `MATERIALITY_COST_FRACTION` from 0.5 to 4.0 — a cell's net CI lower bound must now clear 4x the class mean round-trip cost to promote.
- Also fixed a circular import between `audit3_tribunal` and `audit3_edge_hunt` that caused `_canon_symbol` to fall back to a non-canonicalizing stub (breaking BTC-USD/BTCUSDT grouping).

### `alpha_engine/forward_observations_ingest.py`
- **T4**: Added `pick["volume_ratio_at_entry"] = pick.get("volume_ratio")` at top level of every closed pick row.
- **T21**: Block CRYPTO/COMMODITY/MEMECOIN rows at ingestion (before classification) with reason `blocked_asset_class_<class>`.

### `alpha_engine/forward_validator.py`
- **T4**: Same `volume_ratio_at_entry` stamp applied in the forward_validator close path (consistency).

### `audit_trail/dashboard_generator.py`
- **T5**: Added `pnl_methodology_note` to `dashboard_data.json` summary explaining the three PnL methods and which is authoritative (headline = `total_pnl_pct` rolling-100).

### `audit_dashboard/data/dashboard_data.json`
- **T5**: Added `pnl_methodology_note` to the stale summary (regeneration requires live DB; note documents the fix).

### `audit_dashboard/data/audit2_pods.json` (NEW)
- **T12**: Extracted the PODS array from `audit2.js` JS literal into a JSON file with schema + source attribution.

### `audit_dashboard/data/value_screener_picks.json` (NEW)
- **T10**: Created with methodology (Magic Formula x Piotroski x Acquirer's Multiple x SafetyGate), universe gates, and empty picks array (no fundamentals fetcher wired yet; zero emitted is correct).

### `audit_dashboard/audit3.html`
- **T7**: G8 selection-alpha now renders "not evaluated — G8 selection-alpha gate unavailable..." when `selection_alpha.available` is false.

### `reports/backtesting_methodology_audit_2026-06-02.md` (NEW)
- **T13**: Stub document explaining the original is absent, pointing to `docs/BACKTEST_ADMISSIBILITY_STANDARD.md` (M-108) as the canonical replacement.

### `reports/hypothesis_registry.json`
- **T15**: Added H-142 risk_parity_etf_allocation pod (PRE_REGISTERED, OOS-decay gate: OOS Sharpe >= 0.80 on rolling 2-year windows).
- **T16**: Added H-143 sector_rotation_top3_12m pod (PRE_REGISTERED, distinct from H-040: long-only top-3, 12-month lookback, no trend filter).

### `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md`
- **T17**: Retracted the Sharpe 0.88 / MaxDD −19% claim; status is now "CLAIM NOT REPRODUCED" pointing to TAA_SETTLE_2026-11-19.md.

### `reports/TAA_SETTLE_2026-11-19.md`
- **T19**: Added ETF slippage derivation section (8bps per-pick vs 5bps per-turnover for monthly rotation).

### Tests updated
- `tests/test_audit3_tribunal.py`: Updated materiality floor tests (0.5x → 4x), recency tests (use FOREX with higher net edge to clear 4x floor), high-cost class test (equity verdict is now WEAK not CANDIDATE).
- `tests/test_forward_observations_ingest.py`: Changed CRYPTO cohort rows to EQUITY + matching strategy (CRYPTO now blocked by T21).

## Verification

- 200 tests pass (`test_audit3_*`, `test_forward_observations_*`, `test_audit_summary_render`, `test_audit_metric_invariants`, `test_audit_dashboard_payload`), 1 xfailed, 1 xpassed (pre-existing known bugs).
- All modified Python files compile cleanly.
- Integration POC on `feat/audit3-p0-p1-correctness`: `n_cells_total=179`, `n_proven=0`, all classes `beta_dominant` — consistent with the $2k verdict (ETF TAA for drawdown control only; CRYPTO/COMMODITY killed; nothing else clears all six repo gates).

## Branch state

- `feat/audit3-p0-p1-correctness` pushed to origin, PR #965 open against `main`.
- **⚠️ Merge conflict risk**: `origin/main` includes `fix/audit2-3-p0-p1` (coverage honesty, candidate counters, forward benchmark fix) which overlaps with this branch. Conflicts need resolution before merge.

## Open items remaining (from Buffy's TODO ledger)

- T14 (value screener weekly run), T18 (risk model calibration), T22 (dashboard refresh cadence) — these require live DB credentials or external data fetches and were not addressable in this session.
