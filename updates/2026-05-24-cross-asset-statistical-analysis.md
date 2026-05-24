# Cross-Asset Pick Statistical Analysis
**Date:** 2026-05-24 | **AUM:** $100,000 | **Analyst:** Quant Desk

---

## 1. Methodology & Assumptions

### WR Estimation for Picks Without Track Record (n < 20)
Picks lacking explicit WR are assigned an estimated WR derived from the stated confidence level using a simple linear mapping:

```
WR_est = 0.50 + (conf% - 0.50) × 0.25
```

| Confidence | Implied WR |
|-----------|-----------|
| 80% | 57.5% |
| 50% | 50.0% |
| 30% | 45.0% |
| none | 50.0% (coin flip) |

Picks with verified WR: **PG (64%)**, **SOLUSDT (65%)** — these are the only two with n >= 20.
Picks with WR=0% (Penny, Futures): flagged as **unreliable** — no track record, no RR given.

### EV Computation
```
EV (risk units) = WR × RR − (1 − WR)
EV% = EV × 0.01          (assuming 1% of position risked per trade)
```

### Sharpe Estimation
```
Daily Sharpe = EV% / daily_vol_estimate
Annual Sharpe ≈ Daily Sharpe × √252
```

Daily volatility assumptions per asset class:
- EQUITY: 1.2% | CRYPTO: 3.0% | ETF: 1.0% | COMMODITY: 1.5% | BOND: 0.5%

### Kelly Criterion
```
Kelly f* = EV / RR    (fraction of bankroll for single uncorrelated bet)
Half-Kelly = f* / 2   (conservative sizing for multi-pick portfolio)
```

---

## 2. Individual Pick Analysis

### EQUITY

| # | Pick | Dir | Entry | WR | RR | EV(R) | EV% | Daily Sharpe | Ann. Sharpe | Kelly f* | Half-Kelly | Status |
|---|------|-----|-------|----|----|-------|------|-------------|------------|----------|------------|--------|
| 1 | **WMT** | SHORT | $140.19 | 57.5%* | 2.1 | 0.783 | 0.78% | 0.652 | **10.35** | 37.3% | 18.6% | est. WR |
| 2 | **PG** | SHORT | $167.37 | **64.0%** | 1.5 | 0.600 | 0.60% | 0.500 | **7.94** | 40.0% | 20.0% | **VERIFIED** |
| 3 | GOOGL | LONG | $186.63 | 45.0%* | 2.5 | 0.575 | 0.58% | 0.479 | **7.60** | 23.0% | 11.5% | est. WR |
| 4 | META | LONG | $620.71 | 50.0%* | 1.7 | 0.350 | 0.35% | 0.292 | 4.63 | 20.6% | 10.3% | est. WR |

*WR estimated from confidence level (n < 20)

### CRYPTO

| # | Pick | Dir | Entry | WR | RR | EV(R) | EV% | Daily Sharpe | Ann. Sharpe | Kelly f* | Half-Kelly | Status |
|---|------|-----|-------|----|----|-------|------|-------------|------------|----------|------------|--------|
| 1 | **SOLUSDT** | LONG | $157.39 | **65.0%** | 2.1 | 1.015 | 1.02% | 0.338 | **5.37** | 48.3% | 24.2% | **VERIFIED** |
| 2 | ETHUSDT | SHORT | $2,150.54 | 50.0%* | 1.7 | 0.350 | 0.35% | 0.117 | 1.85 | 20.6% | 10.3% | est. WR |
| 3 | BTCUSDT | SHORT | $78,626 | 45.0%* | 1.9 | 0.305 | 0.31% | 0.102 | 1.61 | 16.1% | 8.0% | est. WR |

*WR estimated from confidence level (n < 20)

### ETF

| # | Pick | Dir | Entry | WR | RR | EV(R) | EV% | Daily Sharpe | Ann. Sharpe | Kelly f* | Half-Kelly | Status |
|---|------|-----|-------|----|----|-------|------|-------------|------------|----------|------------|--------|
| 1 | **SPY** | SHORT | $726.80 | 57.5%* | 1.9 | 0.668 | 0.67% | 0.668 | **10.59** | 35.1% | 17.6% | est. WR |
| 2 | GLD | LONG | $257.93 | 57.5%* | 1.2 | 0.265 | 0.27% | 0.265 | 4.20 | 22.1% | 11.0% | est. WR |
| 3 | XLE | SHORT | $91.74 | 50.0%* | 1.4 | 0.200 | 0.20% | 0.200 | 3.17 | 14.3% | 7.1% | est. WR |

*WR estimated from confidence level (n < 20)

### BOND (notable: low daily vol inflates Sharpe)

