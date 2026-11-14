# Bonds — Profitability Assessment & Recommendation

**Date:** 2026-11-14 | **Status:** No validated edge; data coverage minimal

## Current State (evidence)
- `data/live_picks.db`: BOND 2 rows (stale ~172d). `alpha_engine/data/active_picks_bond.json` (6 picks) not synced to DB — source-of-truth fragmentation.
- No bond-specific OOS validation in peer/Kilo results.

## Evidence of Edge
- **None validated.** Bond returns are regime/rate-sensitive; naive carry/trend without duration/rate controls is risky.

## Recommendation
- **Primary (to build): Vol-Targeted Bond Trend** (e.g. duration-managed trend on liquid bond ETFs like TLT/IEF/SHY or futures proxies) with:
  - Vol targeting and drawdown caps, rate/regime awareness.
  - Daily data backtest with long history, transaction/carry modeling.
- **Interim:** do not claim profitability; treat existing bond picks as unvalidated.

## Implementation Notes
- Sync `active_picks_bond.json` into canonical store; tag asset_class correctly.
- Backtest across rising/falling-rate regimes; validate OOS and stress for rate shocks.
- Target gates: Sharpe≥1.0, PF≥1.3–1.5, MDD<15–20%, robust across regimes.
