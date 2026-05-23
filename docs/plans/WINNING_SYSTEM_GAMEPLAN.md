# The ANTIGRAVITY Winning System Gameplan
## A Path to Predictive Alpha with Institutional Risk Management

**Version:** 1.0  
**Date:** 2026-03-15  
**Status:** Ready for Implementation

---

## Executive Summary

This document synthesizes our existing infrastructure—400K+ mutation evaluations, vectorized backtesting engines, forward-test tracking, and institutional-grade risk systems—into a cohesive strategy for achieving **consistent, statistically-proven market outperformance** across crypto, forex, and futures markets.

### Key Principles
1. **Prove First, Trade Second** — No strategy enters production without 574+ trade statistical validation
2. **Evolution Over Creation** — Use 4-island mutation engine to discover edges, not guess them
3. **Risk-First Architecture** — Circuit breakers, VaR limits, and dynamic position sizing are non-negotiable
4. **Multi-Asset, Multi-Strategy** — Diversify across regimes, not just symbols

---

## Phase 1: Strategy Discovery (The Mutation Engine)

### 1.1 The 400K Evaluation Funnel

**Current Infrastructure:**
- `alpha_engine/run_massive_mutations.py` — 400K eval runner with 4-island evolution
- `genome/mutation_lab/super_mutations.py` — Crossbreeds proven strategies
- `genome/mutation_lab/promoter.py` — Anti-overfit gates and walk-forward validation

**Process:**

```
Tier 1: Fast Screening (100 candles)
├── 400,000 random mutations across 4 islands
├── Differential Evolution + Gaussian mutation
└── Filter: Min 20 trades, positive expectancy

Tier 2: Validation (500 candles)  
├── Top 10% from Tier 1
├── Multi-symbol robustness (6+ symbols)
├── Noise injection (0.1% per trade)
└── Filter: OOS > 50% of IS performance

Tier 3: Live Simulation (2000 candles)
├── Top 1% from Tier 2
├── Walk-forward analysis (60/40 split)
├── DSR (Deflated Sharpe Ratio) > 1.0
└── Survivors: "Genomes" enter forward test
```

**What to Run:**
```bash
# Weekly mutation run (Saturdays 2am UTC)
python alpha_engine/run_massive_mutations.py --generations 500 --symbols BTCUSDT,ETHUSDT,SOLUSDT

# Promote survivors to forward test
python genome/mutation_lab/promoter.py --input alpha_engine/data/massive_mutation_results.json
```

### 1.2 The ONLY Two Proven Strategy Families

From 574+ real trades analyzed, only these families show statistical significance:

| Family | Core Edge | Win Rate | Sharpe | Status |
|--------|-----------|----------|--------|--------|
| **Keltner Compression Expansion** | Volatility breakout after compression | 72.9% | 2.1 | ✅ PROVEN |
| **Multi-Period RSI Confluence** | Multi-timeframe momentum alignment | 64.0% | 10.86 | ✅ PROVEN |

**All mutations should recombine from these genes.**

---

## Phase 2: Validation Architecture

### 2.1 The Three-Legged Validation Stool

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   VECTORIZED    │  │  EVENT-DRIVEN   │  │  FORWARD TEST   │
│   SCREENING     │→ │   VALIDATION    │→ │   (LIVE)        │
│                 │  │                 │  │                 │
│ < 2 min / strat │  │ < 30 min / strat│  │ 30 days minimum │
│ KIMI_RISEOFTHE  │  │ alpha_engine/   │  │ genome/mutation │
│ CLAW/backtest_  │  │ backtest/engine │  │ _lab/ag_forward │
│ engine.py       │  │ .py             │  │ _tracker.py     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
       │                      │                      │
       └──────────────────────┼──────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │  PROMOTION TO   │
                    │   PRODUCTION    │
                    │  (Confidence:   │
                    │    >95%)        │
                    └─────────────────┘