| # | Pick | Dir | Entry | WR | RR | EV(R) | EV% | Daily Sharpe | Ann. Sharpe | Kelly f* | Half-Kelly | Status |
|---|------|-----|-------|----|----|-------|------|-------------|------------|----------|------------|--------|
| 1 | **TLT** | LONG | $87.66 | 57.5%* | 1.8 | 0.610 | 0.61% | 1.220 | **19.36** | 33.9% | 16.9% | est. WR |
| 2 | **BND** | LONG | $71.47 | 45.0%* | 2.4 | 0.530 | 0.53% | 1.060 | **16.82** | 22.1% | 11.0% | est. WR |
| 3 | **SHY** | SHORT | $82.36 | 57.5%* | 1.6 | 0.495 | 0.50% | 0.990 | **15.71** | 30.9% | 15.5% | est. WR |

*WR estimated from confidence level (n < 20)

### COMMODITY

| # | Pick | Dir | Entry | WR | RR | EV(R) | EV% | Daily Sharpe | Ann. Sharpe | Kelly f* | Half-Kelly | Status |
|---|------|-----|-------|----|----|-------|------|-------------|------------|----------|------------|--------|
| 1 | SI=F | SHORT | $34.93 | 50.0%* | 1.4 | 0.200 | 0.20% | 0.133 | 2.12 | 14.3% | 7.1% | est. WR |
| 2 | CL=F | SHORT | $68.25 | 50.0%* | 1.1 | 0.050 | 0.05% | 0.033 | 0.53 | 4.5% | 2.3% | est. WR |

*WR estimated (no confidence data available)

### PENNY STOCKS -- ALL FLAGGED UNRELIABLE

| # | Pick | Dir | Entry | WR | RR | EV | Status |
|---|------|-----|-------|----|----|----|--------|
| 1 | MVST | LONG | $1.80 | 0% | ? | N/A | **SKIP** - no track record, no RR |
| 2 | KULR | LONG | $2.20 | 0% | ? | N/A | **SKIP** - no track record, no RR |
| 3 | QBTS | LONG | $1.50 | 0% | ? | N/A | **SKIP** - no track record, no RR |

### FUTURES -- ALL FLAGGED UNRELIABLE

| # | Pick | Dir | Entry | WR | RR | EV | Status |
|---|------|-----|-------|----|----|----|--------|
| 1 | ES=F | LONG | 5600 | 0% | ? | N/A | **SKIP** - no track record, no RR |
| 2 | GC=F | LONG | 2500 | 0% | ? | N/A | **SKIP** - no track record, no RR |
| 3 | CL=F | SHORT | 73 | 0% | ? | N/A | **SKIP** - no track record, no RR |

---

## 3. Correlation Matrix & Cluster Flags

### High-Correlation Clusters (DANGER: concentrated directional bets)

| Cluster | Picks | Correlation Est. | Risk |
|---------|-------|-----------------|------|
| **Equity Short Cluster** | SPY SHORT + XLE SHORT + WMT SHORT + PG SHORT | 0.6-0.8 | 4 picks all short equities — massive directional overlap |
| **Bond Long Cluster** | TLT LONG + BND LONG | 0.5-0.7 | Both duration-sensitive bond longs — redundant |
| **Crypto Short Cluster** | ETHUSDT SHORT + BTCUSDT SHORT | 0.7-0.8 | Beta-driven correlated crypto shorts |
| **Gold Duplication** | GLD LONG vs GC=F LONG | ~0.95 | Same underlying — pick one |
| **Oil Duplication** | CL=F SHORT (comm) vs CL=F SHORT (futures) | 1.00 | **EXACT SAME INSTRUMENT listed twice** at different prices ($68.25 vs $73) |

### Negative Correlation Pairs (natural hedges)

| Pair | Correlation | Note |
|------|------------|------|
| META LONG vs SPY SHORT | -0.4 to -0.6 | Long tech vs broad market short — partial offset |
| SOLUSDT LONG vs ETHUSDT/BTCUSDT SHORT | -0.5 to -0.7 | Long one crypto, short the others — messy |
| SHY SHORT vs TLT LONG | -0.3 to -0.5 | Short 1-3yr vs long 20yr Treasuries — curve steepener |
| GLD LONG vs SPY SHORT | -0.1 to -0.4 | Gold/equity inverse relationship — diversification |

### Cluster Recommendations
1. **Equity shorts**: Pick the best 2 (WMT + SPY), drop PG and XLE for diversification
2. **Bond longs**: Drop BND (lower Sharpe, lower conf), keep only TLT
3. **Crypto shorts**: Drop both ETHUSDT and BTCUSDT (low risk-adjusted, estimated WR); keep SOLUSDT LONG as sole crypto exposure
4. **CL=F duplication**: Keep commodity entry at $68.25 (has RR=1.1), drop futures entry

---

## 4. Portfolio Optimization

