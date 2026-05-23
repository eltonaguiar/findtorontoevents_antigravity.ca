# Strong Signals Blueprint: High Profit Factor, Lower Risk

**Goal:** Generate signals that consistently achieve >60% WR, Profit Factor > 1.5, with controlled drawdowns

---

## What Actually Works (Data-Backed)

### 1. Regime-Aligned Direction (The 40-Point Weapon)

**Finding:** Smart Picks achieve ~64% median WR vs 41.9% overall — the difference is regime alignment

**Implementation:**
```python
REGIME_MATCH_WEIGHT = 0.50  # Increase from 0.40 — this is the only thing working

def score_regime_match(pick, regime):
    """
    LONG in bull = full points
    SHORT in bear = full points  
    Neutral = half points
    Opposing = 0 points (hard filter if score < 70)
    """
    if pick.direction == 'LONG' and regime == 'BULLISH':
        return 1.0
    elif pick.direction == 'SHORT' and regime == 'BEARISH':
        return 1.0
    elif regime in ['CHOPPY', 'NEUTRAL']:
        return 0.5
    else:
        return 0.0  # Wrong direction
```

**Key Insight:** Direction > Score in extreme regimes. A Score 99 LONG loses in bearish regime. A Score 94 SHORT wins.

---

### 2. The R:R Sweet Spot (73.7% WR)

**Finding:** R:R 2.0-2.5 = 73.7% WR vs 39% for R:R < 1.5

**Implementation:**
```python
RR_SWEET_SPOT = (2.0, 2.5)

def score_risk_reward(risk_reward):
    if RR_SWEET_SPOT[0] <= risk_reward <= RR_SWEET_SPOT[1]:
        return 5  # Maximum points — this is the zone
    elif 1.5 <= risk_reward < 2.0:
        return 3
    elif 1.0 <= risk_reward < 1.5:
        return 1
    elif risk_reward < 1.0:
        return -100  # HARD BLOCK — negative expectancy
    else:  # > 2.5
        return 1  # TP rarely reached
```

**Action:** Hard filter ANY pick with R:R < 1.5. Boost picks with R:R 2.0-2.5.

---

### 3. Leverage Safety = Best Predictor (67% WR, +1.21% P/L)

**Finding:** Tight stops (1.5-3%) with high ML confidence = best predictor in entire system

**Implementation:**
```python
OPTIMAL_STOP_RANGE = (0.015, 0.03)  # 1.5% - 3%

def score_leverage_safety(stop_distance, ml_confidence, forward_wr):
    score = 0
    
    # Stop distance (optimal zone)
    if OPTIMAL_STOP_RANGE[0] <= stop_distance <= OPTIMAL_STOP_RANGE[1]:
        score += 5  # Sweet spot
    elif 0.01 <= stop_distance < 0.015:
        score += 3  # Tight but acceptable
    elif stop_distance < 0.01:
        score += 1  # Too tight — shakeout risk
    
    # ML confidence
    if ml_confidence >= 0.80:
        score += 3
    elif ml_confidence >= 0.70:
        score += 2
    
    # Forward validated
    if forward_wr >= 0.60 and forward_trades >= 10:
        score += 2
    
    return min(score, 10)  # Cap at 10 points
```

---

### 4. Strategy Track Record (Doubled Weight = 20 pts)

**Finding:** Method 4 backtest showed track record heavy scoring won (PF 0.76 → 1.90 in top quintile)

**Implementation:**
```python
def score_strategy_track_record(strategy):
    closed = strategy.closed_picks
    wr = strategy.win_rate
    
    if closed >= 20:
        if wr >= 0.55:
            return 20  # Proven winner
        elif wr >= 0.45:
            return 10  # Decent
        elif wr < 0.25:
            return -5  # Kill list candidate
    elif closed >= 10:
        if wr >= 0.50:
            return 15
        elif wr < 0.35:
            return -4
    elif closed >= 5:
        if wr >= 0.45:
            return 10
    
    return 5  # Unvalidated baseline
```

---

### 5. Confidence Sweet Spot (Not What You Think)

**Finding:** Confidence 0.60-0.70 had 61% WR (BEST) — but system was penalizing this range!

**Implementation:**
```python
def score_confidence(confidence):
    """
    0.60-0.70 = 61% WR (sweet spot)
    0.70-0.80 = 55% WR
    0.80+ = 49% WR (overconfidence)
    """
    if 0.60 <= confidence <= 0.70:
        return 8  # Best zone
    elif 0.70 < confidence <= 0.80:
        return 6
    elif 0.55 <= confidence < 0.60:
        return 4
    elif confidence > 0.80:
        return 2  # Overconfidence penalty
    else:
        return 0  # Below 0.55 = noise
```

