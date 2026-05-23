# Crypto Hybrid Reversion-Momentum Ensemble
**Bundle Registration: Feb 28, 2026**

---

## Bundle Composition

| # | Strategy | Type | Weight | Rationale |
|---|----------|------|--------|-----------|
| 1 | **Williams %R Trend-Aligned** | Mean Reversion (NEW) | 25% | Trend-continuation pullbacks via %R oscillator |
| 2 | **Connors RSI-2** | Mean Reversion (PROVEN) | 25% | Pure short-term extreme MR, ultra-fast |
| 3 | **Bollinger Mean Reversion** | Mean Reversion (PROVEN) | 25% | Volatility-channel MR with 200 SMA filter |
| 4 | **ORB Breakout** | Momentum/Trend (PROVEN) | 25% | Toby Crabel session breakout, captures expansions |

---

## Strategy Details

### 1. Williams %R Trend-Aligned Pullback (NEW)
```python
Class: WilliamsPRTrendMRStrategy
File: baby_strategies/williams_pr_trend_mr.py
```

**Logic:**
- **LONG:** Williams %R(14) crosses below -80 AND close > SMA(50)
- **SHORT:** Williams %R(14) crosses above -20 AND close < SMA(50)
- **TP/SL:** ATR-based (3x TP, 2x SL)

**Expected Performance:**
- Win Rate: 62-68%
- Trades per symbol (5yr): 150-350
- Profit Factor: >1.5
- Sharpe: ~0.8-1.0

**Validation Status:** ✅ 8/8 checks passed (synthetic data)
**Next Step:** Run full 5-year backtest on 24 symbols

---

### 2. Connors RSI-2 (PROVEN - TIER 1)
```python
Class: ConnorsRSI2Strategy
Status: DEPLOYED
```

**Performance:**
- Trades: 895
- Win Rate: 68.4%
- Sharpe: 1.17
- Profit Factor: 1.53
- P-value: <0.000001

**Logic:** RSI(2) < 5 + Close > 200SMA → LONG, exit RSI(2) > 65

---

### 3. Bollinger Mean Reversion (PROVEN - TIER 1)
```python
Class: BollingerMeanReversionStrategy
Status: DEPLOYED
```

**Performance:**
- Trades: 361
- Win Rate: 60.7%
- Sharpe: 0.72
- Profit Factor: 1.53
- P-value: 0.00003

**Logic:** Touch lower BB(20,2) + price > 90% of 200SMA → LONG

---

### 4. ORB Breakout (PROVEN - TIER 2)
```python
Class: ORBBreakoutStrategy
Status: DEPLOYED
```

**Performance:**
- Trades: 200+
- Win Rate: 55-60%
- Sharpe: ~0.9
- Profit Factor: ~1.4

**Logic:** Toby Crabel Opening Range Breakout - captures first 4H range break

---

## Bundle Rationale

### Why These 4 Strategies Complement Each Other:

| Dimension | Williams %R | Connors RSI-2 | Bollinger | ORB Breakout |
|-----------|-------------|---------------|-----------|--------------|
| **Trigger** | Oscillator pullback | Extreme oversold | Volatility touch | Range breakout |
| **Speed** | Medium (1H-4H) | Fast (1H) | Medium (1H-4H) | Fast (4H session) |
| **Market** | Trending | Any (with filter) | Any | Trend ignition |
| **Correlation** | Low vs others | Low | Low | Low (momentum) |

### Regime Coverage:
- **Bull Market:** Williams %R pullbacks + ORB long breakouts
- **Bear Market:** Williams %R pullbacks (short) + ORB short breakouts  
- **Sideways:** Pure MR strategies (Williams, Connors, Bollinger)

### Risk Diversification:
- 75% Mean Reversion (high WR, quick turns)
- 25% Momentum (catures trends MR misses)
- Different entry triggers = low signal correlation

---

## Expected Combined Performance

| Metric | Expected | Conservative |
|--------|----------|--------------|
| **Combined Win Rate** | 62-65% | 58-60% |
| **Combined Sharpe** | 1.4-1.8 | 1.0-1.2 |
| **Max Drawdown** | -12% to -15% | -18% to -22% |
| **Trades per Year** | 400-800 across 24 symbols | 300-600 |

**Why Sharpe > 1.0 is realistic:**
- Diversification reduces volatility
- MR strategies have high WR (smooth equity curve)
- Momentum leg captures fat tails
- Combined PF should be 1.4-1.6

---

## Implementation Plan

### Phase 1: Full Backtest (This Week)
```bash
# Run full 5-year backtest on Williams %R
py alpha_engine/survivor_backtest.py \
  --strategy williams_pr_trend_mr \
  --symbols BTC,ETH,SOL,ADA,LINK,AVAX,DOT,MATIC,NEAR,APT,ARB,OP,SUI,SEI,TAO,FET,RNDR,INJ,PYTH,JUP,STRK,BLUR,ARB,MATIC \
  --years 5 \
  --checks all_8
```

### Phase 2: Paper Trading (100+ trades)
- Deploy bundle to paper trading
- Target: 100+ trades per strategy
- Monitor: WR, PF, Sharpe, drawdown

### Phase 3: Live Deployment (If paper succeeds)
- Risk allocation: Equal weight (25% each)
- Position sizing: 2% risk per trade per strategy
- Rebalance: Monthly based on performance

---

## Risk Management

### Position Sizing Formula:
```python
risk_per_trade = 0.02  # 2% of capital
position_size = risk_per_trade / (stop_loss_distance / entry_price)
```

### Max Concurrent Positions:
- Per strategy: 5 max
- Per bundle: 20 max (5 × 4 strategies)
- Per symbol: 2 max (avoid overconcentration)

### Circuit Breakers:
- Stop bundle if combined drawdown > 20%
- Stop individual strategy if WR < 45% over 50 trades
- Stop individual strategy if PF < 1.0

---

## Files Location

```
baby_strategies/
├── williams_pr_trend_mr.py          # NEW - Pending full backtest
├── connors_rsi2.py                   # PROVEN
├── bollinger_mean_reversion.py       # PROVEN
└── orb_breakout.py                   # PROVEN

incubator/backtest_team/
└── forward_signal_scanner.py         # Register in TIER1_STRATEGIES

bundle_registry/
└── crypto_hybrid_ensemble.json       # Bundle configuration
```

---

## Next Actions

1. [ ] Run full 5-year backtest on Williams %R (24 symbols)
2. [ ] Verify Williams %R passes all 8 checks with real data
3. [ ] Register all 4 strategies in forward_signal_scanner.py
4. [ ] Create bundle configuration file
5. [ ] Deploy to paper trading for 100+ trades
6. [ ] Monitor for 2-4 weeks before live deployment

---

## Confidence Assessment

| Component | Confidence | Reason |
|-----------|------------|--------|
| Connors RSI-2 | 95% | 895 trades, proven in production |
| Bollinger MR | 90% | 361 trades, solid stats |
| ORB Breakout | 85% | 200+ trades, good diversification |
| Williams %R | 75% | Validated on synthetic, needs real backtest |
| **Combined Bundle** | **85%** | Diversification + proven core |

---

**Status:** PENDING FULL BACKTEST (Williams %R)
**Target Live Date:** 2-4 weeks (after 100+ paper trades)
