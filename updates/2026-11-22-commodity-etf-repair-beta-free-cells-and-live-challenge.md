# Commodity ETF repair, beta-free cells, deep funding history and the live challenge

**Date:** 2026-11-22 · **Type:** research infrastructure + new instruments
**Files:** `tools/per_class_edge_harness.py`, `tools/build_per_class_report.py`,
`tools/fetch_funding_history.py` *(new)*, `tools/realtime_challenge.py` *(new)*,
`.github/workflows/realtime-challenge.yml` *(new)*, `tests/test_per_class_edge_harness.py`

## What was broken

1. **COMMODITY was scored on raw futures.** Yahoo's `=F` series carry unadjusted
   contract rolls — `ZC=F` prints −23.6 % on July 15 in three separate years, and
   `CL=F` closed at **−37.63** on 2020-04-20, which makes `pct_change` meaningless
   (−306 %). The class was reported `DATA_INTEGRITY_FAIL`, which is correct but
   useless: it told us nothing about whether a commodity rule works.
2. **Every cell was long-only**, so each one contained beta to its own universe and
   the "excess vs benchmark" gate was comparing two bets on the same thing.
3. **The funding-carry cell had 9 months of data** — 8 monthly buckets, i.e.
   `INSUFFICIENT_N`, even though `ccxt` (already installed) exposes years of it.
4. **The benchmark gate applied a volatility-blind comparison** to de-risking
   strategies, which cannot pass it by construction.

## What changed

- `COMMODITY_INVESTABLE` (8 liquid commodity ETFs) + cells **H-223/H-224**, so the
  class is measured on an instrument a holder can actually own. The roll lives
  inside NAV, so a pass or fail means something.
- `xsmom_ls()` — dollar-neutral cross-sectional momentum with hard invariants:
  gross exposure ≤ 1 and net exposure 0 raise `AssertionError`. Cells **H-226**
  (equity) and **H-227** (crypto).
- `funding_carry_daily()` — delta-neutral carry from recorded funding prints, with
  an explicit, published daily drag. Cell **H-228**. New
  `tools/fetch_funding_history.py` pulls 32,350 settlements (2021→2026) through
  `ccxt`, preferring the deep archive over the 9-month snapshot.
- `matched_vol_block()` — scales every cell to its benchmark's ex-post volatility
  (capped 4×) and reports the comparison as **G6b**, separate from the strict gate.
  No cell is promoted on G6b.
- Integrity flags are now scoped to the futures cells (`H-210`/`H-211`) so the ETF
  cells cannot inherit a failure they do not have.
- `tools/realtime_challenge.py` + `.github/workflows/realtime-challenge.yml`: open,
  mark and close paper positions on live Binance data every 15 minutes, with a
  committed ledger.

## How it was verified

```
python3 -m pytest tests/test_per_class_edge_harness.py -q     # 10 passed
python3 tools/per_class_edge_harness.py --n-trials 29         # 40 cells, PBO 0.345
python3 tools/build_per_class_report.py                       # report + card regenerated
python3 tools/realtime_challenge.py open  --tag buffy         # 2 live fills taken
python3 tools/realtime_challenge.py mark  --tag buffy         # TP/SL/time logic exercised
```

## Result (honest)

- COMMODITY: ETF repair did not rescue the class — CI-LB −1.32 / −2.79 bps.
- H-226/H-227: both refuted; `H-201` therefore carries real beta, not pure factor.
- H-228 funding carry: PF 2.07, CI-LB +0.143 bps at the registered 1 bps/day drag,
  **`FAILS_2X_COST`**. Gross 7.28 %/yr, Sharpe 3.42, entirely cost-sensitive.
- Declaring 29 trials instead of 23 dropped `H-201` from `dsr 0.9749` to **0.9469**,
  so **no class passes every gate any more**.
- Live challenge: 2 positions opened on live prices with TP/SL/time stop recorded.

## Not claimed

No class is money-ready. Nothing here is a forward-tested edge: the longest
forward record on the desk is one pod with zero closed trades.