---

## The 5-Filter Strong Signal System

To achieve >60% WR with PF > 1.5, apply these 5 filters IN ORDER:

### Filter 1: Regime Alignment (Hard Gate)
- LONG only in BULLISH/LEANING_BULL
- SHORT only in BEARISH/LEANING_BEAR
- **Expected pass rate:** ~40% of picks

### Filter 2: R:R >= 1.5 (Hard Gate)
- Block ANY pick with R:R < 1.5
- Boost picks with R:R 2.0-2.5
- **Expected pass rate:** ~60% of remaining

### Filter 3: Strategy Validation (Hard Gate)
- Min 10 closed trades at >= 45% WR
- Or min 5 trades at >= 55% WR
- **Expected pass rate:** ~50% of remaining

### Filter 4: Confidence 0.55-0.80 (Hard Gate)
- Below 0.55 = noise
- Above 0.80 = overfit
- **Expected pass rate:** ~70% of remaining

### Filter 5: Stop Distance 1.5-4% (Soft Gate)
- Optimal: 1.5-3%
- Penalize < 1% (shakeout risk)
- Penalize > 4% (poor risk management)
- **Expected pass rate:** ~80% of remaining

**Result:** 572 picks → ~40 strong signals (7% pass rate) with expected 65%+ WR

---

## Position Sizing for Strong Signals

```python
def size_strong_signal(pick, portfolio_value):
    """
    Kelly Criterion with fractional scaling
    """
    # Win rate from strategy track record
    wr = pick.strategy.win_rate
    
    # Average win/loss from historical trades
    avg_win = pick.strategy.avg_win_pct  # e.g., +4.04%
    avg_loss = pick.strategy.avg_loss_pct  # e.g., -2.46%
    
    # Kelly %
    edge = (wr * avg_win) - ((1 - wr) * abs(avg_loss))
    kelly_pct = edge / avg_win if avg_win > 0 else 0
    
    # Fractional Kelly (conservative)
    half_kelly = kelly_pct * 0.5
    
    # Volatility scaling
    current_vol = get_30d_volatility(pick.symbol)
    target_vol = 0.20  # 20% annualized target
    vol_scalar = target_vol / current_vol if current_vol > 0 else 1.0
    
    # Correlation penalty
    portfolio_corr = get_correlation_to_portfolio(pick.symbol)
    if portfolio_corr > 0.7:
        corr_scalar = 0.5
    elif portfolio_corr > 0.5:
        corr_scalar = 0.75
    else:
        corr_scalar = 1.0
    
    # Final size
    position_size = half_kelly * vol_scalar * corr_scalar
    
    # Hard caps
    position_size = min(position_size, 0.10)  # Max 10% per pick
    position_size = max(position_size, 0.01)  # Min 1% per pick
    
    return portfolio_value * position_size
```

---

## Strong Signal Example: SP-v015 Analysis

Looking at the current batch, here's what SHOULD have been filtered:

| Symbol | Dir | R:R | Issue | Should Be |
|--------|-----|-----|-------|-----------|
| BTCUSDT (copy_hl) | SHORT | 0.8x | R:R < 1.0 | **BLOCKED** |
| ETHUSDT (clone) | SHORT | 0.4x | R:R < 1.0 | **BLOCKED** |
| LINKUSDT | SHORT | 1.05x | R:R < 1.5 | **BLOCKED** |
| LTCUSDT | SHORT | 1.05x | R:R < 1.5 | **BLOCKED** |
| BTCUSDT (keltner) | SHORT | 1.18x | R:R < 1.5 | **BLOCKED** |
| BNBUSDT | SHORT | 2.2x | ✅ Good | KEEP |
| SIRENUSDT | SHORT | 2.97x | ✅ Good | KEEP |
| AVAXUSDT | LONG | 1.46x | R:R < 1.5 | **BLOCKED** |
| XRPUSDT | LONG | 1.48x | R:R < 1.5 | **BLOCKED** |

**Result:** 11 picks → 2 strong signals (BNB, SIREN) with R:R > 2.0

---

## Expected Performance of Strong Signal System

Based on backtest data from Method 4 and Smart Picks analysis:

