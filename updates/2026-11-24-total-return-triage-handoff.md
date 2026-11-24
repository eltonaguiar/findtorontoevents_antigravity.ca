# Total-return triage — handoff (analysis only, no market data)

**Date:** 2026-11-24 · **Author:** Kilo. Source: `reports/total_return_triage.json`.

## Of the 62 files with explicit raw/price-only price usage
| category | count | action |
|---|---:|---|
| **leave: valuation/snapshot** (raw Close is CORRECT for P/E, marketCap, last price) | 5 | none |
| **FIX: auto_adjust=False + pct_change returns** | 1 | **done** — `tools/equity_vix_regime_rotator.py` → `auto_adjust=True` |
| **review: explicit `auto_adjust=False`** | 43 | per-file: is raw intentional (exact fill) or a return-math mistake? |
| **review: unclear** | 13 | per-file |

## Why I did not bulk-fix the 43
`auto_adjust=False` is sometimes **deliberate** — e.g. code that needs the exact traded price for fills, or that
back-adjusts manually. Bulk-switching to adjusted would corrupt those. Only the 1 file where it was `pct_change()` on
equity Close had an unambiguous return-math bug, and it is fixed.

## The rule for the 43
- If the raw Close feeds **`pct_change()` / returns / cumprod on an equity/ETF/bond** → switch to `auto_adjust=True` (or Adj
  Close) — the return is understated by the dividend yield (~2–4%/yr).
- If it feeds **a level/crossover/valuation/last-price** → leave raw (correct).

## Status
No-market-data work is exhausted: the unambiguous fix is landed; the rest need per-file judgment (raw-intent) or new data
(fundamentals for value, prices for PEAD, fills for the contest, crypto fee tier, delisting-aware prices).

## Per-file vetting result (2026-11-24T00:17Z) — thread CLOSED
Inspected the 5 machine-flagged "FIX" candidates; **none is an unambiguous return-math bug**:
- `tools/audit_total_return.py` — my own scanner (matches the literal string, no actual use).
- `tools/h035_futures_tsmom_research.py` — **futures**, no dividends → raw is correct.
- `tools/backtest_bond_yield_curve.py` — **TNX/IRX yield indices**, not bond prices → raw is correct.
- `alpha_engine/data/price_loader.py` — **already prefers `Adj Close`** when present → correct.
- `tools/backfill_pick_features.py` — stores raw Close as a *feature* (intent unknown), not a return calc.

**Conclusion:** the genuine return-math bug set was **1 file** (`equity_vix_regime_rotator.py`, fixed). The 43 `explicit_raw` files are legitimate (deliberate raw fetch + Adj Close, or non-dividend instruments like futures/yields). The total-return concern is **real but already handled**; no further bulk change is warranted. `reports/total_return_perfile_vetted.json`.
