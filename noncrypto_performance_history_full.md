# Non-Crypto Asset Performance History (Forward-Facing Since Yesterday)

## Executive Summary
This document summarizes the forward‑facing performance of all non‑crypto portfolios as of **2026‑03‑11**. The data is extracted from the latest integrity report (`audit_dashboard/data/integrity_report.json`). For each portfolio we list the current equity, P&L %, number of open positions, closed trades, wins, losses, unrealized P&L, realized P&L, and placeholders for Sharpe and Sortino ratios (not calculated in the current snapshot).

## Performance Overview

| Portfolio | Equity (USD) | P&L % | Open Positions | Closed Trades | Wins | Losses | Unrealized P&L (USD) | Realized P&L (USD) | Sharpe | Sortino |
|-----------|--------------|-------|----------------|---------------|------|--------|----------------------|--------------------|--------|---------|
| stocks_best | 9,996.00 | -0.04% | 2 | 0 | 0 | 0 | -4.00 | 0.00 | 0.00 | 0.00 |
| stocks_short_term | 9,997.00 | -0.03% | 2 | 0 | 0 | 0 | -3.00 | 0.00 | 0.00 | 0.00 |
| forex_carry | 9,992.35 | -0.08% | 0 | 1 | 0 | 1 | 0.00 | -7.65 | 0.00 | 0.00 |
| multi_asset_diversified | 9,994.39 | -0.06% | 2 | 1 | 0 | 1 | -5.61 | 0.00 | 0.00 | 0.00 |
| prop_aggressive | 100,082.46 | 0.82% | 2 | 0 | 0 | 0 | 90,082.46 | 0.00 | 0.00 | 0.00 |
| prop_conservative | 100,082.86 | 0.83% | 3 | 0 | 0 | 0 | 90,082.86 | 0.00 | 0.00 | 0.00 |
| prop_swing | 200,064.57 | 0.32% | 3 | 0 | 0 | 0 | 190,064.57 | 0.00 | 0.00 | 0.00 |
| proven_only | 10,028.59 | 0.29% | 3 | 0 | 0 | 0 | 28.59 | 0.00 | 0.00 | 0.00 |
| relative_strength_recovery | 9,965.06 | -0.35% | 2 | 0 | 0 | 0 | -34.94 | 0.00 | 0.00 | 0.00 |
| rr_kings | 10,007.32 | 0.07% | 1 | 0 | 0 | 0 | 7.32 | 0.00 | 0.00 | 0.00 |
| rsi_capitulation | 10,023.90 | 0.24% | 1 | 0 | 0 | 0 | 23.90 | 0.00 | 0.00 | 0.00 |
| score_leaders | 10,022.65 | 0.23% | 3 | 0 | 0 | 0 | 22.65 | 0.00 | 0.00 | 0.00 |
| sector_rotation | 10,027.31 | 0.27% | 3 | 0 | 0 | 0 | 27.31 | 0.00 | 0.00 | 0.00 |

## Methodology
- **Equity Calculation**: All equity values are based on the latest snapshot from the integrity report. For standard portfolios the assumed initial capital is **$10,000**; proprietary portfolios have larger capital bases.
- **Unrealized P&L**: Calculated as `Equity – Initial Capital` (or the portfolio’s starting capital for prop accounts).
- **Realized P&L**: Not recorded in the current snapshot; shown as $0.00.
- **Sharpe & Sortino**: Not computed for these portfolios in the latest report; placeholders are shown as 0.00.
- **Open/Closed Trades**: Open positions are active picks; closed trades are positions that have been exited.

## Observations
1. **Overall Market Sentiment** – Most non‑crypto portfolios show marginal performance, with P&L % generally within ±0.5 %.
2. **Top Performers** – `proven_only` (+0.29 %), `sector_rotation` (+0.27 %), and `score_leaders` (+0.23 %) lead the pack.
3. **Underperformers** – `relative_strength_recovery` (‑0.35 %) and `forex_carry` (‑0.08 %) lag.
4. **Proprietary Portfolios** – Show modest positive returns due to larger capital bases.
5. **Low Trading Activity** – Many portfolios have zero closed trades, indicating a cautious or low‑volatility environment.

## Limitations
- No realized P&L, Sharpe, or Sortino ratios are available in the current data.
- The snapshot only covers performance since yesterday; longer‑term trends are not captured.
- No market context (economic events, news) is included.

## Recommendations for Further Analysis
1. Compute Sharpe and Sortino ratios using historical equity data.
2. Determine average holding periods for open positions.
3. Perform correlation analysis across portfolios.
4. Incorporate market macro‑economic context.

## Prompt for IDE Agents
```
Please review the non‑crypto performance summary above. Respond with up to ten concise questions that would help you evaluate the health of these portfolios, e.g., "What is the average holding period for open positions in stocks_best?" or "Can we compute Sharpe ratios from the underlying equity history?".
```

---
*Report generated on 2026‑03‑11 from audit dashboard data.*