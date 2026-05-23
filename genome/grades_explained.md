# Signal Quality Grading System

## Overview

The Signal Quality Scoring System uses a comprehensive 6-dimension framework to evaluate trading signals on a scale of 0-100, with grades from A+ to F. Only signals scoring **70 or higher (Grade B- or above)** are approved for live trading.

---

## Grade Scale

| Grade | Score Range | Status | Action |
|-------|-------------|--------|--------|
| **A+** | 95-100 | 🔥 Exceptional | Immediate execution, full position size |
| **A** | 90-94 | ⭐ Excellent | Strong execution, full position size |
| **A-** | 85-89 | ✅ Very Good | Above average, standard execution |
| **B+** | 80-84 | 👍 Good | Solid trade, standard execution |
| **B** | 75-79 | ✓ Above Average | Decent edge, standard execution |
| **B-** | 70-74 | ⚠️ Acceptable | Minimum threshold, reduced size optional |
| **C+** | 65-69 | 🧪 Marginal | **Paper trade only** |
| **C** | 60-64 | ⚠️ Weak | **Paper trade only** |
| **D** | 40-59 | ❌ Poor | **Do not trade** |
| **F** | 0-39 | 🚫 Unacceptable | **Do not trade** |

---

## Grade Descriptions

### A+ (95-100) - Exceptional
**"Hedge Fund Quality"**

Signals in this category represent the highest quality opportunities with exceptional edge and minimal risk.

**Characteristics:**
- Sharpe ratio > 2.0
- 200+ trades with consistent performance
- Perfect regime alignment
- 4+ systems in consensus
- Deep liquidity, tight spreads
- Strong risk-adjusted returns

**Action:** Execute immediately with full position size per Kelly criterion.

---

### A (90-94) - Excellent
**"Strong Edge, High Confidence"**

Outstanding signals with proven historical performance and strong market conditions.

**Characteristics:**
- Sharpe ratio 1.7-2.0
- 150+ trades
- Optimal regime fit
- 3-4 systems agreeing
- Excellent market structure

**Action:** Execute with full position size.

---

### A- (85-89) - Very Good
**"Above Average Expectations"**

High-quality signals that exceed our baseline requirements across most dimensions.

**Characteristics:**
- Sharpe ratio 1.4-1.7
- 100+ trades
- Good regime alignment
- 3+ systems in consensus

**Action:** Standard execution.

---

### B+ (80-84) - Good
**"Solid Trade with Acceptable Risk"**

Reliable signals with adequate backtesting and reasonable market conditions.

**Characteristics:**
- Sharpe ratio 1.2-1.4
- 75+ trades
- Acceptable regime fit
- 2-3 systems agreeing

**Action:** Standard execution with normal position sizing.

---

### B (75-79) - Above Average
**"Decent Edge"**

Respectable signals that meet our minimum standards with some room for improvement.

**Characteristics:**
- Sharpe ratio 1.0-1.2
- 50+ trades
- Moderate regime alignment
- 2 systems in consensus

**Action:** Execute with standard or slightly reduced position size.

---

### B- (70-74) - Acceptable
**"Minimum Threshold for Live Trading"**

The lowest grade we will execute in live trading. These signals meet baseline requirements but warrant caution.

**Characteristics:**
- Sharpe ratio 0.8-1.0
- 30+ trades
- Marginal regime fit
- 1-2 systems agreeing
- Adequate market structure

**Action:** Execute with reduced position size (50-75% of Kelly). Monitor closely.

⚠️ **This is the minimum threshold for live trading.**

---

### C+ (65-69) - Marginal
**"Paper Trade Only"**

Signals that show promise but lack sufficient validation for live capital.

**Characteristics:**
- Sharpe ratio 0.6-0.8
- 20-30 trades
- Weak regime alignment
- Limited consensus

**Action:** **Paper trade only** - track performance but do not use live capital.

---

### C (60-64) - Weak
**"Insufficient Edge"**

Signals with concerning weaknesses in multiple dimensions.

**Characteristics:**
- Sharpe ratio 0.5-0.6
- < 25 trades
- Poor regime fit
- Single system signal

**Action:** **Do not trade.** Continue paper trading and strategy refinement.

---

### D (<60) - Reject
**"Do Not Trade"**

Signals that fail to meet minimum standards across multiple critical dimensions.

**Characteristics:**
- Sharpe ratio < 0.5
- Insufficient sample size
- Misaligned with current regime
- Poor market structure

**Action:** **Do not trade.** Signal should be rejected and strategy re-evaluated.

---

## Scoring Methodology

### Component Weights

