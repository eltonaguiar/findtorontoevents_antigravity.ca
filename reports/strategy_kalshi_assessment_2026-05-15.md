# Kalshi Signals Assessment — 2026-05-15

**Status:** Exists | Very Low Integration

## Current State
- `alpha_engine/kalshi_signals.py` exists.
- Referenced lightly in `score_booster.py`.
- Part of the broader `prediction_market_agents/` framework.

## Key Issues
- Extremely low production volume.
- Almost never appears as a primary source for emitted picks.
- Kalshi (event contracts) has excellent resolution quality and lower noise than many crypto sources, but it is barely used.

## 90-Day Recommendation
- **P0**: Build a dedicated Kalshi event-contract scanner focused on high-liquidity political, economic, and weather markets.
- **P1**: Wire Kalshi signals into the non-crypto quality gates with high trust when resolution is binary and timely.
- **P2**: Use Kalshi as a strong orthogonal signal to traditional price-based strategies (especially for EQUITY and COMMODITY macro bets).

**Verdict**: One of the most under-used high-quality data sources in the entire stack. Fixing this is high-leverage for improving win rates with relatively clean, resolvable outcomes.