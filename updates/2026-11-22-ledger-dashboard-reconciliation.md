# Ledger vs dashboard reconciliation — 0% of 3,500 closed picks are forward-creditable

**Date:** 2026-11-22
**Tool:** `tools/provenance_reconcile.py`
**Artifact:** `reports/provenance/reconciliation.json`
**Ledger item:** T5

---

## Why a reconciliation was needed at all

The provenance ledger proves a pick existed before its outcome **only if it sees the
same picks the rest of the system reports**. A ledger that agrees with itself and
disagrees with the dashboard measures a parallel universe — a valid hash chain over a
population nobody trades.

So the question is not "is the chain intact" (that is `provenance_ledger.py --verify`)
but **"does the chain cover the same picks"**. Until today that had never been asked.

## The measured answer

```
ledger records: 0        dashboard closed picks: 3,500

counts:
  ledger_total      0
  dashboard_total   3500
  in_both           0
  ledger_only       0
  dashboard_only    3500      <-- every single pick
  near_miss         0
  symbol_mismatch   0

coverage:
  ledger_covered_pct      null   (undefined, not 100%)
  dashboard_covered_pct   0.0

status: NO DATA
```

**Every one of the 3,500 closed picks on the dashboard is `dashboard_only`:** it never
passed through the emit-time hook, so **no forward credit can ever be assigned to it.**
That is not a reconciliation failure — it is the survivorship defect the ledger was
built to close, now measured for the first time at its true size.

By asset class, the 3,500 uncredited picks are:

| class | count |
|---|---|
| CRYPTO | 1,835 |
| EQUITY | 782 |
| ETF | 588 |
| FOREX | 204 |
| COMMODITY | 50 |
| BOND | 37 |

## Reading the status honestly

`status: NO DATA`, not `OK`, and `ledger_covered_pct: null`, not `0%` or `100%`.

Coverage from an empty ledger is **undefined**. Reporting it as `0%` would be a
measurement of nothing dressed as a measurement; reporting it as `100%` (which a naive
`in_both / ledger_total` would, via a zero denominator) would be actively false. The
tool returns `None` and says why. Three empty-side cases are handled and tested:
both empty, ledger empty, dashboard empty.

## Method

**Key** = (normalised symbol, side, strategy) + timestamp window.

- Symbols are normalised through `provenance_resolver.resolve_symbol`, so `BTCUSDT`
  and `BTC-USD` compare equal, as do `EURUSD` and `EUR/USD`. Without this the
  reconciliation would report large spurious divergence that is purely notation.
- A **72-hour** window, because the ledger records *emit* time and the dashboard
  records *trade* time. Those are not the same instant.
- Outside the window is **`near_miss`, never coverage**. A matching key with a
  744-hour gap consumes no dashboard row.

## Two defects found while building it

### 1. Matching by key-group swallowed duplicate rows

The first version matched on key and then excluded **every** dashboard row sharing
that key. On a real-data check — a synthetic ledger of 6 actual dashboard rows against
the full 3,500 — it reported `dashboard_only: 3491` when the true answer was `3494`.
Three duplicate `(symbol, side, strategy)` rows were silently absorbed by neighbours
that happened to match.

That matters because this dashboard carries repeated `(symbol, side, strategy)` rows;
an earlier round measured **1,864 duplicate signal-timestamp groups**. An off-by-N in
the survivorship count is exactly the kind of error this tool exists to detect
elsewhere.

**Fixed:** each dashboard row is consumed at most once, greedily nearest-timestamp
first. Verified: 6 real rows → `in_both: 6`, `dashboard_only: 3494` exactly. And a
two-identical-rows / one-ledger-row case yields `in_both: 1, dashboard_only: 1` — the
second row is not swallowed.

### 2. Coverage could divide by zero

`in_both / ledger_total` with `ledger_total == 0` is a crash or an infinity. Now
`None`, with the reason stated.

## Categories and what each one means

| category | meaning | who owns it |
|---|---|---|
| `in_both` | matched within the window | — |
| `dashboard_only` | on the dashboard, never emitted through the hook | **survivorship — the ledger's blind spot** |
| `ledger_only` | hook fired for a pick the dashboard does not show | the dashboard, or the hook firing twice |
| `near_miss` | same key, timestamps apart | a clock or a lag problem, not coverage |
| `symbol_mismatch` | same side+strategy, different normalised symbol | notation or a symbol-map gap |

## Verification

```
python3 tools/provenance_reconcile.py --selftest
  counts: {'ledger_total': 3, 'dashboard_total': 3, 'in_both': 2,
           'ledger_only': 1, 'dashboard_only': 1, 'near_miss': 0, ...}
  symbol normalisation BTCUSDT == BTC-USD matched          ok
  EURUSD == EUR/USD matched                                ok
  empty ledger + 3 dashboard picks -> status=NO DATA
  coverage is None (undefined), NOT 100%                   ok
  both empty -> status=NO DATA, coverage=None              ok
  same key, 744h apart -> in_both=0 near_miss=1
  outside the window is NOT counted as coverage            ok
  ALL RECONCILE SELFTESTS PASSED
```

Real-data check (synthetic ledger built from 6 actual dashboard rows, against all
3,500): `in_both 6 / dashboard_only 3494 / ledger_only 0` — exact.

## What this means

This is the first hard number on the programme's binding constraint. The ledger is not
merely empty; **the population it would have to cover is 3,500 picks wide and none of
them are in it**. Merging PR #1064 makes the hook live and future picks creditable, but
it does **not** retroactively credit anything: the 3,500 stay `dashboard_only` forever,
because a pick's emit time cannot be reconstructed after the fact. That is the whole
reason the ledger records at emit time rather than after.

Zero capital sanctioned. Not investment advice.
