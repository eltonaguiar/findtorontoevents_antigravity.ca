# Quant Picks NOW — Multi-Asset Screener Deployed

**2026-06-06** | `tools/picks_now_professional.py`

Deployed an institutional-grade multi-factor quant screener that generates actionable "right now" picks across 6 asset classes.

## Methodology

The screener uses the same factors professional hedge funds/quant firms apply:

| Factor | Weight | Source | Hedge Fund Analog |
|--------|--------|--------|-------------------|
| Momentum (3m/1m/5d) | 30% | yfinance | AQR Time-Series Momentum |
| Mean Reversion (RSI + Bollinger) | 20% | yfinance | Two Sigma Statistical Arbitrage |
| Analyst Consensus | 25% | yfinance recommendationMean | Citadel / Point72 Fundamental Overlay |
| Vol-Adjusted Safety | 15% | yfinance realized vol | Bridgewater Risk-Parity |
| DB Edge Overlay | 10% | ejaguiar1_stocks `at_pick_outcomes` | Renaissance Internal Cross-Validation |

## Top Picks — 2026-06-06

### EQUITY (best risk/reward)
- **AMZN $246** — Score 133/100. 62 analysts STRONG_BUY, $313 target (+27%). 3m uptrend intact, 5d pullback to lower Bollinger Band. AWS + AI growth structural.
- **AVGO $386** — Score 128. 45 analysts STRONG_BUY, $513 target (+33%).
- **GOOGL $369** — Score 121. 53 analysts STRONG_BUY, $431 target (+17%).
- **AAPL $307** — Score 108. 43 analysts BUY. Lowest equity vol (19%). Most resilient today.
- **NVDA $205** — Score 105. 59 analysts STRONG_BUY, $298 target (+46%). Highest upside. -8.5% 5d flush.

### ETF
- **QQQ $705** — Score 96. TREND+DIP. 3m uptrend +16%, 4d pullback -5%.
- **SPY $738** — Score 90. Uptrend +9% 3m, Low vol 13%.
- **IWM $282** — Score 96. Small-cap rally still intact.

### BOND 🛡️ SAFEST — All score 75
- **TLT $85** — Lowest vol in universe (9% annualized). Flight-to-safety. Only -0.5% today.
- **IEF $94 / SHY $82 / AGG $98** — All sub-6% vol. Dividend yields 3-5%.

### FOREX (mean reversion on USD strength)
- **GBPUSD $1.33** — Score 92. RSI 39 oversold. DB edge: 59% WR n=114.
- **EURUSD $1.15** — Score 90. RSI 33, lower BB. USD strength mean-reversion.
- **EURGBP $0.86** — Score 80. DB edge: 56% WR n=171.

### COMMODITY (oversold bounce plays)
- **ZC=F (Corn) $418** — Score 81. RSI 28, lower BB. Mean reversion setup.
- **ZS=F (Soybeans) $1,122** — Score 81. RSI 30.
- **HG=F (Copper) $6.26** — Score 80. DB edge 47% WR n=228.

### CRYPTO ⚠️ AVOID — broad panic
- RSI 11-15 across all coins. BTC -19% 5d, ETH -23%. Not bouncing yet.

## Market Regime: RISK-OFF
Equities -3-6%, Crypto -16-23%, Gold -5%, USD bid. Bonds the only safe haven.

## Output Files
- `audit_dashboard/data/picks_now.json` — Machine-readable JSON
- `reports/PICKS_NOW_2026-06-06.md` — Full report
- `tools/picks_now_professional.py` — Reusable screener

## Next Steps
1. Schedule daily cron via GitHub Actions
2. Wire picks_now.json into a visible surface on `/audit/`
3. Add insider transaction data feed (SEC EDGAR scrape)
4. Add earnings surprise calendar overlay
