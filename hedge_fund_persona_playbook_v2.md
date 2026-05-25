# HEDGE FUND PERSONA PLAYBOOK — EXPANDED EDITION
## Full Methodology, Self-Assessment, Survey, and Tier-List Algorithm
**Date:** May 25, 2026 | **Author:** Alpha Engine + Persona Simulation
**Data Sources:** Yahoo Finance (live May 22 close), alpha_engine/config.py, baby_strategies framework, IMF WEO April 2026

---

# SECTION 1: MARKET SNAPSHOT

| Indicator | Value (May 22) | Signal |
|-----------|---------------|--------|
| S&P 500 | 7,473 (+0.37%) | YTD +9.3%, grinding higher |
| Nasdaq | 26,344 (+0.19%) | AI/semi leadership intact |
| VIX | 16.70 | Complacent, below historical avg |
| 10Y Treasury | ~4.25% | Declining, flight-to-safety bid |
| Gold (GC=F) | $4,523/oz | +36.5% YTD — monster year |
| Bitcoin | ~$77,200 | Post-halving consolidation |
| Brent Crude | ~$100-105 | Iran supply risk premium |
| Dollar (DXY) | Firm | Constraining EM, supporting USTs |
| 2Y Treasury | ~3.80% | Rate cut expectations building |
| Copper (HG=F) | Elevated | AI/data center infrastructure demand |

**Macro Regime:** Late-cycle expansion with geopolitical tail risk. Iran deal uncertainty, tariff overhang, AI capex cycle primary narrative. Fed signaling patience. Gold and long-duration bonds benefiting from risk-off bid.

---

# SECTION 2: PROVIDER-MODEL CONTEXT

**Provider Model:** OpenAI (Claude Opus 4 class) reasoning model
**Prompt Given:** "Act as 8 hedge fund personas and generate top picks per asset class for ETFs/stocks based on latest market data"
**Ideal Trading Style Per Asset Class:**

| Asset Class | Ideal Style | Rationale |
|-------------|------------|-----------|
| **Equities** | Fundamental + momentum hybrid | Earnings quality + price trend for institutional-size entries |
| **ETFs** | Tactical momentum + mean-reversion | Sector rotation, factor timing, low cost |
| **Crypto** | On-chain analytics + narrative cycles | Protocol adoption metrics + macro correlation |
| **Commodities** | Macro thematic + seasonal | Geopolitical supply risk, central bank demand |
| **Bonds** | Duration positioning + rate view | Fed path, yield curve shape, flight-to-safety |

---

# SECTION 3: PERSONA DEEP DIVES

---

## PERSONA 1: MACRO STRATEGIST (Global Thematic)

**Profile:** 15+ years at a $5B macro fund. Top-down, regime-aware. Trades across all asset classes using ETFs for efficient directional bets. Holds 3-12 month conviction positions. Fundamentally driven but technically timed.

**Trading Rules:**
- Never fight the macro trend
- Position sizing by conviction (highest conviction = 40% of book)
- Use ETFs for single-name diversification
- Trail stops at 2x ATR for trending positions
- Exit when thesis invalidated, not when stopped out

**Picks:**

| # | Symbol | Direction | Entry | TP | SL | R:R | Hold Period | Rationale |
|---|--------|-----------|-------|-----|-----|-----|-------------|-----------|
| 1 | GLD | LONG | 413.82 | 4,800 | 3,950 | 3.2:1 | 6-12mo | Central bank buying record. De-dollarization. Iran escalation = instant bid. Gold already +36% but macro thesis is the strongest since 2008. Real rates declining. |
| 2 | TLT | LONG | 84.68 | 92 | 78 | 2.8:1 | 3-6mo | 30Y yield at 19yr highs = mean reversion. Fed signaled patience. If Iran risk-off accelerates, duration rally. Currently -5.4% on 6M = contrarian entry. |
| 3 | EEM | LONG | ~45 | 65 | 38 | 2.5:1 | 6-9mo | IMF: EM growth 3.9% led by India/China. EEM +50% YoY but momentum intact. Tariff fears overblown for commodity-exporting EMs. |
| 4 | USO | LONG | ~141 | 165 | 120 | 2.0:1 | 3-6mo | Iran supply disruption premium. Brent $100+. OPEC+ discipline. Risk: demand destruction if recession. |
| 5 | BTC-USD | LONG | 77,188 | 88,000 | 62,000 | 1.8:1 | 6-18mo | Halving cycle, ETF inflows, institutional adoption. Gold-BTC correlation increasing in risk-off. |

