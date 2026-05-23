# Alpha Engine — Multi-Strategy Quantitative Research Platform

A Renaissance-grade research system for discovering, validating, and deploying alpha-generating strategies with robust risk controls.

## Architecture

```
alpha_engine/
├── data/               # Data Layer (7 modules)
│   ├── price_loader    # OHLCV from Yahoo Finance + cache
│   ├── fundamentals    # Quarterly financials, ratios, ROIC
│   ├── macro           # VIX, DXY, Yields, regime classification
│   ├── sentiment       # News RSS + VADER + keyword scoring
│   ├── insider         # SEC Form 4, cluster buy detection
│   ├── earnings        # Surprise history, PEAD, revision momentum
│   └── universe        # Universe management + liquidity filters
│
├── features/           # Feature Factory (14 families)
│   ├── momentum        # Multi-horizon returns, MA slopes, RSI, MACD
│   ├── cross_sectional # Rank returns vs universe, residual momentum
│   ├── volatility      # Realized vol, ATR, beta, kurtosis, Parkinson
│   ├── volume          # Dollar volume, Amihud illiquidity, OBV, flow
│   ├── mean_reversion  # Bollinger z-score, Hurst, stochastic, reversal
│   ├── regime          # Vol/corr/rate/trend regime features
│   ├── fundamental     # ROE, ROIC, Piotroski, accruals, balance sheet
│   ├── growth          # Revenue/earnings growth, PEG, GARP, leverage
│   ├── valuation       # PE/PB/PS ranks, sector-neutral value, deep value
│   ├── earnings_feat   # Consecutive beats, PEAD signal, revision momentum
│   ├── seasonality     # Day-of-week, January effect, turn-of-month
│   ├── options         # IV rank proxy, vol term structure, gamma squeeze
│   ├── sentiment       # Attention proxy, smart money, breadth, confirmation
│   └── flow            # Accumulation, money flow, block trades, short interest
│
├── strategies/         # Strategy Generator (10 strategies)
│   ├── momentum        # Classic momentum, trend following, breakout
│   ├── mean_reversion  # Bollinger MR, short-term reversal
│   ├── earnings_drift  # PEAD, consecutive beats "Safe Bet"
│   ├── quality_value   # Quality compounders, value+quality, dividend aristocrats
│   ├── ml_ranker       # LightGBM/XGBoost cross-sectional ranker
│   └── generator       # Strategy candidate factory
│
├── backtest/           # Backtest Engine
│   ├── engine          # Event-driven backtester, full metrics
│   ├── costs           # IB/Questrade cost models, slippage, spread
│   ├── portfolio       # Portfolio construction, sector limits, drawdown halt
│   └── position_sizing # Kelly criterion, vol targeting, fixed risk
│
├── validation/         # Validation Engine ("Truth Machine")
│   ├── metrics         # Sharpe, Sortino, Calmar, Deflated Sharpe, TACO checklist
│   ├── walk_forward    # Walk-forward optimization
│   ├── purged_cv       # Purged K-fold CV with embargo
│   ├── monte_carlo     # Bootstrap, block bootstrap, White's reality check
│   └── stress_test     # Crisis periods, 3-windows rule, slippage sensitivity
│
├── ensemble/           # Meta-Learner
│   ├── meta_learner    # Strategy Arbitrator (combines all signals)
│   ├── regime_allocator # Regime-aware weight shifting
│   └── signal_combiner # Equal weight, performance weighted, rank average
│
├── reporting/          # Report Generator
│   ├── report_gen      # Markdown/HTML daily reports
│   └── pick_list       # Actionable picks with sizing, stops, rationale
│
└── main.py             # CLI runner
```

## Quick Start

```bash
# Install dependencies
cd alpha_engine
pip install -r requirements.txt

# Generate today's picks (default universe, top 20)
python -m alpha_engine.main --mode picks

# Quick picks (fewer tickers, faster)
python -m alpha_engine.main --mode quick

# Full S&P 500 universe
python -m alpha_engine.main --mode picks --universe sp500 --top-k 30
```

## Key Concepts

### The Alpha Layer (What We Added)
| Signal | Source | Implementation |
|--------|--------|---------------|
| Sentiment Velocity | RSS + VADER | `data/sentiment.py` |
| Insider Cluster Buy | SEC Form 4 | `data/insider.py` |
| Macro Regime Switch | VIX + DXY + TNX | `data/macro.py` → `ensemble/regime_allocator.py` |
| PEAD Drift | Earnings surprises | `data/earnings.py` → `strategies/earnings_drift.py` |
| Dividend Aristocrats | 25+ year div increases | `strategies/quality_value.py` |
| Kelly Criterion | Optimal bet sizing | `backtest/position_sizing.py` |

### Meta-Learner Architecture
1. **Input Layer**: 14 feature families → 150+ variables
2. **Strategy Layer**: 10 strategies generate signals independently
3. **Sentiment Layer**: VADER + keyword scoring on news headlines
4. **Regime Layer**: VIX/DXY/Yield classify market into risk_on/neutral/risk_off/crisis
5. **Arbitrator**: Regime-aware weighting → combined score → final picks
6. **Risk Layer**: Kelly criterion + sector caps + drawdown halt

### Non-Negotiables (TACO Checklist)
- **T**ransaction costs: IB model ($0.005/share + 10bps slippage + spread)
- **A**voided leakage: Purged CV with embargo, walk-forward
- **C**onsistent across regimes: 3-windows test (pre-2020, covid, rate-hike)
- **O**ut-of-sample beats benchmark: Walk-forward Sharpe must be positive

### Risk Management
- Max 2% portfolio risk per momentum trade
- Max 5% for "Safe Bet" dividend aristocrats
- Quarter-Kelly position sizing
- 5% max single position, 25% max sector
- 15% drawdown = halt all trading

## Strategy Descriptions

| Strategy | Edge Source | Holding Period | Risk Level |
|----------|-----------|---------------|-----------|
| Classic Momentum | Behavioral herding | 1 month | Medium |
| Trend Following | Slow info diffusion | 1-3 months | Medium |
| Breakout Momentum | Attention bias | 1-2 weeks | Higher |
| Bollinger MR | Overreaction | 3-5 days | Higher |
| Short-Term Reversal | Liquidity provision | 1-3 days | Higher |
| PEAD (Earnings Drift) | Analyst lag | 6-8 weeks | Medium |
| Consecutive Beats | Earnings quality | 3-6 months | Lower |
| Quality Compounders | Underpriced boring | 6-12 months | Lower |
| Value + Quality | Cheap + good | 3-6 months | Medium |
| Dividend Aristocrats | Flight to quality | 12+ months | Lowest |

## Output

Each run generates:
1. **Pick List**: Top-K stocks with entry, stop, target, sizing
2. **Watchlist**: Stocks approaching buy threshold
3. **Avoid List**: Stocks with upcoming earnings or negative signals
4. **Report**: Full Markdown report with regime, allocation, drivers
5. **JSON**: Machine-readable picks for API consumption
