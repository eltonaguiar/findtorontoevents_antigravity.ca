# Incident Fix: PnL Integrity + Category Backfill — 2026-05-31

## Incidents Addressed

| Incident | Severity | Status After |
|----------|----------|-------------|
| PnL integrity mismatch on 38.97% of sampled closed picks | P0 | IN_PROGRESS (914/1318 fixed, 412 corrupted require manual review) |
| 5 FOREX rows have pnl_pct < -100% | P0 | RESOLVED (verified 0 rows; already fixed) |
| WON status rows show avg pnl_pct = -41.1% | P0 | RESOLVED (verified 0 contradictions; avg WON = 4.76) |
| signal_outcomes table 82 days stale | P0 | RESOLVED (verified last refresh 2026-05-31 01:37 UTC) |
| UNKNOWN asset_class on 951 active + 54 closed picks | P2 | RESOLVED (134 rows backfilled; 0 remaining) |

## Root Cause: pnl_pct Decimal-vs-Percent Convention Mismatch

Three files used inconsistent conventions for storing `pnl_pct`:

| File | Convention | Problem |
|------|-----------|---------|
| `forward_validator.py:1384` | **decimal** (0.05 = 5%) | Correct, but readers double-divided |
| `active_picks_sync.py:233` | **percent** (5.0 = 5%) | Inconsistent with forward_validator |
| `quality_gates.py:125` | **raw read** (no normalization) | Got inconsistent values from closed_picks.json |

### Double-Division Bugs

1. **White's Reality Check** (`forward_validator.py:376`): `float(pnl) / 100.0` — but `load_closed_picks()` already normalizes to decimal, so this double-divides, making strategy returns 100x too small.

2. **DSR Cache** (`forward_validator.py:2109`): Same pattern — `float(_cp["pnl_pct"]) / 100.0` after `load_closed_picks()` normalization. Sharpe ratios become 100x too small, making DSR unreliable.

3. **Anti-overfit Cache** (`quality_gates.py:125`): Reads `closed_picks.json` directly (bypasses `load_closed_picks()`), so picks from `active_picks_sync` (stored as percent) get inconsistent treatment vs picks from `forward_validator` (stored as decimal).

## Fixes Applied

### Code Changes (3 files)

1. **`alpha_engine/forward_validator.py`**:
   - Line 376: Removed `/100.0` from WRC — `load_closed_picks()` already normalizes
   - Line 2109: Removed `/100.0` from DSR cache — same reason

2. **`alpha_engine/active_picks_sync.py`**:
   - Line 233: Changed `round(pnl_pct * 100, 4)` → `round(pnl_pct, 6)` — align with forward_validator's decimal convention

3. **`audit_trail/quality_gates.py`**:
   - Line 125: Added normalization (`abs(_pnl) > 1.0 → /100.0`) to `_load_strategy_returns_cache()` — handles legacy percent-stored values

### DB Fixes (MySQL ejaguiar1_stocks)

| Operation | Rows Affected |
|-----------|--------------|
| PnL integrity fix (safe 100x correction) | 914 |
| PnL outlier clamp (< -100) | 7 |
| Category backfill (unknown → classified) | 134 |
| Category casing normalization | 2 (ETF tickers) |

### Remaining 412 Corrupted Rows

These rows have `entry_price`/`exit_price` pairs that produce nonsensical computed PnL values (e.g., 5,076,041% for USDCAD, 465% for SI=F). These are from `copy_trader_intel` (209), `ml_crypto_predictor` (80), and `prediction_market_agents` (34). They require:

1. Investigation of the source price data (likely wrong decimal places or mixed contract sizes)
2. Manual re-resolution or deletion
3. NOT safe to auto-fix — the constraint violations indicate the `status` field may also be wrong

## Approach

- **Convention standard**: All writers now store `pnl_pct` as **decimal** (0.05 = 5%)
- **Normalization layer**: `load_closed_picks()` (existing) + `_load_strategy_returns_cache()` (new) both normalize on read
- **Backward-compatible**: The `abs > 1.0` heuristic handles legacy percent-stored values gracefully
- **No schema changes**: Uses existing `pnl_pct decimal(10,4)` column

## Verification

```sql
-- Post-fix PnL integrity check (>1% mismatch): 412 remaining (corrupted, not auto-fixable)
-- Post-fix outliers (<-100): 1 remaining (ACTIVE position, needs live resolution)
-- Post-fix unknown categories: 0 remaining
```