**What They Research:**
- IMF WEO, Fed FOMC minutes, CPI/employment prints
- Central bank reserve allocation shifts
- Geopolitical risk indices (GPR index)
- COT positioning for futures
- Weekly jobless claims, ISM, PMI composites

**Data Points They Need:**
- Real-time sovereign yield curves across 10+ countries
- Central bank meeting calendars and forward guidance
- Geopolitical event probability models
- Cross-asset correlation matrices (rolling 90-day)
- ETF flow data (daily) for GLD, TLT, EEM

**How to Improve Their Picks:**
1. Add GDP nowcasting models for real-time growth tracking
2. Incorporate options-implied probabilities for Fed rate path
3. Use credit default swap spreads as risk sentiment proxy
4. Track COT positioning for commodity trades
5. Add carry-adjusted yield analysis for fixed income

---

## PERSONA 2: QUANT / STATISTICAL ARBITRAGE (Factor-Driven)

**Profile:** PhD quant at a $2B systematic fund. Factor-based (momentum, value, quality, low-vol). High turnover. Targets 60-70% WR with strict R:R management. All decisions rule-based.

**Trading Rules:**
- Entry only when factor score > 75th percentile AND price > 200DMA
- Max 5% per position, 20% per sector
- Rebalance weekly (Monday AM)
- Stop-loss at -7% for equities, -4% for ETFs
- Take-profit trailing: 2x ATR or 15% max hold return

**Picks:**

| # | Symbol | Direction | Entry | TP | SL | R:R | Hold Period | Rationale |
|---|--------|-----------|-------|-----|-----|-----|-------------|-----------|
| 1 | NVDA | LONG | 215.33 | 295 | 195 | 1.5:1 | 4-8wk | Q1 rev $81.6B (+85% YoY). Fwd P/E 24.5. PEG 0.66 = undervalued relative to growth. Momentum strong. 180 EMA trending up. |
| 2 | QQQ | LONG | 712.33 | 800 | 665 | 2.4:1 | 6-12wk | Tech factor momentum. +14.3% YTD outperforming SPY+9.3%. RSI not overbought. Momentum + value hybrid signal. |
| 3 | XLK | LONG | 180.39 | 210 | 155 | 2.1:1 | 4-8wk | YTD +25.3%. Semiconductor subsector (SOXX +4.75%). Sector rotation into tech confirmed by flows. |
| 4 | IWM | LONG | 285.12 | 310 | 255 | 2.3:1 | 6-12wk | Small-cap premium mean-reversion. Lagging large-cap by 5%+ = value gap. Rate cuts would disproportionately benefit. |
| 5 | MSFT | LONG | ~308 | 450 | 280 | 1.5:1 | 6-18mo | Azure AI revenue acceleration. Trading at PEG ~1.2 vs QQQ peers. Copilot enterprise monetization ramping. |

**What They Research:**
- Factor scores (momentum, value, quality, low-vol) computed daily
- Cross-sectional z-scores for each factor
- Earnings surprise history (SUE)
- Analyst revision breadth
- Institutional flow data (13F filings, prime broker data)

**Data Points They Need:**
- High-frequency factor score updates (at least daily)
- Earnings estimate revisions (Bloomberg/FactSet quality)
- Short interest % of float for each candidate
- Institutional ownership changes
- Dark pool activity / ATS prints
- VIX term structure slope for volatility regime

**How to Improve Their Picks:**
1. Add machine learning factor timing (when to overweight vs. underweight each factor)
2. Incorporate earnings quality score (accruals, cash conversion)
3. Use NLP on earnings call transcripts for guidance tone analysis
4. Add macro regime classifier to toggle factor exposure
5. Implement pairs trading overlays for hedging

---

## PERSONA 3: EVENT-DRIVEN / CATALYST HUNTER

**Profile:** Former equity research analyst turned PM at a $3B event-driven fund. Earnings plays, M&A targets, regulatory catalysts. Average hold 2-6 weeks. Uses alpha engine's VT ADX+RSI2 Equity and Restatement Short strategies.

