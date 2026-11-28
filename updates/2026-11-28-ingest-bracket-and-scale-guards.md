# 2026-11-28 — Ingest guards for off-scale prices and impossible brackets

Follow-up to `updates/2026-11-28-label-drift-and-bad-row-quarantine.md`. That
work repaired the table; this work stops the same rows being written again.

## 1. What was broken

### 1.1 Impossible brackets reached the table unchallenged

`alpha_engine/mysql_trading_sync.py` is the single production INSERT path into
`trading_picks`. It validated entry and exit **price scale** but had no bracket
check at all, so a take-profit or stop-loss on the wrong side of its own entry
was written every run. Those rows are unresolvable by construction: a LONG stop
above entry triggers on the first tick, and a SHORT take-profit above entry is a
loss recorded as a target.

Measured on the live batch (dry run, 2026-11-28T03:0xZ): **150 of 10,376**
picks queued for upsert carried an impossible bracket.

Two distinct shapes, both visible in the log:

| Shape | Example | Cause |
|---|---|---|
| `stop_loss == entry_price` | `inverse_luxalgo_confluence::BTCUSDT` stop 60434.0 = entry 60434.0 | the `inverse_*` strategies invert direction but keep the original stop |
| SHORT with take-profit above entry | `SOLUSDT` short tp 72.8382 vs entry 71.41 | same inversion, TP kept from the long |

### 1.2 Crypto was exempt from the price-scale guard

Both `_validate_entry_price_scale` and `_validate_exit_price_scale` opened with

```python
if cat == "CRYPTO":
    return True, ""
```

on the stated grounds that "crypto spans extreme ranges (micro-cap → BTC)". That
reasoning does not hold: the guard compares a pick to the close of the **same
symbol**, so the absolute range is irrelevant — only the relative gap matters.
Crypto was therefore the one class with no scale defence, which is how
`ARBUSDT entry 0.000629 vs a real 0.1148` (**182x**) reached the table.

A second, independent reason crypto never passed: the price cache was loaded
from `stock_ohlcv` only. Crypto symbols live in `crypto_ohlcv`.

## 2. What changed

`alpha_engine/mysql_trading_sync.py`

1. **`_validate_bracket_geometry(entry, tp, sl, direction)`** — rejects a
   bracket on the wrong side of entry (LONG: `tp <= entry` or `sl >= entry`;
   SHORT mirrored) or more than `BRACKET_MAX_MULTIPLE = 100`x away. Runs before
   the `dry_run` return so `--dry-run` reports exactly what it would drop.
2. **Crypto/MEMECOIN scale thresholds added** (`20.0`) and the crypto
   short-circuit removed from both scale validators. 20x separates a decimal
   error (10x/100x/1000x) from entry-vs-close drift on the symbol being synced
   (normally <2x).
3. **`crypto_ohlcv` merged into the price cache**, so the guard has data for the
   class it now checks.

### 2.1 The drift check found the writers

Running `tools/backfill_category_aliases.py` after the 02:52Z normalisation
reported **6 rows** back on lowercase aliases (`prediction_market` x5, `meme`
x1) and **67 empty** labels. Counting the categories of every prepared row
showed the scale of what was still arriving: **593 of 10,376** rows would have
been written with an EMPTY category.

Three causes, all fixed at the source:

| Writer | Emitted | Fix |
|---|---|---|
| `tools/pm_macro_expansion.py:171` | `"prediction_market"` (lowercase) | now `"PREDICTION_MARKET"` |
| `tools/etf_sector_emitter.py` | `asset_class: "ETF"` but **no** `category` | `pick_to_row` now falls back to `asset_class` / `assetClass` / `class` before guessing from the symbol |
| `iso_regime_terminal`, `signal_validation` | neither field | `pick_to_row` now falls back to `detect_asset_class(symbol)`, and to ISO-pair detection for `USD-JPY` / `USD-CHF` |

`mutual_fund` from the classifier is deliberately **not** accepted — it is not a
member of the canonical enum, so those rows stay empty for
`tools/backfill_unknown_category.py` instead of introducing a 12th label.

## 3. Verification

| Check | Result |
|---|---|
| `pytest tests/test_sync_bracket_and_scale_guards.py tests/test_mysql_sync_category_inference.py` | **36 passed** |
| `py_compile alpha_engine/mysql_trading_sync.py` | OK |
| Bracket guard, live batch dry run | **150 suppressed**, 10,226 remain (10,376 prepared) |
| Category of every prepared row (monkeypatched `pick_to_row`) | **0 non-canonical** — before the fixes: 593 empty |
| `tools/backfill_category_aliases.py` after `--apply` | plan: 0 labels, 0 rows to rewrite |
| Previously-known impossible brackets in `trading_picks` | 1,554 stops + 1,492 take-profits (the population this guard now blocks) |

`--dry-run` does **not** exercise the entry/exit scale guards: it returns before
the DB connection those guards need. The bracket guard was moved above the
dry-run return for that reason, and scale-guard behaviour is covered by unit
tests instead. This is a real limitation of the dry-run signal, stated here so
nobody reads a clean dry run as "scale is fine".

