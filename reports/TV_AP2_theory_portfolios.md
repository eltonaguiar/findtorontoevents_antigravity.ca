# TradingView Paper Trading Theory Portfolios — TV_AP2

**Created:** 2026-04-02 23:45 UTC
**Account:** BROKIE USD (Paper Trading)
**Starting Balance:** $997.99

## Portfolio: TV_AP2_TopScored (first 5 trades)
Based on highest-scored picks from findtorontoevents.ca/audit

| # | Symbol | Side | Entry | Score | Source | Strategy |
|---|--------|------|-------|-------|--------|----------|
| 1 | XRPUSDT | LONG | 1.3203 | 120 | battleground | drawdown_recovery_rsi_xrp |
| 2 | ALGOUSDT | LONG | 0.1070 | 120 | super_signals | super signal via ml_crypto_pred |
| 3 | TONUSDT | LONG | 1.233 | 120 | super_signals | super signal via ml_crypto_pred |
| 4 | DOGEUSDT | SHORT | 0.09043 | 120 | pm_kalshi_signals | kalshi_mtf_consensus |
| 5 | LTCUSDT | LONG | 52.30 | 120 | claude_gainer_st | st_fear_greed_contrarian |

## Portfolio: TV_AP2_ShortKing (bearish bias)
Theory: SHORT direction has 50.2% WR vs LONG 43.6% in current market

| # | Symbol | Side | Entry | Score | Source |
|---|--------|------|-------|-------|--------|
| 6 | ETHUSDT | SHORT | 2055.81 | 115 | prediction_market |
| 7 | BTCUSDT | SHORT | 66897.58 | 102 | battleground (Keltner) |
| 8 | SOLUSDT | SHORT | 78.92 | 91 | prediction_market |

## Theory Rationale

### TV_AP2_ShortKing
- Data shows SHORT WR 50.2% vs LONG 43.6% on closed trades
- Prediction market consensus + Keltner compression both favor shorts
- Copy trader hs_lb_None has 92.3% WR on shorts specifically
- If market continues bearish, shorts should outperform

### TV_AP2_ProvenEdge (not yet separate — mixed in above)
- st_fear_greed_contrarian: 73.9% WR on 138 trades — highest volume proven
- crypto_keltner_compression: 69.6% WR — statistically significant (p=0.025)
- drawdown_recovery_rsi: 55.6% WR — ETH-specific edge

### TV_AP2_HighTrust (target — next session)
- Score >= 60 AND Trust >= 5 = 74.5% WR in backtest data
- Needs separate BROKIE USD account to isolate

## Portfolio: TV_AP3_Superstar (Good Friday Session — Apr 3, 2026)
Based on 66-script backtest sweep superstars + FGI=9 extreme fear contrarian signals

| # | Symbol | Side | Entry | Score | Source | Strategy |
|---|--------|------|-------|-------|--------|----------|
| 9 | BTCUSDT | LONG | 67,006.56 | 130 | superstar+fgi | Triple_EMA+Vol_Spike+FGI_contrarian |
| 10 | ETHUSDT | LONG | 2,062.66 | 130 | superstar+fgi | Triple_EMA+Ichimoku(PF9.5)+FGI_contrarian |
| 11 | SOLUSDT | LONG | ~80.17 | 125 | superstar+fgi | Triple_EMA(PF1.49)+FGI_contrarian |
| 12 | ALGOUSDT | LONG | 0.1173 | 120 | momentum+fgi | +10.6% momentum + super signal + FGI=9 |
| 13 | BNBUSDT | LONG | 586.21 | 120 | fgi_contrarian | st_fear_greed_contrarian_regime_filtered (69.4% WR) |
| 14 | DYDXUSDT | LONG | 0.1037 | 115 | momentum | +8% daily momentum + EMA stack alignment |

### TV_AP3 Theory Rationale
- **FGI = 9 (Extreme Fear):** st_fear_greed_contrarian has 69.4% base WR — best contrarian signal
- **Superstar Strategy Confluence:** Triple_EMA (PF 1.50 avg, 6/6 profitable) + Volume_Spike (PF 3.84-6.93 on majors) both confirm LONG bias on BTC/ETH/SOL
- **Good Friday Low Volume:** Crypto markets thin on holidays — mean-reversion expected from extreme fear overshoot
- **All LONGs:** Bearish sentiment has been priced in; contrarian LONG edge is statistically validated

### Account Snapshot (Apr 3, 2026 00:30 UTC)
- **Starting Balance:** $3,000.00
- **Realized PnL:** +$1,996.11 (from prior TV_AP2 trades)
- **Open Positions:** 6 (all LONG crypto)
- **Available Funds:** $2,925.47

## Tracking
- Monitor via TradingView Paper Trading panel
- Compare against findtorontoevents.ca/audit closed picks WR
- Update CHATWITHIT.MD with results weekly
