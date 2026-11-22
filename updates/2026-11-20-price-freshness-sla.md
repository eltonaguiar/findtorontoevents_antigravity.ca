# Per-class price freshness is now enforced, not printed (2026-11-20)

## What was broken

`alpha_engine/audit3_selection_alpha.py` maps every asset class to a price table
(`TABLE_FOR`) and declares a per-class staleness tolerance (`TOLERANCE_MS`). When a
table goes stale, the class silently reverts to `unmeasured` and its selection-alpha
gate can never be evaluated — however fresh the other classes are.

The only freshness check for those tables was an inline block in
`.github/workflows/audit3-ledger.yml` that:

1. **Only printed a warning.** A stale equity table produced `::warning` and the job
   stayed green — the alarm had no authority.
2. **Hardcoded `5` days** instead of reading `TOLERANCE_MS`, so the alarm and the gate
   could disagree about what "stale" means, and the gate is the one that decides
   whether a class is measured.

Contrast: `crypto_ohlcv` already had a hard, fail-loud assert in
`crypto-ohlcv-refresh.yml`. The daily tables had nothing equivalent.

## What changed

**`tools/price_freshness_sla.py`** (new) — checks every distinct table and exits
non-zero on breach.

- Reads `TABLE_FOR` and `TOLERANCE_MS` **from the gate itself**, so there is one
  source of truth and they cannot drift.
- A table shared by two classes (`etf_daily_ohlcv` serves `ETF` and `BOND`) is checked
  **once**, at the tightest tolerance, naming every class it gates.
- An **empty table is a failure**, not a pass — no rows means structurally
  unmeasurable, which is exactly the silent state this is meant to catch.
- Exit codes distinguish the three honest answers: `0` fresh, `1` stale, `2` could not
  check (no creds/driver). "I could not look" is never reported as "it is fine".

**`.github/workflows/audit3-ledger.yml`** — the inline block is replaced by an
enforcing step: `rc=1` fails the run with an `::error`; `rc=2` warns that freshness is
*unknown* rather than assuming it is fresh.

**`tests/test_price_freshness_sla.py`** (new, 7 tests) — covers the pure `evaluate()`
half with no DB: full class coverage, shared-table dedup at the tightest tolerance,
fresh-vs-stale, today's bar being 0 days old (not 1), empty-as-failure, the `ms` vs
`date` column kinds, and a future timestamp not being reported stale.

## Verification

```
python3 -m pytest tests/test_price_freshness_sla.py -q   → 7 passed
python3 tools/price_freshness_sla.py --warn-only          → runs against the real DB
```

Live output at the time of writing:

| table | classes | last | age | tolerance | status |
|---|---|---|---|---|---|
| crypto_ohlcv | CRYPTO | — | 0.1d | 0.1d | **STALE** |
| equity_daily_ohlcv | EQUITY | 2026-11-19 | 0.7d | 5.0d | OK |
| etf_daily_ohlcv | BOND/ETF | 2026-11-19 | 0.7d | 5.0d | OK |
| futures_daily_ohlcv | COMMODITY/FUTURES | 2026-11-20 | −0.3d | 5.0d | OK |
| fx_prices | FOREX | 2026-11-19 | 0.7d | 5.0d | OK |

## Open — one real disagreement, not fixed here

`crypto_ohlcv` is governed by **three different staleness numbers**:

- `TOLERANCE_MS["CRYPTO"]` = **3h** (the selection-alpha gate)
- the refresh cron = **every 4h** (`52 */4 * * *`)
- the assert in `crypto-ohlcv-refresh.yml` = **8h**

A 3h SLA against a 4h refresh cadence will fail on a perfectly healthy pipeline —
it would measure the cron, not the data. This needs one owner decision on which
number is canonical; changing `TOLERANCE_MS` changes the measurement gate, and
changing the cron changes cost. Not changed unilaterally.
