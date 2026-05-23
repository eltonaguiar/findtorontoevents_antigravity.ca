# Strategy Incubator Inventory

**Last Updated:** 2026-02-26

## Overview

Total Strategies: **442** (220 new + 222 existing)
- **Active (OHLCV-based):** 174 strategies ready for backtesting
- **Parked (Specialized Data):** 46 strategies requiring external APIs
- **Google Antigravity:** 20 advanced quantitative strategies (201-220)
- **Existing:** 222 strategies in legacy systems

---

## Active Strategies (OHLCV-Only)

These strategies can be backtested immediately with standard OHLCV candle data.

### Multi-Timeframe (011-015)
| # | Strategy | Data Required | Status |
|---|----------|---------------|--------|
| 011 | Triple Timeframe Confluence | OHLCV | ✅ Ready |
| 012 | HTF Trend Filter | OHLCV | ✅ Ready |
| 013 | Multi-TF Momentum | OHLCV | ✅ Ready |
| 014 | Fractal Confluence | OHLCV | ✅ Ready |
| 015 | Cross-TF Divergence | OHLCV | ✅ Ready |

### Volatility (036-040)
| # | Strategy | Data Required | Status |
|---|----------|---------------|--------|
| 036 | ATR Regime Detection | OHLCV | ✅ Ready |
| 037 | Bollinger Squeeze | OHLCV | ✅ Ready |
| 038 | Volatility Breakout | OHLCV | ✅ Ready |
| 039 | GARCH Volatility | OHLCV | ✅ Ready |
| 040 | Volatility Cycle | OHLCV | ✅ Ready |

### Machine Learning (041-045)
| # | Strategy | Data Required | Status |
|---|----------|---------------|--------|
| 041 | Random Forest Ensemble | OHLCV | ✅ Ready |
| 042 | Feature Importance | OHLCV | ✅ Ready |
| 043 | Anomaly Detection | OHLCV | ✅ Ready |
| 044 | Clustering Regime | OHLCV | ✅ Ready |
| 045 | PCA Reduction | OHLCV | ✅ Ready |

### Statistical Arbitrage (046-050)
| # | Strategy | Data Required | Status |
|---|----------|---------------|--------|
| 046 | Pairs Trading | OHLCV | ✅ Ready |
| 047 | Cointegration | OHLCV | ✅ Ready |
| 048 | Z-Score Mean Reversion | OHLCV | ✅ Ready |
| 049 | Kalman Pairs | OHLCV | ✅ Ready |
| 050 | Triangular Arbitrage | OHLCV | ✅ Ready |

### Traditional Indicators (071-100)
| # | Strategy | Data Required | Status |
|---|----------|---------------|--------|
| 071 | RSI Divergence | OHLCV | ✅ Ready |
| 072 | MACD Histogram | OHLCV | ✅ Ready |
| 073 | Stochastic | OHLCV | ✅ Ready |
| 074 | Williams %R | OHLCV | ✅ Ready |
| 075 | CCI | OHLCV | ✅ Ready |
| 076 | ADX | OHLCV | ✅ Ready |
| 077 | Ichimoku Cloud | OHLCV | ✅ Ready |
| 078 | Parabolic SAR | OHLCV | ✅ Ready |
| 079 | Keltner Channels | OHLCV | ✅ Ready |
| 080 | Donchian Channels | OHLCV | ✅ Ready |
| 081 | Chaikin Money Flow | OHLCV | ✅ Ready |
| 082 | OBV | OHLCV | ✅ Ready |
| 083 | MFI | OHLCV | ✅ Ready |
| 084 | TSI | OHLCV | ✅ Ready |
| 085 | Ultimate Oscillator | OHLCV | ✅ Ready |
| 086 | ROC | OHLCV | ✅ Ready |
| 087 | DPO | OHLCV | ✅ Ready |
| 088 | Aroon | OHLCV | ✅ Ready |
| 089 | BOP | OHLCV | ✅ Ready |
| 090 | Chande Forecast | OHLCV | ✅ Ready |
| 091 | Schaff TC | OHLCV | ✅ Ready |
| 092 | KST | OHLCV | ✅ Ready |
| 093 | Elder Ray | OHLCV | ✅ Ready |
| 094 | Force Index | OHLCV | ✅ Ready |
| 095 | EOM | OHLCV | ✅ Ready |
| 096 | VZO | OHLCV | ✅ Ready |
| 097 | PVT | OHLCV | ✅ Ready |
| 098 | NVI | OHLCV | ✅ Ready |
| 099 | PVI | OHLCV | ✅ Ready |
| 100 | VW MACD | OHLCV | ✅ Ready |

