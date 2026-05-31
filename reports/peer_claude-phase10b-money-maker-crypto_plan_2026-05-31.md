# /money-maker-readyv2 — CRYPTO — PLAN (2026-05-31)

## Scope
Per-class action plan for CRYPTO toward Tier-2 hedge-fund-grade performance (PF>1.5 / WR>50 / MDD<20 at n>=100 clean).

## Methodology
1. Aggregate live `ejaguiar1_stocks.trading_picks` for `LOWER(category)='crypto'`, last 90d.
2. Per-strategy PF/WR/avg_pnl with n>=5.
3. Cross-reference vs `audit_trail/quality_gates.py::BLOCKED_SOURCE_SYSTEMS` and `_BLOCKED_SOURCE_STRATEGY_PAIRS`.
4. Audit emission cadence to detect blocked-but-emitting strategies (the real bottleneck).
5. Inspect resolver labels (`TP_HIT` vs `WON`, `LOST` vs `SL_HIT`).
6. Phase 3 MC watchlist: no CRYPTO candidate flagged (none of EQUITY/FOREX MC winners are CRYPTO).

## Data sources
- `mysql.50webs.com:ejaguiar1_stocks.trading_picks` (live).
- `audit_trail/quality_gates.py` blocklist registries.
- `reports/money_ready_verdict_2026-05-17.json` (latest verdict snapshot).

## Output
`reports/peer_claude-phase10b-money-maker-crypto_result_2026-05-31.md`.
