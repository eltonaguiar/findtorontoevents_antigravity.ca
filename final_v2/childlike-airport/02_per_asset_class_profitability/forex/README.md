# Forex — Profitability Assessment & Recommendation

**Date:** 2026-11-14 | **Status:** No validated edge; minimal coverage

## Current State (evidence)
- `data/live_picks.db`: FOREX 4 rows (stale ~172d). Overall system PnL/integrity issues apply.
- No forex-specific OOS-validated strategy in peer/Kilo results.

## Evidence of Edge
- **None validated here.** FX edges are typically thin and sensitive to costs, carry, and macro regimes.

## Recommendation
- **Primary (to build): FX Momentum/Trend** (time-series and/or cross-sectional) with strict risk controls.
- **Required safety:** wire/enable `fx_kill_switch.py` (or equivalent) for drawdown/vol/event halts; robust spread/slippage modeling.
- **Interim:** no profitability claim for existing FX picks.

## Implementation Notes
- Use liquid majors/crosses; model realistic spreads, rollover, and session effects.
- Regime/macro filters (volatility, risk-on/off) recommended; validate OOS across regimes.
- Gates: net-of-cost Sharpe/PF/MDD, PBO/DSR where applicable, sufficient trade count.
