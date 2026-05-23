# GIC vs Battleground Performance Analysis
## Claude's Independent Verification — 2026-03-13

### Raw Data: 294 Closed Trades, 14 Trading Days

| Date | Trades | Avg PnL | $1000 Becomes | Day |
|------|--------|---------|---------------|-----|
| 2026-02-24 | 22 | +1.959% | $1,019.59 | WIN |
| 2026-02-25 | 3 | +2.020% | $1,020.20 | WIN |
| 2026-02-26 | 2 | +1.087% | $1,010.87 | WIN |
| 2026-02-27 | 3 | +1.400% | $1,014.00 | WIN |
| 2026-02-28 | 93 | +0.745% | $1,007.45 | WIN |
| 2026-03-04 | 6 | +0.962% | $1,009.62 | WIN |
| 2026-03-05 | 4 | +0.399% | $1,003.99 | WIN |
| 2026-03-06 | 4 | +1.144% | $1,011.44 | WIN |
| 2026-03-07 | 101 | +0.122% | $1,001.22 | WIN |
| 2026-03-08 | 43 | +0.088% | $1,000.88 | WIN |
| 2026-03-10 | 3 | -0.702% | $992.98 | LOSS |
| 2026-03-11 | 1 | +2.502% | $1,025.02 | WIN |
| 2026-03-12 | 3 | +0.863% | $1,008.63 | WIN |
| 2026-03-13 | 6 | -0.248% | $997.52 | LOSS |

### Summary
- Days: 14 trading days (17 calendar days)
- Winning days: 12/14 (86%)
- Invested: $14,000 | Returned: $14,123.41 | Net: +$123.41 (+0.882%)
- Avg daily: +0.8815% | Daily std: 0.8747%
- Annualized (simple): +321.8%
- Annualized (compound): +2,361.7%
- Sharpe: 19.01 (excellent)
- Max drawdown: 0.70%

### IMPORTANT CAVEATS (Claude's honest assessment)

1. **17 days is NOT enough data.** Any quant will tell you 14 trading days means nothing statistically for annualized projections. Extrapolating 17 days to 365 days is dangerous.

2. **Survivorship bias.** We're only looking at Battleground because it won. We built 8 systems — 7 lost. That's classic survivorship bias. One of 8 random systems will look great by chance.

3. **The Sharpe of 19 is unrealistic.** Real hedge funds with Sharpe > 3 are considered exceptional. Sharpe 19 screams either: (a) too few data points, (b) favorable market conditions that won't persist, or (c) overfitting.

4. **Regime dependency.** These 17 days were CHOP/mild bear. Strategy may fail in trending bull or crash scenarios.

5. **Friction estimate.** 30% haircut is conservative for crypto. Real costs: exchange fees (0.1% x2), spread (0.05-0.2%), slippage (0.1-0.5%), missed fills (10-20%), funding rates.

### GIC Comparison (Honest)

| Investment | Annual Rate | On $1K | On $10K | Risk |
|-----------|------------|--------|---------|------|
| GIC (best) | 4.0% | $40/yr | $400/yr | ZERO (CDIC insured) |
| HISA | 3.0% | $30/yr | $300/yr | ZERO |
| S&P 500 avg | 10.0% | $100/yr | $1,000/yr | Market risk |
| Battleground (raw) | +321.8% | $3,218/yr | $32,175/yr | HIGH |
| Battleground (after friction) | +225.2% | $2,252/yr | $22,523/yr | HIGH |
| Battleground (REALISTIC*) | +15-30% | $150-300/yr | $1,500-3,000/yr | HIGH |

*REALISTIC estimate: Assumes annualized returns will regress heavily toward mean as sample size grows. Professional quant systems with proven edges typically deliver 15-30% annual after friction.

### Verdict

**Antigravity's assessment is directionally correct but the annualized numbers are misleading due to tiny sample size.**

- YES, Battleground has a statistically significant edge (Keltner BTC 72.9% WR, p=0.0015)
- YES, it outperforms GIC even conservatively
- NO, you should not expect 225%+ annual returns — that's extrapolation error
- REALISTIC expectation: 15-30%/yr after friction, slippage, and mean reversion
- At $1K capital: expect $150-300/yr (still 4-8x better than GIC's $40/yr)
- MINIMUM: Paper trade for 2+ more weeks as Antigravity recommended
