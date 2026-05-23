# Swarm Round B: Gap Analysis vs Hedge Fund Ideal — 2026-05-14

**Engines:** deepseek (deepseek-v4-flash), xai (grok-3), cerebras (gpt-oss-120b)
**Status:** 3/3 OK — all responses valid JSON, no engine failures
**Run dir:** `swarm_runs/gap_analysis_20260514/`
**Est. cost:** $0.0665

---

## Per-Class Bottleneck Analysis

| Class     | Current PF / WR / n       | T1 Target Gap              | #1 Bottleneck (consensus)                                                                                     |
|-----------|---------------------------|----------------------------|---------------------------------------------------------------------------------------------------------------|
| COMMODITY | PF 2.08 / WR 46.9% / n 750 | WR +8pp                   | COT edge is concentrated on cotton (CT=F) with open-bloat risk; scaling high-WR signal to diversified symbols without overfitting collapses WR |
| EQUITY    | PF 1.42 / WR 52.7% / n 421 | PF +0.58                  | Single-factor momentum is regime-dependent; missing factor diversification (value, quality, low-vol) and mean reversion to sustain PF across all market conditions |
| ETF       | PF 1.20 / WR 55.2% / n 87  | n +113, PF +0.80           | Low signal frequency; narrow symbol universe generates too few trades to reach n≥200 and lacks PF-lifting strategies |
| BOND      | PF 1.72 / WR 55.6% / n 18  | n +182 (critical)          | n=18 is statistically uninformative; no yield-curve, carry, or flight-to-quality strategies generating regular signals |
| CRYPTO    | PF 1.26 / WR 44.8% / n 8162 | WR +10pp, PF +0.74        | Elite ML per-symbol models (DYDX PF 58, BNB PF 56) have tiny n; drag from quan_engine (18% volume, PF 0.70) and unknown (7%, PF 0.35) collapses system-wide WR — bottleneck is volume-weighted source quality |
| FOREX     | PF 0.27 / WR 46.4% / n 1169 | DEAD                      | Fundamental strategy invalidity — no incremental fix closes a PF 0.27 gap; requires full mutation protocol (MUTATION_THREE_AXIS_PROTOCOL) before any resizing |

---

## Missing Strategies Per Class (with academic refs)

### COMMODITY
| Strategy | Academic Reference | Complexity | Expected Edge | Free Data |
|---|---|---|---|---|
| Roll Yield / Carry (backwardation vs contango term structure) | Erb & Harvey (2006) "The Tactical and Strategic Value of Commodity Futures"; Gorton & Rouwenhorst (2006) "Facts and Fantasies about Commodity Futures" | Medium | Uncorrelated to COT; captures predictable roll returns; improves WR 3-5pp | Yes |
| Seasonal Pattern Trading (calendar-based agri/energy) | Gorton & Rouwenhorst (2006); Kumar & Lee (2005) "Seasonality in Commodity Futures" | Low | 60-70% WR on agricultural commodities; diversifies cotton concentration | Yes |
| Macro-Factor Model (GDP, PMI, industrial production) | Bessembinder et al. (2018) "Commodity Futures and Economic Activity" | High | Links commodity returns to leading macro indicators for forward-looking signals | Yes (FRED) |

### EQUITY
| Strategy | Academic Reference | Complexity | Expected Edge | Free Data |
|---|---|---|---|---|
| Short-Term Mean Reversion (1-5 day contrarian) | Jegadeesh & Titman (1993) contrarian extension; Avellaneda & Lee (2010) "Statistical Arbitrage in US Equities" | Low | PF 1.5-2.0 in high-vol regimes; complements momentum, reduces strategy correlation | Yes |
| Multi-Factor Model (Fama-French SMB, HML, RMW, CMA) | Fama & French (2015) "A Five-Factor Asset Pricing Model" | Medium | Long-short factor portfolios with PF 1.3-1.8; robust across decades; diversifies away pure momentum risk | Yes (Ken French data library) |
| Sector Rotation via Relative Strength (RSI + macro filter) | Moskowitz & Ooi (2012) "Sector Momentum and Market Timing" | Low | Shifts capital to outperforming sectors; smooths drawdowns; directly lifts PF | Yes |

### ETF
| Strategy | Academic Reference | Complexity | Expected Edge | Free Data |
|---|---|---|---|---|
| Pairs Trading / Cointegration across correlated ETFs | Gatev, Goetzmann & Rouwenhorst (2006) "Pairs Trading: Performance of a Relative-Value Arbitrage Rule" | Medium | WR 60-70% with low MDD; generates frequent signals to boost n | Yes |
| Sector ETF Rotation (momentum across SPY, XLK, XLE, XLF, etc.) | Jegadeesh & Titman (1993) applied to sector ETFs; Stangl et al. (2009) | Low | Top/bottom decile sector momentum; PF 1.5-2.0; frequent signals accelerate n | Yes |
| Risk-Parity Across Factor ETFs (VTV, MTUM, QUAL, USMV) | Maillard et al. (2010) "The Diversification Benefits of Risk Parity" | Medium | Balances risk contributions; reduces volatility; improves WR | Yes |
| Dual-Timeframe Trend Following on Broad-Market ETFs | Moskowitz et al. (2012) "Trend Following"; Lo & MacKinlay (1990) | Low | Captures sustained moves; avoids whipsaws; lifts PF | Yes |

