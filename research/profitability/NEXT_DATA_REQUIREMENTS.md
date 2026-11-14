# Next Data Requirements — What Would Be Needed to Prove an Edge

**Status:** the keyless, daily/4h, price-only hypothesis space is exhausted. 23 candidates and the
peer VWAP claim all failed rigorous proof. This document lists the minimum new data and experiments
that could change that, with the gates they must pass.

## Why current data is insufficient

- Daily/4h OHLCV cannot test market-making, microstructure, or intrabar execution.
- Price-only ETF data omits dividends and fundamentals.
- Funding rates are available, but venue capital/margin and basis are not.
- No options data, so volatility-risk-premium and hedging strategies are untestable.
- No earnings/event dates, so event-driven drift is untestable.

## Priority datasets

| # | Dataset | Concrete source | What it enables | Effort |
|---|---|---|---|---|
| 1 | **1m/5m L2 order book + trades** | Binance/Coinbase historical archives; Tardis.dev | Market-making, microprice, order-flow imbalance | High (storage) |
| 2 | **Options surfaces + DVOL** | Deribit public API (instruments, DVOL), Amberdata/Tardis | Vol-risk premium, covered calls, delta-hedged carry | Medium |
| 3 | **Funding + basis + margin** | Binance/OKX/Bybit funding + mark/index + fee tiers | Capital-adjusted carry, cross-venue basis | Medium |
| 4 | **Earnings dates + estimates** | Nasdaq/Refinitiv/FMP | Post-earnings drift, surprise momentum | Medium |
| 5 | **FX policy rates + forwards** | BIS/central banks, Refinitiv | G10 carry, forward discount | Medium |
| 6 | **Adjusted total-return equities** | CRSP/Compustat or Polygon | Cross-sectional momentum/value/quality with dividends | Medium |

## Pre-registered experiments

1. **VWAP/microstructure (1m, L2):** rebuild the peer VWAP test with intrabar stops, 100% gross cap,
   proper annualization, CSCV PBO, true DSR, and a clean forward window.
2. **Options vol-risk premium:** short delta-hedged ATM straddles / covered calls on BTC/ETH; model
   gamma, theta, fees, and margin. Gate on tail risk and drawdown, not just Sharpe.
3. **Capital-adjusted funding/basis:** cross-venue long spot/short perp with actual fee tiers,
   margin, and transfer costs; report return on capital, not notional.
4. **Earnings drift:** event-window CAR with point-in-time earnings dates and costs.
5. **FX carry:** G10 long high-yielder/short low-yielder with forwards and policy rates.

## Gates any new candidate must pass

- Clean forward or truly unseen OOS; no post-hoc regime filtering.
- Correct annualization: `sqrt(periods_per_year)` from bar frequency, never from trade count.
- Intrabar stops and gap handling; conservative same-bar stop-first assumption.
- Concurrent capital model with gross exposure cap; return on capital, not notional.
- True Deflated Sharpe (N = all trials), CSCV PBO, and a stationary-bootstrap Reality Check.
- 2× cost and one-period execution lag must still pass.
- Independent replication + adversarial review before any "PROVED" claim.

## What would NOT count

- Another parameter sweep on the same 730-day window.
- A higher reported Sharpe from annualizing per-trade returns.
- Dropping losing symbols after seeing OOS.
- Post-hoc regime filters applied to an unfiltered trade list.
- "PBO < 0.5" from a bootstrap p-value that is ~0.5 by construction.

## Honest expectation

Even with these datasets, most candidates will fail. The documented edges that survive in literature
(TSMOM, XS momentum, carry, vol-risk premium) are small, capacity-limited, and regime-dependent.
Proof requires clean forward data, realistic capital, and correction for every trial — not a higher
backtest Sharpe.