### Alternative Chart Types (101-125)
| # | Strategy | Data Required | Status |
|---|----------|---------------|--------|
| 101 | Heikin Ashi | OHLCV | ✅ Ready |
| 102 | Renko | OHLCV | ✅ Ready |
| 103 | Point & Figure | OHLCV | ✅ Ready |
| 104 | Kagi | OHLCV | ✅ Ready |
| 105 | Three Line Break | OHLCV | ✅ Ready |
| 106 | Pivot Points | OHLCV | ✅ Ready |
| 107 | Camarilla | OHLCV | ✅ Ready |
| 108 | Woodie Pivots | OHLCV | ✅ Ready |
| 109 | DeMark Pivots | OHLCV | ✅ Ready |
| 110 | Floor Trader Pivots | OHLCV | ✅ Ready |
| 111 | Andrews Pitchfork | OHLCV | ✅ Ready |
| 112 | Gann Lines | OHLCV | ✅ Ready |
| 113 | Speed Resistance | OHLCV | ✅ Ready |
| 114 | Fibonacci Time | OHLCV | ✅ Ready |
| 115 | Fibonacci Arcs | OHLCV | ✅ Ready |
| 116 | Fibonacci Fans | OHLCV | ✅ Ready |
| 117 | Trend Intensity | OHLCV | ✅ Ready |
| 118 | VHF | OHLCV | ✅ Ready |
| 119 | RVI | OHLCV | ✅ Ready |
| 120 | COG | OHLCV | ✅ Ready |
| 121 | Fisher Transform | OHLCV | ✅ Ready |
| 122 | Inertia | OHLCV | ✅ Ready |
| 123 | Psychological Line | OHLCV | ✅ Ready |
| 124 | Rainbow MA | OHLCV | ✅ Ready |
| 125 | McGinley Dynamic | OHLCV | ✅ Ready |

### Advanced Moving Averages (126-135)
| # | Strategy | Data Required | Status |
|---|----------|---------------|--------|
| 126 | Hull MA | OHLCV | ✅ Ready |
| 127 | ALMA | OHLCV | ✅ Ready |
| 128 | ZLEMA | OHLCV | ✅ Ready |
| 129 | Triangular MA | OHLCV | ✅ Ready |
| 130 | VIDYA | OHLCV | ✅ Ready |
| 131 | Kaufman Efficiency | OHLCV | ✅ Ready |
| 132 | Fractal Dimension | OHLCV | ✅ Ready |
| 133 | Hurst Exponent | OHLCV | ✅ Ready |
| 134 | MAD | OHLCV | ✅ Ready |
| 135 | Standard Error | OHLCV | ✅ Ready |

### Volatility Measures (136-144)
| # | Strategy | Data Required | Status |
|---|----------|---------------|--------|
| 136 | Historical Volatility | OHLCV | ✅ Ready |
| 137 | Parkinson HL | OHLCV | ✅ Ready |
| 138 | Garman-Klass | OHLCV | ✅ Ready |
| 139 | Rogers-Satchell | OHLCV | ✅ Ready |
| 140 | Yang-Zhang | OHLCV | ✅ Ready |
| 141 | Volatility Cone | OHLCV | ✅ Ready |
| 142 | VRP | OHLCV | ✅ Ready |
| 143 | Vol of Vol | OHLCV | ✅ Ready |
| 144 | Beta Adjusted | OHLCV | ✅ Ready |