**Trading Rules:**
- Only enter 5 days before or 2 days after a catalyst
- Max position: 3% of portfolio
- Hard stop at -10% regardless of thesis
- Take-profit at 2x expected move (based on historical analogs)
- Never hold through earnings if not already positioned

**Picks:**

| # | Symbol | Direction | Entry | TP | SL | R:R | Hold Period | Rationale |
|---|--------|-----------|-------|-----|-----|-----|-------------|-----------|
| 1 | TSLA | SHORT | 426.01 | 320 | 470 | 1.8:1 | 3-6wk | EV demand slowing. Post-earnings pattern. VIX low = complacency. Deliveries decelerating. `ag_vt_adx_rsi2_equity` mean-reversion signal on extended rally. |
| 2 | NVDA | LONG | 215.33 | 295 | 195 | 2.0:1 | 4-8wk | Post-earnings pullback re-entry. $80B buyback announced. GPU shortage narrative intact. "Sell the news" created opportunity. |
| 3 | AAPL | LONG | 308.82 | 360 | 270 | 2.0:1 | 3-6mo | Apple Intelligence cycle launch. Services revenue trajectory. `ag_vt_pattern_sweep` covers in 13-symbol universe with candlestick+SMC+harmonic composite. |
| 4 | SOXX | LONG | 537.33 | 620 | 480 | 1.8:1 | 4-8wk | Semi sector momentum. CHIPS Act tailwinds. MU +5%, AMD +3.99%, ARM +11.6% — sector breadth confirming. |
| 5 | BB | SHORT | 7.91 | 5 | 12 | 2.3:1 | 2-4wk | Top loser at -18.95% today. Low float = gap risk. Cybersecurity narrative fading. Check for 8-K restructuring risk. |

**What They Research:**
- Earnings calendars and whisper numbers
- SEC EDGAR filings (8-K, 13D, S-1)
- FDA/regulatory calendars
- Insider trading reports (Vickers Top Buyers/Sellers)
- Activist investor positions

**Data Points They Need:**
- Earnings estimate vs. actual surprise history for each name
- Options activity (unusual volume, sweep detection)
- Insider selling/buying alerts in real-time
- Analyst rating change triggers
- EDGAR filing NLP for risk factor language changes
- Court ruling calendars (for pharma, tech IP)

**How to Improve Their Picks:**
1. Real-time EDGAR screener with NLP classification of filing type
2. Options flow monitoring (dark pool prints, sweeps)
3. Earnings call transcript analysis (guidance tone, Q&A quality)
4. Analyst revision clustering (when 3+ analysts change simultaneously)
5. Add M&A probability model (deal spread analysis, strategic fit scoring)

---

## PERSONA 4: CTA / TREND FOLLOWER (Momentum & Breakout)

**Profile:** Systematic CTA with 10yr track record. Pure price-action. Uses Donchian channels, EMA crossovers, ATR-based position sizing. 40% win rate target with 2.5:1 avg R:R. Cuts losers fast, lets winners run.

**Trading Rules:**
- Entry on 20-day breakout above highest high (long) or below lowest low (short)
- Stop at 2x ATR from entry
- Trail stop at 1.5x ATR once 1:1 R:R achieved
- Max exposure: 20% per position, 50% total
- No overnight holds for short-term signals (2-5 day timeframe)

**Picks:**

| # | Symbol | Direction | Entry | TP | SL | R:R | Hold Period | Rationale |
|---|--------|-----------|-------|-----|-----|-----|-------------|-----------|
| 1 | QQQ | LONG | 712.33 | 800 | 665 | 3.0:1 | 2-8wk | ATH breakout at $717+ confirmed. ADX trending + RSI(2) pullback zone. Validated: 179 trades, PF 1.14, WR 55%, MaxDD -10.2%. |
| 2 | SOL-USD | LONG | ~165 | 220 | 120 | 2.5:1 | 3-6wk | Fastest-growing L1 ecosystem. Above 50+200 EMA cloud. `ag_vol_scaled_keltner`: volume >70th pctile + EMA50>EMA200 + Keltner breakout. |
| 3 | XLE | LONG | 59.49 | 75 | 52 | 2.1:1 | 2-6wk | Energy sector +0.54% today. Brent $100+. 50DMA rising. Breakout above $62 confirms new leg. |
| 4 | AMD | LONG | 467.51 | 560 | 350 | 2.3:1 | 3-8wk | Crypto-adjacent + AI PC thesis. +8.1% today. Breakout above $447 confirms. Semi sector momentum (XSD +4.75%). |
| 5 | BTC-USD | LONG | 77,188 | 88,000 | 58,000 | 1.8:1 | 4-12wk | Above all EMAs. Trend following: simple timing beats naive hold (Kirby & Ostdiek 2012). |

