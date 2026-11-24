# Price tables backfilled, BOND given a table, and coverage rendered on /audit3

**Date:** 2026-11-19 · **Files:** `tools/backfill_daily_ohlcv.py` (new),
`alpha_engine/audit3_selection_alpha.py`, `audit_dashboard/audit3.html`,
`tests/test_selection_alpha_coverage.py`

Three things were needed before the FOREX / COMMODITY / BOND gates could measure anything:
fresh bars, a table mapping for BOND, and a page that says why a gate is unmeasured.

---

## 1. Backfill — data, not code

New `tools/backfill_daily_ohlcv.py` (dry-run by default, `--apply` to write, upsert-only against
the existing `(symbol, trade_date)` unique keys, `--since` bounds writes so history is never
rewritten). Run:

```
python3 tools/backfill_daily_ohlcv.py --since 2026-06-18 --apply
python3 tools/fx_backfill.py --apply --since 2026-02-10 --until 2026-11-19
```

| table | before | after |
|---|---|---|
| `equity_daily_ohlcv` | 2026-06-18, 230 symbols | **2026-11-19, 235** (+25,252 rows) |
| `etf_daily_ohlcv` | 2026-10-30, **36 symbols** | **2026-11-19, 59** (+6,372 rows) |
| `futures_daily_ohlcv` | 2026-06-21, 11 symbols | **2026-11-19, 17** (+1,836 rows) |
| `fx_prices` | 2026-02-09, 15 pairs | **2026-11-18, 15** (+3,030 rows) |

The ETF universe was **widened on purpose** (`ETF_SYMBOLS | BOND_SYMBOLS`), because freshness
alone does not help if the symbol was never tracked. Four metal symbols
(`XAUUSD=F` etc.) are not Yahoo tickers and are reported as `no_data` rather than failing.

## 2. The historical class repair was a no-op — already fixed upstream

Census before: **288** `asset_class='equity'` rows on BASE-USD symbols (ETH 57, BTC 48, ADA 33,
SOL 33, LINK 33, AVAX 33, DOGE 26, XRP 25), dated 2026-05-31 → 2026-11-19.

Immediately before running the UPDATE, the same predicate returned **0 rows**, and the BASE-USD
class spread is now `CRYPTO 5269, MEME 73, forex 68` — no equity left. No fiat or metal base was
ever in the set, so the guard clause had nothing to protect.

Explanation: the emitter fix (PR #939) is consumed by `universal_pick_resolver`, which re-stamps
`asset_class` on rows it re-resolves. The 288 rows were corrected by the normal pipeline between
the census and the repair, so the repair itself updated nothing. Recording it because the
sequence matters: the class fix repaired the past automatically, and a manual UPDATE would have
been redundant.

## 3. BOND had no price table at all

`TABLE_FOR` mapped CRYPTO / EQUITY / ETF / FOREX / COMMODITY — **BOND was missing**, so its gate
could never be measured no matter how fresh the tables were. The backfill exposed it: coverage
showed no BOND entry at all.

Fixed by mapping `BOND -> etf_daily_ohlcv` (bond ETFs are ETF-table instruments; this is exactly
why the ETF backfill widened to `BOND_SYMBOLS`), plus a `TOLERANCE_MS` entry. Two tests assert
the mapping exists and that every backfilled class has a table.

## 4. Coverage is now rendered on /audit3

A table under the class table shows, per class: symbols priced (`found/requested`), last bar
(red with "Nd stale" past 7 days), G8 gate status, and the symbols with no bars. A note explains
that the gate needs a bar at or after each exit, so a pick closing past its table's last bar
cannot be priced.

Implementation notes:
- `covRows` collided with the existing excluded-cohorts variable; `node --check` caught the
  redeclaration and it was renamed to `alphaCovRows` before merging.
- Staleness is computed against the browser's UTC date, so the badge is relative rather than
  hard-coded.
- Rendered only when the ledger carries `bar_coverage`; an older ledger simply shows nothing
  rather than a misleading empty table.

## Verification

Local end-to-end after the backfill and the BOND mapping:

```
coverage: CRYPTO 36/173 2026-11-19 · EQUITY 23/37 2026-11-19 · ETF 19/19 2026-11-19
          FOREX 12/44 2026-11-18 · COMMODITY 8/9 2026-11-19 · BOND 2/2 2026-11-19
by_class: CRYPTO -0.374% (1727) · EQUITY +0.032% (709) · ETF -0.117% (541)
          FOREX -0.037% (116) · COMMODITY -3.567% (46) · BOND -0.109% (34)
class gates: 6 of 7 measured (FUTURES still unmeasured — n=4)
cells with gate: 171 of 171
```

`75 passed` across selection-alpha coverage, audit3 selection alpha, tribunal and db sync.

## Open

- `FUTURES` still has no `TABLE_FOR` entry and only 4 picks — leave it unmeasured.
- Bars go stale again without a schedule. The backfill is manual by design; adding it to
  `audit3-ledger.yml` before the alpha step (bounded `--since`, `continue-on-error`) is the
  durable fix and needs sign-off because it writes to the DB on every run.
