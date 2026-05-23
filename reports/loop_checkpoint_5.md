# Loop Checkpoint 5 — T+~120m (2026-05-08 20:15 UTC)

## 🔴 1-line bug fix located: `multi_asset/scanner.py:2232`

WON-with-negative-PnL bug (1,247 polluted rows in `trading_picks`, avg pnl -85.38%) traces to a missing guard in the multi_asset scanner closer:

```python
# Line 2231-2237 — BUGGED
if hit_tp:
    pick["status"] = "WON"               ← NO GUARD on pnl sign
    pick["exit_price"] = tp
    pick["exit_reason"] = "TAKE_PROFIT"
    pick["pnl_pct"] = pick["unrealized_pnl_pct"]
    pick["closed_at"] = datetime.now(timezone.utc).isoformat()
    closed.append(pick)
elif hit_sl:
    is_trailing = pick.get("trailing_active", False)
    pick["status"] = "WON" if pick["unrealized_pnl_pct"] > 0 else "LOST"   ← CORRECT GUARD
    ...
```

When `tp` is contaminated by stale price-cache (cross-symbol leak), `current_price <= tp` (SHORT) triggers spuriously, exit_price set to garbage tp value, pnl_pct computed as garbage unrealized, status forced to WON regardless.

### Recommended fix

Apply the same guard to `hit_tp` branch:

```python
if hit_tp:
    pick["status"] = "WON" if pick["unrealized_pnl_pct"] > 0 else "LOST"
    pick["exit_price"] = tp if pick["unrealized_pnl_pct"] > 0 else current_price  # don't trust contaminated tp
    pick["exit_reason"] = "TAKE_PROFIT" if pick["unrealized_pnl_pct"] > 0 else "TP_OUTOFRANGE"
    pick["pnl_pct"] = pick["unrealized_pnl_pct"]
    pick["closed_at"] = datetime.now(timezone.utc).isoformat()
    closed.append(pick)
```

Plus add a sanity check earlier:
```python
# Before line 2218
if entry_price > 0 and (current_price < 0.01 * entry_price or current_price > 100 * entry_price):
    print(f"  [SCALE_WARN] {symbol}: current_price={current_price} is 100x off from entry={entry_price} — skipping resolution")
    still_open.append(pick)
    continue
```

This prevents resolution when price feed is contaminated, preventing the bug at root cause rather than masking the WON label.

### Risk / scope

- File `multi_asset/scanner.py` is 2,400+ lines, runs in production via `multi_asset/scanner.py` direct invocation.
- The fix is local to one function (likely `_check_open_picks` or similar around line 2200).
- Need backtest of the fix on the 1,247 known-bad rows to confirm WON status flips to LOST and pnl signs become consistent.
- After fix lands, run a one-shot backfill UPDATE on existing data:
  ```sql
  UPDATE trading_picks
  SET status = 'LOST'
  WHERE source_system = 'multi_asset_copytrader'
    AND status = 'WON'
    AND pnl_pct < 0;
  -- Affects ~1,247 rows. Run inside a transaction. Verify count first.
  ```

### Why fix this NOW (not later)

- It's a 1-line code fix
- It's the **only source of WON-with-negative-PnL** (8 other source_systems are clean per checkpoint 4 sweep)
- It's the **most-cited Kimi finding** (Critical Issue #1) and confirmed by my live db_health check
- Dashboard `won_pnl_contradiction` card will flip from red→green after fix + backfill

## Other progress this checkpoint

- ✅ outcome_coverage discrepancy reconciled (12.27% vs 0.09% — different denoms)
- ✅ WON-mislabel root cause located in `multi_asset/scanner.py:2232`
- ⏳ Penny-skyrocket workflow YAML validation pending
- ⏳ 2nd full bg health-run pid 3257 not yet logged final output

## Up next

- T+140m wakeup → validate penny-skyrocket YAML + try manual trigger
- Confirm bg pid 3257 finished + db_health.json refreshed
- Build the multi_asset/scanner.py fix patch (or punt to user since it's a code change, not analysis)

## Files
- This: `reports/loop_checkpoint_5.md`
- Bug: `multi_asset/scanner.py:2231-2245`
- Detection query already shipped: `tools/db_health_check.py::check_won_pnl_contradiction`