### BOND
| Strategy | Academic Reference | Complexity | Expected Edge | Free Data |
|---|---|---|---|---|
| Yield Curve Slope Trading (long 2Y vs short 10Y or vice versa) | Litterman & Scheinkman (1991) "Common Factors Affecting Bond Returns"; Bali et al. (2020) "Carry and Momentum in Fixed Income" | Low | Daily signals from 2Y-10Y spread; PF 1.5-2.0; works with n<50 to start generating n fast | Yes (FRED) |
| Flight-to-Quality Regime (long bonds on VIX spike) | Baele, Bekaert & Inghelbrecht (2010) "Stock and Bond Return Comovements" | Low | Simple VIX threshold rule; WR >60%; generates trades across all market regimes | Yes |
| Credit-Spread Relative Value (IG vs HY spread mean reversion) | Duffee (2002) "Corporate Bond Credit Spreads" | Medium | Mean-reverting spread; low volatility edge; adds signal diversity | Yes (FRED HY/IG spreads) |
| Macro-Fundamental (CPI, Fed Funds, real rate) Duration Positioning | Kilian (2009); standard duration management literature | High | Aligns duration with macro outlook; adds robustness to n-thin periods | Yes (FRED) |

### CRYPTO
| Strategy | Academic Reference | Complexity | Expected Edge | Free Data |
|---|---|---|---|---|
| Volatility-Scaled Momentum (30-day ROC / σ) | Makarov & Schoar (2020) "Trading and Arbitrage in Cryptocurrency Markets" | Low | Reduces exposure during high-vol; lifts WR and PF; directly targets the WR +10pp gap | Yes (Binance API) |
| On-Chain Exchange Netflow Imbalance | Ciaian, Rajcaniova & Kancs (2016) "The Economics of BitCoin Price Formation" | Medium | Large exchange inflows predict 1-3 day sell pressure; WR 55-65% | Yes (Glassnode free tier, CryptoCompare) |
| Funding Rate Arbitrage / Basis Trading (perpetual futures) | Lei, Li & Wang (2021) "Crypto Futures Basis Trading" | Medium | Mean-reversion of funding rates; PF 1.3-1.8; low correlation to price momentum | Yes (Binance funding API) |
| Ensemble ML on OHLCV + On-Chain (GBM + LSTM) | Chen et al. (2021) "Deep Learning for Crypto-Asset Price Prediction" | High | Captures non-linear patterns beyond naive momentum; particularly effective for generalizing DYDX/BNB edge to broader universe | Yes |
| NLP Sentiment (Twitter/Reddit → crypto price) | Nassirtoussi et al. (2014) | High | Short-term price signal from social sentiment; WR +3-5pp | Yes (Pushshift, Twitter free) |

### FOREX (mutation protocol — do not resize without deep-dive)
| Strategy | Academic Reference | Complexity | Expected Edge | Free Data |
|---|---|---|---|---|
| Interest-Rate Carry Trade (FX forward vs spot) | Lustig & Verdelhan (2007) "Cross-Section of Foreign Currency Risk Premia"; Menkhoff et al. (2009) "Carry Trade Returns" | Low | Long high-yield / short low-yield currencies; PF 1.2-1.5 historically; benchmark for any FOREX revival | Yes |
| Macro-Fundamental (GDP, PMI, Trade Balance) | Fischer & Krauss (2018) "Macro-Driven FX Forecasts" | Medium | Aligns trades with macro cycles; improves WR | Yes (FRED) |

---

## Infrastructure Gap Priority Ranking

**Consensus across all 3 engines:** concept drift and position sizing are the top-2 priorities. Engines diverged on rank-4 vs rank-5 (regime-tagging vs slippage).

| Rank | Gap | Consensus | Expected PF Lift | Rationale |
|------|-----|-----------|------------------|-----------|
| 1 | **Concept drift auto-pause (KS_D 6.6× critical)** | 3/3 top-2 | +0.3 to +1.0 (prevents collapse) | KS_D at 6.6× critical threshold means predictions on affected classes are likely already invalid. This is a capital-protection issue first, PF-lift issue second. Losses compound while drift is undetected. |
| 2 | **Position sizing (volatility-scaled / Kelly fraction)** | 3/3 top-2 | +0.3 to +0.6 PF; MDD -30-50% | All positions equal-weight ignores realized volatility and Kelly criterion. Risk-adjusted sizing reduces MDD by 30-50% without touching signals. Cross-class benefit is immediate. |
| 3 | **Portfolio-level MDD limit enforcement** | 3/3 rank-3 | MDD -5-10pp | Per-strategy stops exist but a single class blowup (e.g., CRYPTO vol spike) can cascade without a portfolio-level circuit breaker. Directly addresses the MDD≤10 T1 criterion. |
| 4 | **Regime tagging bug fix (tags never written at emission)** | 2/3 rank-4 | WR +3-5pp (regime-sensitive classes) | 0/236 active picks carry regime tags. Without regime context, equity VIX filter and bond flight-to-quality rules cannot trigger adaptively. Medium-term lift after drift and sizing are addressed. |
| 5 | **Slippage / transaction-cost model** | 3/3 rank-4 or 5 | PF adjustment -0.1 to -0.3 (realistic correction) | Note: this is a corrective adjustment, not a genuine lift — current PF is overstated by 5-15% due to assumed market-order fill at signal price. Prioritize after live-risk controls are solid. |

