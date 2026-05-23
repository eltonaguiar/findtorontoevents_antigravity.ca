# Researcher 005: Dr. Raj Patel — Risk Management Specialist

## Persona
- **Title:** Risk Management Specialist, Crypto Quantitative Systems
- **Expertise:** Position sizing, drawdown control, volatility targeting, Kelly criterion, Monte Carlo validation
- **Years Experience:** 15
- **Background:** PhD Columbia Financial Engineering, former Goldman Sachs risk desk, specialized in crypto fat-tailed distributions and ML trading system risk frameworks.

## Research Question
**What risk management frameworks maximize Sharpe ratio and minimize drawdown for crypto ML trading systems?**

## Context: Current System Failures
Our 3 ML trading systems are hemorrhaging capital:

| System | Win Rate | PnL | Core Problem |
|--------|----------|-----|--------------|
| System A | 10% | -7.77% | Stops too tight, 90% losers |
| System B | 20% | -5.42% | Transaction costs eat edge |
| System C | 0% | -5.89% | No edge detected |
| **Combined** | **~10%** | **-19.08%** | **Catastrophic failure** |

**Identified failure modes:**
1. Stop losses triggered within minutes on 15m timeframe (whipsaw)
2. Transaction costs (0.25-0.7% round trip) consume most of the small gains
3. Position sizing ignores volatility regime
4. No drawdown circuit breakers
5. No cost-aware edge filtering

---

## PART 1: DIAGNOSTIC — WHY 10% WIN RATE IS A DEATH SENTENCE

### 1.1 The Break-Even Win Rate Formula

For a trading system to be profitable:

```
Break-Even Win Rate = 1 / (1 + Reward:Risk Ratio)
```

| Reward:Risk | Min Win Rate Required | Your 10% WR: Need R:R of... |
|-------------|----------------------|----------------------------|
| 1:1 | 50% | N/A (impossible at 10% WR) |
| 2:1 | 33% | N/A |
| 3:1 | 25% | N/A |
| 5:1 | 17% | N/A |
| 10:1 | 9.1% | **Minimum viable** |
| 15:1 | 6.3% | Comfortable |

**Critical finding:** At 10% win rate, you need a minimum 10:1 reward-to-risk ratio BEFORE transaction costs. After 0.5% round-trip costs on a typical 2% target move, your effective R:R drops to approximately 7.5:1, which requires a 12% win rate to break even.

### 1.2 The Transaction Cost Death Spiral

```
Net Edge = Gross Edge - (Transaction Cost x Trade Frequency)

Example with current system:
- Avg winner: +2.0% (before costs)
- Avg loser: -0.5% (stop loss)
- Win rate: 10%
- Round-trip cost: 0.5% (taker + slippage)

Gross Expectancy = (0.10 x 2.0%) + (0.90 x -0.5%) = 0.20% - 0.45% = -0.25%
Net Expectancy = -0.25% - 0.5% = -0.75% per trade

At 10 trades/day = -7.5% per day (explains -19% in days)
```

**Verdict:** The system has NEGATIVE expectancy. No position sizing framework can fix a negative edge. Risk management preserves capital while you fix the signal — it cannot create alpha from noise.

---

## PART 2: STOP LOSS OPTIMIZATION — THE #1 PRIORITY

### 2.1 Why Fixed Stops Fail on 15-Minute Crypto

The core problem: crypto 15m candles routinely produce wicks of 0.3-0.8% that recover within the same candle. A fixed 0.5% stop loss will be hit by normal market noise approximately 60-70% of the time on BTC/USDT 15m charts.

**Research evidence:**
- Academic study (Semantic Scholar, 2024): ATR-based variable stops with period=12 and multiplier=6 showed best results for crypto
- LuxAlgo research: ATR stops boost performance 15% vs fixed stops, reduce max drawdown by 22%
- Go Markets analysis: 1.5x ATR minimum for day trading, 3-4x ATR for swing

### 2.2 ATR-Based Stop Loss Framework

```python
# RECOMMENDED: Adaptive ATR Stop Loss
def calculate_stop_distance(candles, timeframe='15m'):
    """
    ATR-based stop that adapts to crypto volatility regimes.

    Research-backed parameters:
    - ATR Period: 14 (standard) or 7 (more responsive for 15m)
    - Multiplier: 2.5-3.5x for crypto (NOT 1.5x — too tight for crypto noise)
    - Minimum floor: Never less than 1.0% on any crypto pair
    """
    atr = calculate_atr(candles, period=14)

    # Regime-adaptive multiplier
    current_vol = atr / candles[-1]['close']  # ATR as % of price
    historical_vol_median = rolling_median(atr_pct, 100)

    if current_vol > historical_vol_median * 1.5:
        multiplier = 3.5  # High vol regime: WIDE stops
    elif current_vol < historical_vol_median * 0.7:
        multiplier = 2.0  # Low vol regime: tighter stops OK
    else:
        multiplier = 2.5  # Normal regime

    stop_distance = atr * multiplier
    stop_pct = stop_distance / candles[-1]['close']

    # FLOOR: Never risk less than cost of being wrong
    min_stop_pct = max(0.01, round_trip_cost * 3)  # 3x transaction cost minimum

    return max(stop_pct, min_stop_pct)
```