## 4. OHLCV price-alignment check, 20–50% PnL band

Requested follow-up to the `ZS=F` finding: are other rows off-scale by a factor
small enough to have escaped the `>1000%` sweep?

Method (`reports/ohlcv_alignment_20_50_20261128T030306Z.json`): for each row,
compare entry against the close at `opened_at` (fallback `created_at`) and exit
against the close at `closed_at`, ±3 days, on the row's own date. Thresholds:
`OFF_SCALE` >2.0x, `SUSPECT` 1.5–2.0x, else `OK`; no bar → `UNVERIFIABLE`.

**31 rows in the band: 28 OK, 3 UNVERIFIABLE, 0 OFF_SCALE, 0 SUSPECT.**

The 3 unverifiable are `OP-USD` (x2) and `BCH-USD` — `cash`/legacy symbols with
no bar in `stock_ohlcv` or `crypto_ohlcv`, so no claim is made either way. The
28 verified rows match their bars (worst exit ratio 1.229, on `ENJUSDT`).

Largest entry ratio among the OK rows is 1.347 (`AVAXUSDT` 9.0 vs 6.68) — real
separation between entry time and the daily close, not a scale error, and the
exits on those rows match to 1.004.

## 5. Limitations

- The bracket guard sees only the `direction` string the emitter supplies. If an
  emitter mislabels direction, a correct bracket is rejected. The observed
  rejections are dominated by `inverse_*` strategies whose stops equal their
  entries, which is not a direction-labelling artefact.
- Scale guards compare against the **latest** bar, so a genuinely long-dormant
  pick can drift past the class threshold and be suppressed. Crypto's 20x
  threshold is set wide for that reason.
- The 67 rows that were already in the table with an empty category are **not**
  fixed by the next sync: the upsert only touches rows it prepares, and none of
  those 67 are in a current batch (the prepared-row audit is 0 empty). 36 of them
  (26 ETF, 7 EQUITY, 3 BOND) were relabelled by
  `tools/backfill_unknown_category.py --table trading_picks --apply`
  (`reports/label_fill_20261128T035540Z.json`, with a 36-row backup in
  `ejaguiar1_backups.trading_picks_label_fill_20261128T035540Z`). The remaining
  **31** have no deterministic class (`JTO-USD2`, `BRK-B`, `USD-JPY`, `USD-CHF`, …)
  and keep the `empty_category` gate red. `USD-JPY`/`USD-CHF` *would* be labelled
  `FOREX` by the sync's ISO-pair rule, but the backfill tool's classifier returns
  `unknown` for them; that asymmetry is reported here rather than guessed around.

## 6. Rebase onto `origin/main` and push

The four original commits, plus three follow-ups written during verification,
were rebased onto `origin/main` (`7347c52cedf0`) in a separate worktree and
pushed from there, because the working branch itself carries 9,141
commits by other authors and bots and `AGENTS.md` forbids pushing such a branch.

| Step | Result |
|---|---|
| Cherry-pick of the four commits | one conflict only: `tools/agent_ownership.json` (absent upstream, modified by me). Resolved by **keeping** it — `tools/git_guard_check.py` reads it. |
| Merge side effect | `test_unclassifiable_stays_empty` **failed**: AAPL now infers `EQUITY`. The test encoded the pre-fallback contract, so the earlier "35 passed" only ever held before the classifier fallback was added. Fixed in `31bc898ec232` — equities must be `EQUITY` (never crypto/futures), and a genuinely unknown symbol (`NOTREAL`) still stays empty. |
| `pytest` after the rebase | **36 passed** |
| `--dry-run` after the rebase | 10,736 prepared · **132** brackets suppressed · 10,604 remain |
| Prepared-row categories after the rebase | **0 non-canonical, 0 empty** — CRYPTO 9,517 · EQUITY 696 · FOREX 259 · COMMODITY 154 · ETF 61 · FUTURES 33 · BOND 11 · PREDICTION_MARKET 4 · MEMECOIN 1 |
| Live label gates after the push | `label_drift` **PASS** — non-canonical labels: none · `empty_category` **67 → 31** after the 36-row backfill |

Branch `fix/ingest-guards-and-labels-20261128` pushed to `origin` at
`31bc898ec232`; `git ls-remote` confirms the remote ref equals the local HEAD.
Twenty-one files, every one of them mine (the branch also carries the
follow-up commits that correct this record).

The 132-vs-150 difference is data, not code: the two runs prepared different
source mixes (10,736 rows after the rebase vs 10,376 before it).

## 7. Provenance

- Batch size and bracket rejections: `python3 -m alpha_engine.mysql_trading_sync --dry-run`, 2026-11-28T03:1xZ (pre-rebase) and the same command in `.push-wt` (post-rebase).
- Category distribution: `pick_to_row` monkeypatched over the same dry run, in both trees.
- Band audit: `reports/ohlcv_alignment_20_50_20261128T030306Z.json`.
- Bracket population counts: `updates/2026-11-28-label-drift-and-bad-row-quarantine.md` §4.
