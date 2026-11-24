# FUTURES is now a measured class, not an unmapped one

Surface: `findtorontoevents.ca/audit3` → G8/G9 class gate. Code:
`alpha_engine/audit3_selection_alpha.py`, `tools/backfill_daily_ohlcv.py`.

## What was wrong

`FUTURES` is a genuine payload class, not a synonym for `COMMODITY`:

```
symbol=ES=F  strategy=futures_tsmom_winner  _class=FUTURES  LONG  pnl=-2.5
symbol=NQ=F  strategy=futures_tsmom_winner  _class=FUTURES  LONG  pnl=+4.0
symbol=GC=F  strategy=futures_tsmom_winner  _class=FUTURES  LONG  pnl=+7.338
symbol=HG=F  strategy=futures_tsmom_winner  _class=FUTURES  LONG  pnl=-3.0967
```

`_class()` returns `FUTURES`, but `TABLE_FOR` had no entry, and `load_bars()` skips
classes outside `TABLE_FOR`. So the gate reported the class as **unmeasured** no
matter how fresh the tables were — exactly the defect BOND had, and the reason the
earlier note "FUTURES still unmeasured (n=4)" was never going to resolve itself.

## What changed

* `TABLE_FOR["FUTURES"] = ("futures_daily_ohlcv", "date")` and a matching
  `TOLERANCE_MS` entry (5 days, same as the other daily tables).
* `tools/backfill_daily_ohlcv.py` gained `FUTURES_CLASS_ROOTS = ("ES", "NQ")` in its
  futures universe: `COMMODITY_SYMBOLS` covers gold/copper/etc. but not index
  futures, so only 2 of the 4 picks could have been priced at all. Measuring half a
  class and reporting it as the class is a bias, not a gap.
* Backfilled `ES=F` and `NQ=F` to today.

## Verified

* Coverage moved from `symbols_found=2` (`GC=F`, `HG=F` only) to **4/4**, `last_bar`
  2026-11-19.
* The class now appears in `by_class`:

```
FUTURES  n=4  pick=+2.021%  hold=+0.000%  alpha=+2.021%  CI=[None, None]
```

## What this result does and does not mean

It does **not** mean FUTURES has edge. `n=4` is far below any usable threshold
(`alpha_ci` is `[None, None]` because `bootstrap_mean_ci` needs ≥5 rows), and the
hold is `0.000%` because these picks are ~30-minute trades measured against *daily*
bars — the direction-adjusted benchmark has no resolution at that horizon, so
`alpha ≈ pick return` by construction. The honest reading is "now measurable,
still unmeasured in any meaningful sense", and the page says so via the CI being
absent rather than implying a win.

The follow-up that would make this class real is intraday futures bars; the class
gate and the mapping are now in place for whenever that data exists.

## Tests

`tests/test_selection_alpha_coverage.py`: `test_futures_has_a_price_table_mapping`,
`test_every_payload_class_is_mappable` (iterates every class present in the payload).
15 passed in that file.