| Metric | Current (All Picks) | Strong Signal (Filtered) |
|--------|--------------------|--------------------------|
| Win Rate | 41.9% | 65-70% |
| Profit Factor | 1.19 | 1.8-2.2 |
| Avg Win | +4.04% | +5.2% |
| Avg Loss | -2.46% | -1.8% |
| Expectancy | +0.26% | +1.8% |
| Max Drawdown | Unknown | <15% |
| Sharpe | 2.95 (inflated) | 1.5-2.0 |
| Trades per week | ~50 | ~5-10 |

---

## Implementation Status (Updated 2026-03-24)

### Phase 1: Hard Gates — DEPLOYED
- [x] Regime alignment hard gate — `strong_signals.py` filter 1
- [x] R:R >= 1.5 hard gate — `strong_signals.py` filter 2
- [x] Strategy validation hard gate — `strong_signals.py` filter 3
- [x] Wired into `alpha-engine-live.yml` workflow (runs every 30 min)
- [x] Gold star badge on audit dashboard for strong signals

### Phase 2: Scoring Fixes — DEPLOYED
- [x] Confidence scoring fixed (0.60-0.70 = max 8pts) — `strong_signals.py`
- [x] Track record doubled to 20pts — `strong_signals.py`
- [x] Half-Kelly position sizing with vol scaling — `strong_signals.py`
- [x] Non-crypto TP/SL caps — `non_crypto_policy.py` (forex 1%/0.5%, equity 5%/3%)

### Phase 3: Advanced Monitoring — DEPLOYED
- [x] Prediction quality tracker (14 metrics hourly) — `prediction_quality_tracker.py`
- [x] Feature stability monitor — `feature_stability_monitor.py`
- [x] Rolling walk-forward validation — `rolling_walk_forward.py`
- [x] Dynamic ensemble weighting — `dynamic_ensemble.py`
- [x] Prediction anomaly detector — `prediction_anomaly_detector.py`
- [ ] Volume-percentile gating — pending
- [ ] Portfolio correlation caps — pending
- [ ] Microstructure regime detection — pending (VPIN requires tick data)

---

## Live Metric Targets & Improvement Tracking

The prediction quality tracker (`prediction_quality_tracker.py`) runs hourly and writes to `data/prediction_quality_history.json`. Monitor these targets:

| Metric | Current Baseline | 2-Week Target | 1-Month Target | 3-Month Target |
|--------|-----------------|---------------|----------------|----------------|
| Hit Rate (directional) | ~50% | >55% | >60% | >65% |
| Profit Factor (7d) | ~1.2 | >1.3 | >1.5 | >1.8 |
| Sharpe Ratio (daily) | ~0.85 | >1.0 | >1.2 | >1.5 |
| Max Drawdown | Unknown | <20% | <15% | <10% |
| Confidence-Profit Corr | Unknown | >0.05 | >0.10 | >0.15 |
| WR Trend (7d vs 30d) | Flat | 7d > 30d | Sustained | Sustained |
| Alpha vs BTC B&H (7d) | Unknown | Positive | >2% | >5% |
| Avg R:R of Winners | ~1.5 | >1.8 | >2.0 | >2.2 |
| Strong Signal Pass Rate | ~7% | 5-10% | 5-10% | 5-10% |
| Strong Signal WR | Unknown | >60% | >65% | >70% |
| Max Consecutive Losses | 26 | <15 | <10 | <8 |

### Key Signposts for "Ready for Real Money"
1. Strong signal WR >60% sustained over 30+ days
2. Profit factor >1.5 on strong signals for 3 consecutive months
3. Max drawdown <15% across all regimes
4. Confidence-profit correlation >0.1 (predictions have real information)
5. Alpha vs BTC buy-and-hold positive for 3 consecutive months
6. Strategy track record: 10+ validated strategies with >50% OOS WR

---

## Summary: The Strong Signal Checklist

A pick qualifies as "strong signal" ONLY if:

- [x] Direction matches regime (LONG in bull, SHORT in bear)
- [x] R:R >= 1.5 (optimal: 2.0-2.5)
- [x] Strategy has 10+ trades at >= 45% WR
- [x] Confidence 0.55-0.80 (0.60-0.70 = best)
- [x] Stop distance 1.5-3%
- [x] Not from banned system (rapid_fire, etc.)
- [ ] Symbol not over-concentrated in portfolio (pending)
- [ ] Correlation to existing picks < 0.7 (pending)

**Expected output:** 5-10 strong signals per week with 65%+ WR and PF > 1.5

All infrastructure is now deployed. The remaining work is **time + data accumulation + iteration**.

---

*Strong signals beat quantity. Every time.*
