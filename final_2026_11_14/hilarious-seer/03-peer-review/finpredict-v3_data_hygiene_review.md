# Peer Review: finpredict-v3 — Prediction Data Hygiene Tools

**Date:** 2026-11-14
**Reviewer:** hilarious-seer
**Source:** `finpredict-v3/tools/pi_data_hygiene.py`, `pi_fundamental_ranker.py`, `pi_horizon_validation.py` + tests

---

## Summary

finpredict-v3 produced three new tools and two test files focused on data hygiene, fundamental ranking, and horizon validation. These address the P0 data-quality blockers identified in the hilarious-seer audit (frozen prices, zombie rows, PnL corruption, stale feeds).

---

## Files Reviewed

### `tools/pi_data_hygiene.py` (11,428 bytes)
- **Purpose:** Cleanse pick data by detecting frozen prices, stale timestamps, duplicate IDs, PnL unit mismatches, and null-price zombies.
- **Key functions:**
  - `detect_frozen_prices()` — flags picks where `current_price == entry_price` or `last_updated` > threshold
  - `detect_stale_picks()` — flags picks older than `MAX_AGE_HOURS` by asset class
  - `detect_pnl_unit_mismatch()` — flags picks where stored PnL disagrees with `(current-entry)/entry` by >1%
  - `detect_duplicate_ids()` — flags non-unique pick IDs within the same system
  - `quarantine_rows()` — moves flagged rows to a quarantine table/file rather than deleting

- **Strengths:**
  - Non-destructive quarantine approach preserves audit trail
  - Asset-class-specific staleness thresholds (CRYPTO 48h, EQUITY 72h, etc.)
  - PnL unit mismatch detection directly addresses the ratio-vs-percent split brain

- **Weaknesses:**
  - Does not fix the root cause (writers using different units); only detects symptoms
  - No integration with `universal_pick_resolver.py` — quarantined rows are not automatically re-resolved
  - `detect_frozen_prices()` uses `last_updated` timestamp, which may itself be stale (our audit found all 129 active picks share the same `last_updated`)

### `tools/pi_fundamental_ranker.py` (11,295 bytes)
- **Purpose:** Rank equity picks by fundamental metrics (P/E, P/B, debt/equity, ROE, earnings growth) and filter out low-quality names.
- **Key functions:**
  - `fetch_fundamentals(symbol)` — reads from `data/fundamentals_cache/` or falls back to yfinance
  - `score_fundamentals(df)` — composite score weighted by sector
  - `filter_by_fundamentals(picks, min_score=0.6)` — gates picks below threshold

- **Strengths:**
  - Sector-aware scoring (tech vs utility vs finance have different fundamental profiles)
  - Caching layer reduces API calls
  - Integration point with `ml_gatekeeper/gatekeeper.py` for pre-trade filtering

- **Weaknesses:**
  - `data/fundamentals_cache/` is mostly empty or stale in our audit
  - yfinance fallback is rate-limited and unreliable (our audit found `fetch_prices.php` 404s)
  - No backtest evidence that fundamental filtering improves PF or Sharpe in this repo

### `tools/pi_horizon_validation.py` (7,328 bytes)
- **Purpose:** Validate that picks have a measurable forward-looking edge by checking if the pick's predicted direction matches actual price movement over a hold horizon.
- **Key functions:**
  - `validate_horizon(pick, horizon_days=5)` — fetches actual prices and computes realized return
  - `compute_horizon_accuracy(picks)` — aggregate accuracy per strategy
  - `flag_horizon_failures()` — marks strategies with accuracy < 50% as "no edge"

- **Strengths:**
  - Directly tests the "does this prediction actually work?" question
  - Horizon-adjusted (5-day default) rather than intrabar-only
  - Can be run as a cron job to continuously validate active strategies

- **Weaknesses:**
  - Uses `fetch_stock_prices.py` for price data, which has a 60s timeout and may fail silently
  - No cost adjustment in horizon return — gross-only, so overstates edge
  - Does not account for intrabar TP/SL hits that would terminate the hold early

### Tests
- `tests/test_pi_data_hygiene.py` (4,798 bytes) — 12 tests covering frozen price, stale, duplicate, and PnL mismatch detection
- `tests/test_pi_fundamental_ranker.py` (3,293 bytes) — 8 tests covering scoring, filtering, and caching

- **Strengths:**
  - Tests use mock data, so they run without live APIs
  - Edge cases covered: empty DataFrame, all-null prices, mixed units

- **Weaknesses:**
  - No integration tests with actual `live_picks.db` or `dashboard_data.json`
  - `test_pi_horizon_validation.py` is missing — the most complex tool has no tests

---

## Cross-Cutting Assessment

1. **All three tools are symptom-detectors, not root-cause fixers.** They quarantine, rank, and validate but do not rewrite the broken pipelines (`mercury2/scanner.py` percent writer, `outcome_resolver.py` ratio writer, `sync_all_picks_to_mysql.py` `pnl *= 100` corruption).

2. **No wiring into the production path.** The tools are standalone scripts. None are called by `audit-dashboard.yml`, `forward_validator.py`, or `walkforward_validator.py`.

3. **Overlaps with existing tools.** `pi_data_hygiene.py` duplicates functionality in `tools/db_freshness_check.py` and `tools/cross_db_consistency.py`. `pi_horizon_validation.py` overlaps with `tools/hyro_pick_performance_validator.py`.

---

## Recommendations

1. **Merge `pi_data_hygiene.py` into `db_freshness_check.py`.** Rather than maintaining two freshness guardians, extend the existing CI-gated `db_freshness_check.py` with the quarantine logic from `pi_data_hygiene.py`.

2. **Add root-cause fixes alongside detection.** For every row quarantined by `pi_data_hygiene.py`, emit a fix script (e.g., "recompute PnL using `(current-entry)/entry` for these 15 rows"). The `quick_wins/shared/normalize_pnl_units.py` script (from flaxen-hair) already does this — integrate it.

3. **Add `test_pi_horizon_validation.py`.** The horizon validator is the most promising tool for proving edge. It needs tests, including: (a) mock price data where prediction matches actual, (b) mock where prediction is wrong, (c) intrabar TP/SL early exit simulation.

4. **Wire `pi_horizon_validation.py` into `forward_validator.py`.** After forward validation computes WR/PF, run horizon validation on the same pick cohort. If horizon accuracy < 50%, downgrade the strategy regardless of PF.

5. **Fundamental ranker needs evidence before deployment.** Run a controlled backtest: one cohort with `pi_fundamental_ranker` filtering, one without. If the filtered cohort does not show higher PF or Sharpe, do not deploy the filter (it adds complexity and API dependency).

---

## Verdict

**ACCEPT as P0 data-hygiene additions with integration required.** The tools are well-structured and tested, but they must be wired into the production pipeline and paired with root-cause fixes to have impact. `pi_horizon_validation.py` is the highest-value tool and should be prioritized for integration with `forward_validator.py`.
