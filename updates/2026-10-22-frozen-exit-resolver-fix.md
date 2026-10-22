# P0-1 Fix: Frozen-Exit Resolver — Per-Symbol Price Per-Pick

**Agent:** INCEPTION / VLLM
**Date:** 2026-10-22
**Branch:** `fix/frozen-exit-resolver` (clean, from `origin/main`)

---

## What was broken

`audit_trail/universal_pick_resolver.py` fetched live prices **once per run**
(`_fetch_prices_failover()` at line ~1117) and stamped that single snapshot onto
**every** unresolved pick of a symbol (line ~1265: `current_price = prices.get(norm_sym) ...`).

When several picks of the same symbol resolved in one run, they all received the
**identical** exit price + `resolved_at` timestamp → manufactured fake-clustered
"wins" (artifact cells). This corrupted any naive win-rate / profit-factor
evaluation. Example: QUBT showed 301 "wins" all at exit `6.365` from one frozen price.

## What I changed

Added `_per_pick_price(pick, norm_sym, ohlc_bars_cache, current_price)`:

- Prefers the **first intrabar OHLC bar at/after the pick's entry timestamp**
  (entry-anchored; different entries anchor to different bars → per-pick price).
- Falls back to the **live run-wide snapshot** only when no usable bar exists —
  byte-identical to legacy behavior in that case (zero regression when no bars).

Wired it into the two fallback resolution paths:

1. **close_approx** fallback (line ~1430): `check_tp_sl(pick, pp_price)` now uses
   the per-pick price instead of the frozen snapshot; `current_price_at_resolve`
   records `pp_price`.
2. **TIME_EXIT** path (line ~1470): PnL and exit price computed against `pp_price`.

## Files changed

| File | Change |
|------|--------|
| `audit_trail/universal_pick_resolver.py` | Added `_per_pick_price`; wired into close_approx + TIME_EXIT fallback resolution |
| `tests/test_resolver_frozen_exit_fix.py` | NEW — 5 regression tests |

## Tests

```
python3 -m pytest tests/test_resolver_frozen_exit_fix.py tests/test_universal_pick_resolver.py -q
=> 10 passed
python3 -m pytest tests/ -q -k "resolver or outcome or orphan"
=> 227 passed, 14 skipped (pre-existing skips)
```

Regression cases covered:
- pick resolves against its **own** post-entry bar, not the frozen snapshot;
- two picks of the same symbol with different entries resolve to **different** prices;
- no bars → fallback to snapshot (legacy behavior preserved);
- bars strictly before entry are ignored (no stale-window look-ahead);
- unparseable timestamp → graceful fallback to snapshot.

## What's remaining (next)

- **P1-2**: Re-run the walk-forward harness over **newly resolved** picks (after
  this fix is deployed) to see whether any sleeve clears the strict gate.
- **P1-1**: ship the artifact detector (`wins > 2× distinct exit dates`) as a
  standing CI check.
- **P1-3**: open a sealed forward paper cohort.
- Historical rows already resolved under the old bug remain in
  `dashboard_data.json` — the harness flags them via the artifact detector rather
  than silently trusting them.
