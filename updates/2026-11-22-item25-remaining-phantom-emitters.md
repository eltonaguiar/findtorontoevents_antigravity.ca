# Item 25 — the remaining three POD-EQUITY-BREAKOUT phantom emitters

**Task:** Item 25 of the research-integrity programme. **Date:** 2026-11-22.
**Scope:** fix the emission (not the existence) of `rs-breakout-scout`,
`vol-contraction-scout`, `adx-trend-scout` into the table
[`tools/pod_emission_audit.py`](../tools/pod_emission_audit.py:62) counts. Sequel to
[N2](./2026-11-22-n2-pod-equity-breakout-emitters.md), which did `donchian-stock-breakout`.

## 1. What was broken (with file:line)

Same root cause as N2, cause class **(a): emitter exists but is never wired to the counted table.**

- The three strategies ARE implemented in
  [`KIMI_RISEOFTHECLAW/live_scanner.py`](../KIMI_RISEOFTHECLAW/live_scanner.py):
  `signal_volatility_contraction_breakout` at
  [:3191](../KIMI_RISEOFTHECLAW/live_scanner.py:3191), `signal_adx_trend_filter` at
  [:4987](../KIMI_RISEOFTHECLAW/live_scanner.py:4987), `signal_relative_strength_breakout` at
  [:5858](../KIMI_RISEOFTHECLAW/live_scanner.py:5858).
  (The line numbers cited in the task brief — 5276/5300/6030 — have drifted; these are the
  current ones, confirmed by grep.)
- But the scanner persists to a **local SQLite** store
  ([`live_scanner.py`](../KIMI_RISEOFTHECLAW/live_scanner.py:9575), `db.write_pick(pick)`), never to
  MySQL `trading_picks`. `KIMI_RISEOFTHECLAW/data/*.db` are 0 bytes on disk.
- Measurement contract: a strategy counts as emitted only with ≥1 row in `trading_picks` or
  `at_signal_outcomes`, matched on `strategy` ([:62](../tools/pod_emission_audit.py:62)).

## 2. The three strategies' semantics, read from source

All are LONG-only (they return `"BUY"` or `None`), signature
`(symbol: str, df: pd.DataFrame, all_data: dict, drought: int = 0) -> tuple[str | None, str]`.
`drought=0` is the scanner default and is what the emitter uses.

| Strategy | Source | Needs | Fires when (drought=0) |
|---|---|---|---|
| `adx-trend-scout` | `signal_adx_trend_filter` [:4987](../KIMI_RISEOFTHECLAW/live_scanner.py:4987) | Close, High, Low; ≥30 bars | Wilder-14 ADX ≥ 25 AND DI+ > DI- AND close ≥ 0.99·SMA20 |
| `vol-contraction-scout` | `signal_volatility_contraction_breakout` [:3191](../KIMI_RISEOFTHECLAW/live_scanner.py:3191) | Close, High, Low, Volume; ≥30 bars | BB(20,2) width ≤ 1.05·(40d min) AND TR ≤ 1.02·(NR7 min) AND close ≥ 0.99·SMA20 AND mean5(vol) < 1.2·mean20(vol) AND RSI(14, Wilder) ≤ 68 |
| `rs-breakout-scout` | `signal_relative_strength_breakout` [:5858](../KIMI_RISEOFTHECLAW/live_scanner.py:5858) | Close + **SPY** Close; ≥25 bars | RS = close/SPY at 20d high (≥0.999·max) AND close ≥ 0.99·SMA50 AND 5d RS change ≥ +0.5% |

Notes: `rs-breakout` aligns symbol and SPY by taking the **last `min(len)` bars of each** positionally
([:5873-5876](../KIMI_RISEOFTHECLAW/live_scanner.py:5873)); the emitter does exactly the same.
`SPY_5y.csv` is present in the cache, so this pod is not blocked. None of the three had ambiguous
semantics, so nothing is `BLOCKED_RATIONALE`.

## 3. What was changed

**One file modified:** [`tools/emit_equity_breakout_pod.py`](../tools/emit_equity_breakout_pod.py) —
extended, not forked.

- Added a `STRATEGIES` registry mapping `{donchian, rs-breakout, vol-contraction, adx-trend}` to the
  audit strategy name and a minimum-bar count; `--strategy` selects one, `--strategy all` runs all
  four, `donchian` remains the default (so old invocations are unchanged).
- Added `adx_trend_signals`, `vol_contraction_signals`, `rs_breakout_signals` as **vectorised
  line-for-line re-implementations** of the three live functions. They are not new strategies: they
  are the same rules evaluated at every bar so the most recent real signal can be located.
- The MySQL insert path was **not** duplicated: `upsert_rows(conn, rows)` is the single shared
  writer, and the `UPSERT` statement + `_COLS` are shared by every strategy. `donchian`'s output is
  byte-identical to before.
- Preserved: dry-run default, idempotency by deterministic `id`
  (`sha256(strategy|symbol|signal-date)` = PRIMARY KEY, so `ON DUPLICATE KEY UPDATE`), stop-checked-first,
  −8bp slippage, real cached OHLCV only.
- Exit convention unchanged from donchian (entry at signal close, 20-bar time stop or 2×ATR20 stop,
  whichever comes first): none of the three defines its own exit (`rs-breakout`'s docstring says
  "Exit: handled by stop/trailing stop system"), so the proven shared convention applies.

**One test added:** [`tests/test_equity_breakout_pod_emitter.py`](../tests/test_equity_breakout_pod_emitter.py).

## 4. Verification (commands + literal output)

### Faithfulness of the re-implementations

