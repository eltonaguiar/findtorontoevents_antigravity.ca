# Statistical Edge Analysis - 2026-05-16

## Summary
This report presents the statistical edge (expectancy) calculation for all asset classes with available data in the system. The analysis includes FOREX, MEMECOIN, CRYPTO, and PENNY_STOCK. Data for other asset classes (EQUITY, ETF, FUTURES, BOND, COMMODITY) is not available in the current dataset.

## Methodology
- Data sources: `bt_backtest_trades` and `at_signal_outcomes` tables
- Win/loss threshold: 0.1bp for CRYPTO, 5bp for non-CRYPTO assets
- Statistical edge formula: (win_rate * avg_win) - ((1-win_rate) * avg_loss)
- Sample size note: FOREX, MEMECOIN, and CRYPTO have sufficient data (≥30 trades) for statistical significance. PENNY_STOCK has insufficient data (5 trades) for reliable analysis.
- Results ordered by statistical edge (highest to lowest)

## Results

| asset_class | total_trades | win_rate_pct | avg_win_pct | avg_loss_pct | statistical_edge | sample_size |
|-------------|--------------|--------------|-------------|--------------|------------------|-------------|
| FOREX       | 50           | 90.00        | 0.7043      | 0.0992       | 0.6239           | sufficient    |
| MEMECOIN    | 51,711       | 46.75        | 13.5338     | 23.8713      | -6.3844          | sufficient    |
| CRYPTO      | 1,486,575    | 33.14        | 11.1665     | 26.7425      | -14.1813         | sufficient    |
| PENNY_STOCK | 5            | 0.00         | 0.0000      | 2.4000       | -2.4000          | insufficient  |

## Key Findings

### FOREX
- Strongest statistical edge: 0.6239
- Exceptionally high win rate: 90%
- Favorable risk-reward: avg win (0.7043%) is 7x larger than avg loss (0.0992%)
- Sample size: 50 trades (meets minimum threshold)

### MEMECOIN
- Negative statistical edge: -6.3844
- Slightly below 50% win rate: 46.75%
- Poor risk-reward: avg loss (23.8713%) is nearly 2x larger than avg win (13.5338%)
- Large sample size: 51,711 trades (highly statistically significant)

### CRYPTO
- Strongly negative statistical edge: -14.1813
- Low win rate: 33.14%
- Poor risk-reward: avg loss (26.7425%) is more than 2x larger than avg win (11.1665%)
- Very large sample size: 1.48M trades (extremely statistically significant)


### PENNY_STOCK
- Negative statistical edge: -2.4000
- 0% win rate based on 5 trades
- Very small sample size: 5 trades (insufficient for statistical significance)
- Results should be interpreted with extreme caution due to small sample size

## Missing Asset Classes
The following asset classes from the audit dashboard dropdown have no data in the current dataset:
- EQUITY (stocks)
- ETF
- FUTURES
- BOND
- COMMODITY

These asset classes show no activity in both backtest trades and signal outcomes tables, indicating the strategies may not be implemented or data is not being recorded.

## Conclusion
The FOREX strategy demonstrates a statistically significant edge with strong performance characteristics. In contrast, MEMECOIN and CRYPTO strategies show negative expectancy, indicating they are not profitable in their current form. PENNY_STOCK shows negative performance but with insufficient data for reliable analysis. The absence of data for EQUITY, ETF, FUTURES, BOND, and COMMODITY suggests these strategies are not active or not being tracked in the current system. The FOREX strategy appears to be the only one ready for real-money deployment based on these results.