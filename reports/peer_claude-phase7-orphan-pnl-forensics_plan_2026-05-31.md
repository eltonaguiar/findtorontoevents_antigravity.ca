# Plan — Phase 7 forensics: 293 NULL pnl_pct rows

## Goal
Diagnose why 293 closed `trading_picks` rows still have NULL `pnl_pct` after Phase 6
backfilled 347. Categorize by recoverability and recommend backfill vs. exclude.

## Method
- Live count verify (read-only) on `ejaguiar1_stocks.trading_picks`.
- Split by `exit_price` presence (recoverable vs unrecoverable).
- Group by `source_system`, `strategy`, `category`, `status`, `exit_reason`.
- Age distribution via `DATEDIFF(NOW(), closed_at)`.
- Math sanity check: recompute pnl_pct from entry/exit/direction for rows that have both.
- Symbol/category check for re-fetch feasibility (Binance vs yfinance).

## Deliverable
`reports/peer_claude-phase7-orphan-pnl-forensics_result_2026-05-31.md`
plus a docs-only PR with the recommendation.