Compared each vectorised series to the **real** `live_scanner` function called on a truncated frame
(as-of that bar), over every equity symbol and every bar:

```
$ python3 /tmp/item25_equiv.py
equivalence: agree=159368 mismatch=0 positive_cases_seen=16986
```

### Dry runs (row counts that would be inserted)

```
$ for s in donchian adx-trend vol-contraction rs-breakout; do python3 tools/emit_equity_breakout_pod.py --strategy $s | tail -4; done
-- donchian-stock-breakout: 44 rows from real signals on cached OHLCV
-- adx-trend-scout: 44 rows from real signals on cached OHLCV
-- vol-contraction-scout: 44 rows from real signals on cached OHLCV
-- rs-breakout-scout: 43 rows from real signals on cached OHLCV
```

### BEFORE (audit, read-only)

```
$ python3 tools/pod_emission_audit.py --manifest reports/audit3_confirmatory.json
pod emission audit: 23 strategies, 14 phantom
  PHANTOM POD-EQUITY-BREAKOUT: rs-breakout-scout (0 picks, 0 intrabar)
  PHANTOM POD-EQUITY-BREAKOUT: vol-contraction-scout (0 picks, 0 intrabar)
  PHANTOM POD-EQUITY-BREAKOUT: adx-trend-scout (0 picks, 0 intrabar)
  ... (11 other pods)
```

Per-entry: `donchian-stock-breakout {'picks': 44, ... 'ok': True}`, and for each of the three
`{'picks': 0, 'intrabar': 0, 'emitted': False, 'ok': False}`.

### Apply (live MySQL)

```
$ python3 tools/emit_equity_breakout_pod.py --strategy adx-trend --apply | tail -1
applied adx-trend-scout: 44 row(s) touched; trading_picks now has 44 rows for adx-trend-scout
$ python3 tools/emit_equity_breakout_pod.py --strategy vol-contraction --apply | tail -1
applied vol-contraction-scout: 44 row(s) touched; trading_picks now has 44 rows for vol-contraction-scout
$ python3 tools/emit_equity_breakout_pod.py --strategy rs-breakout --apply | tail -1
applied rs-breakout-scout: 43 row(s) touched; trading_picks now has 43 rows for rs-breakout-scout
```

**Shared state changed:** 131 new rows inserted into MySQL `trading_picks`.

### Idempotency (live re-run)

```
$ python3 tools/emit_equity_breakout_pod.py --strategy adx-trend --apply | tail -1
applied adx-trend-scout: 0 row(s) touched; trading_picks now has 44 rows for adx-trend-scout
```

`0 row(s) touched` and the count still 44: the second run duplicates nothing.

### AFTER (same audit)

```
$ python3 tools/pod_emission_audit.py --manifest reports/audit3_confirmatory.json
pod emission audit: 23 strategies, 11 phantom
```

Per-entry for POD-EQUITY-BREAKOUT:

```
{'strategy': 'donchian-stock-breakout',  'picks': 44, 'intrabar': 0, 'emitted': True, 'ok': True}
{'strategy': 'rs-breakout-scout',        'picks': 43, 'intrabar': 0, 'emitted': True, 'ok': True}
{'strategy': 'vol-contraction-scout',    'picks': 44, 'intrabar': 0, 'emitted': True, 'ok': True}
{'strategy': 'adx-trend-scout',          'picks': 44, 'intrabar': 0, 'emitted': True, 'ok': True}
```

No POD-EQUITY-BREAKOUT line remains in the phantom list; the total dropped 14 → 11 (the other 11
phantom pods are out of scope).

### Row facts (MySQL read-back)

| Strategy | Rows | Symbols | created_at range |
|---|---|---|---|
| `adx-trend-scout` | 44 | 44 | 2025-10-29 → 2026-11-18 |
| `vol-contraction-scout` | 44 | 44 | 2025-07-29 → 2026-10-28 |
| `rs-breakout-scout` | 43 | 43 | 2026-08-05 → 2026-11-18 |

### Idempotency test

```
$ python3 -m pytest tests/test_equity_breakout_pod_emitter.py -q
....                                                                     [100%]
4 passed in 1.20s
```

The first test upserts the same rows twice into a fake connection that enforces PRIMARY KEY `id`
semantics and asserts the store size is unchanged after the second pass.

## 5. Plumbing status vs strategy status

**Plumbing: FIXED** for all three. Each now has rows in `trading_picks`, and the audit counts them
(`ok: True`). This is the whole of what Item 25 asked for.

**Strategy quality: NOT ESTABLISHED here, and the incidental numbers are not encouraging.**
*Not a verdict* — just what the emitted rows show, at 8bp EQUITY round-trip:

| Strategy | mean net | rows with net > 0 |
|---|---|---|
| `adx-trend-scout` | −3.12% | 8 / 44 |
| `vol-contraction-scout` | +0.17% | 15 / 44 |
| `rs-breakout-scout` | −3.67% | 1 / 43 |

Emitting rows for a weak strategy is a plumbing success and a profitability non-event. As with the
donchian rows (PF 0.247, and the pod's published PF 1.479 unreproduced), these rows should be read as
"now measurable", not "now good".

## 6. Not done / still phantom / why

- `intrabar` (`at_signal_outcomes`) is still 0 for all four: that table is filled by
  [`audit_trail/universal_pick_resolver.py`](../audit_trail/universal_pick_resolver.py) over time,
  after the picks resolve. Out of scope here.
- 11 other pods remain phantom (e.g. `vwap_reversion`, `bollinger_mr`, `faber_taa`,
  `commodity_basis_carry`, `btc-4h-rsi-macd-scout`). Out of Item 25's scope.
- No git commit, no push, no COMS (per the task brief).
