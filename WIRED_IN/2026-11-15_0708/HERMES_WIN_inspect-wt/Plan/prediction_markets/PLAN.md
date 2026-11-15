# PLAN — Prediction Markets (Kalshi / Polymarket)

**Status:** Structurally blocked. **Gap filled:** F10 (copy-trading produced no winners).

## Hypothesis
There is **no** retail-accessible copy-trading edge in Kalshi/Polymarket. Any profitable approach must be a *maker* strategy with inventory management, not follower/copy trading.

## Why copy-trading fails (structural, not implementation)
1. **Zero-sum:** every dollar won is a dollar lost by another participant, minus fees. Copying a winner means paying up after their price impact.
2. **Adverse selection:** when a sharp trader fills, the counterparty is usually informed; followers receive the leftover, negative-expectancy side.
3. **Maker-taker fees:** Polymarket/Kalshi charge on fill; high-frequency copying is fee-dominated.
4. **Size mismatch:** a whale's edge may exist at $50k depth; a $500 copy sits at a worse price and moves less.
5. **Latency:** leaderboard data lags fills; by the time a position is public, the edge is consumed.

## The only testable alternative
A **market-making / liquidity-provision** model: quote both sides on high-volume recurring markets (weather, sports, econ releases), harvest spread, manage inventory risk. This is a *business* (capital + infrastructure + risk desk), not a signal.

## Proof tests (if attempted)
1. ✅ Temporal (2019-2024 train / 2025-2026 test)
2. ✅ WFO on quote parameters
3. ✅ Multiple testing (1 config)
4. ✅ Monte Carlo (inventory paths)
5. ✅ Friction (maker rebate, settlement, gas on-chain)
6. ✅ Significance (net spread after adverse selection)
7. ✅ Regime (event-dense vs quiet)
8. ✅ Shuffle control (random quotes must not profit)
9. ✅ Forward (paper market-making 6 months)
10. ✅ Reproducibility

## Expected outcome
Honest verdict likely: **no deployable retail edge**. Recommendation is to stop allocating research effort here and redirect to maker-infrastructure only if the team has operational capacity. Document the negative result and move on.
