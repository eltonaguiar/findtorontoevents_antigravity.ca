# Ledger data health: impossible and improbable rows per asset class — 2026-11-22

## What was built

`tools/ledger_data_health.py` — arithmetic/structural checks per asset class, run on
the 3,500-pick closed ledger, `universal_resolved_picks.json` (4,877) and the
registry's own `impossible_winrate` flags. Output:
`reports/2026-11-22-data-health.{json,md}`.

## Findings (3,500 closed picks)

| class | rows | BAD_PRICE | FLAT | LEVELS | EXIT_SIGN | GAIN_BEYOND_LEVELS | NO_MOVE(_EXIT) | OUTLIER z>10 |
|---|---|---|---|---|---|---|---|---|
| CRYPTO | 2070 | 0 | 2 | 39 | 12 | 297 | 1 | 6 |
| EQUITY | 690 | 9 | 10 | 2 | 0 | 86 | 0 | 0 |
| ETF | 503 | 0 | 0 | 0 | 0 | 16 | 1 | 0 |
| FOREX | 199 | 29 | 40 | 2 | 2 | 1 | 1 | 0 |
| BOND | 28 | 0 | 1 | 1 | 1 | 0 | 0 | 0 |
| COMMODITY | 9 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |

**1. `exit_price = 0.0` on 38 rows marked CLOSED** (EQUITY 9, FOREX 29), all with
`pnl_pct = 0.0`. Examples: V, MA, JPM, JNJ, GOOGL with a positive entry and exit 0.0.
These are unresolved placeholders being counted as closed trades.

**2. P/L of exactly 0.0 on 54 rows** (FOREX 40, EQUITY 10, CRYPTO 2, COMMODITY 1,
BOND 1). 14 of them have `entry_price == exit_price`, and several still carry
`exit_reason = TP_HIT` / `SL_HIT` — a take-profit that did not move the price.
Example: `AVAXUSDT entry=9.625 exit=9.625 status=CLOSED reason=TP_HIT`.

**3. Stop/target on the wrong side of entry: 44 rows** (CRYPTO 39, FOREX 2,
EQUITY 2, BOND 1). Example `AVAXUSDT SHORT entry 9.625, sl 9.4325 (below), tp
9.91375 (above)` — both levels inverted for a short. `HYPEUSDT LONG entry 39.91,
sl 78.19, tp 39.9379`.

**4. Exit beyond the declared TP/SL envelope: 400 rows.** This is the biggest one,
and the first interpretation I formed was wrong. I checked whether the P/L was
fabricated by testing `pnl_pct / price_move` on all 400:

```
ratio median 1.00, IQR [1.00, 1.00], 399/400 within 10% of median
```

So the **P/L is exactly the price move** — arithmetically consistent with
`entry_price`/`exit_price`. What is stale is the **level pair** on those rows:
HYPEUSDT exited at 79.14 (+98.3%) while its own `take_profit` sits at 39.938
(+0.07%). The outcome is real against its prices; the stop/target fields describe a
different state of the record. Consequence: **`stop_loss`/`take_profit` cannot be
trusted for first-touch logic on 11.4% of the ledger** — which is why
`tools/first_touch_resolve.py` walks bars rather than levels.

**5. `universal_resolved_picks.json`: 1,112 of 4,877 rows have no `exit_price` and
no `pnl_pct`** — they are not resolved and should not be in a "resolved" file.
589 CRYPTO rows share duplicate ids. `closed_at` is absent on 100% (the schema uses
`resolved_at`; that one is a naming mismatch, not a defect).

**6. Robust outliers**: CRYPTO 6 rows with MAD z > 10 (worst 22.7), range
−97.2% to +100.0%. No other class exceeds z 5.8.

## What this changes

* Cost/edge numbers computed from `recent_closed` carry 38 unresolved zeros and 54
  flat rows; at 2,070 CRYPTO rows those 2 rows barely move a class PF, but at 199
  FOREX rows the 69 affected rows (35%) are the difference between "weak" and
  "unmeasurable".
* Registry `impossible_winrate` flags: none set on any class.
* Nothing here says P/L values were invented — the one place that could have
  (400 rows) reconciles to the price move exactly. It says the **level fields are
  unreliable** and **unresolved rows are being counted as closed**.

## Repro

```
python3 tools/ledger_data_health.py \
  --dashboard <dashboard_data.json> \
  --resolved <universal_resolved_picks.json> \
  --registry <pf_registry.json>
```
