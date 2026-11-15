# Asset-Class Profitability Plans

## Shared Rules for All Classes
1. Measurement integrity first (recompute PnL vs real prices, full costs).
2. Pre-register the test and the success criteria.
3. Must beat the relevant buy-and-hold benchmark after costs on clean OOS / forward data.
4. Promotion gates remain off until thresholds are met.
5. Parallel track: low-cost diversified ETF/MF allocation as the actual capital deployment vehicle.

## EQUITY (Priority 1)
- Goal: demonstrate positive information ratio vs SPY total return.
- Approaches: dual momentum, quality + momentum, simple factor portfolios, regime-filtered mean reversion on liquid names.
- Test: large universe or S&P 500 constituents, multi-year, walk-forward. n ≥ 500 independent observations preferred.
- Success: excess return > 0, IR ≥ 0.3–0.5, PF ≥ 1.15 after costs, max DD controlled.
- Why highest priority: only class with a clear transparent benchmark and some prior positive cost-margin signals.

## MUTUAL FUNDS / BROAD ETFs (Highest probability of positive real returns, lowest risk)
- Goal: capture equity risk premium and bond yields at minimal cost.
- Approach: rules-based selection of low-ER, high-AUM funds + simple allocation (e.g., 60/40 or risk-parity lite) with periodic rebalance.
- This is not "prediction." It is cost and diversification discipline.
- Expected outcome: positive real returns over 10+ years with high probability; will not consistently beat the market by large margins after costs (by construction for pure index).
- Infrastructure: build NAV cache, metadata, and ranking if you want to select among active funds; otherwise just hold VTI/VXUS/BND equivalents.

## CRYPTO (Conditional Priority 2)
- Fix fill bugs first.
- Test only trend and carry ideas that have economic rationale and survived prior filters.
- Hard requirement: must beat BTC buy-and-hold after costs on forward data (n ≥ 100).
- High volatility means position sizing must be small.

## COMMODITY / FUTURES
- Classic time-series momentum (CTA) and carry have the strongest historical practitioner and academic records among active strategies.
- Test with realistic roll costs.
- Low-frequency versions preferred.

## ETF (Tactical)
- Treat similarly to equity. Sparse current coverage is a data problem, not a reason to ignore.
- Simple dual-momentum or relative-strength across major ETFs (SPY, QQQ, IWM, EFA, etc.) is a well-known approach.

## BOND
- Mostly beta (yield) + duration risk. Active timing is hard.
- Useful as ballast in a portfolio, not as a high-alpha source for this system.

## FOREX
- Lowest priority. Most strategies fail after realistic spreads. Mutation or kill unless a clean large-n test clears gates.

## PREDICTION MARKETS
- Zero-sum (minus fees). Professional/bot dominance is structural.
- Do not expect durable retail edge from copy-trading.
