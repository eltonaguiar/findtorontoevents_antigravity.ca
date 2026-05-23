# Research Summary: Academic Trading Strategies (Forex, Commodities, Futures, Stocks)

**Domain:** Systematic trading strategies from peer-reviewed academic papers (2020-2026)
**Researched:** 2026-03-21
**Overall confidence:** HIGH (strategies backed by major journals: JFE, JoF, Review of Finance, AQR)

## Executive Summary

This research surveyed 35 published academic trading strategies across forex, commodities, futures, and stocks. The focus was on strategies with reproducible rules, out-of-sample validation, and implementability with free data (yfinance, FRED, AQR datasets).

The strongest finding is that **cross-asset time-series momentum** (Sharpe 1.84) dominates all other published strategies. It combines bond-equity cross-predictions with standard trend-following across 58 futures. The second-tier strategies are the combined FX carry+momentum+value portfolio (Sharpe 0.95, proven over 200+ years) and AQR's Value and Momentum Everywhere (Sharpe 1.10, free data available).

Several widely-cited strategies have **decayed or failed** post-publication: traditional stock momentum returns dropped 50% since the mid-1990s, short interest alpha is eliminated by borrowing costs (Muravyev 2022), insider trading alpha occurs 70-80% before public disclosure, and VIX term structure strategies showed negative out-of-sample performance.

The recommended portfolio combines the top 4-6 strategies with expected portfolio Sharpe of ~1.20, using entirely free data sources.

## Key Findings

**Stack:** Python (yfinance, pandas, scipy, statsmodels) + FRED API + AQR datasets for factor replication
**Architecture:** Multi-strategy portfolio with vol-targeting position sizing, monthly rebalancing
**Critical pitfall:** Tail risk in short volatility strategies (VIX, options selling) can produce -800% losses. NEVER implement without crash protection.

## Implications for Roadmap

Based on research, suggested implementation phases:

1. **Phase 1: Core Trend-Following** - Implement TSMOM and cross-asset momentum
   - Addresses: Time-series momentum across 25-30 instruments
   - Avoids: Complexity of options-based strategies
   - Data: yfinance + FRED (free)
   - Expected Sharpe: 1.3-1.8

2. **Phase 2: FX Multi-Factor** - Implement combined carry+momentum+value
   - Addresses: Currency diversification
   - Requires: FRED interest rates, OECD PPP data
   - Expected Sharpe: 0.95

3. **Phase 3: Equity Factors** - Low-vol + intangible-adjusted value
   - Addresses: Equity exposure with downside protection
   - Data: yfinance + SEC EDGAR/SimFin for financials
   - Expected Sharpe: 0.80-0.86

4. **Phase 4: Commodity Double-Sort** - Momentum + term structure
   - Addresses: Commodity diversification
   - Requires: Multi-contract futures data (Quandl if budget allows)
   - Expected Sharpe: 0.96

5. **Phase 5: Event-Driven** - PEAD with enhanced multi-quarter SUE
   - Addresses: Alpha from earnings patterns
   - Requires: Analyst estimates data
   - Expected Sharpe: 0.80

**Phase ordering rationale:**
- Phase 1 first because it has the highest Sharpe and uses free data
- FX second because it provides uncorrelated returns to equity-heavy phases
- Equity factors third to add equity exposure with risk management
- Commodity and event-driven later as they need additional data sources

**Research flags for phases:**
- Phase 4: Needs deeper research on free commodity data alternatives
- Phase 5: PEAD declining - validate with recent data before full implementation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Cross-asset momentum | HIGH | AQR-backed, 40+ year backtest, live fund validation |
| FX multi-factor | HIGH | 200+ year evidence, multiple independent papers |
| Low-vol anomaly | HIGH | Outperforming in 2025, extensive literature |
| PEAD | MEDIUM | Declining magnitude, enhanced version needs validation |
| Insider/Congressional | LOW | Conflicting evidence, practical implementation issues |
| ESG momentum | LOW | Expensive data, OOS negative, mixed significance |

## Gaps to Address

- Free multi-contract commodity futures data (needed for term structure strategy)
- Real-time earnings surprise data (needed for PEAD implementation)
- Walk-forward backtesting framework for regime detection
- Transaction cost estimation for each strategy in current market conditions
