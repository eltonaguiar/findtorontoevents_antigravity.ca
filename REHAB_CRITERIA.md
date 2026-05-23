# Symbol and Strategy Rehabilitation Criteria

This document formalizes the criteria for unblocking symbols and strategies that were previously blacklisted due to poor performance.

## The Rehabilitation Ladder

To ensure we don't prematurely unblock "toxic" assets while also not missing out on recovered edge, we use a staged approach.

### Stage 1: SHADOW (Pilot Hole)
*Required to move from HARD_BLOCKED.*
- **Trades (n):** ≥ 10 post-block resolved picks.
- **Win Rate (WR):** ≥ 50%.
- **Profit Factor (PF):** ≥ 1.3.
- **Expectancy:** Positive total PnL.
- **Action:** Surface on dashboard with `[SHADOW]` label. 25% position sizing suggested.

### Stage 2: PROBATION (Semi-Live)
*Required to move from SHADOW.*
- **Trades (n):** ≥ 20 post-block resolved picks.
- **Win Rate (WR):** ≥ 52%.
- **Profit Factor (PF):** ≥ 1.3.
- **Data Quality:** Deduped count / Raw count ≥ 0.8.
- **Action:** Surface on dashboard with `[PROBATION]` label. 50% position sizing suggested.

### Stage 3: FULL UNBLOCK
*Required to move from PROBATION.*
- **Trades (n):** ≥ 30 post-block resolved picks.
- **Wilson 95% Lower Bound WR:** ≥ 45%.
- **Profit Factor (PF):** ≥ 1.5.
- **Robustness:** Max Strategy Share ≤ 40% (ensures edge isn't from a single strategy).
- **Time Window:** ≥ 14 calendar days of consistent performance.
- **Action:** Remove from `BLOCKED_SYMBOLS` or `BLOCKED_SOURCE_SYSTEMS`.

## Automated Monitoring

- **`tools/analyze_symbol_rehab_candidates.py`:** Runs daily to identify symbols ready for promotion.
- **`tools/blacklist_reconciler.py`:** Runs daily to identify strategies ready for promotion.

## Re-Block Trigger (Safety Gate)

Once fully unblocked, a symbol/strategy enters a "High Watch" state for 30 days.
- If **Trailing 7-day PF < 0.8** OR **Trailing 7-day WR < 40%** (on n ≥ 5), it is immediately returned to **HARD_BLOCKED**.
- This prevents "regime trap" where we unblock just as the recovery ends.