### Risk Metrics (145-170)
| # | Strategy | Data Required | Status |
|---|----------|---------------|--------|
| 145 | Sharpe Ratio | OHLCV | ✅ Ready |
| 146 | Sortino Ratio | OHLCV | ✅ Ready |
| 147 | Calmar Ratio | OHLCV | ✅ Ready |
| 148 | Information Ratio | OHLCV | ✅ Ready |
| 149 | Treynor Ratio | OHLCV | ✅ Ready |
| 150 | Omega Ratio | OHLCV | ✅ Ready |
| 151 | Kelly Criterion | OHLCV | ✅ Ready |
| 152 | Risk Parity | OHLCV | ✅ Ready |
| 153 | Max Drawdown | OHLCV | ✅ Ready |
| 154 | Ulcer Index | OHLCV | ✅ Ready |
| 155 | Pain Ratio | OHLCV | ✅ Ready |
| 156 | Sterling Ratio | OHLCV | ✅ Ready |
| 157 | Burke Ratio | OHLCV | ✅ Ready |
| 158 | Martin Ratio | OHLCV | ✅ Ready |
| 159 | Kappa | OHLCV | ✅ Ready |
| 160 | Prospect Ratio | OHLCV | ✅ Ready |
| 161 | Conditional Sharpe | OHLCV | ✅ Ready |
| 162 | DD Duration | OHLCV | ✅ Ready |
| 163 | TUW | OHLCV | ✅ Ready |
| 164 | Recovery | OHLCV | ✅ Ready |
| 165 | Gain/Pain | OHLCV | ✅ Ready |
| 166 | Profit Factor | OHLCV | ✅ Ready |
| 167 | Win Rate | OHLCV | ✅ Ready |
| 168 | Payoff Ratio | OHLCV | ✅ Ready |
| 169 | Expectancy | OHLCV | ✅ Ready |
| 170 | R-Multiple | OHLCV | ✅ Ready |

### Statistical Tests (171-200)
| # | Strategy | Data Required | Status |
|---|----------|---------------|--------|
| 171 | SQN | OHLCV | ✅ Ready |
| 172 | Edge Ratio | OHLCV | ✅ Ready |
| 173 | E-Ratio | OHLCV | ✅ Ready |
| 174 | MAE/MFE | OHLCV | ✅ Ready |
| 175 | Trade Distribution | OHLCV | ✅ Ready |
| 176 | Consecutive | OHLCV | ✅ Ready |
| 177 | Monte Carlo | OHLCV | ✅ Ready |
| 178 | Bootstrap | OHLCV | ✅ Ready |
| 179 | Walk Forward | OHLCV | ✅ Ready |
| 180 | Out of Sample | OHLCV | ✅ Ready |
| 181 | Regime Switch | OHLCV | ✅ Ready |
| 182 | HMM | OHLCV | ✅ Ready |
| 183 | CUSUM | OHLCV | ✅ Ready |
| 184 | Change Point | OHLCV | ✅ Ready |
| 185 | Spectral | OHLCV | ✅ Ready |
| 186 | Wavelet | OHLCV | ✅ Ready |
| 187 | Entropy | OHLCV | ✅ Ready |
| 188 | Mutual Info | OHLCV | ✅ Ready |
| 189 | Granger | OHLCV | ✅ Ready |
| 190 | Cointegration Test | OHLCV | ✅ Ready |
| 191 | ADF | OHLCV | ✅ Ready |
| 192 | KPSS | OHLCV | ✅ Ready |
| 193 | Phillips-Perron | OHLCV | ✅ Ready |
| 194 | Variance Ratio | OHLCV | ✅ Ready |
| 195 | Ljung-Box | OHLCV | ✅ Ready |
| 196 | Jarque-Bera | OHLCV | ✅ Ready |
| 197 | Shapiro-Wilk | OHLCV | ✅ Ready |
| 198 | Kolmogorov-Smirnov | OHLCV | ✅ Ready |
| 199 | Anderson-Darling | OHLCV | ✅ Ready |
| 200 | Combined Ensemble | OHLCV | ✅ Ready |