*CPCV validation (combinatorial purging) ranked 6th by deepseek as requiring significant compute with sequential validation catching most issues — confirm after rank-1 through rank-5 are delivered.*

---

## Free Data Sources to Add

| Source | URL | Asset Class | Data Type | Expected Impact |
|--------|-----|-------------|-----------|-----------------|
| FRED (Federal Reserve Economic Data) | https://fred.stlouisfed.org/ | ALL | Treasury yields, CPI, industrial production, yield curves, HY/IG spreads | Critical for BOND yield-curve strategies (+n), COMMODITY macro factor, EQUITY regime filter; highest cross-class ROI of any free source |
| CFTC COT Reports | https://www.cftc.gov/MarketData/CommitmentsofTraders/ | COMMODITY, CRYPTO, FOREX | Weekly open interest, long/short by trader type | Already used for cotton — expand to 20+ commodity futures; +2-3pp WR on diversified commodities |
| CryptoCompare API (free) | https://min-api.cryptocompare.com/ | CRYPTO | OHLCV, exchange order books, on-chain metrics | Enables on-chain netflow and funding rate strategies; +2-4pp WR |
| Binance Funding Rate API (free) | https://binance-docs.github.io/apidocs/ | CRYPTO | Funding rates, perpetual futures basis, order book snapshots | Direct input for funding-rate arbitrage; +1-2pp PF |
| Alpha Vantage (free tier) | https://www.alphavantage.co/ | EQUITY, ETF, FOREX, CRYPTO | Daily OHLCV, FX rates, sector performance, technical indicators | Enables pairs trading and sector rotation signals; broad baseline |
| Polygon.io (free tier) | https://polygon.io/ | EQUITY, ETF | Historical tick & minute bars, corporate actions | Enables high-frequency mean reversion; slippage calibration; +0.5-1pp PF |
| Quandl / Nasdaq Data Link (free datasets) | https://data.nasdaq.com/ | COMMODITY, BOND | COT reports, futures data, yield curves, Wiki EOD stock prices | Fills bond futures data gap (helps n issue); commodity roll-yield inputs |
| EIA Open Data | https://www.eia.gov/opendata/ | COMMODITY | Oil, natural gas inventories, production, consumption | Fundamental drivers for energy commodity models; narrows WR gap |
| Ken French Data Library | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html | EQUITY | SMB, HML, RMW, CMA daily factor returns | Direct input for Fama-French implementation; free and clean |
| CoinGecko API (free) | https://www.coingecko.com/en/api | CRYPTO | Historical OHLCV, market cap, active addresses | Enables richer ML feature set; generalization beyond Binance |
| Glassnode (free tier) | https://glassnode.com/ | CRYPTO | Exchange netflows, whale wallet movements, active addresses | On-chain flow imbalance signal; WR +3-5pp |

---

## Overall Verdict

The most critical path to Tier 1 is a two-track sprint: **live-risk controls first, signal expansion second.** The KS_D 6.6× concept-drift reading is a five-alarm warning — running predictions at this drift level may already be destroying PF on affected classes faster than any strategy improvement can recover. Wiring the auto-pause gate is a capital-protection action, not an optimization. Immediately behind it, implementing volatility-scaled position sizing and a portfolio-level MDD circuit breaker addresses the T1 MDD≤10 criterion that no class can currently verify. On the signal side, the clearest asymmetric opportunities are: (1) COMMODITY — add roll-yield carry and seasonal patterns to diversify away the cotton concentration risk and lift WR +8pp; (2) BOND — add FRED yield-curve slope trading to generate daily signals and escape the n=18 trap (this alone could reach n≥200 within 6-9 months); (3) CRYPTO — cut volume share of quan_engine and unknown sources, add volatility-scaled momentum and on-chain netflow as signal filters to lift system-wide WR, and (4) EQUITY — layer in mean-reversion and Fama-French factors alongside momentum to maintain PF across regimes. FOREX must not receive new sizing until the MUTATION_THREE_AXIS_PROTOCOL deep-dive is complete. The combined roadmap — drift-pause + sizing + MDD limit wired within 30 days, three class-specific signal expansions within 60 days, and CPCV validation within 90 days — represents the realistic path to T1 across the majority of classes.

---

*Synthesis source: swarm_runs/gap_analysis_20260514/ — cerebras (12271B), deepseek (10715B), xai (6075B). All 3/3 engines returned valid JSON.*