### Constraints
- Max 2 picks per asset class
- Max 10 total positions
- $100,000 AUM
- Method: Simple Risk Parity (weight ∝ 1/volatility)

### Risk Parity Weight Factors

| Class | Daily Vol | Factor (1/vol) |
|-------|----------|----------------|
| BOND | 0.5% | 2.000 |
| ETF | 1.0% | 1.000 |
| EQUITY | 1.2% | 0.833 |
| COMMODITY | 1.5% | 0.667 |
| CRYPTO | 3.0% | 0.333 |

### Top Picks by Sharpe (within class, max 2/class)

| Rank | Pick | Class | Ann. Sharpe | EV(R) | Direction | Include? |
|------|------|-------|------------|-------|-----------|----------|
| 1 | TLT LONG | BOND | 19.36 | 0.610 | LONG | YES |
| 2 | BND LONG | BOND | 16.82 | 0.530 | LONG | YES (but correlated w/TLT) |
| 3 | SPY SHORT | ETF | 10.59 | 0.668 | SHORT | YES |
| 4 | WMT SHORT | EQUITY | 10.35 | 0.783 | SHORT | YES |
| 5 | PG SHORT | EQUITY | 7.94 | 0.600 | SHORT | YES (verified WR) |
| 6 | GOOGL LONG | EQUITY | 7.60 | 0.575 | LONG | NO - class limit |
| 7 | SOLUSDT LONG | CRYPTO | 5.37 | 1.015 | LONG | YES (verified WR) |
| 8 | META LONG | EQUITY | 4.63 | 0.350 | LONG | NO - class limit |
| 9 | GLD LONG | ETF | 4.20 | 0.265 | LONG | YES |
| 10 | XLE SHORT | ETF | 3.17 | 0.200 | SHORT | NO - class limit |
| 11 | SI=F SHORT | COMM | 2.12 | 0.200 | SHORT | YES |
| 12 | ETHUSDT SHORT | CRYPTO | 1.85 | 0.350 | SHORT | YES |
| 13 | BTCUSDT SHORT | CRYPTO | 1.61 | 0.305 | SHORT | NO - class limit |
| 14 | CL=F SHORT | COMM | 0.53 | 0.050 | SHORT | NO - near-zero EV |

### Recommended 10-Position Portfolio (Risk Parity Weights)

| # | Pick | Class | Direction | Ann. Sharpe | Risk Parity Weight | $ Allocation |
|---|------|-------|-----------|------------|-------------------|-------------|
| 1 | TLT LONG | BOND | LONG | 19.36 | 20.7% | $20,690 |
| 2 | BND LONG | BOND | LONG | 16.82 | 20.7% | $20,690 |
| 3 | SPY SHORT | ETF | SHORT | 10.59 | 10.3% | $10,345 |
| 4 | GLD LONG | ETF | LONG | 4.20 | 10.3% | $10,345 |
| 5 | WMT SHORT | EQUITY | SHORT | 10.35 | 8.6% | $8,621 |
| 6 | PG SHORT | EQUITY | SHORT | 7.94 | 8.6% | $8,621 |
| 7 | SI=F SHORT | COMM | SHORT | 2.12 | 6.9% | $6,897 |
| 8 | CL=F SHORT | COMM | SHORT | 0.53 | 6.9% | $6,897 |
| 9 | SOLUSDT LONG | CRYPTO | LONG | 5.37 | 3.4% | $3,448 |
| 10 | ETHUSDT SHORT | CRYPTO | SHORT | 1.85 | 3.4% | $3,448 |

**Total: $100,002** (rounding)

### CRITICAL ISSUES WITH THIS PORTFOLIO

1. **Bond concentration**: TLT + BND = 41.4% of AUM, highly correlated (~0.6). A rate shock hits both simultaneously.
2. **Equity short concentration**: SPY + WMT + PG = 3 short-equity bets (27.5% AUM) with high correlation.
3. **CL=F SHORT at $6,897**: Near-zero EV (0.05 risk units), waste of capital.
4. **ETHUSDT SHORT**: Low Sharpe (1.85), estimated WR, conflicts directionally with SOLUSDT (crypto long + short together = messy).

### ADJUSTED PORTFOLIO (Correlation-Aware, 8 Positions)

