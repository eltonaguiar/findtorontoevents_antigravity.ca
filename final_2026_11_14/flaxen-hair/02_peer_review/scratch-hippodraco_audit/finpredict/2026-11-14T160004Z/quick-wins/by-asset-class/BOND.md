# BOND — quick wins

## 1. Bond price backfill (or stop emitting unquoted signals) (S / H)
- **Problem:** `run_bond_scanner()` writes `active_picks_bond.json` with `entry_price` only (never `current_price`); `enrich_all_picks()` only reads `active_picks.json`, so bonds bypass enrichment → `current_price=null`, seeds ~25h old, class stuck INSUFFICIENT_DATA.
- **Fix:** Fetch a real mark via yfinance/FRED (extend `universal_price_enricher` + `_EQUITY_ETF_TICKERS`/`BOND_SYMBOLS` in `universal_pick_resolver.py:433-443`) — **never** stamp `current_price = entry_price` (that manufactures the frozen-price artifact). Gate emission: drop signals whose `entry_price` is `None`, and add a coverage gate (`<80% priced → DATA_STALE`).
- **Targets:** `alpha_engine/bond_scanner.py` `run_bond_scanner()` (~:334); `alpha_engine/bond_data_fred.py`.
- **Verify:** every emitted bond pick has non-null `current_price`; /audit BOND no longer lists `current_price=null`.

## 2. Auto-expire stale unquoted BOND seeds (S–M / M)
- **Problem:** 15 OPEN seeds ~25h old with `current_price=null` never resolve (no price → no TP/SL/time-exit) → zombie OPEN rows.
- **Fix:** Close any BOND pick with `current_price=null` and `age > 24h` as `exit_reason=STALE_NO_QUOTE` (combine with #1 so freshly-backed bonds aren't swept).
- **Targets:** `alpha_engine/bond_scanner.py` or `audit_trail/universal_pick_resolver.py` time-exit path.
- **Verify:** after scanner+resolver pass, no BOND OPEN pick older than 24h with `current_price=null`.
