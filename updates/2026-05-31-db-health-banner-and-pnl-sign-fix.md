# DB Health Banner Fix + PnL Sign-Based Integrity (2026-05-31)

## Problem
The "⚠ DATA INTEGRITY FAILURE — DO NOT TRADE ON THESE NUMBERS" banner on https://findtorontoevents.ca/audit/ was showing stale/misleading information:
1. Claimed "PnL integrity" was failing — but the 33.46% "mismatch" was a false positive from comparing magnitude against an unleveraged formula on leveraged SHORT trades
2. Claimed "forward-validator freshness" was failing — but the validator was healthy (last close 1h ago, not frozen)
3. Claimed "ghost rows (22,947)" were failing — but they were YELLOW (threshold_pass=true), not RED

Additionally:
- `tools/db_health_check.py` used hardcoded wrong DB password (`"stocks"`), causing hourly cron runs to fail with auth errors
- 593 non-canonical status rows (CLOSED_SL, CLOSED_TP, WON) were making `status_standardization` RED

## Changes

### 1. `tools/db_health_check.py`
- **`_conn()`**: Now uses `tools/db_env.get_stocks_creds()` (canonical `DB_PASSWORDS_JSON` source) instead of hardcoded wrong password
- **`check_pnl_integrity()`**: Rewrote to use SIGN consistency (direction-aware, leverage-agnostic). The old magnitude-based comparison flagged ~33% because leveraged perps (100-130x) store pnl_pct scaled by leverage, while the recomputed formula is unleveraged. SIGN never flips from leverage or fees, so 0.54% mismatch = GREEN
- **`check_open_bloat()`**: Fixed suspect-count logic to compare TOTAL row count vs info_schema (not OPEN vs info_schema, which was comparing apples to oranges)
- **`any_red_t1`**: New overall flag that only considers Tier 1 checks for the alarm banner. Tier 2/3 (like phantom_expired) no longer trigger the banner

### 2. `audit_dashboard/dashboard_enhancements.js`
- Banner now uses `any_red_t1` instead of `any_red`
- Failing checks list is dynamic (built from actual RED Tier 1 data) instead of hardcoded wrong claims

### 3. `trading_picks` DB fixes (direct, not in PR)
- WON (pnl>0) → TP_HIT: 220 rows
- WON (pnl IS NULL) → EXPIRED: 192 rows
- CLOSED_TP → TP_HIT: 85 rows
- CLOSED_SL → SL_HIT: 96 rows
- Total: 593 non-canonical rows → 0 remaining

## Results (after fix)
| Check | Tier | Before | After |
|-------|------|--------|-------|
| pnl_integrity | Tier 1 | 🔴 33.46% | 🟢 0.54% (sign-based) |
| status_standardization | Tier 1 | 🔴 593 rows | 🟢 0 rows |
| open_bloat | Tier 1 | 🔴 count_suspect | 🟢 not frozen |
| won_pnl_contradiction | Tier 3 | 🟢 | 🟢 |
| phantom_expired | Tier 2 | — | 🔴 100% (non-crypto historical) |

Banner now only fires for Tier 1 REDs → currently does NOT show.

## Verification
- `python3 tools/db_health_check.py --check status_standardization --check pnl_integrity --check open_bloat --check won_pnl_contradiction` → all GREEN
- `any_red_t1: false` in db_health.json output