### 2.3 Stop Loss Distance Recommendations by Timeframe

| Timeframe | ATR Period | Multiplier | Typical BTC Stop | Min Stop |
|-----------|-----------|------------|-----------------|----------|
| 5m | 7 | 2.0x | 0.3-0.5% | 0.5% |
| **15m** | **14** | **2.5-3.5x** | **0.8-1.5%** | **1.0%** |
| 1h | 14 | 2.5x | 1.5-2.5% | 1.5% |
| 4h | 14 | 3.0x | 3.0-5.0% | 2.5% |
| 1d | 20 | 3.0x | 5.0-8.0% | 4.0% |

### 2.4 The "3x Transaction Cost" Rule

**Rule:** Your stop loss distance must be AT MINIMUM 3x your round-trip transaction cost. Otherwise, the cost-to-stop ratio destroys your edge.

```
If round-trip cost = 0.5%:
  Minimum stop = 0.5% x 3 = 1.5%
  Minimum target = stop x 2 = 3.0% (for 2:1 R:R)

If round-trip cost = 0.25% (maker fees):
  Minimum stop = 0.25% x 3 = 0.75%
  Minimum target = 0.75% x 2 = 1.5%
```

**Implication:** On 15m timeframe with taker fees, you need price moves of 3%+ to have viable trades. This severely limits trade frequency. Solution: use MAKER orders (limit orders) to cut costs, or move to 1h/4h timeframes.

### 2.5 Chandelier Stop (Best for Trend Following)

```python
def chandelier_stop(candles, atr_period=14, multiplier=3.0):
    """
    Trailing stop based on highest high minus ATR multiple.
    Best for capturing trends while giving room for pullbacks.
    """
    atr = calculate_atr(candles, atr_period)
    highest_high = max(c['high'] for c in candles[-atr_period:])
    lowest_low = min(c['low'] for c in candles[-atr_period:])

    long_stop = highest_high - (atr * multiplier)
    short_stop = lowest_low + (atr * multiplier)

    return long_stop, short_stop
```

---

## PART 3: KELLY CRITERION — OPTIMAL POSITION SIZING

### 3.1 Classical Kelly Formula

```
f* = (p * b - q) / b

where:
  f* = fraction of capital to risk
  p  = probability of winning
  q  = probability of losing (1 - p)
  b  = ratio of average win to average loss (reward:risk)
```

### 3.2 Kelly Applied to Current Systems

```
System A (10% WR, avg win 2%, avg loss 0.5%):
  p = 0.10, q = 0.90, b = 2.0/0.5 = 4.0
  f* = (0.10 * 4.0 - 0.90) / 4.0 = (0.40 - 0.90) / 4.0 = -0.125

  Kelly says: DO NOT TRADE. Negative f* means negative edge.

System B (20% WR, avg win 1.5%, avg loss 0.5%):
  p = 0.20, q = 0.80, b = 1.5/0.5 = 3.0
  f* = (0.20 * 3.0 - 0.80) / 3.0 = (0.60 - 0.80) / 3.0 = -0.067

  Kelly says: DO NOT TRADE. Still negative edge.
```

**This is the fundamental problem.** Kelly criterion is telling us these systems have no edge. No position sizing method can fix a system with negative expectancy.

### 3.3 What Kelly Would Look Like With a Viable System

```
Target system (55% WR, avg win 2%, avg loss 1%):
  p = 0.55, q = 0.45, b = 2.0/1.0 = 2.0
  f* = (0.55 * 2.0 - 0.45) / 2.0 = (1.10 - 0.45) / 2.0 = 0.325

  Full Kelly: Risk 32.5% per trade (DANGEROUS)
  Half Kelly: Risk 16.25% per trade (still aggressive)
  Quarter Kelly: Risk 8.125% per trade (professional)
  Eighth Kelly: Risk 4.0% per trade (conservative — RECOMMENDED for crypto)
```

### 3.4 Fractional Kelly: Research Consensus

| Fraction | Growth Capture | Drawdown Reduction | Recommended For |
|----------|---------------|-------------------|-----------------|
| Full Kelly (100%) | 100% | Baseline (50%+ DD common) | Never in practice |
| Half Kelly (50%) | ~75% | ~50% reduction | Confident systems with 500+ trades |
| **Quarter Kelly (25%)** | **~50%** | **~75% reduction** | **Standard for crypto** |
| Eighth Kelly (12.5%) | ~25% | ~87% reduction | New/unproven systems |

