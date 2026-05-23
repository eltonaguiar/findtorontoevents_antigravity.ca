# Kelly Criterion Position Sizing: Mathematical Derivation

## Executive Summary

This document provides the complete mathematical derivation of the corrected Kelly Criterion position sizing algorithm with ATR-based volatility adjustment. It explains the double-counting bug and presents the proper formula implementation.

---

## 1. The Double-Counting Bug Explained

### Buggy Implementation (WRONG)
```python
position_dollars = (risk_per_trade / dollar_vol) * account_equity
```

**The Problem:**
- `risk_per_trade` already contains `account_equity` (it's typically calculated as `account_equity * target_risk_pct`)
- Multiplying by `account_equity` again causes **double-counting**
- Result: Position sizes that are **equity²** instead of **equity**

### Example of the Bug
```
Account Equity: $100,000
Target Risk: 1%
ATR: $2.50
Stop ATR Mult: 2.0

risk_per_trade = $100,000 × 1% = $1,000
dollar_vol = $2.50 × 2 = $5.00

BUGGY: position = ($1,000 / $5.00) × $100,000 = $20,000,000  ❌ (20,000% of equity!)
CORRECT: position = $1,000 / ($5.00 / $450) = $90,000         ✓ (90% of equity)
```

---

## 2. Corrected Formula Derivation

### Step 1: Define Risk Amount
The dollar amount we're willing to lose on this trade:

$$
\text{Risk Amount} = \text{Account Equity} \times \text{Target Risk \%} \times \text{Kelly Fraction}
$$

### Step 2: Define Stop Distance
The stop distance as a percentage of price, based on ATR:

$$
\text{Stop Distance}_{\$} = \text{ATR}_{14} \times \text{Stop ATR Mult}
$$

$$
\text{Stop Distance}_{\%} = \frac{\text{Stop Distance}_{\$}}{\text{Current Price}} = \frac{\text{ATR}_{14} \times \text{Stop ATR Mult}}{\text{Current Price}}
$$

### Step 3: Calculate Position Size
The position size that makes our risk equal the target risk amount:

$$
\text{Position}_{\$} = \frac{\text{Risk Amount}}{\text{Stop Distance}_{\%}}
$$

### Step 4: Apply Position Cap
Maximum position as percentage of equity:

$$
\text{Position}_{\$} = \min\left( \frac{\text{Risk Amount}}{\text{Stop Distance}_{\%}}, \text{Account Equity} \times \text{Max Position \%} \right)
$$

### Complete Formula

$$
\boxed{
\text{Position}_{\$} = \min\left( \frac{E \times r \times f_k}{\frac{\text{ATR} \times m}{P}}, E \times c \right)
}
$$

Where:
- $E$ = Account Equity
- $r$ = Target Risk % per trade
- $f_k$ = Kelly Fraction (typically 0.5 for Half-Kelly)
- ATR = 14-period Average True Range
- $m$ = Stop ATR Multiplier
- $P$ = Current Price
- $c$ = Max Position Cap %

---

## 3. Kelly Criterion Derivation

### Original Kelly Formula (Betting)

From Kelly's 1956 paper "A New Interpretation of Information Rate":

For a bet with:
- $p$ = probability of winning
- $q = 1-p$ = probability of losing
- $b$ = win/loss ratio (odds received)

The optimal fraction of bankroll to bet is:

$$
f^* = \frac{pb - q}{b} = p - \frac{q}{b}
$$

### Trading Adaptation

For trading with percentage returns:
- $p$ = win rate
- $\bar{w}$ = average winning trade return
- $\bar{l}$ = average losing trade return (positive value)

The Kelly fraction becomes:

$$
f^* = \frac{p \cdot \bar{w} - (1-p) \cdot \bar{l}}{\bar{w} \cdot \bar{l}} \times \bar{l} = \frac{p \cdot \bar{w} - (1-p) \cdot \bar{l}}{\bar{w}}
$$

Or equivalently:

$$
f^* = p - \frac{(1-p) \cdot \bar{l}}{\bar{w}} = p - \frac{q}{b}
$$

Where $b = \frac{\bar{w}}{\bar{l}}$ is the win/loss ratio.

### Fractional Kelly

For safety, traders use a fraction of full Kelly:

$$
f_{\text{fractional}} = f^* \times f_{\text{kelly}}
$$

Where $f_{\text{kelly}}$ is typically 0.25 to 0.5 (Quarter to Half Kelly).

---

## 4. Asset Class Specific Adjustments

### Stocks and ETFs
```
Quantity = Position$ / Price
```

### Futures
```
Quantity = Position$ / (Price × Contract Multiplier)
```

Common multipliers:
- CL (Crude Oil): 1,000 barrels
- GC (Gold): 100 troy ounces
- ES (E-mini S&P): $50 per point
- NQ (E-mini Nasdaq): $20 per point

### Cryptocurrency
```
Quantity = Position$ / Price
```
Round to exchange-specific minimum quantity (e.g., 0.0001 BTC).

---

## 5. Edge Case Handling

### Zero ATR
When ATR = 0 (illiquid or newly listed asset):
- Use minimum risk buffer: `min_risk_buffer = 0.001` (0.1%)
- Position size = `Risk Amount / min_risk_buffer`

### Very Small Accounts
When position size < minimum lot size:
- Return zero quantity
- Log warning for insufficient capital

### Extreme Volatility
When ATR is very high relative to price:
- Position cap prevents excessive exposure
- Max position % acts as circuit breaker

---

## 6. Academic References

### Primary Sources

1. **Kelly, J.L. (1956)** - "A New Interpretation of Information Rate"
   - Bell System Technical Journal, 35(4), 917-926
   - Original derivation of Kelly Criterion
   - DOI: 10.1002/j.1538-7305.1956.tb03809.x

2. **Thorp, E.O. (2006)** - "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market"
   - Handbook of Asset and Liability Management, Volume 1
   - Application to trading and portfolio management
   - Available at: https://www.eecs.harvard.edu/cs286r/courses/fall12/papers/Thorp_KellyCriterion2007.pdf

3. **Breiman, L. (1961)** - "Optimal Gambling Systems for Favorable Games"
   - Proceedings of the Fourth Berkeley Symposium on Mathematical Statistics and Probability
   - Mathematical foundations of Kelly betting

### Position Sizing and Risk Management

4. **Vince, R. (1990)** - "Portfolio Management Formulas"
   - John Wiley & Sons
   - Practical implementation of position sizing

5. **Vince, R. (2007)** - "The Handbook of Portfolio Mathematics"
   - John Wiley & Sons
   - Advanced position sizing techniques

6. **Rotando, L.M. & Thorp, E.O. (1992)** - "The Kelly Criterion and the Stock Market"
   - American Mathematical Monthly, 99(10), 922-931

### Volatility-Based Sizing

7. **Wilder, J.W. (1978)** - "New Concepts in Technical Trading Systems"
   - Trend Research
   - Original ATR calculation

8. **Kaufman, P.J. (2013)** - "Trading Systems and Methods"
   - John Wiley & Sons (5th Edition)
   - Chapter on volatility-based position sizing

### Fractional Kelly Research

9. **MacLean, L.C., Thorp, E.O., & Ziemba, W.T. (2011)** - "The Kelly Capital Growth Investment Criterion"
   - World Scientific Publishing
   - Comprehensive treatment of Kelly and fractional Kelly

10. **Ziemba, W.T. (2015)** - "A Response to Paul A Samuelson's Objections to Kelly Capital Growth Investing"
    - Journal of Portfolio Management, 42(1), 153-159

---

## 7. Implementation Checklist

- [x] Kelly fraction calculation with bounds checking
- [x] ATR-based stop distance calculation
- [x] Position size calculation (corrected formula)
- [x] Position cap enforcement
- [x] Asset class specific quantity calculation
- [x] Zero ATR handling
- [x] Small account handling
- [x] Futures contract multiplier support
- [x] Crypto minimum quantity handling
- [x] Unit tests for all scenarios

---

## 8. Quick Reference Card

```
INPUTS:
  E = Account Equity
  ATR = 14-period Average True Range
  P = Current Price
  p = Win Rate (0-1)
  w = Average Win %
  l = Average Loss %
  m = Stop ATR Multiplier (default: 2.0)
  f = Kelly Fraction (default: 0.5)
  r = Target Risk % (default: 0.01)
  c = Max Position % (default: 0.20)

FORMULAS:
  Kelly Full:    k = (p × w - (1-p) × l) / w
  Kelly Frac:    kf = k × f
  Risk Amount:   R = E × r × kf
  Stop Dist %:   s = (ATR × m) / P
  Position $:    pos = min(R / s, E × c)
  Quantity:      q = pos / P  (adjust for contract multipliers)

OUTPUTS:
  Position in dollars
  Position in shares/contracts
  Risk amount
  Risk % of equity
  Kelly fraction used
```

---

*Document Version: 1.0*
*Last Updated: 2026-03-12*
