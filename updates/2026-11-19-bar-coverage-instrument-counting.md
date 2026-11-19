# Bar coverage now counts instruments, not symbol spellings

Surface: `findtorontoevents.ca/audit3` → `selection_alpha.bar_coverage` (rendered as
the "Bar coverage" table). Code: `alpha_engine/audit3_selection_alpha.py`,
`audit_dashboard/audit3.html`.

## What was wrong

`symbol_candidates()` deliberately emits several spellings of the same instrument,
because vendors disagree about them:

* CRYPTO `BTC-USD` → `BTCUSDT`, `BTCUSD`, `BTC`
* FOREX  `AUDJPY=X` → `AUD/JPY`, `AUDJPY`, `AUD-JPY`

`bar_coverage()` counted **every spelling** as its own requested symbol, so the table
reported ratios nobody can act on:

| class | before | after |
|---|---|---|
| CRYPTO | 36 / 173 | **36 / 57** |
| FOREX | 12 / 44 | **12 / 17** |
| EQUITY | 37 / 37 | 37 / 37 |
| ETF | 19 / 19 | 19 / 19 |
| BOND | 2 / 2 | 2 / 2 |
| COMMODITY | 8 / 9 | 8 / 9 |

Most of the "missing" CRYPTO entries were variants of symbols already priced, which
made the class look far less measurable than it is — and hid the genuinely missing
ones in the noise.

## What changed

* `instrument_key(klass, sym)` — one identity per instrument: strips `/`, `-`, `.`,
  `=X`, and the `USDT`/`USDC`/`BUSD`/`USD`/`PERP` crypto suffixes.
* `_instrument_groups()` groups the wanted spellings by that key.
* `bar_coverage()` now reports:
  * `symbols_requested` / `symbols_found` — **instruments** (the actionable ratio);
  * `variants_considered` — the old spelling count, kept for comparison;
  * `missing_symbols` — one entry per missing instrument, labelled with its shortest
    spelling (`ADA`, not `ADAUSD`).
* An instrument counts as priced when **any** of its spellings has bars — the same
  rule `alpha_for()` uses to pick a series, so coverage and measurement agree.
* UI label `Symbols priced` → `Instruments priced`, and the note explains that
  spellings collapse.

## Verified

* 4 new tests in `tests/test_selection_alpha_coverage.py` (crypto collapse, one-entry
  missing naming, forex vendor spellings, distinct instruments still counted apart)
  plus the 8 existing coverage tests and `tests/test_audit3_selection_alpha.py`:
  **30 passed**.
* Real run against the production payload (3,500 closed picks): CRYPTO `36/57`
  (variants 173), FOREX `12/17` (variants 44), EQUITY `37/37`, ETF `19/19`,
  BOND `2/2`, COMMODITY `8/9` (`HE=F` has no vendor data).

## Still open (now visible instead of buried)

The remaining missing CRYPTO instruments are mostly malformed tickers in the picks
themselves — `ADAT`, `ARBT`, `AVAXT`, `BNBT`, `BTCT`, `DOGET` — which are data-entry
artifacts, not gaps in the price tables. The instrument-level count is what makes that
distinguishable. FOREX still genuinely lacks `AUDJPY`, `CHF`, `JPY`, `NZDJPY`,
`USDZAR` rows in `fx_prices`.
