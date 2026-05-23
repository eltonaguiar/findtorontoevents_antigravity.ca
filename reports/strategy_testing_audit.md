# Strategy Testing Audit — 2026-04-02

## Key Findings
- **148 strategies passed backtest but stuck** — not promoted to forward testing
- **Zero MC validations significant** (all p > 0.05, portfolio = LIKELY_RANDOM)
- **1 super strategy**: crypto_liquidation_flow_exhaustion_v1 (passes BTC+ETH+SOL)
- **11 STRONG/VIABLE strategies lack walk-forward validation**
- **MySQL missing**: walkforward, MC, incubator backtests, strategy scores

## Super Strategy
crypto_liquidation_flow_exhaustion_v1: BTC Sh=2.52, ETH Sh=3.70, SOL Sh=6.51

## Walk-Forward STRONG (p < 0.05)
1. st_bb_squeeze_expansion: 100% WR, 14 trades, p=0.0
2. Bollinger MR: 83.3% WR, 12 trades, p=0.0006
3. hs_lb_None: 91.7% WR, 12 trades, p=0.00002
4. macd_rsi_confluence: 74.1% WR, 27 trades, p=0.00019
5. crypto_kalman_trend_residual_reversion_v1: 83.3% WR, p=0.0067
6. vwap_deviation_reversion_sol_v1: 80% WR, p=0.0083
7. copy_hl_whale_24.5M: 68.8% WR, p=0.016
8. crypto_keltner_compression_v1: 75% WR, p=0.025
