# Fix spec — Garbage-price ingest guard

## Problem (evidence, live 2026-11-14)
- BTCUSDT SHORT with entry_price=0.3322 (Oct 8–11) and entry_price=1.334 (Aug 6–7) — 5 orders of
  magnitude off (BTC ~63k–86k in that period).
- BTCUSDT SHORT entry_price=0.0 emitted **2026-11-14T13:54 by `prediction_market_consensus`**
  (fresh row, fetch ~15:45Z). XRPUSDT rows with entry 0.0 as well.
- These rows poison: pnl math (entry 0 → division artifacts), dedup keys, resolver output,
  and any WR/PF aggregate that includes them.

## Proposed changes
1. **Ingest-time validation** in the pick-write path(s) (active_picks_sync.py,
   prediction_market_consensus.py emitter, and audit_trail ingest):
   ```python
   def validate_entry_price(sym, price, ts):
       if not price or price <= 0: reject("entry_price_missing_or_nonpositive")
       ref = reference_price(sym)  # latest cached quote
       if ref and not 0.05 <= price/ref <= 20: reject("entry_price_out_of_band")
   ```
   Reject at emit time, not display time.
2. **Retro-scan job**: hourly, scan last 7d of rows for entry_price out of 5–20x band vs the
   stored `stock_prices.json`/crypto cache; quarantine to a `data_quality_quarantine` table and
   exclude from aggregates; emit count to `pipeline_health.json`.
3. **prediction_market_consensus specifically**: it emitted the live XRPUSDT entry=0.0 row — audit
   its pick construction (likely missing quote at consensus time; the consensus layer should
   inherit the price from its child signals or refuse to emit).
4. Dashboard: surface `quarantined_rows_24h` so regressions are visible.

## Acceptance test
- Zero rows with entry_price<=0 or >20x band in active_raw/recent_closed after 48h.
- `prediction_market_consensus` emits nothing rather than an invalid row.
