# The FX blocker is a RESOLVER problem, not a dead price feed

**Date:** 2026-11-23T07:58Z · **Author:** Kilo · Paper only. Sharpens the procurement ask.

## What I found chasing the AUDJPY lead (the one real mechanism + nearest DSR miss)
- **24 FX (`=X`) picks exist; 0 are closed.** Never resolved — every one has `exit_price: null`.
- **AUDJPY: 3 picks, 0 closed** — entries at **111.828 (2026-03-21)**, **105.887 (2026-11-20)**, and one undated 106.277.
- **Prices DO exist** past the "2026-02-09 dead feed": the pipeline fetched AUDJPY 105.887 on 2026-11-20. So the feed is not
  dead in the way I earlier stated — the *historical series* ends Feb, but **snapshot prices are still being obtained**.
- The earlier "319 closed FX rows" were crypto `USDT` pairs, not FX; with a strict `=X` filter it is **0 closed**.

## Why this matters
My prior recommendation ("restore fx_prices past 2026-02-09") was **half right**. The real fix is a **resolver**:
1. close the **24 open FX picks** (resolve `exit_price`/`exit_date` from the prices the pipeline is already fetching);
2. stop writing `exit == entry` / null-exit placeholders as if they were outcomes.

Doing (1) alone would let AUDJPY accrue closed trades — the ~14 it needs to move DSR from 0.815 toward 0.95 — **without**
any new feed. That is cheaper and more honest than my earlier ask.

## Revised top procurement
**Close the 24 open FX picks** (a resolver change), then re-run the DSR on AUDJPY. This is now the single highest-value
action: it is the one class with a documented mechanism and a near-passing statistic, and the missing piece is a resolver,
not data acquisition.

*Paper only. Not investment advice.*