| Component | Weight | Max Points | Description |
|-----------|--------|------------|-------------|
| **Backtest Validity** | 25% | 25 pts | Sharpe ratio, win rate, profit factor |
| **Statistical Significance** | 20% | 20 pts | Sample size, trade count |
| **Regime Alignment** | 15% | 15 pts | Current market fit |
| **Risk-Adjusted Return** | 20% | 20 pts | Sortino, Calmar, max drawdown |
| **Consensus Strength** | 10% | 10 pts | Multi-system agreement |
| **Market Structure** | 10% | 10 pts | Liquidity, spread, volume |

### Detailed Scoring

#### Backtest Validity (0-25 points)

| Sharpe Ratio | Points |
|--------------|--------|
| > 2.0 | 25 |
| > 1.5 | 22 |
| > 1.2 | 18 |
| > 1.0 | 15 |
| > 0.8 | 10 |
| > 0.5 | 5 |
| ≤ 0.5 | 0 |

#### Statistical Significance (0-20 points)

| Total Trades | Points |
|--------------|--------|
| > 500 | 20 |
| > 200 | 18 |
| > 100 | 15 |
| > 50 | 12 |
| > 30 | 10 |
| > 20 | 7 |
| ≤ 20 | trades × 0.3 |

#### Regime Alignment (0-15 points)

| Condition | Points |
|-----------|--------|
| Optimal regime + Sharpe > 2.0 | 15 |
| Optimal regime + Sharpe > 1.5 | 13 |
| Optimal regime + Sharpe ≤ 1.5 | 11 |
| Non-optimal + Sharpe > 1.0 | 9 |
| Non-optimal + Sharpe > 0.5 | 6 |
| Non-optimal + Sharpe ≤ 0.5 | 3 |
| Unknown regime | 7.5 |

#### Risk-Adjusted Return (0-20 points)

Combines Sortino ratio, Calmar ratio, and max drawdown scores.

#### Consensus Strength (0-10 points)

| Systems Agreeing | Points |
|------------------|--------|
| 5+ | 10 |
| 4 | 9 |
| 3 | 7 |
| 2 | 5 |
| 1 | 3 |
| 0 | 0 |

#### Market Structure (0-10 points)

Based on volume, spread, and volatility conditions.

---

## Trading Thresholds

```
LIVE TRADING:     Score ≥ 70 (Grade B- or higher)
PAPER TRADING:    Score ≥ 65 (Grade C+ or higher)
REJECT:           Score < 65 (Grade C or lower)
```

### Recommended Position Sizing by Grade

| Grade | Position Size |
|-------|---------------|
| A+ | 100% of Kelly |
| A | 100% of Kelly |
| A- | 90% of Kelly |
| B+ | 85% of Kelly |
| B | 75% of Kelly |
| B- | 50% of Kelly |

---

## Verdict Mapping

| Grade | LONG Direction | SHORT Direction |
|-------|---------------|-----------------|
| A+ | STRONG_BUY | STRONG_SELL |
| A | BUY | SELL |
| A- | MODERATE_BUY | MODERATE_SELL |
| B+ | MODERATE_BUY | MODERATE_SELL |
| B | MODERATE_BUY | MODERATE_SELL |
| B- | BUY* | SELL* |
| C+ | HOLD | HOLD |
| C | HOLD | HOLD |
| D | REJECT | REJECT |
| F | REJECT | REJECT |

\* With reduced position size

---

## Example Scoring

### Example 1: High-Quality Signal (Grade A-)

```
BTCUSDT LONG - EMA Cross Strategy

Backtest Validity:        22/25  (Sharpe 1.85)
Statistical Significance: 15/20  (156 trades)
Regime Alignment:         13/15  (Trending bull, optimal)
Risk-Adjusted Return:     17/20  (Sortino 2.1, Calmar 2.5)
Consensus Strength:        9/10  (4 systems)
Market Structure:         10/10  ($35B volume, 0.05% spread)
─────────────────────────────────────────
TOTAL SCORE:              86/100  → Grade: A-
```

**Verdict:** MODERATE_BUY with 90% Kelly sizing

---

### Example 2: Minimum Viable Signal (Grade B-)

```
SOLUSDT SHORT - RSI Divergence

Backtest Validity:        10/25  (Sharpe 0.95)
Statistical Significance: 10/20  (45 trades)
Regime Alignment:          6/15  (Ranging, suboptimal)
Risk-Adjusted Return:     13/20  (Sortino 1.3, Calmar 1.6)
Consensus Strength:        5/10  (2 systems)
Market Structure:          9/10  ($2B volume, 0.1% spread)
─────────────────────────────────────────
TOTAL SCORE:              53/100  → Grade: B-
```

**Verdict:** SELL with 50% Kelly sizing (reduced risk)

---

## Best Practices

1. **Always check the grade** before executing any trade
2. **Review component scores** to understand strengths/weaknesses
3. **Consider correlation** with existing positions
4. **Respect the minimum threshold** - no exceptions for live trading
5. **Monitor B- signals** more closely than higher grades
6. **Paper trade C+ signals** to gather more data

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-02 | Initial grading system v1.0 |
