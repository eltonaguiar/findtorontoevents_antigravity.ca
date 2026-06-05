# 2026-06-05-recency-gate-stale-resolver-implementation

## Overview
Implemented a recency gate as the primary hard gate in the money-readiness pipeline and performed a stale pick resolution run for the trading database.

## Changes

### 1. Recency Gate Implementation
- **File**: [`alpha_engine/eagle_gates.py`](alpha_engine/eagle_gates.py)
    - Added `passes_recency_gate(picks)`:
        - **Gate 0**: Requires at least one pick within the last 14 days.
        - **Gate 0.5**: Requires the most recent pick to be within the last 48 hours.
    - Integrated `passes_recency_gate` into `passes_hard_money_gates` as the absolute first check (Gate 0).
- **File**: [`alpha_engine/money_ready_verdict.py`](alpha_engine/money_ready_verdict.py)
    - Imported `passes_recency_gate` from `eagle_gates`.
    - Updated `_verdict()` to accept `recency_ok` and return `NOT_READY` if the recency gate fails.
    - Updated `money_ready_verdict()` to call `passes_recency_gate` and pass the result to `_verdict()`.
    - Added `recency_ok` and `_recency_warn` to the final results dictionary for visibility in the audit dashboard.
    - Removed the redundant internal `_recency_gate` function.

### 2. Stale Resolver Tooling
- **File**: [`tools/mysql_resolve_at_pick_outcomes.py`](tools/mysql_resolve_at_pick_outcomes.py)
    - Created a new tool to resolve stale `OPEN` rows in the `at_pick_outcomes` table.
    - The tool joins `at_pick_outcomes` with `trading_picks` to retrieve entry prices and directions, then uses `yfinance` to resolve the outcome based on asset-class-specific hold periods.
- **Database Run**:
    - Verified `at_pick_outcomes` was already fully resolved (0 OPEN rows).
    - Ran `tools/mysql_stale_picks_resolver.py` against `trading_picks` with a 90-day threshold.
    - **Result**: Resolved 42 stale picks (24 WIN, 18 LOSS).

## Verification
- All modified files (`alpha_engine/eagle_gates.py`, `alpha_engine/money_ready_verdict.py`, `tools/mysql_resolve_at_pick_outcomes.py`) were verified to compile cleanly using `py_compile`.
- Stale resolver run verified via `--dry-run` and then applied to the database.