### Google Antigravity Quantitative Strategies (201-220)
| # | Strategy | Technique | LONG+SHORT | Status |
|---|----------|-----------|------------|--------|
| 201 | Garman-Klass Vol Breakout | GK vol estimator | ✅ | ✅ Ready |
| 202 | Fractal Dimension Regime | Higuchi fractal dim | ✅ | ✅ Ready |
| 203 | Liquidation Cascade Detector | Price accel + vol explosion | ✅ | ✅ Ready |
| 204 | Wavelet Trend-Noise | Haar wavelet decomposition | ✅ | ✅ Ready |
| 205 | Jump Diffusion Detector | BNS jump test | ✅ | ✅ Ready |
| 206 | Information Ratio Momentum | Rolling IR quality gate | ✅ | ✅ Ready |
| 207 | VPIN Toxicity Flow | VPIN proxy | ✅ | ✅ Ready |
| 208 | Spectral Cycle Detector | FFT cycle detection | ✅ | ✅ Ready |
| 209 | Adaptive Kelly Regime | Kelly criterion embedded | ✅ | ✅ Ready |
| 210 | Correlation Breakdown Alpha | AC regime detection | ✅ | ✅ Ready |
| 211 | Realized Vol Smile | Up-vol vs down-vol asymmetry | ✅ | ✅ Ready |
| 212 | Regime-Switching GARCH | GARCH(1,1) forecast | ✅ | ✅ Ready |
| 213 | Cross-Timeframe Divergence | 3 synthetic TFs | ✅ | ✅ Ready |
| 214 | Microstructure Spread Proxy | Corwin-Schultz spread | ✅ | ✅ Ready |
| 215 | Max Drawdown Recovery Timing | DD/DU recovery | ✅ | ✅ Ready |
| 216 | Dispersion Mean Reversion | Intra-bar dispersion z | ✅ | ✅ Ready |
| 217 | Omega Ratio Gate | Omega ratio quality | ✅ | ✅ Ready |
| 218 | Power Law Tail Risk | Hill tail estimator | ✅ | ✅ Ready |
| 219 | Entropy-Weighted Momentum | Shannon entropy weighting | ✅ | ✅ Ready |
| 220 | Cointegration Residual Spread | Self-cointegration + half-life | ✅ | ✅ Ready |

---

## Parked Strategies (Require Specialized Data)

These strategies require data sources not available in standard OHLCV backtests. They remain in `parked/` folder until real data infrastructure is built.

### On-Chain Metrics (001-010)
| # | Strategy | Data Required | Why Parked |
|---|----------|---------------|------------|
| 001 | Whale Wallet Accumulation | On-chain: whale balances, exchange flows | Requires blockchain node/API |
| 002 | Exchange Netflow | On-chain: inflows/outflows | Requires Glassnode/CryptoQuant API |
| 003 | Network Velocity | On-chain: transaction volume | Requires blockchain analytics |
| 004 | Active Addresses | On-chain: unique addresses | Requires node access |
| 005 | Miner Position Index | On-chain: miner flows | Requires specialized data feed |
| 006 | MVRV Ratio | On-chain: market cap/realized cap | Requires realized cap data |
| 007 | NUPL Sentiment | On-chain: net unrealized profit/loss | Requires UTXO data |
| 008 | SOPR Momentum | On-chain: spent output profit ratio | Requires blockchain history |
| 009 | LTH/SHR Ratio | On-chain: holder composition | Requires address clustering |
| 010 | Coin Days Destroyed | On-chain: CDD metric | Requires UTXO age tracking |

### Cross-Asset Correlations (016-020)
| # | Strategy | Data Required | Why Parked |
|---|----------|---------------|------------|
| 016 | BTC-SPX Correlation | SPX prices, volumes | Requires equity market data |
| 017 | BTC-DXY Inverse | DXY index data | Requires forex data feed |
| 018 | ETH-BTC Ratio | Dual asset tracking | Requires multi-asset feeds |
| 019 | Correlation Regime | Multi-asset correlation | Requires multiple markets |
| 020 | Cross-Asset Momentum | Multi-market momentum | Requires broad market data |

### Market Microstructure (021-030)
| # | Strategy | Data Required | Why Parked |
|---|----------|---------------|------------|
| 021 | Order Book Imbalance | L2 order book (bids/asks) | Requires exchange L2 WebSocket |
| 022 | Spread Analysis | Real-time spreads | Requires tick-level data |
| 023 | Depth Ratio | Order book depth | Requires L2 order book |
| 024 | Trade Flow Imbalance | Tick-by-tick trades | Requires trade stream |
| 025 | VWAP Deviation | Intraday VWAP | Requires tick data |
| 026 | Asian Session | Session-specific data | Requires time-based data |
| 027 | London Session | Session-specific data | Requires time-based data |
| 028 | NY Session | Session-specific data | Requires time-based data |
| 029 | Session Overlap | Multi-session data | Requires timezone handling |
| 030 | Weekend Gap | Gap detection | Requires 24/7 market data |