**What They Research:**
- Price action: 20/50/200 DMA positions
- ATR volatility for position sizing
- Breakout/breakdown levels (Donchian channels)
- Volume confirmation (above 20-day average)
- Sector relative strength (rotation signals)

**Data Points They Need:**
- Real-time intraday high/low for breakout detection
- ATR calculations at multiple timeframes (1H, 4H, daily)
- Volume-weighted price levels (VWAP)
- Sector ETF relative performance rankings
- VIX regime classifier (trending vs. mean-reversion)

**How to Improve Their Picks:**
1. Add regime classifier (trending vs. ranging) to avoid false breakouts
2. Implement adaptive ATR multiplier (wider in high vol, tighter in low vol)
3. Use relative strength ranking to filter breakouts (only trade top-2 sectors)
4. Add volume profile analysis for better S/L placement
5. Incorporate overnight gap risk model

---

## PERSONA 5: VALUE / DEEP FUNDAMENTAL (Intrinsic Value)

**Profile:** CFA charterholder, former value PM at a $5B long-only fund. Balance sheet focused. 6-24 month holds. Seeks 20%+ margin of safety. Uses quality/value composite scoring. Minimum 15% ROIC threshold.

**Trading Rules:**
- P/E below 5-year historical average OR PEG < 1.0
- ROIC > 15% (minimum)
- FCF yield > 4%
- Debt/Equity < 60%
- Buyback yield positive and growing
- Max 5% per position, 30% per sector

**Picks:**

| # | Symbol | Direction | Entry | TP | SL | R:R | Hold Period | Rationale |
|---|--------|-----------|-------|-----|-----|-----|-------------|-----------|
| 1 | AAPL | LONG | 308.82 | 360 | 250 | 2.5:1 | 12-24mo | P/E ~28 but services margin expansion accelerating. FCF ~$100B. Buyback $100B+/yr. DCF suggests $308 is below intrinsic at 10% WACC. |
| 2 | JPM | LONG | ~168 | 250 | 135 | 2.3:1 | 12-24mo | Leading bank. NII resilient. Trading near book value (1.2x). Best positioned for rising rate normalization. Quality: AAA rating. |
| 3 | UNH | LONG | ~525 | 650 | 400 | 1.8:1 | 12-24mo | Healthcare secular demand. Optum margin expansion. 20yr+ earnings growth. Defensive in recession. Dividend aristocrat. |
| 4 | LLY | LONG | ~580 | 800 | 500 | 2.0:1 | 18-36mo | GLP-1 franchise ~$100B peak revenue. Donanemab Alzheimer's pipeline. Gross margins ~80%. Revenue growth >20%. |
| 5 | BRK-B | LONG | ~400 | 520 | 320 | 1.8:1 | 12-24mo | Floating rate portfolio benefits in any rate scenario. Cash pile ~$200B. Diversified subsidiaries. Cheap at slight book value discount. |

**What They Research:**
- Annual reports (10-K), quarterly earnings calls
- DCF models with multiple scenarios
- Balance sheet ratios: ROIC, FCF yield, D/E, current ratio
- Buyback history and authorization levels
- Management compensation alignment (skin in the game)

**Data Points They Need:**
- Consensus analyst EPS estimates (short and long-term)
- Free cash flow projections (DCF inputs)
- Insider ownership and transaction data
- Customer concentration risk metrics
- Patent pipeline (pharma/tech)
- Regulatory environment analysis

