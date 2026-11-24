# Per-class alpha was computed then thrown away; `unmeasured` hid stale price tables

**Date:** 2026-11-19 · **Files:** `alpha_engine/audit3_tribunal.py`,
`alpha_engine/audit3_selection_alpha.py`, `tests/test_selection_alpha_coverage.py`

Debugging the deployed ledger right after G8 went live turned up two defects that both made
`/audit3` look more complete than it was.

---

## Bug 1 — `by_class` was computed, gated on, then dropped

`audit3_selection_alpha.py` produces `by_class`, and `apply_selection_alpha_gate()` reads
`alpha["by_class"]` to decide each class gate. But the ledger's publish step copied a
**hand-written whitelist**:

```python
for key in ("generated_at", "covered", "n_universe", "missing", "overall", "by_slice"):
```

No `by_class`. Result: the page could show `CRYPTO: measured` with **no alpha number anywhere
in the payload**. That is exactly why `class_alpha` printed `{}` while `by_slice` was full.

### Fix
Whitelist is now the named constant `ALPHA_PASSTHROUGH_KEYS`, including `by_class` and
`bar_coverage`, so a test can assert the set instead of grepping a literal.

## Bug 2 — `unmeasured` carried no reason, and the reason was stale tables

Four class gates read `unmeasured`. Not a loader bug — table freshness:

| table | last bar | distinct symbols | payload picks closing after it |
|---|---|---|---|
| `equity_daily_ohlcv` | **2026-06-18** | 230 | **486 of 765** |
| `fx_prices` | **2026-02-09** | 15 | 121 of 199 |
| `futures_daily_ohlcv` | **2026-06-21** | 11 | 51 of 51 |
| `etf_daily_ohlcv` | 2026-10-30 | 36 | none after 10-30, but only 36 symbols tracked |
| `crypto_ohlcv` | 2026-11-19 | — | 0 — current |

`_close_at()` needs a bar at or after the exit timestamp, so a pick closing past the table's
last bar is `no_bar` — correct, but silent. That explains `no_bar:EQUITY` 437 and
`no_bar:FOREX` 159, and why crypto was measurable while FOREX/COMMODITY/BOND were not.

### Fix
Sidecar gains `bar_coverage` per class (`symbols_requested`, `symbols_found`, `last_bar`,
`missing_symbols` capped at 10), published through the whitelist.

Decision notes:
- **Separate `bar_coverage()`**, not a change to `load_bars()` — its `rows -> bars` contract is
  relied on elsewhere and stays intact.
- **`_wanted_symbols()` re-derives the request map** rather than threading a second return value
  through the fetch path.
- **`last_bar` is `max()` over the series, not the list tail.** A unit test caught this: the
  first implementation took `series[-1]` while the doc claimed the maximum, so an unordered
  series would misreport freshness. The implementation was fixed, not the test.
- **`missing_symbols` capped at 10** — names the cause without bloating the payload.

## Verification
- `tests/test_selection_alpha_coverage.py` — 7 tests (whitelist contents, existing keys,
  found/missing counts, no-bars class, empty input, max-not-tail).
- Local end-to-end on the live payload: `by_class {CRYPTO -0.374%, EQUITY +0.114%,
  ETF -0.272%}` plus a coverage block land in the ledger.
- Suites: selection-alpha coverage, audit3 selection alpha, tribunal, db sync, exit A/B, H-145.

## Open — data work, not code
1. Backfill `equity_daily_ohlcv` from 2026-06-18, `fx_prices` from 2026-02-09,
   `futures_daily_ohlcv` from 2026-06-21.
2. Widen `etf_daily_ohlcv` past 36 symbols — the ETF gate rests on a narrow book.
3. Until then `unmeasured` is the honest reading, and `bar_coverage` now states the cause.