```

### 2.2 Statistical Thresholds for Promotion

| Metric | Minimum Threshold | Target |
|--------|------------------|--------|
| **Total Trades** | 100 (backtest) + 30 (forward) | 200+ |
| **Win Rate** | >55% (p < 0.05 via Z-test) | >60% |
| **Sharpe Ratio** | >1.0 | >1.5 |
| **Max Drawdown** | <15% | <10% |
| **Profit Factor** | >1.3 | >1.5 |
| **DSR (Deflated Sharpe)** | >0.8 | >1.2 |
| **OOS/IS Ratio** | >0.5 | >0.8 |

---

## Phase 3: Multi-Asset Strategy Matrix

### 3.1 Crypto (Primary Focus)

**Proven Techniques:**
- **LSTM + ARIMA Ensemble** (`docs/the research.litcoffee` lines 58-200)
- **Funding Rate Arbitrage** — Premium divergence mean-reversion
- **Cross-Asset Momentum** — BTC → ETH → SOL lag exploitation
- **On-Chain Flow Analysis** — Exchange inflow/outflow signals

**Symbols:** BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, DOGEUSDT, AVAXUSDT  
**Timeframes:** 15m, 1h, 4h (avoid <15m noise)

**Implementation:**
```python
# From genome/mutation_lab/super_mutations.py
SUPER_MUTATION_STRATEGIES = {
    "keltner_compression_expansion": keltner_compression_strategy,
    "rsi_confluence_multi_tf": rsi_confluence_strategy,
    "funding_rate_arbitrage": funding_arb_strategy,
}
```

### 3.2 Forex (Secondary - Requires COT)

**Current Status:** 0/8 wins — needs fundamental overlay

**Required Additions:**
1. **COT Positioning Data** — Commitment of Traders extremes
2. **Carry Volatility Timing** — High-yield vs safe-haven dynamics
3. **Macro Calendar Filter** — NFP, CPI, FOMC volatility windows

**Symbols:** EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD  
**Timeframes:** 1h, 4h, 1d (avoid high-spread periods)

**Implementation Path:**
- Integrate `onchain_metrics_agent.py` pattern for COT data
- Use `funding_arb_analysis.py` logic for carry trades
- Add `market_regime_detector.py` for vol-timing

### 3.3 Futures (Tertiary - Term Structure)

**Proven Techniques:**
- **Term Structure Arbitrage** — Contango/backwardation roll yield
- **Calendar Spreads** — Inter-month mispricing
- **Cross-Asset Correlation** — Gold/oil/equity dispersion

**Symbols:** ES, NQ, GC, CL, ZB  
**Focus:** Micro-contracts for position sizing granularity

---

## Phase 4: Risk Management Architecture

### 4.1 The Risk Layer Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    PORTFOLIO LEVEL                          │
│  • Global Max DD: 8% (circuit breaker)                      │
│  • Daily VaR Limit: 2% of equity                            │
│  • Auto-flatten on breach                                   │
│  File: portfolio_circuit_breaker.py                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     SLEEVE LEVEL                            │
│  • Per-asset max DD: 6%                                     │
│  • Correlation-aware position sizing                        │
│  • Dynamic volatility scaling (Kelly-derived)               │
│  File: risk_quantification_agent.py                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    STRATEGY LEVEL                           │
│  • Per-strategy max risk: 1% of equity                      │
│  • Concurrent positions: Max 3 per symbol                   │
│  • Max hold time: Strategy-defined (default 12 bars)        │
│  File: genome/mutation_lab/backtest_antigravity.py          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     TRADE LEVEL                             │
│  • Stop Loss: 1.3x ATR (dynamic)                            │
│  • Take Profit: 2.3x ATR (R:R = 1.77)                       │
│  • Slippage assumption: 0.05% per trade                     │
│  File: alpha_engine/run_massive_mutations.py                │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Position Sizing Formula

```python
def calculate_position_size(equity, volatility, confidence, max_risk=0.01):
    """
    Kelly-derived fractional sizing with volatility scaling
    """
    # Base Kelly fraction (from backtest edge)
    kelly_f = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
    
    # Half-Kelly for safety
    half_kelly = kelly_f * 0.5
    
    # Volatility scaling (target 20% annualized vol)
    vol_scalar = 0.20 / current_volatility
    
    # Confidence decay (new strategies start at 25% size)
    confidence_mult = min(1.0, confidence)
    
    # Final size
    risk_amount = equity * max_risk * half_kelly * vol_scalar * confidence_mult
    position_size = risk_amount / (atr * 1.3)  # 1.3x ATR stop
    
    return position_size
```

### 4.3 Circuit Breaker States

```python
from portfolio_circuit_breaker import PortfolioCircuitBreaker

breaker = PortfolioCircuitBreaker(
    global_max_dd_percent=8.0,
    sleeve_max_dd_percent=6.0,
    cooldown_minutes=30,
    auto_flatten_on_trigger=True
)

# In trading loop
equity = get_portfolio_value()
breaker.update_equity(equity)

if not breaker.can_trade():
    logger.critical(f"CIRCUIT BREAKER: {breaker.get_status()}")
    close_all_positions()
    sleep(breaker.remaining_cooldown())
