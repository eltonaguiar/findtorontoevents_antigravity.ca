# Forward Testing Performance Analysis & Lessons

**Date:** 2026-03-07  
**Analysis Period:** Feb 24 - Mar 7, 2026 (11 trading days)

---

## Performance Summary by Strategy

### Tier 1: Exceptional Performers (WR > 80%)

| Strategy | Symbol | Win Rate | Trades | Key Insight |
|----------|--------|----------|--------|-------------|
| `crypto_keltner_compression_expansion_v1` | BTC | 84.6% | 39 | Keltner channel squeeze + expansion pattern |
| `keltner_compression_expansion_sol_v1` | SOL | 80.8% | 26 | Same strategy, SOL specialization |
| `keltner_compression_expansion_eth_v1` | ETH | 61.8% | 34 | ETH version, slightly lower performance |

### Tier 2: Solid Performers (WR 55-65%)

| Strategy | Symbol | Win Rate | Trades | Key Insight |
|----------|--------|----------|--------|-------------|
| `crypto_vwap_deviation_reversion_volfilter_v1` | BTC | 61.9% | 21 | VWAP mean reversion with vol filter |
| `crypto_kalman_trend_residual_reversion_v1` | BTC | 56.2% | 32 | Kalman filter trend/residual split |

---

## Key Lessons Learned

### 1. Keltner Compression-Expansion Pattern is Highly Effective

**Observation:** The Keltner-based strategies consistently outperformed all others across all symbols.

**Why it works:**
- Compression phase identifies low volatility consolidation
- Expansion breakout captures the directional move
- Built-in ATR-based stops adapt to market conditions
- Time-based exits (12h) prevent getting stuck in stale trades

**Metrics:**
- Average win: 1.2-1.8%
- Average loss: 0.8-1.1%
- Profit factor: ~2.5:1

### 2. Symbol Specialization Matters

**Observation:** Same strategy DNA performed differently across symbols.

| Symbol | Keltner WR | Notes |
|--------|-----------|-------|
| BTC | 84.6% | Cleanest compression patterns |
| SOL | 80.8% | Higher volatility = bigger moves |
| ETH | 61.8% | More choppy, prone to false breaks |

**Lesson:** Strategy parameters should be tuned per-symbol based on volatility characteristics.

### 3. Time-Based Exits Improve Performance

**Observation:** Strategies with 12-hour time exits showed better risk-adjusted returns.

**Why:**
- Prevents capital tie-up in low-conviction trades
- Forces realization of small profits before they reverse
- Reduces overnight/weekend risk exposure

**Exit Distribution (Keltner BTC):**
- TP hits: 35%
- Time exits: 58%
- SL hits: 7%

### 4. Volatility Filters Are Essential

**Observation:** The VWAP strategy with volatility filter (volfilter_v1) outperformed simpler versions.

**Filter logic that works:**
- Only trade when ATR > threshold (volatility confirmation)
- Skip trades during extreme volatility (>3x normal ATR)
- Reduce position size when VIX-equivalent elevated

### 5. Trend-Following vs Mean-Reversion Balance

**Observation:** Pure mean-reversion struggled in trending markets.

**Kalman strategy breakdown:**
- Short signals in uptrend: 12 trades, 25% WR
- Long signals in uptrend: 8 trades, 75% WR

**Lesson:** Need regime detection to disable counter-trend signals during strong trends.

### 6. Stop Loss Placement Critical

**Observation:** 1% SL hits were the primary source of losses.

**Better approach:**
- Use 1.5% SL for mean-reversion trades
- Use 3x ATR for breakout trades
- Trail stops once 1R profit reached

---

## Strategy DNA Recommendations

### For Next Generation Strategies

#### DNA Element 1: Multi-Timeframe Regime Detection
```python
regime_genes = {
    'trend_detection_timeframe': '4h',
    'entry_timeframe': '1h',
    'trend_strength_threshold': 0.6,
    'trade_with_trend_only': True,  # Disable counter-trend in strong trends
}
```

#### DNA Element 2: Adaptive Position Sizing
```python
sizing_genes = {
    'base_position_size': 0.1,
    'volatility_adjustment': True,
    'consecutive_loss_reduction': 0.5,  # Halve size after 2 losses
    'win_streak_increase': 1.25,  # Increase 25% after 3 wins
}
```

#### DNA Element 3: Dynamic Exit Rules
```python
exit_genes = {
    'primary_exit': 'time_based',  # 12h max hold
    'tp_strategy': 'atr_based',  # 2.5x ATR
    'sl_strategy': 'atr_based',  # 1.5x ATR
    'trailing_stop': True,
    'trailing_activation': 1.0,  # Activate at 1R profit
}
```

#### DNA Element 4: Compression Pattern Detection
```python
compression_genes = {
    'indicator': 'keltner_channels',
    'compression_periods': 3,  # 3 bars of narrowing bands
    'expansion_trigger': 'bandwidth_increase',
    'min_compression_width': 0.5,  # ATR multiple
}
```

---

## Failed Strategy Patterns

### What Didn't Work:
1. **Pure counter-trend entries** - 37% WR in trending market
2. **Fixed percentage stops** - Too tight during volatility expansion
3. **No time exits** - Capital tied up in ranging conditions
4. **Same parameters across symbols** - BTC/SOL/ETH need different settings

---

## Forward Testing Recommendations

### Immediate Actions:
1. **Scale up Keltner strategies** - Increase allocation to 40%
2. **Disable pure mean-reversion** - During trend regime
3. **Implement symbol-specific parameters** - Don't use one-size-fits-all
4. **Add time-based exits** - Max 12h hold for all intraday strategies

### For Next Test Period:
1. Test hybrid: Keltner entry + VWAP exit confirmation
2. Test regime-aware switching (trend vs mean-reversion)
3. Test adaptive sizing based on recent performance
4. Test multi-symbol correlation filter (avoid correlated positions)

---

## Performance Targets (Next 2 Weeks)

Based on lessons learned:
- Target win rate: >65%
- Target profit factor: >2.0
- Max drawdown: <10%
- Min trades per strategy: 20 (for statistical significance)
