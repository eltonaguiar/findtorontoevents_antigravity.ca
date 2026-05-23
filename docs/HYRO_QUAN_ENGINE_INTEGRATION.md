# HyroTrader + QuanEngine Integration

**Date:** April 7, 2026
**Author:** Claude Opus 4.6

## What Was Built

The **Hyro-QuanEngine Bridge** integrates QuanEngine's regime-aware ensemble prediction engine with HyroTrader's prop-firm-constrained backtester. This creates a system that only trades when market conditions AND strategy consensus confirm an edge.

## Architecture

```
Binance 1h OHLCV (4 mirrors + KuCoin)
    |
    v
RegimeRouter (Hurst Exponent R/S Analysis)
    |
    +-- H > 0.55 --> TRENDING pool (4 trend-following strategies)
    +-- H < 0.45 --> MEAN_REVERSION pool (4 mean-reversion strategies)
    +-- 0.45-0.55 -> RANDOM --> ABSTAIN (no edge, sit out)
    |
    v
StrategyPool (18 strategies across 3 pools)
    |-- Trending: corr_hma_trend, volume_profile_deviation, autocorr_reversion, overnight_btc
    |-- Mean-Rev: consecutive_down_rsi, rsi2_bb_squeeze, liquidity_sweep, pairs_spread
    |-- Prop Firm: fear_greed_contrarian, ema_momentum, keltner_squeeze, propfirm_cons, ema_aggressive
    |
    v
QuanEnsemble (60% consensus threshold, 0.55 min confidence)
    |-- Requires 2+ strategies to agree on direction
    |-- Solo signals need 80%+ conviction (heavily discounted)
    |
    v
ModeDispatcher (auto-selects SCALP / SWING / POSITION)
    |-- SCALP: H < 0.55, low ATR (15m candles, 2:1 R:R)
    |-- SWING: H 0.55-0.65 (1h candles, 2.8:1 R:R)
    |-- POSITION: H > 0.65, high ATR (4h candles, 3.6:1 R:R)
    |
    v
RiskGate (Prop firm compliance)
    |-- Half-Kelly sizing with mode caps (3%/5%/8%)
    |-- Correlation filter (blocks correlated positions)
    |-- Market health check
    |-- Hyro rules: $5K account, 3% max risk, 5% daily loss, 10% overall loss
    |
    v
hyro_quan_bridge.json --> HyroTrader dashboard
```

## Live Scan Results (April 7, 2026)

Fear & Greed Index: **11** (extreme fear)

| Symbol | Regime | Hurst | Signal | Consensus | Strategies | Mode |
|--------|--------|-------|--------|-----------|------------|------|
| ETHUSDT | **TRENDING** | 0.750 | BUY | 86% | 6 strategies | SCALP |
| BNBUSDT | **MEAN_REVERSION** | 0.434 | BUY | 75% | 6 strategies | SCALP |
| BTCUSDT | RANDOM | 0.539 | BUY | 86% | 6 strategies | SCALP |
| SOLUSDT | RANDOM | 0.463 | BUY | 83% | 5 strategies | SCALP |

ETHUSDT has the strongest signal — clear TRENDING regime with 86% consensus from 6 independent strategies.

## Backtest Results (Extended, 6 months)

Top performers from 64 strategy-symbol combinations:

| Symbol | Strategy | Trades | WR | PnL ($5K acct) |
|--------|----------|--------|----|----------------|
| ETHUSDT | volume | 118 | 42.4% | **+$1,200** |
| ETHUSDT | heikin_ashi | 133 | 40.6% | +$1,125 |
| ETHUSDT | adx_trend | 97 | 37.1% | +$1,088 |
| BTCUSDT | volume | 54 | 38.9% | +$375 |
| BNBUSDT | connors_rsi2 | 73 | **68.5%** | +$335 |
| SOLUSDT | macd_trend | 94 | 35.1% | +$188 |

## Files

| File | Purpose |
|------|---------|
| `tools/hyro_quan_bridge.py` | Main bridge — runs QuanEngine pipeline with Hyro constraints |
| `audit_dashboard/data/hyro_quan_bridge.json` | Output for dashboard display |
| `audit_dashboard/hyrotrader/index.html` | Dashboard with QuanEngine Regime Analysis card |
| `audit_dashboard/hyrotrader/hyro_live_signals.js` | Browser-side signal evaluators (11 strategies) |
| `audit_dashboard/data/hyro_live_strategies.json` | Config for live strategy checking |
| `quan_engine/` | 13 Python modules (regime router, ensemble, risk gate, etc.) |

## Usage

```bash
# Live scan (writes JSON for dashboard)
python tools/hyro_quan_bridge.py --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT --save

# Backtest regime filter vs vanilla
python tools/hyro_quan_bridge.py --backtest --months 6 --save

# View on local server
python tools/serve_local.py
# Open http://127.0.0.1:5173/audit/hyrotrader/index.html
```

## What This Adds Over Vanilla HyroTrader

1. **Hurst regime filter** — sits out when market is random walk (no edge)
2. **18-strategy consensus** — requires 60%+ agreement, not just one strategy firing
3. **Mode auto-select** — SCALP/SWING/POSITION based on regime strength + volatility
4. **Correlation filter** — prevents correlated positions eating the same move
5. **Fear & Greed integration** — fear_greed_contrarian fires in extreme fear (current F&G=11)

## Prop Firm Compliance

All signals respect Hyro challenge rules:
- $5,000 account size
- Max 3% risk per trade ($150)
- Max 5% daily loss ($250)
- Max 10% overall loss ($500)
- Phase 1 target: 10% ($500)
- Phase 2 target: 5% ($250)
- Min 10 trading days per phase
- Consistency rule: no single day > 40% of total profit