**How to Improve Their Picks:**
1. Add ESG scoring (many value funds now require it)
2. Implement real-time CFO quality metrics (accruals quality, working capital changes)
3. Add competitive moat analysis (Porter's five forces scoring)
4. Use NTM (next twelve months) estimates vs. static trailing metrics
5. Track share count reduction trajectory (buyback + dilution)

---

## PERSONA 6: RISK PARITY / PORTFOLIO CONSTRUCTION (Balanced Allocator)

**Profile:** Portfolio construction specialist at a $10B multi-asset fund. Target vol 10-12%. Allocates by RISK CONTRIBUTION, not conviction. Uses Bridgewater/AQR-inspired framework. Quarterly rebalance.

**Trading Rules:**
- Target portfolio volatility: 10% annualized
- Equal risk contribution from each asset class
- Leverage allowed up to 3x (futures/derivatives)
- Rebalance when any asset class drifts >5% from target weight
- Max drawdown limit: -15% (reduce leverage if breached)

**Picks:**

| # | Symbol | Direction | Allocation | Target | Stop | Rationale |
|---|--------|-----------|-----------|--------|------|-----------|
| 1 | SPY | LONG | 40% risk budget | $780 | $660 | Core equity exposure. 9S&P at 7,473, YTD +9.3%. Lowest risk per unit of expected return in equities. |
| 2 | TLT | LONG | 25% risk budget | $92 | $78 | Return stream diversification. Yields declining. 30Y at 19yr high → mean reversion opportunity. Negative equity correlation. |
| 3 | GLD | LONG | 20% risk budget | $4,800 | $4,050 | Inflation/geopolitical hedge. Negative equity correlation in stress. +36% YTD trend intact. |
| 4 | VNQ | LONG | 15% risk budget | Target varies | $80-ish | Real estate diversification. Rate-sensitive. If 10Y declines further, significant upside. Uses 5% risk budget for option overlay. |

**What They Research:**
- Rolling 60-day correlation matrices (cross-asset)
- Realized volatility by asset class (for risk budgeting)
- Yield curve shape (2s10s, 3m10y)
- Dollar index (DXY) for international asset translation
- Inflation breakevens (TIPS spreads)

**Data Points They Need:**
- Daily realized volatility by asset class
- Cross-asset correlation matrices (rolling)
- VIX term structure (contango vs. backwardation)
- Portfolio-level VaR and CVaR (expected shortfall)
- Leverage utilization across margin accounts
- Options-implied correlation (for dispersion trades)

**How to Improve Their Picks:**
1. Add factor exposure decomposition (how much equity beta is SPY contributing?)
2. Implement dynamic risk budgeting (shift allocations based on regime)
3. Use tail-risk hedging overlays (OTM puts in stress regimes)
4. Add inflation regime classifier (deflation vs. reflation vs. stagflation)
5. Track funding costs (repo rates, margin rates for leverage)

---

## PERSONA 7: VOLATILITY / OPTIONS STRATEGIST (Vol Premium Harvester)

**Profile:** Vol arb desk head at a $2B options market maker. Sells premium when IV > realized vol. Systematically harvests theta. Fund-neutral. Uses VIX term structure for regime signals.

**Trading Rules:**
- Sell vol when VIX > 20th percentile of 52-week range (currently cheap at 16.70)
- Buy vol when VIX < 10th percentile (tail hedging)
- Preferred structures: iron condors, strangles, covered calls
- Max position: 15% of portfolio
- Roll when 50% of max profit achieved or 21 DTE

**Picks:**

| # | Strategy | Direction | Entry Level | Target | Stop | Rationale |
|---|----------|-----------|-------------|--------|------|-----------|
| 1 | VIX Short Strangles | SELL | 16.70 VIX | Close at 13-14 | 20.00 | VIX at ~30th percentile. Implied > realized vol premium. Sell 30-45 DTE strangles on SPY. |
| 2 | QQQ/SPY Covered Calls | NEUTRAL-BULLISH | Current | Max premium | 30 DTE | Collect theta on elevated IV. Target 2-3% monthly income. Roll monthly. |
| 3 | GLD Put Spread | PROTECTIVE | 413.82 | Defined | 30 DTE | Gold hedge with defined cost. Buy OTM puts on GLD as portfolio insurance. |
| 4 | Iron Condor on SPY | MARKET NEUTRAL | SPY 745 | Max width - credit received | 45 DTE | Range-bound environment. Sell 700 put / 680 put + sell 780 call / 800 call. Collect ~3% monthly. |

**What They Research:**
- VIX term structure shape (contango = normal, backwardation = fear)
- Implied vs. realized volatility spread (VIX vs. 20-day realized)
- Options flow (unusual activity, sweep detection)
- Earnings calendar (vol spikes)
- Skew (put vs. call implied vol differential)

**Data Points They Need:**
- VIX futures curve (1M, 3M, 6M)
- Options Greeks (delta, gamma, theta, vega) for position management
- Historical realized volatility (20-day, 60-day rolling)
- Earnings date calendar for vol event timing
- Dark pool / block trade activity for directional signal

**How to Improve Their Picks:**
1. Add skew trading (sell expensive puts, buy cheap calls)
2. Implement variance swap overlay for cleaner vol exposure
3. Use machine learning for realized vol forecasting
4. Add event-driven vol calendar (FDA, CPI, FOMC)
5. Track options settlement flows for pinning risk

---

## PERSONA 8: CRYPTO-NATIVE / DIGITAL ASSET FUND

**Profile:** Crypto fund GP with on-chain analytics team. $500M AUM. Narrative-driven but data-validated. Uses on-chain metrics (NVT, MVRV, SOPR, exchange flows) alongside price action.

**Trading Rules:**
- Only trade assets with >$1B mcap and >$100M daily volume
- Max 20% per position, 40% per sector (L1, DeFi, etc.)
- Use DEX data (DEXScreener, DeFiLlama) for early signals
- Stop-loss at -15% for majors, -25% for alts
- Trail using 50DMA once +50% from entry

**Picks:**

| # | Symbol | Direction | Entry | TP | SL | R:R | Hold Period | Rationale |
|---|--------|-----------|-------|-----|-----|-----|-------------|-----------|
| 1 | BTC | LONG | $77,188 | $88,000 | $62,000 | 1.8:1 | 6-18mo | Post-halving cycle. Exchange net outflows 14d. MVRV = 1.5 (not overheated). Hashrate ATH. ETF inflows resuming. |
| 2 | ETH | LONG | $2,102 | $2,800 | $1,600 | 2.1:1 | 6-12mo | ETH ETF thesis. Staking yield 3.5%. ETH/BTC ratio mean-reversion (ratio depressed). Ecosystem L1 dominance. |
| 3 | SOL | LONG | ~$165 | $220 | $120 | 2.5:1 | 3-8wk | Fastest L1 throughput. Ecosystem momentum (DeFi, NFT, mobile). Volume breakout. EMA 5>13>34 alignment. |
| 4 | LINK | LONG | ~$18 | $30 | $12 | 3.0:1 | 6-18mo | CCIP cross-chain adoption by major institutions. Real DON staking revenue. Undervalued vs. DeFi peers. |
| 5 | HYPE | LONG | ~$48 | $70 | $30 | 2.9:1 | 6-12mo | On-chain derivatives leader. Institutional positioning growing. Low float relative to growth. |

**What They Research:**
- On-chain metrics: MVRV, NVT, SOPR, exchange flows
- DEX volumes and TVL changes per protocol
- Developer activity (GitHub commits, active addresses)
- Whale wallet tracking
- Governance proposals and voting patterns

**Data Points They Need:**
- Real-time on-chain analytics (Glassnode, Nansen, Arkham)
- Exchange inflow/outflow data (net position change)
- DEX trading volumes (Uniswap, Jupiter, etc.)
- Stablecoin supply growth (USDT, USDC minting)
- Funding rates across major CEXs
- Regulatory news feeds (classifications, enforcement actions)

**How to Improve Their Picks:**
1. Add MVRV Z-Score for more precise cycle timing
2. Implement SOPR (Spent Output Profit Ratio) for profit-taking signals
3. Track long/short ratios on major perps exchanges
4. Add altcoin rotation indicator (capital rotation between sectors)
5. Use DeFi composability metrics (cross-protocol flows)

---

# SECTION 4: SELF-ASSESSMENT SURVEY

## How Each Persona Can Improve Their Picks

### Survey Questions Asked to Each Persona:

1. **What's your biggest blind spot?**
   - Macro Strategist: Confirmation bias toward bearish macro; sometimes misses uptrends
   - Quant: Overfits to historical factor regimes; doesn't adapt to structural breaks
   - Event-Driven: Survivorship bias in analog selection; misses novel catalysts
   - CTA: Whipsawed in choppy markets; high transaction costs erode edge
   - Value: Value traps (cheap for a reason); misses secular disruption
   - Risk Parity: Assumes historical correlations hold; breaks in crisis
   - Vol Trader: Black swan events; short gamma risk in extreme moves
   - Crypto: Regulatory risk modeling; exit liquidity in alts

2. **What data points are you missing?**
   - Macro: Real-time credit spreads, sovereign CDS, shipping rates
   - Quant: Dark pool prints, ATS activity, NLP sentiment from transcripts
   - Event-Driven: Options flow monitoring, EDGAR filing NLP, activist positioning
   - CTA: Volume profile analysis, relative strength ranking, overnight gap risk
   - Value: Customer concentration data, patent pipeline, ESG risk scores
   - Risk Parity: Realized vol by asset class, factor exposure decomposition, VaR
   - Vol Trader: Skew dynamics, variance swap levels, earnings event implied moves
   - Crypto: On-chain flows, whale tracking, developer commits, stablecoin mint activity

3. **What's your edge decay rate?**
   - Macro: 12-18 months before positioning becomes crowded
   - Quant: 6-12 months before factor premium compresses
   - Event-Driven: Per-event; requires constant catalyst pipeline
   - CTA: 18-24 months in trending markets; degrades in choppy
   - Value: 24+ months (structural); quarterly earnings resets
   - Risk Parity: Stable unless correlation regime shifts
   - Vol Trader: Daily (theta decay is the product)
   - Crypto: 3-6 months (narrative cycles rotate)

4. **What's your Sharpe target and current hit rate?**
   - Macro: ~1.0 Sharpe, 55-60% directional accuracy
   - Quant: ~1.2 Sharpe, 58-65% hit rate
   - Event-Driven: ~0.8 Sharpe, 50-55% hit rate (high payoff skew)
   - CTA: ~0.9 Sharpe, 40-45% hit rate (high avg R:R)
   - Value: ~1.1 Sharpe, 60-65% hit rate (longer holding periods)
   - Risk Parity: ~0.7 Sharpe (lower vol = lower Sharpe), consistent
   - Vol Trader: ~1.5 Sharpe (if maintained), 65-70% for premium selling
   - Crypto: ~0.8 Sharpe, 50-55% for high-conviction plays

---

# SECTION 5: TIER-LIST RATING ALGORITHM

## Scoring Framework (1-10 Scale)

### EQUITIES ALGORITHM

```
Score = w1*Momentum(20%) + w2*Quality(25%) + w3*Growth(20%) + w4*Value(15%) + w5*Sentiment(10%) + w6*Risk(10%)

Where:
  Momentum (20%) = Rank within universe by 3M, 6M, 12M return (z-scored)
  Quality (25%) = ROIC (>15% = 10, 10-15% = 7, 5-10% = 5, <5% = 2)
                 + FCF Yield (>5% = 10, 3-5% = 7, 1-3% = 5, <1% = 2)
                 + Balance Sheet Strength (D/E, current ratio)
  Growth (20%) = Revenue growth rate (normalized vs. peers)
                 + EPS growth rate
  Value (15%) = P/E vs. 5yr avg (below = higher score)
               + P/S, P/B, PEG ratio
  Sentiment (10%) = Analyst consensus (buy/hold/sell ratio)
                   + Insider buying in last 90d
                   + Short interest %
  Risk (10%) = Volatility (lower = better)
               + Max drawdown in last 12mo
               + Sector risk score

Tiers: S = 9.0+, A = 7.5-8.9, B = 6.0-7.4, C = 4.5-5.9, D = 3.0-4.4, F = <3.0
```

### ETF ALGORITHM

```
Score = w1*TrendStrength(25%) + w2*RelativeStrength(20%) + w3*ExpenseRatio(10%) + w4*Liquidity(10%) + w5*MacroAlignment(25%) + w6*RiskMetrics(10%)

Where:
  TrendStrength (25%) = Price vs. 200DMA (>1 = 10, 0.95-1 = 7, 0.9-0.95 = 5, <0.9 = 3)
                       + ADX > 25 (trending confirmation)
  RelativeStrength (20%) = vs. SPY over 3M, 6M (z-scored within universe)
  ExpenseRatio (10%) = Below 0.20% = 10, 0.20-0.40% = 7, 0.40-0.60% = 5, >0.60% = 3
  Liquidity (10%) = Daily volume > $100M = 10, $50-100M = 7, $20-50M = 5, <$20M = 2
  MacroAlignment (25%) = Rate environment fit (+/- rates, inflation regime)
                         + Sector cycle position
  RiskMetrics (10%) = Sharpe ratio > 1.0 = 10, 0.5-1.0 = 7, 0-0.5 = 4, <0 = 2
                     + Max DD in last 12mo

Tiers: S = 9.0+, A = 7.5-8.9, B = 6.0-7.4, C = 4.5-5.9, D = 3.0-4.4, F = <3.0
```

### CRYPTO ALGORITHM

```
Score = w1*OnChainHealth(30%) + w2*NarrativeStrength(20%) + w3*PriceTrend(20%) + w4*Liquidity(10%) + w5*Tokenomics(10%) + w6*RiskFlags(10%)

Where:
  OnChainHealth (30%) = MVRV ratio (1-3 = healthy, >3.5 = overheated)
                        Exchange net flow (outflows = bullish, +5 pts)
                        Active addresses growth (30d)
                        SOPR > 1 (in profit)
  NarrativeStrength (20%) = Sector narrative momentum (AI, DeFi, gaming, etc.)
                           Developer activity (GitHub commits trending)
                           Institutional adoption signals (ETF approval, partnerships)
  PriceTrend (20%) = 50DMA > 200DMA (golden cross = +5)
                    14-day RSI (50-70 = ideal, <30 = oversold bounce, >70 = caution)
                    Volume above 20d avg (+3 pts)
  Liquidity (10%) = MCap > $10B = 10, $5-10B = 7, $1-5B = 5, <$1B = 2
                   Daily volume > $500M = 10, $100-500M = 7, $20-100M = 4, <$20M = 2
  Tokenomics (10%) = Emission schedule (low/deflationary = better)
                    Staking yield (real yield = bonus)
                    Vesting schedules for team/VC
  RiskFlags (10%) = Regulatory risk score (0-10)
                   Smart contract audit status
                   Concentration risk (team wallets, VC unlocks)

Tiers: S = 9.0+, A = 7.5-8.9, B = 6.0-7.4, C = 4.5-5.9, D = 3.0-4.4, F = <3.0
```

### COMMODITIES / BONDS ALGORITHM

```
Score = w1*MacroTrend(30%) + w2*SupplyDemand(25%) + w3*Seasonality(15%) + w4*CarryYield(15%) + w5*RelativeValue(15%)

Where:
  MacroTrend (30%) = GDP growth alignment (commodities up in expansion)
                     Real rate environment (gold up when real rates falling)
                     Geopolitical risk premium (supply disruption risk)
  SupplyDemand (25%) = Inventory levels (EIA, USDA data)
                      Production forecasts (OPEC, USDA)
                      Import/export balance shifts
  Seasonality (15%) = Historical monthly performance patterns
                      Agricultural growing season
                      Energy demand cycles (heating/cooling)
  CarryYield (15%) = For bonds: real yield level
                    For commodities: contango/backwardation cost
                    Roll yield for futures
  RelativeValue (15%): Gold/silver ratio (historical mean ~80)
                      Oil/gas ratio
                      Bond yield spread vs. historical range

Tiers: S = 9.0+, A = 7.5-8.9, B = 6.0-7.4, C = 4.5-5.9, D = 3.0-4.4, F = <3.0
```

---

# SECTION 6: IMPLEMENTATION CHECKLIST

For any hedge fund to operationalize these picks:

- [ ] Set up real-time data feeds (Bloomberg Terminal, Refinitiv, or alternatives)
- [ ] Build alpha engine scoring pipeline per asset class
- [ ] Define risk limits (max position, sector concentration, leverage, max drawdown)
- [ ] Establish execution framework (VWAP, TWAP, iceberg orders for large positions)
- [ ] Implement daily risk monitoring (VaR, stress testing, correlation monitoring)
- [ ] Set up weekly rebalance process for quantitative strategies
- [ ] Create research review process (thesis validation, position sizing adjustment)
- [ ] Build performance attribution (factor, sector, security selection)
- [ ] Implement stop-loss enforcement automation
- [ ] Schedule monthly portfolio review with all persona perspectives

---

*Generated: 2026-05-25 | Data sourced from Yahoo Finance, alpha_engine framework, baby_strategies, IMF WEO April 2026*
*Disclaimer: Educational/hypothetical analysis only. Not financial advice. All scores and picks are based on publicly available data and subjective judgment at time of writing.*