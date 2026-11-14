# Commodities — Profitability Assessment & Recommendation

**Date:** 2026-11-14 | **Status:** No validated edge; known P/L/data defect

## Current State (evidence)
- `data/live_picks.db`: COMMODITY 5 rows (stale). Audit context flags **~98.4% futures zero-P/L bug** / unresolved pricing in parts of the universe (commodity/futures handling unreliable).
- No OOS-validated commodity strategy in peer/Kilo results.

## Evidence of Edge
- **None validated.** Trend-following is the canonical commodity approach but unproven in this system as-is.

## Recommendation
- **Primary (to build/fix): Commodity Trend Following** (e.g. breakout or SMA/TSMOM on liquid futures/ETFs) with proper contract/roll handling.
- **Prerequisite:** **fix futures/commodity zero-P/L and pricing/resolution bug** (98.4% zero-P/L symptom) so backtests and live marks are trustworthy.

## Implementation Notes
- Use continuous/adjusted series or explicit roll logic; model margin, carry, and slippage.
- Diversify across sectors (energy, metals, ags) to reduce single-market regime risk.
- Validate OOS across regimes; enforce MDD and vol-targeting; require clean PnL accounting before any profitability claim.