| # | Pick | Class | Direction | Adjusted Weight | $ Allocation | Rationale |
|---|------|-------|-----------|----------------|-------------|-----------|
| 1 | TLT LONG | BOND | LONG | 20.0% | $20,000 | Best Sharpe in universe |
| 2 | SHY SHORT | BOND | SHORT | 15.0% | $15,000 | Replaces BND; negatively correlated with TLT (curve steepener) |
| 3 | SPY SHORT | ETF | SHORT | 15.0% | $15,000 | Best equity-short proxy |
| 4 | GLD LONG | ETF | LONG | 12.0% | $12,000 | Diversifier vs equity shorts |
| 5 | WMT SHORT | EQUITY | SHORT | 12.0% | $12,000 | Strong EV (0.783), 80% conf |
| 6 | PG SHORT | EQUITY | SHORT | 12.0% | $12,000 | Verified WR=64%, solid |
| 7 | SOLUSDT LONG | CRYPTO | LONG | 8.0% | $8,000 | Verified WR=65%, highest raw EV |
| 8 | SI=F SHORT | COMM | SHORT | 6.0% | $6,000 | Only viable commodity (CL=F dropped) |

**Total: $100,000** | **Net directional exposure**: Short bias (SPY+WMT+PG+SHY+SI=F = 5 shorts vs TLT+GLD+SOL = 3 longs) — defensively positioned for drawdown.

---

## 5. Final Rankings

### TOP 3 RISK-ADJUSTED PICKS

| Rank | Pick | Class | Ann. Sharpe | EV(R) | WR Status | Key Strength |
|------|------|-------|------------|-------|-----------|-------------|
| **1** | **TLT LONG** | BOND | 19.36 | 0.610 | est. (80% conf) | Low bond vol magnifies Sharpe; strong RR(1.8) |
| **2** | **SPY SHORT** | ETF | 10.59 | 0.668 | est. (80% conf) | Diversified equity short; broad market hedge |
| **3** | **WMT SHORT** | EQUITY | 10.35 | 0.783 | est. (80% conf) | Highest equity EV; consumer staples short |

### TOP 3 BY VERIFIED WR (n >= 20, most reliable)

| Rank | Pick | Class | Ann. Sharpe | EV(R) | WR |
|------|------|-------|------------|-------|-----|
| 1 | **PG SHORT** | EQUITY | 7.94 | 0.600 | 64% |
| 2 | **SOLUSDT LONG** | CRYPTO | 5.37 | 1.015 | 65% |

Only two picks have verified track records. PG and SOLUSDT are the **anchor positions** — all others are speculative.

### WORST 3 RISK-ADJUSTED PICKS

| Rank | Pick | Class | Ann. Sharpe | EV(R) | WR Status | Why Bad |
|------|------|-------|------------|-------|-----------|---------|
| **21** | CL=F SHORT | COMM | 0.53 | 0.050 | est. (50% WR) | Near-zero EV; even if WR=55%, EV barely positive |
| **20** | BTCUSDT SHORT | CRYPTO | 1.61 | 0.305 | est. (30% conf) | Low conviction (equiv to 45% WR); high crypto vol kills Sharpe |
| **19** | ETHUSDT SHORT | CRYPTO | 1.85 | 0.350 | est. (no conf) | Coin-flip WR assumption; no edge demonstrated |

---

## 6. Key Findings & Recommendations

### Immediate Actions

1. **Drop all PENNY (MVST, KULR, QBTS) and FUTURES (ES=F, GC=F, CL=F) picks.** WR=0% with no RR data means these are pure gambles — no statistical basis for inclusion.

2. **Resolve CL=F duplication.** The same instrument is shorted twice at different prices ($68.25 commodity, $73 futures). The commodity entry has RR=1.1 (marginally useful); the futures entry has WR=0% (useless). Keep only the commodity entry or drop both — the EV is near zero either way.

3. **Prioritize PG SHORT and SOLUSDT LONG.** These are the only two picks with verified track records (WR 64% and 65% respectively, n>=20). They are your anchor positions.

4. **Reduce bond duration concentration.** TLT LONG + BND LONG together = 41% of portfolio in a highly correlated pair. Replace BND with SHY SHORT to create a curve-steepener that benefits from the same macro view but reduces correlation risk.

### Caveats

- **WR estimates are fragile.** Only 2 of 21 picks have verified WR. The other 13 picks with estimated WR use a linear confidence-to-WR mapping that has no empirical validation. Treat Sharpe ratios for estimated-WR picks as **directional signals only**, not precise measurements.
- **Sharpe inflation for bonds.** Daily vol of 0.5% for bonds makes Sharpe ratios 2-6x higher than equity/crypto picks. This is a mathematical artifact of the ratio, not a guarantee of superior risk-adjusted returns. In practice, bond strategies at 20 Sharpe do not exist.
- **No covariance matrix for Kelly.** Individual Kelly fractions are computed assuming uncorrelated bets. With the heavy equity-short and bond-long clusters, actual optimal Kelly would be significantly lower (~30-50% of individual Kelly).
- **Missing data.** No TP/SL price levels were provided. The analysis assumes a 1% position risk model with RR determining the win/loss ratio. Actual TP/SL dollar levels would allow more precise position sizing.

---

*Generated: 2026-05-24 | Methodology: EV/RR framework, simple risk parity, estimated WR where n<20*