**Key research (Thorp, 2008):** Half Kelly captures ~75% of optimal growth with ~50% less drawdown. For crypto's fat tails, Quarter Kelly is the professional standard.

**Key research (Matthew Downey, 2024):** When parameter uncertainty is factored in (you don't know your true win rate precisely), the optimal fraction drops further. For a system where you estimate 55% WR but uncertainty is +/-10%, optimal Kelly fraction drops to ~20-28% of full Kelly.

### 3.5 Adaptive Kelly with Rolling Estimation

```python
def adaptive_kelly(trade_history, lookback=50, max_fraction=0.25):
    """
    Dynamic Kelly that adapts to recent performance.
    Uses rolling window to estimate p, b with confidence adjustment.

    Parameters:
    - lookback: trades to use for estimation (min 30)
    - max_fraction: cap on Kelly fraction (0.25 = Quarter Kelly)
    """
    if len(trade_history) < 30:
        return 0.01  # Minimum bet until sufficient data

    recent = trade_history[-lookback:]
    wins = [t for t in recent if t['pnl'] > 0]
    losses = [t for t in recent if t['pnl'] <= 0]

    if not losses or not wins:
        return 0.01

    p = len(wins) / len(recent)
    avg_win = sum(t['pnl'] for t in wins) / len(wins)
    avg_loss = abs(sum(t['pnl'] for t in losses) / len(losses))
    b = avg_win / avg_loss

    kelly_raw = (p * b - (1 - p)) / b

    if kelly_raw <= 0:
        return 0.0  # NO EDGE — do not trade

    # Apply fractional Kelly with confidence scaling
    n = len(recent)
    confidence_factor = min(1.0, n / 100)  # Scale up as more data
    kelly_adjusted = kelly_raw * max_fraction * confidence_factor

    # Hard caps
    return min(kelly_adjusted, 0.05)  # Never more than 5% per trade
```

---

## PART 4: VOLATILITY TARGETING

### 4.1 Core Concept

Instead of fixed position sizes, scale positions inversely with realized volatility so each trade contributes roughly the same risk to the portfolio.

```
Position Size = (Target Volatility / Realized Volatility) x Base Position

Example:
  Target daily vol: 1%
  BTC realized 20d vol: 3.5%
  Base position: $10,000

  Adjusted position = (1% / 3.5%) x $10,000 = $2,857

  If vol spikes to 7%:
  Adjusted position = (1% / 7%) x $10,000 = $1,429 (halved!)
```

### 4.2 Regime-Conditional Volatility Targeting

Research from Financial Analysts Journal (2020) shows that **conditional** volatility targeting — adjusting only in extreme states — outperforms continuous targeting:

```python
def regime_conditional_size(base_size, current_vol, historical_vol_percentiles):
    """
    Only adjust in extreme vol regimes, not continuously.
    Research shows this reduces turnover while maintaining protection.

    Regimes (based on 252-day realized vol percentile):
    - Low vol (<20th pctile): 1.2x base (slight increase)
    - Normal (20th-80th): 1.0x base (no adjustment)
    - High vol (80th-95th): 0.5x base (halve exposure)
    - Crisis (>95th pctile): 0.25x base (quarter exposure)
    """
    vol_percentile = percentile_rank(current_vol, historical_vol_percentiles)

    if vol_percentile < 20:
        return base_size * 1.2
    elif vol_percentile < 80:
        return base_size * 1.0
    elif vol_percentile < 95:
        return base_size * 0.5
    else:  # Crisis regime
        return base_size * 0.25
```

### 4.3 Impact on Sharpe Ratio

Research findings (Man Group, QuantPedia, Concretum Group):
- Volatility targeting increases Sharpe ratio for momentum strategies by 15-30%
- Conditional targeting (extremes only) achieves similar Sharpe improvement with 60% less turnover
- For crypto specifically: targeting 10-15% annualized vol is typical for institutional funds
- Key insight: vol targeting works because crypto returns are negatively correlated with volatility (crashes = high vol)

---

## PART 5: MAXIMUM DRAWDOWN CONTROLS

### 5.1 Circuit Breaker Framework

```python
class DrawdownCircuitBreaker:
    """
    Multi-tier drawdown protection system.

    Research basis: Strub (2012) "Trade Sizing Techniques for
    Drawdown and Tail Risk Control" — SSRN 2063848
    """

    TIERS = {
        'yellow':  {'drawdown': 0.05, 'action': 'reduce_50pct'},    # 5% DD
        'orange':  {'drawdown': 0.10, 'action': 'reduce_75pct'},    # 10% DD
        'red':     {'drawdown': 0.15, 'action': 'stop_new_trades'}, # 15% DD
        'black':   {'drawdown': 0.20, 'action': 'close_all'},       # 20% DD — liquidate
    }

    def __init__(self, peak_equity):
        self.peak_equity = peak_equity
        self.current_tier = None

    def check(self, current_equity):
        drawdown = (self.peak_equity - current_equity) / self.peak_equity

        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            self.current_tier = None
            return 'green', 1.0  # New high — full size

        for tier_name, tier_config in sorted(
            self.TIERS.items(),
            key=lambda x: x[1]['drawdown'],
            reverse=True
        ):
            if drawdown >= tier_config['drawdown']:
                return tier_name, self._get_scaling(tier_config['action'])

        return 'green', 1.0

    def _get_scaling(self, action):
        return {
            'reduce_50pct': 0.50,
            'reduce_75pct': 0.25,
            'stop_new_trades': 0.0,
            'close_all': -1.0,  # Signal to close positions
        }[action]
```

### 5.2 Daily Loss Limits

```python
DAILY_LOSS_LIMIT = 0.02      # 2% max daily loss
WEEKLY_LOSS_LIMIT = 0.05     # 5% max weekly loss
MONTHLY_LOSS_LIMIT = 0.10    # 10% max monthly loss

def check_daily_limit(today_pnl, account_equity):
    daily_loss_pct = abs(today_pnl) / account_equity if today_pnl < 0 else 0
    if daily_loss_pct >= DAILY_LOSS_LIMIT:
        return 'HALT_TRADING'
    elif daily_loss_pct >= DAILY_LOSS_LIMIT * 0.75:
        return 'REDUCE_SIZE_50PCT'
    return 'CONTINUE'
```

### 5.3 Consecutive Loss Counter

```python
def consecutive_loss_handler(consecutive_losses):
    """
    Scale down after consecutive losses.

    Research: Most profitable algo systems cap at 3-5 consecutive
    losses before pausing. This prevents tilt and regime-change damage.
    """
    if consecutive_losses >= 5:
        return 0.0   # STOP: 5+ losses = likely regime change
    elif consecutive_losses >= 3:
        return 0.25  # Quarter size: 3-4 losses
    elif consecutive_losses >= 2:
        return 0.50  # Half size: 2 losses
    return 1.0       # Full size: 0-1 losses
```

---

## PART 6: TRANSACTION COST-AWARE POSITION SIZING

### 6.1 The Minimum Edge Threshold

**Rule: Never trade when expected edge < 3x transaction cost.**

```python
def should_trade(signal_strength, expected_move_pct, round_trip_cost_pct):
    """
    Cost-aware trade filter.

    Most ML systems produce signals with tiny edges (0.1-0.3%).
    After costs, these are NEGATIVE expectancy.
    """
    net_expected_move = expected_move_pct - round_trip_cost_pct

    # Minimum edge threshold: 3x costs
    min_edge = round_trip_cost_pct * 3

    if expected_move_pct < min_edge:
        return False, f"Edge {expected_move_pct:.2%} < min {min_edge:.2%}"

    # Signal strength filter
    if signal_strength < 0.7:  # Only take high-confidence signals
        return False, f"Signal {signal_strength:.2f} < 0.70 threshold"

    return True, f"Net edge: {net_expected_move:.2%}"
```

### 6.2 Fee Optimization Strategies

| Strategy | Impact | Implementation |
|----------|--------|----------------|
| **Use limit orders (maker)** | Save 0.1-0.3% per trade | Post-only mode; accept partial fills |
| **Reduce trade frequency** | Linear cost reduction | Only trade high-conviction signals |
| **Move to higher timeframe** | Larger moves vs same cost | 1h or 4h instead of 15m |
| **Volume tier discounts** | 10-50% fee reduction | Consolidate to one exchange |
| **BNB/exchange token fees** | 10-25% discount | Hold exchange tokens for fee payment |

### 6.3 Cost-Adjusted Expectancy Formula

```
Net Expectancy = (WR x AvgWin) - ((1-WR) x AvgLoss) - RoundTripCost

For profitability:
  (WR x AvgWin) > ((1-WR) x AvgLoss) + RoundTripCost

Rearranged (minimum win rate for given R:R and costs):
  WR_min = (AvgLoss + Cost) / (AvgWin + AvgLoss)

Example (1.5% target, 1% stop, 0.5% cost):
  WR_min = (1.0 + 0.5) / (1.5 + 1.0) = 1.5 / 2.5 = 60%

Example (3% target, 1.5% stop, 0.5% cost):
  WR_min = (1.5 + 0.5) / (3.0 + 1.5) = 2.0 / 4.5 = 44%

Example (5% target, 2% stop, 0.5% cost):
  WR_min = (2.0 + 0.5) / (5.0 + 2.0) = 2.5 / 7.0 = 36%
```

**Key insight:** Moving to 4h timeframe with 5% targets and 2% stops requires only 36% win rate after costs. The 15m timeframe with tight stops requires 60% win rate — which your ML systems cannot achieve.

---

## PART 7: RISK PARITY ACROSS MULTIPLE STRATEGIES

### 7.1 Hierarchical Risk Parity (HRP)

Research (De Prado, 2016; ScienceDirect 2020): HRP outperforms traditional mean-variance and basic risk parity in crypto because it handles non-normal distributions and unstable correlations.

```python
def strategy_risk_parity(strategies, lookback_days=60):
    """
    Allocate capital across strategies based on inverse volatility,
    adjusted for correlation structure.

    Each strategy gets weight inversely proportional to its risk contribution.
    """
    returns = get_strategy_returns(strategies, lookback_days)

    # Step 1: Inverse volatility weights
    vols = returns.std()
    inv_vol_weights = (1.0 / vols) / (1.0 / vols).sum()

    # Step 2: Correlation adjustment
    corr_matrix = returns.corr()

    # Penalize highly correlated strategies
    for i, strat_i in enumerate(strategies):
        for j, strat_j in enumerate(strategies):
            if i != j and corr_matrix.iloc[i, j] > 0.6:
                # Reduce weight for correlated pairs
                inv_vol_weights[i] *= 0.7
                inv_vol_weights[j] *= 0.7

    # Renormalize
    final_weights = inv_vol_weights / inv_vol_weights.sum()

    # Step 3: Performance gate — zero out losing strategies
    for strat in strategies:
        if strat.sharpe_30d < 0:
            final_weights[strat.name] = 0.0

    return final_weights / final_weights.sum() if final_weights.sum() > 0 else None
```

### 7.2 Strategy Allocation Rules

| Strategy Sharpe (30d) | Allocation | Action |
|----------------------|------------|--------|
| > 1.0 | Full allocation | Scale up to max Kelly |
| 0.5 - 1.0 | 50% allocation | Standard sizing |
| 0.0 - 0.5 | 25% allocation | Reduced — on watch |
| **< 0.0** | **0% allocation** | **DO NOT TRADE** |
| < -0.5 for 2 weeks | Remove | Strategy is broken |

### 7.3 Current Systems Assessment

```
System A: Sharpe ≈ -2.5 → ALLOCATION: 0% — DO NOT TRADE
System B: Sharpe ≈ -1.5 → ALLOCATION: 0% — DO NOT TRADE
System C: Sharpe ≈ -3.0 → ALLOCATION: 0% — DO NOT TRADE

RECOMMENDED ACTION: Halt all live trading immediately.
Run paper trading only until a system achieves Sharpe > 0.5
over 100+ trades.
```

---

## PART 8: ANTI-MARTINGALE RECOVERY FRAMEWORK

### 8.1 Core Principle

**Anti-Martingale:** Increase size after wins, decrease after losses. This is the opposite of the gambler's fallacy approach and is mathematically sound for systems with positive expectancy.

```python
def anti_martingale_sizing(base_size, recent_results, scale_factor=0.5):
    """
    Anti-Martingale: grow with wins, shrink with losses.

    - After win: increase by scale_factor (e.g., 1.5x)
    - After loss: decrease by scale_factor (e.g., 0.67x)
    - Cap at 2x base, floor at 0.25x base
    """
    current_size = base_size

    for result in recent_results[-5:]:  # Last 5 trades
        if result > 0:
            current_size *= (1 + scale_factor)
        else:
            current_size *= (1 - scale_factor * 0.67)

    # Bounds
    current_size = max(base_size * 0.25, min(base_size * 2.0, current_size))

    return current_size
```

### 8.2 Recovery Protocol After Large Drawdown

```
Phase 1: HALT (Drawdown > 15%)
  - Stop all live trading
  - Analyze what went wrong
  - Duration: minimum 1 week

Phase 2: PAPER TRADE (Demonstrate edge)
  - Run system on paper for 50+ trades
  - Must achieve: WR > 40%, Sharpe > 0.5, positive expectancy
  - Duration: 2-4 weeks

Phase 3: QUARTER SIZE
  - Resume live with 25% of normal position size
  - Must achieve: 20+ profitable trades in a row (on net)
  - Duration: until confidence restored

Phase 4: HALF SIZE
  - Scale to 50% if Phase 3 successful
  - Run for another 30+ trades

Phase 5: FULL SIZE
  - Only after demonstrating consistent positive expectancy
  - With all circuit breakers active
```

---

## PART 9: MONTE CARLO VALIDATION

### 9.1 Purpose

Monte Carlo simulation tests whether your strategy's performance is statistically robust or just lucky. It answers: "Would this strategy be profitable across 1,000 different orderings of the same trades?"

### 9.2 Implementation

```python
import numpy as np

def monte_carlo_validate(trade_returns, n_simulations=2000, confidence=0.95):
    """
    Bootstrap Monte Carlo validation of strategy.

    Shuffles trade order to test if results are path-dependent.
    Returns confidence intervals for key metrics.

    Research: 2000+ simulations for statistically valid results
    (law of large numbers convergence).
    """
    n_trades = len(trade_returns)
    results = {
        'final_equity': [],
        'max_drawdown': [],
        'sharpe': [],
        'worst_streak': [],
    }

    for _ in range(n_simulations):
        # Bootstrap: sample with replacement
        shuffled = np.random.choice(trade_returns, size=n_trades, replace=True)

        # Calculate equity curve
        equity = np.cumprod(1 + shuffled)
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak

        results['final_equity'].append(equity[-1])
        results['max_drawdown'].append(drawdown.max())
        results['sharpe'].append(
            np.mean(shuffled) / np.std(shuffled) * np.sqrt(252) if np.std(shuffled) > 0 else 0
        )

        # Worst losing streak
        losing = shuffled < 0
        worst = 0
        current = 0
        for is_loss in losing:
            if is_loss:
                current += 1
                worst = max(worst, current)
            else:
                current = 0
        results['worst_streak'].append(worst)

    # Confidence intervals
    alpha = (1 - confidence) / 2
    report = {}
    for metric, values in results.items():
        values = sorted(values)
        report[metric] = {
            'median': values[len(values) // 2],
            'ci_lower': values[int(len(values) * alpha)],
            'ci_upper': values[int(len(values) * (1 - alpha))],
            'p_profitable': sum(1 for v in values if v > 1.0) / len(values)
                           if metric == 'final_equity' else None,
        }

    return report

# Validation criteria
def is_strategy_valid(mc_report):
    """
    A strategy passes Monte Carlo validation if:
    1. 95% CI lower bound for Sharpe > 0
    2. Median max drawdown < 25%
    3. Probability of profit > 70%
    4. Worst losing streak < 15 trades (at 95% CI)
    """
    checks = {
        'sharpe_positive': mc_report['sharpe']['ci_lower'] > 0,
        'drawdown_acceptable': mc_report['max_drawdown']['median'] < 0.25,
        'likely_profitable': mc_report['final_equity']['p_profitable'] > 0.70,
        'streak_manageable': mc_report['worst_streak']['ci_upper'] < 15,
    }
    return all(checks.values()), checks
```

### 9.3 Interpretation Guide

| Monte Carlo Result | Interpretation | Action |
|-------------------|---------------|--------|
| P(profit) > 90% | Strong edge confirmed | Trade with Quarter Kelly |
| P(profit) 70-90% | Moderate edge | Trade with Eighth Kelly |
| P(profit) 50-70% | Marginal/uncertain edge | Paper trade only |
| P(profit) < 50% | No edge | Do not trade |
| 95% CI Sharpe includes 0 | Edge not statistically significant | Need more data or better signal |
| Max DD > 30% at median | Unacceptable risk | Reduce position size or improve stops |

---

## PART 10: INTEGRATED RISK MANAGEMENT SYSTEM

### 10.1 The Complete Framework

```python
class CryptoMLRiskManager:
    """
    Integrated risk management system for crypto ML trading.
    Combines all research findings into a single decision framework.
    """

    def __init__(self, config):
        self.max_risk_per_trade = config.get('max_risk_per_trade', 0.02)    # 2%
        self.daily_loss_limit = config.get('daily_loss_limit', 0.02)         # 2%
        self.weekly_loss_limit = config.get('weekly_loss_limit', 0.05)       # 5%
        self.target_vol = config.get('target_vol', 0.15)                     # 15% annual
        self.min_edge_multiple = config.get('min_edge_multiple', 3.0)        # 3x costs
        self.kelly_fraction = config.get('kelly_fraction', 0.25)             # Quarter Kelly
        self.max_consecutive_losses = config.get('max_consecutive_losses', 5)
        self.circuit_breaker = DrawdownCircuitBreaker(config['initial_equity'])

    def calculate_position_size(self, signal, market_data, portfolio_state):
        """
        Master position sizing function.
        Returns position size (0 = don't trade).
        """

        # GATE 1: Is the system trading?
        tier, scaling = self.circuit_breaker.check(portfolio_state['equity'])
        if scaling <= 0:
            return 0, f"Circuit breaker: {tier}"

        # GATE 2: Daily/weekly loss limits
        if abs(portfolio_state['daily_pnl']) / portfolio_state['equity'] >= self.daily_loss_limit:
            return 0, "Daily loss limit reached"

        # GATE 3: Consecutive loss check
        loss_scaling = consecutive_loss_handler(portfolio_state['consecutive_losses'])
        if loss_scaling == 0:
            return 0, f"Consecutive losses: {portfolio_state['consecutive_losses']}"

        # GATE 4: Minimum edge threshold (cost-aware)
        round_trip_cost = signal['estimated_cost']
        min_edge = round_trip_cost * self.min_edge_multiple
        if signal['expected_move'] < min_edge:
            return 0, f"Edge {signal['expected_move']:.3%} < min {min_edge:.3%}"

        # GATE 5: Signal confidence
        if signal['confidence'] < 0.7:
            return 0, f"Low confidence: {signal['confidence']:.2f}"

        # SIZE 1: Kelly-based sizing
        kelly_size = adaptive_kelly(
            portfolio_state['trade_history'],
            max_fraction=self.kelly_fraction
        )

        # SIZE 2: Volatility targeting
        vol_scaling = self.target_vol / (market_data['realized_vol_20d'] * np.sqrt(252))
        vol_adjusted_size = kelly_size * min(vol_scaling, 2.0)  # Cap at 2x

        # SIZE 3: Regime adjustment
        regime_scaling = regime_conditional_size(1.0,
            market_data['realized_vol_20d'],
            market_data['vol_percentiles']
        )

        # SIZE 4: Apply all scaling factors
        final_size = (
            vol_adjusted_size
            * regime_scaling
            * scaling          # Circuit breaker
            * loss_scaling     # Consecutive losses
        )

        # HARD CAP: Never exceed max risk per trade
        max_size = self.max_risk_per_trade * portfolio_state['equity']
        final_size = min(final_size * portfolio_state['equity'], max_size)

        return final_size, "Approved"
```

### 10.2 Pre-Trade Checklist

Before EVERY trade, verify:

```
[ ] 1. System has positive expectancy (Kelly f* > 0)
[ ] 2. Signal confidence > 0.70
[ ] 3. Expected move > 3x transaction cost
[ ] 4. ATR-based stop is set (2.5-3.5x ATR on 15m)
[ ] 5. Stop distance > 3x round-trip cost (min 1.0% for crypto)
[ ] 6. No circuit breaker active
[ ] 7. Under daily/weekly loss limits
[ ] 8. Consecutive losses < 5
[ ] 9. Position size <= 2% of equity
[ ] 10. Total portfolio exposure < 20% of equity
```

---

## PART 11: SPECIFIC RECOMMENDATIONS FOR YOUR SYSTEMS

### 11.1 Immediate Actions (Week 1)

1. **HALT ALL LIVE TRADING IMMEDIATELY.** All three systems have negative expectancy. Continuing to trade is guaranteed capital destruction.

2. **Widen stops to 2.5-3.5x ATR(14) on 15m charts.** Your current stops are getting hit by normal market noise. For BTC on 15m, this means stops of 0.8-1.5% instead of whatever you're currently using (likely 0.3-0.5%).

3. **Switch to MAKER orders only.** Cut transaction costs from 0.5-0.7% to 0.1-0.2%. This alone could flip marginal signals from negative to positive expectancy.

4. **Implement the 3x cost rule.** Filter out all trades where expected move < 3x round-trip cost. This will dramatically reduce trade frequency but eliminate the guaranteed losers.

### 11.2 Medium-Term Fixes (Weeks 2-4)

5. **Move to 1h or 4h timeframe.** On 15m with current costs, you need impossibly precise signals. On 4h, a 3-5% target with 1.5-2% stop and 0.3% cost is viable at just 36-40% win rate.

6. **Implement circuit breakers.** The drawdown framework above with 5%/10%/15%/20% tiers.

7. **Paper trade all systems for 50+ trades.** Validate that changes produce positive Kelly f* before going live.

8. **Run Monte Carlo validation.** 2000 simulations, require P(profitable) > 70% and Sharpe CI lower bound > 0.

### 11.3 Long-Term Architecture (Months 1-3)

9. **Implement full risk parity.** Allocate across strategies using inverse-volatility weighting with correlation adjustment.

10. **Deploy adaptive Kelly.** Rolling 50-trade window, Quarter Kelly fraction, with confidence scaling.

11. **Build regime detection.** Use volatility percentiles to auto-scale position sizes. High vol = small positions.

12. **Add anti-martingale scaling.** Grow position sizes during winning streaks, shrink during losses.

### 11.4 The Hard Truth

With a 10% win rate, your ML models are performing **worse than random**. A coin flip would give you 50% win rate. This is not a risk management problem — it is a **signal quality problem**. The priority order is:

```
Priority 1: Fix the ML signal (target >40% WR with >2:1 R:R)
Priority 2: Reduce transaction costs (maker orders, higher timeframe)
Priority 3: Implement proper stop losses (ATR-based, regime-adaptive)
Priority 4: Add position sizing (Kelly + vol targeting)
Priority 5: Add portfolio-level controls (circuit breakers, risk parity)
```

Risk management cannot create edge. It can only **preserve capital** while you find it and **maximize returns** once you have it.

---

## Key Formulas Reference

| Formula | Expression | Use Case |
|---------|-----------|----------|
| Kelly Fraction | f* = (pb - q) / b | Optimal position size |
| Break-Even WR | WR_min = 1 / (1 + R:R) | Minimum win rate needed |
| Cost-Adj WR | WR_min = (Loss + Cost) / (Win + Loss) | With transaction costs |
| Net Expectancy | E = WR x W - (1-WR) x L - C | Expected PnL per trade |
| Vol Target Size | Pos = (TargetVol / RealizedVol) x Base | Volatility normalization |
| ATR Stop | Stop = Price - ATR(14) x Multiplier | Dynamic stop distance |
| Max DD Probability | P(DD > x) = e^(-2x^2/sigma^2/T) | Probability of drawdown |

## Academic References

1. Thorp, E. O. (2008). "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market." Handbook of Asset and Liability Management.
2. Strub, I. S. (2012). "Trade Sizing Techniques for Drawdown and Tail Risk Control." SSRN 2063848.
3. Rockafellar, R. T., & Uryasev, S. (2000). "Optimization of Conditional Value-at-Risk." Journal of Risk.
4. De Prado, M. L. (2016). "Building Diversified Portfolios that Outperform Out-of-Sample." Journal of Portfolio Management.
5. Moreira, A., & Muir, T. (2017). "Volatility-Managed Portfolios." Journal of Finance.
6. Harvey, C. R., et al. (2020). "Conditional Volatility Targeting." Financial Analysts Journal.
7. Liu, Y., Tsyvinski, A., & Wu, X. (2022). "Common Risk Factors in Cryptocurrency." Journal of Financial Economics.
8. Poundstone, W. (2005). "Fortune's Formula." Hill and Wang.
9. McNeil, A., Frey, R., & Embrechts, P. (2015). "Quantitative Risk Management." Princeton University Press.

## Web Research Sources

- [Kelly Criterion for Crypto Traders (Medium, Jan 2026)](https://medium.com/@tmapendembe_28659/kelly-criterion-for-crypto-traders-a-modern-approach-to-volatile-markets-a0cda654caa9)
- [Fractional Kelly Simulations (Matthew Downey)](https://matthewdowney.github.io/uncertainty-kelly-criterion-optimal-bet-size.html)
- [Conditional Volatility Targeting (Financial Analysts Journal)](https://www.tandfonline.com/doi/full/10.1080/0015198X.2020.1790853)
- [Position Sizing: Vol Targeting vs Parity vs Pyramiding (Concretum Group)](https://concretumgroup.com/position-sizing-in-trend-following-comparing-volatility-targeting-volatility-parity-and-pyramiding/)
- [Volatility Targeting Introduction (QuantPedia)](https://quantpedia.com/an-introduction-to-volatility-targeting/)
- [Trade Sizing for Drawdown Control (SSRN)](https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3231836_code1554519.pdf?abstractid=2063848&mirid=1)
- [ATR Stop-Loss Strategies (LuxAlgo)](https://www.luxalgo.com/blog/5-atr-stop-loss-strategies-for-risk-control/)
- [ATR Dynamic Stop Loss (Flipster)](https://flipster.io/blog/atr-stop-loss-strategy)
- [Stop Loss Strategies Comparison (Semantic Scholar PDF)](https://pdfs.semanticscholar.org/1f98/04b60040af7a8b8a077852b296502a134e4f.pdf)
- [Hierarchical Risk Parity for Crypto (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S154461232030177X)
- [Monte Carlo for Trading Validation (trader-algoritmico.com)](https://trader-algoritmico.com/blog/monte-carlo-simulation-for-trading-strategy-validation)
- [Kelly Criterion in Practice (Alpha Theory)](https://www.alphatheory.com/blog/kelly-criterion-in-practice-1)
- [Reducing Drawdown: 7 Techniques (Tradetron)](https://tradetron.tech/blog/reducing-drawdown-7-risk-management-techniques-for-algo-traders)
- [Volatility is Back: Target Returns or Risk? (Man Group)](https://www.man.com/insights/volatility-is-back-better-to-target-returns-or-target-risk)
- [Maker/Taker Fee Math (Axon Trade)](https://axon.trade/fees-rebates-and-maker-taker-math)

---
*Researcher ID: 005* | *Status: COMPLETE* | *Last Updated: 2026-02-24*