### Funding & Derivatives (031-035)
| # | Strategy | Data Required | Why Parked |
|---|----------|---------------|------------|
| 031 | Funding Arbitrage | Funding rates across exchanges | Requires funding rate APIs |
| 032 | Funding Trend | Historical funding | Requires perp data |
| 033 | Premium Index | Perp premium data | Requires exchange API |
| 034 | Perp-Spot Basis | Basis tracking | Requires dual market data |
| 035 | Predicted Funding | Funding predictions | Requires exchange-specific data |

### Options & Advanced (051-070)
| # | Strategy | Data Required | Why Parked |
|---|----------|---------------|------------|
| 051 | Options Volume Flow | Options chain data | Requires Deribit/similar API |
| 052 | Gamma Exposure | Options Greek data | Requires options market maker data |
| 053 | Social Sentiment | Social media APIs | Requires Twitter/Reddit API |
| 054 | Fear & Greed | CNN Fear/Greed index | Requires web scraping/API |
| 055 | Liquidation Cascade | Liquidation data | Requires exchange liquidation feed |
| 056 | Flash Crash | Flash crash detection | Requires tick data |
| 057 | Wyckoff Accumulation | Volume profile analysis | Requires footprint data |
| 058 | OI Delta | Open interest changes | Requires futures data |
| 059 | Long/Short Ratio | Exchange positioning | Requires exchange API |
| 060 | Harmonic Patterns | Pattern detection | Complex pattern library needed |
| 061 | Elliott Wave | Wave analysis | Subjective, requires wave counting |
| 066 | Market Maker | Flow detection | Requires order flow data |
| 067 | Cross-Exchange Arb | Multi-exchange prices | Requires real-time arb monitoring |
| 068 | Mempool Gas | Ethereum mempool | Requires Ethereum node |
| 069 | IV Skew | Options implied vol | Requires options data |
| 070 | Max Pain | Options max pain | Requires options chain |

---

## Data Infrastructure Roadmap

To activate parked strategies, we need:

### Phase 1: On-Chain Data (Priority: Medium)
- **Glassnode API** or **CryptoQuant**: Whale flows, MVRV, NUPL, SOPR
- **Blockchain Nodes**: Direct RPC access for custom metrics
- **Cost**: $300-500/month for commercial APIs

### Phase 2: Cross-Asset Data (Priority: Low)
- **Yahoo Finance API**: SPX, DXY data (free tier available)
- **Polygon.io**: Equity data ($49/month)

### Phase 3: L2 Order Book (Priority: High for scalping)
- **Exchange WebSockets**: Binance, Bybit, OKX (free)
- **Data Storage**: Time-series DB for tick data

### Phase 4: Options Data (Priority: Low)
- **Deribit API**: Crypto options (free)
- **TradFi Options**: Expensive, limited value

---

## Backtest Priority Queue

### Immediate (This Week)
1. Traditional Indicators (071-100) - 30 strategies
2. Volatility Measures (036-040) - 5 strategies
3. Multi-Timeframe (011-015) - 5 strategies

### Next (Next 2 Weeks)
1. Statistical Tests (171-200) - 30 strategies
2. Risk Metrics (145-170) - 26 strategies
3. ML Strategies (041-045) - 5 strategies

### Later (Month 2)
1. Chart Types (101-125) - 25 strategies
2. Moving Averages (126-135) - 10 strategies
3. Stat Arb (046-050) - 5 strategies

---

## Dashboard Links

- **SUPERPOWERS ARENA:** https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/battleground/
- **Predictions Dashboard:** https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/predictions/dashboard/
- **KIMI Claw Research:** https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/KIMI_CLAW_RESEARCH_FEB162026/

---

*Note: All strategies require real market data for validation. Synthetic data is only used for initial testing.*
