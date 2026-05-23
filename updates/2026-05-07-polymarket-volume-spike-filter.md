# Update: Polymarket Volume Spike Filter — CRYPTO LONG Entry Confirmation

**Date:** 2026-05-07
**Files created/modified:**
- `alpha_engine/polymarket_volume_filter.py` — new module
- `alpha_engine/feed_hygiene.py` — step 5c integration
- `tests/test_polymarket_volume_filter.py` — 17 unit tests

---

## What was implemented

Added a Polymarket volume spike filter as a momentum confirmation layer in the CRYPTO entry pipeline. When a CRYPTO LONG (or BUY) pick is being ingested, the filter checks whether the corresponding Polymarket markets for that symbol show elevated volume (current >> historical median). A Polymarket volume spike indicates smart-money crowd conviction and is used to:

1. **Gate LONG entries** — block (return `False` from `is_valid_active_pick`) when there ARE active Polymarket markets but NO volume spike detected (proving coverage exists but conviction is absent).
2. **Boost confidence** — when a spike IS confirmed, apply `+5%` confidence boost (capped at `0.90` max, no negative boost for high-confidence picks).

---

## Design decisions

- **Conservative pass-through:** If Polymarket data is unavailable, symbol has no active markets, or entry is SHORT/non-crypto — the filter passes through without blocking. Polymarket is one signal among many.
- **Lower-middle median:** For even-length volume lists, the lower-middle value is used as median (index `(n-1)//2`). Conservative — makes spikes slightly harder to trigger.
- **Empty exempt list:** All major USDT crypto symbols have some Polymarket coverage, so no exemptions are needed. The no-data pass-through handles symbols with zero markets.
- **Session cache:** Signals are cached for 5 minutes (`_CACHE_MAX_AGE_SECONDS=300`) to avoid repeated file I/O. Call `invalidate_cache()` at scan start for fresh data.
- **Rollback:** `export POLYMARKET_VOL_SPIKE_DISABLED=1` disables the filter entirely.

---

## Bug fixed during implementation

**Boost formula went negative for high-confidence picks:**

```python
# OLD (buggy): boost = min(0.05, 0.20 - current_conf)
# When current_conf=0.70 → boost = min(0.05, -0.50) = -0.50 → new_conf = 0.20 ❌

# FIXED: boost = min(_CONF_SPIKE_BOOST, max(0.90 - current_conf, 0.0))
# When current_conf=0.70 → boost = min(0.05, 0.20) = 0.05 → new_conf = 0.75 ✅
# When current_conf=0.88 → boost = min(0.05, 0.02) = 0.02 → new_conf = 0.90 (capped) ✅
```

---

## Test results

All 17 tests pass:
- `test_exempt_symbols_pass` — empty exempt list
- `test_non_long_entries_pass` (×4 directions) — SHORT/SELL/NEUTRAL/FLAT pass through
- `test_env_var_disabled_passes_through` — POLYMARKET_VOL_SPIKE_DISABLED=1
- `test_no_markets_passes_through` — no Polymarket markets = pass-through
- `test_no_spike_passes_with_warning` — no spike → warning but passes
- `test_volume_spike_detected` — spike detected correctly
- `test_confidence_boost_on_spike` — boost = +0.05 on current=0.70 → new=0.75
- `test_no_boost_without_spike` — no boost when no spike
- `test_cache_invalidation` — cache refresh on invalidate
- `test_short_not_gated_regardless_of_volume` — SHORT never gated
- `test_low_volume_markets_ignored` — <$1000 volume markets filtered
- `test_top_direction_majority_long` — direction majority computed
- `test_feed_hygiene_long_no_markets_passes` — feed_hygiene integration
- `test_feed_hygiene_spike_boost` — feed_hygiene confidence boost

---

## Integration points

**`alpha_engine/feed_hygiene.py` — step 5c:**
```python
if _HAS_PM_VOL_FILTER:
    if symbol.endswith('USDT') and direction in ('LONG', 'BUY'):
        confirmed, reason = is_polymarket_volume_confirmed(symbol, direction)
        if not confirmed:
            return False  # BLOCK (missing spike + active markets)
        if confirmed:
            current_conf = float(pick.get('confidence', 0) or 0)
            new_conf, boost_reason = apply_confidence_boost(pick, current_conf)
            if new_conf != current_conf:
                pick['confidence'] = new_conf
                pick['_pm_vol_spike_boost'] = boost_reason
```

**Source file:** `alpha_engine/data/polymarket_signals.json` — keyed by `symbol`, `direction`, `volume`, `probability`.