```

---

## Phase 5: Live Execution Framework

### 5.1 The Hourly Monitor

**File:** `hourly_strategy_monitor.py`  
**Schedule:** Every hour at :17 minutes

**Actions:**
1. Pull all active picks from 3 systems (KIMI, Crypto, Forex)
2. Update unrealized PnL
3. Check circuit breaker status
4. Log to `alpha_engine/data/pick_monitor_report.json`

**Quality Score Calculation:**
```
Quality Score = (Win Rate * 0.4) + (Sharpe * 0.3) + (Profit Factor * 0.2) + (Activity * 0.1)
Current Baseline: 60.3% (needs improvement to >75%)
```

### 5.2 The Forward Test Tracker

**File:** `genome/mutation_lab/ag_forward_tracker.py`

**Process:**
1. New genomes enter 30-day forward test (paper trading)
2. Track: Win rate, Sharpe, max DD, trade frequency
3. Auto-promote if metrics exceed thresholds
4. Auto-demote if <50% win rate after 20 trades

### 5.3 Execution Checklist

Before ANY trade:
- [ ] Circuit breaker status = NORMAL
- [ ] Strategy confidence > 0.5 (25% size if < 0.75)
- [ ] Position size < max risk per trade (1% equity)
- [ ] No correlated position already open
- [ ] Market regime = favorable (not extreme vol)
- [ ] Stop loss and take profit calculated (ATR-based)

---

## Phase 6: The Path to 75%+ Quality Score

### 6.1 Current State Analysis

| System | Trades | Win Rate | Status |
|--------|--------|----------|--------|
| Battleground | 298 | 61.7% | ✅ KEEP |
| Cross Aggregation | 48 | 58.3% | ✅ KEEP |
| Claude Gainer ML | 32 | 56.2% | ✅ KEEP |
| KIMI | -112% cumulative | 0% (inverse) | ❌ FADE |
| Forex | 0/8 | 0% | ❌ NEEDS COT |

### 6.2 Improvement Roadmap

**Week 1-2: Inverse KIMI**
- Take opposite of KIMI signals
- Track performance separately
- Expected: +20% quality score boost

**Week 3-4: Forex COT Integration**
- Add COT positioning overlay
- Trade only extreme positioning + technical alignment
- Target: 55%+ win rate

**Week 5-8: Mutation Survivors**
- 9 genomes from 400K evals enter forward test
- Promote top 2-3 to production
- Retire bottom 20% of current strategies

**Week 9-12: Ensemble Weighting**
- Dynamic weighting based on recent performance
- Bayesian model averaging
- Target: 75% quality score

---

## Phase 7: Technology Stack

### 7.1 Required Components

| Component | File | Purpose |
|-----------|------|---------|
| **Mutation Engine** | `alpha_engine/run_massive_mutations.py` | Strategy discovery |
| **Vectorized Backtest** | `KIMI_RISEOFTHECLAW/backtest_engine.py` | Fast screening |
| **Event Backtest** | `alpha_engine/backtest/engine.py` | Precise validation |
| **Forward Tracker** | `genome/mutation_lab/ag_forward_tracker.py` | Live testing |
| **Risk Manager** | `risk_quantification_agent.py` | VaR, sizing |
| **Circuit Breaker** | `portfolio_circuit_breaker.py` | Drawdown protection |
| **Pick Monitor** | `hourly_strategy_monitor.py` | Hourly tracking |

### 7.2 Data Flow

```
OHLCV Data (yfinance/ccxt)
    ↓
Mutation Engine → Generates Strategies
    ↓
Vectorized Backtest → Screens 400K mutations
    ↓
Event-Driven Backtest → Validates survivors
    ↓
Forward Test (30 days) → Live paper trading
    ↓
Promotion to Production → Live trading
    ↓
Risk Management Layer → Position sizing, circuit breakers
    ↓
Pick Monitor → Tracks all positions hourly
    ↓
Performance Feedback → Retires weak strategies
```

---

## Phase 8: Success Metrics

### 8.1 Monthly KPIs

| Metric | Current | Target 3M | Target 6M |
|--------|---------|-----------|-----------|
| **Quality Score** | 60.3% | 70% | 75%+ |
| **Win Rate (Live)** | ~58% | 62% | 65% |
| **Sharpe Ratio** | ~1.2 | 1.5 | 1.8+ |
| **Max Drawdown** | ~12% | <10% | <8% |
| **Monthly Return** | ~4% | 6% | 8%+ |
| **Strategies Live** | 6 | 10 | 15 |
| **Mutation Survivors** | 9 | 20 | 50 |

### 8.2 Red Lines (Auto-Stop)

- Global drawdown > 8% → Halt all trading, 30-min cooldown
- Any strategy < 50% win rate after 50 trades → Retire immediately
- Daily VaR > 2% → Reduce position sizes by 50%
- Correlation between strategies > 0.7 → Diversify or retire one

---

## Immediate Action Items

### Today
- [ ] Review the 9 mutation survivors in `genome/data/`
- [ ] Start inverse-KIMI paper trading
- [ ] Configure circuit breaker with 8% max DD

### This Week
- [ ] Run full mutation batch: `python alpha_engine/run_massive_mutations.py`
- [ ] Integrate COT data for forex (use `onchain_metrics_agent.py` pattern)
- [ ] Set up hourly monitor cron job

### This Month
- [ ] Promote 2-3 mutation survivors to production
- [ ] Retire bottom 20% of underperforming strategies
- [ ] Achieve 65%+ quality score

---

## Conclusion

We have all the pieces:
- ✅ Mutation engine (400K evals)
- ✅ Vectorized backtesting
- ✅ Risk management (VaR, circuit breakers)
- ✅ Forward test tracking
- ✅ Multi-asset infrastructure

**The path to winning is not building more—it's disciplined execution of what we have.**

Every strategy must prove itself through:
1. 400K mutation screening
2. Vectorized + event-driven validation  
3. 30-day forward test
4. Statistical significance (p < 0.05)
5. Live production with circuit breakers

**Quality Score > 75% is achievable within 90 days.**

---

*Generated: 2026-03-15*  
*Next Review: 2026-03-22*  
*Owner: ANTIGRAVITY Trading Systems*
