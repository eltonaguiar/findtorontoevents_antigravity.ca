# Multi-Asset Strategy Expansion Analysis
## Date: 2026-04-12

---

## 1. GRADUATION CANDIDATES (Baby Strategies Ready for Production)

Based on analysis of `alpha_engine/data/strategy_performance.json`:

**Quality Gates Applied:**
- Win Rate >= 45%
- Profit Factor >= 1.2
- Total PnL > 0
- Minimum 5 trades

### Top Graduates (10 candidates found):

| Strategy | Trades | WR | PF | PnL% | Statistically Significant |
|----------|--------|----|----|------|---------------------------|
| ml_enhanced_FETUSDT_1d_B_lightgbm | 30 | 80.0% | 43.03 | 8.3% | * |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | 35 | 65.7% | 4.41 | 1.6% | * |
| ml_enhanced_BNBUSDT_15m_B_lightgbm | 19 | 89.5% | 58.82 | 0.9% | * |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | 25 | 64.0% | 2.81 | 0.9% | |
| ml_enhanced_TONUSDT_4h_D_ensemble_stack | 9 | 88.9% | 7.92 | 0.5% | * |
| ml_enhanced_APEUSDT_1d_D_ensemble_stack | 12 | 75.0% | 4.32 | 0.3% | * |
| macd_crossover | 16 | 68.8% | 4.09 | 0.2% | |
| ml_enhanced_FETUSDT_15m_B_lightgbm | 17 | 70.6% | 1.35 | 0.1% | * |
| rsi_overbought | 5 | 60.0% | 2.25 | 0.1% | |
| ml_enhanced_ADAUSDT_15m_B_lightgbm | 16 | 75.0% | 1.46 | 0.0% | * |

**Recommendation:** Graduate these 10 strategies to production pipeline with proper symbol/asset class restrictions.

---

## 2. KILL LIST (Strategies to Remove)

Based on performance analysis - WR < 35% OR PF < 0.8 OR PnL < -50%:

| Strategy | Trades | WR | PF | PnL% |
|----------|--------|----|----|------|
| quan_engine_scalp | 3305 | 28.5% | 0.39 | -577.7% |
| ... (20+ total identified) |

**Recommendation:** Remove these underperformers from the active pipeline to reduce drawdown and improve aggregate metrics.

---

## 3. NEW STRATEGY EXPANSION TEST

Created comprehensive strategy expansion bundle testing 10 core strategies across 5 asset classes:

### Strategies Tested:
- bollinger_mr (Mean Reversion)
- rsi_reversal (RSI Oversold)
- macd_crossover (MACD Cross)
- supertrend (Trend Following)
- keltner_mr (Keltner Channel MR)
- stochastic_mr (Stochastic MR)
- adx_trend (ADX Trend)
- williams_r (Williams %R)
- ema_cross (EMA Crossover)
- breakout (Price Breakout)

### Results Summary:
- **All 10 strategies failed** quality gates in quick test
- New strategies need more parameter tuning before deployment
- The framework is ready for more extensive testing

---

## 4. ASSET CLASS SYMBOLS MAPPING

| Asset Class | Available Symbols (USDT) |
|-------------|-------------------------|
| FOREX | EURUSDT, GBPUSDT, AUDUSDT, USDCAD, USDJPY, USDCHF, NZDUSDT |
| COMMODITY | PAXGUSDT, XAUTUSDT, XLMUSDT, DOTUSDT, AVAXUSDT, LINKUSDT, UNIUSDT |
| EQUITY | BNBUSDT, SOLUSDT, ADAUSDT, XRPUSDT, DOGEUSDT, MATICUSDT, LTCUSDT, ETCUSDT |
| ETF | BTCTUSDT, PAXGUSDT, LINKUSDT |
| FUTURES | PERPUSDT, SOLUSDT, ETHUSDT, BTCUSDT |

---

## 5. RECOMMENDATIONS

### Immediate Actions:
1. **Graduate 10 baby strategies** to production (see table above)
2. **Kill 20 underperforming strategies** from active pipeline
3. **Tune new expansion strategies** - current parameters too strict

### Next Steps:
1. Run Layer 1-5 backtest on graduate candidates
2. Create asset-class specific parameter sets for new strategies
3. Integrate graduates into forward_test_portfolios.py
4. Monitor graduate performance in live trading

---

## Files Created:
- `baby_strategies/multi_asset_expansion_bundle.py` - Full expansion bundle
- `baby_strategies/quick_expansion_test.py` - Quick test framework
- `STRATEGY_EXPANALYSIS.md` - This document