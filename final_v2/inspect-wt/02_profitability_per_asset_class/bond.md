# BOND / FIXED INCOME — how to get profitable (deepAI)

## My measured truth (live, 2026-11-14)
- Active: 30 picks, **93.3% zombie**, repriced n=13 all 0.00% — a dead class wearing green.
- Closed ledger: **n=1–3** (policy-clean but statistically meaningless); seeds are null-price.
- **Vacuous PASS:** 0 picks renders green — the dashboard reports health where there is no
  data at all (my `fixspec_surface_disagreement_banner` / `fixspec_mutual_fund_vaporware`
  patterns apply).
- finpredict roadmap + finpredict-v3 agree: `INSUFFICIENT_DATA`, price backfill absent,
  no realized evidence of any bond module.

## What peers propose
- **Duration / rate-trend rotation + carry**, realistic Sharpe **~0.3–0.6** (finpredict);
- backfill real marks (yfinance/FRED), never `current=entry` (both peers — matches my veto
  in session 1 against forced backfill).

## My plan
1. **Mark the class `NOT_BUILT / INSUFFICIENT_DATA` today** (kill the vacuous PASS) — one line
   in the surface banner spec I already wrote.
2. **Backfill real marks** (`AGG`, `TLT`, `IEF`, `^TNX` via yfinance/FRED) with a staleness
   guard; explicit veto on `current=entry` or any synthetic fill (binding veto list, agreed
   across peers).
3. **Only then** build ONE sleeve: **rate-trend / duration rotation** (e.g. 10y-yield trend →
   rotate TLT/IEF/SHY; or carry + trend overlay on a 3-bond universe), monthly rebalance,
   pre-registered, excess-of-benchmark paired bootstrap, T2∧v3 forward gates.
4. **Do not** port the equity/ETF scout zoo to bonds — n=1 with zero realized evidence means
   every bond "strategy" in the 683-zoo is untested speculation.

**Tradable today: NO.** Path: marks backfill → one rotation sleeve → gates. Honest expectation:
Sharpe 0.3–0.6, diversifying, capacity-fine (bonds are deep) but low absolute return.
