# Strategy Exposure Review + Expansion Backtests

Generated: 2026-04-12T20:37:16.953350+00:00

## Strong But Underexposed Strategies

- ml_enhanced_BNBUSDT_15m_B_lightgbm: WR 89.5% | PF 58.82 | closed 19 | symbols 1
- ml_enhanced_TONUSDT_4h_D_ensemble_stack: WR 87.5% | PF 3.50 | closed 8 | symbols 1
- ml_enhanced_FETUSDT_1d_B_lightgbm: WR 80.0% | PF 43.03 | closed 30 | symbols 1
- ml_enhanced_INJUSDT_1d_B_lightgbm: WR 78.6% | PF 3.55 | closed 14 | symbols 1
- ml_enhanced_APEUSDT_1d_D_ensemble_stack: WR 75.0% | PF 4.32 | closed 12 | symbols 1
- ml_enhanced_STRKUSDT_15m_D_ensemble_stack: WR 73.3% | PF 3.26 | closed 15 | symbols 1
- ml_enhanced_ADAUSDT_15m_B_lightgbm: WR 73.3% | PF 1.37 | closed 15 | symbols 1
- ml_enhanced_RENDERUSDT_1h_D_ensemble_stack: WR 70.6% | PF 5.39 | closed 34 | symbols 1
- ml_enhanced_RENDERUSDT_4h_D_ensemble_stack: WR 69.6% | PF 3.91 | closed 23 | symbols 1
- ml_enhanced_FETUSDT_15m_B_lightgbm: WR 68.8% | PF 1.28 | closed 16 | symbols 1
- ml_enhanced_DOGEUSDT_15m_D_ensemble_stack: WR 68.8% | PF 1.20 | closed 16 | symbols 1

## Expansion Backtest Recommendations

- ml_enhanced_ensemble_transfer -> ETF IWM: WR 25.0% | PF 1.91 | trades 40 | avg +0.481%
- ml_enhanced_ensemble_transfer -> EQUITY NVDA: WR 38.6% | PF 1.87 | trades 44 | avg +1.083%
- ml_enhanced_ensemble_transfer -> EQUITY MSFT: WR 43.1% | PF 1.81 | trades 65 | avg +0.394%
- ml_enhanced_lightgbm_transfer -> ETF SPY: WR 26.7% | PF 1.68 | trades 75 | avg +0.336%
- ml_enhanced_ensemble_transfer -> CRYPTO ADA-USD: WR 31.2% | PF 1.63 | trades 64 | avg +1.390%
- ml_enhanced_lightgbm_transfer -> CRYPTO BNB-USD: WR 21.3% | PF 1.55 | trades 122 | avg +0.816%
- ml_enhanced_lightgbm_transfer -> FOREX USDJPY=X: WR 19.0% | PF 1.49 | trades 84 | avg +0.166%
- ml_enhanced_lightgbm_transfer -> FUTURES GC=F: WR 25.3% | PF 1.49 | trades 87 | avg +0.310%
- ml_enhanced_lightgbm_transfer -> ETF QQQ: WR 25.0% | PF 1.46 | trades 88 | avg +0.297%
- ml_enhanced_lightgbm_transfer -> FUTURES ES=F: WR 19.7% | PF 1.45 | trades 66 | avg +0.244%
- ml_enhanced_lightgbm_transfer -> FOREX GBPUSD=X: WR 18.9% | PF 1.44 | trades 111 | avg +0.092%
- ml_enhanced_lightgbm_transfer -> EQUITY META: WR 21.5% | PF 1.42 | trades 79 | avg +0.463%
- ml_enhanced_ensemble_transfer -> CRYPTO ETH-USD: WR 34.0% | PF 1.39 | trades 53 | avg +0.675%
- ml_enhanced_lightgbm_transfer -> ETF GLD: WR 25.3% | PF 1.38 | trades 91 | avg +0.259%
- ml_enhanced_ensemble_transfer -> ETF SPY: WR 39.6% | PF 1.35 | trades 53 | avg +0.137%
- ml_enhanced_ensemble_transfer -> ETF QQQ: WR 37.9% | PF 1.34 | trades 58 | avg +0.193%

Note: these transfers show positive expectancy and PF > 1.3 despite lower raw WR, implying asymmetric payoff structures. Use tighter risk caps and regime filters before promoting to production.

## Files
- C:\findtorontoevents_antigravity.ca\audit_dashboard\data\strategy_expansion_backtests.json
