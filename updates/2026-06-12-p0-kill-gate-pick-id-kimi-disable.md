# P0 Fixes: Kill Gate Wiring, Pick ID Double-Stamp, kimi_riseoftheclaw Disable

**Date:** 2026-06-12  
**Author:** Kilo  
**Status:** Ready for review

## Summary

Three critical fixes to stop the bleeding in the trading system:

1. **Kill gate wiring** — Dead code that never fired; now reads forward-test stats
2. **Pick ID double-stamp** — Same pick recorded multiple times due to missing entry_price
3. **kimi_riseoftheclaw disable** — 76% of picks at 28.4% WR blocked at admission

## Fix 1: Kill Gate Wiring

**File:** `audit_trail/quality_gates.py:6927-6965`

**Problem:** The kill gate was wired but read `stats.wins` and `stats.n` which don't exist in picks. Production scanner enriches picks with `strat_fwd_wr` (percentage) and `strat_fwd_trades` (integer). The condition `_wins_kg is not None and _n_kg is not None` was always False.

**Fix:** Convert `strat_fwd_wr` (e.g., `62.5`) + `strat_fwd_trades` (e.g., `30`) into `wins`/`n` via `wins = round(wr_pct / 100.0 * trades)`, then pass to `evaluate_kill()`. Legacy `stats.wins`/`stats.n` kept as fallback.

**Impact:** Strategies with WR < 35% over 50+ trades will now be killed at admission. Fail-open on missing stats.

## Fix 2: make_pick_id() Double-Stamp

**File:** `audit_trail/universal_pick_resolver.py:886-895`

**Problem:** When a pick has a pre-existing `id` field, `make_pick_id()` returns `id::{source}::{raw_id}` — no entry_price. This allows the same pick to be recorded multiple times at different entry prices. Evidence: BNBUSDT+prediction_market_consensus had 687 duplicate picks.

**Fix:** Append entry_price to the id path: `id::{source}::{raw_id}::{entry}`. Fallback path already includes entry_price.

**Impact:** Picks with same raw_id but different entry prices will now be treated as distinct. First resolver run will re-resolve existing picks (new key format won't match old keys) — acceptable one-time cost.

## Fix 3: kimi_riseoftheclaw Disable

**Files:**
- `audit_trail/quality_gates.py:1962` — Added to `BLOCKED_SOURCE_SYSTEMS`
- `audit_trail/quality_gates.py:5917` — Score changed from +15 to -30
- `audit_trail/backfill_local_sources.py:424,449-450` — Ingestion commented out
- `audit_dashboard/template.html:9320` — Uncommented in `BLOCKED_SYSTEMS`

**Problem:** kimi_riseoftheclaw produces 138K+ picks at 28.4% WR, PF 0.69. It's 76% of all system picks. 99.4% are duplicates (866 distinct out of 141K). Dormant since March but ingestion-ACTIVE (NULL ts bypasses dedup).

**Fix:** Added to `BLOCKED_SOURCE_SYSTEMS` (defense-in-depth), score downgraded, ingestion commented out, dashboard filter enabled. Config flag pattern — reversible by removing from set.

**Impact:** ~105K active picks from this source will be filtered out. Pick volume will drop significantly. EQUITY stars (rs-breakout 75% WR, donchian-stock 78.6% WR) are lost but sample sizes are small (n<40).

## Verification

- All three modified Python files pass syntax check
- No tests broken (kill gate was already fail-open)
- Dashboard JS change is display-only

## Rollback

1. Remove `"kimi_riseoftheclaw"` from `BLOCKED_SOURCE_SYSTEMS`
2. Revert score from -30 to +15
3. Uncomment ingestion lines in `backfill_local_sources.py`
4. Re-comment in `template.html`
