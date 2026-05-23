# Multi-Asset Predictability Tournament Plan

**Goal:** Find what we can predict with HIGH certainty, then put real money behind it.
**Date:** 2026-03-11
**Status:** PLANNING → EXECUTION

---

## The Problem

- Crypto has been a failure — too volatile, 51.9% WR barely beats a coin flip
- We have 1,615 strategies, 26 portfolios, 81+ systems — but no confident money-maker
- Most systems are crypto-only; we've barely tested other asset classes
- We need to find the asset class where our algorithms have REAL predictive edge

## The Solution: Multi-Asset Predictability Tournament

Run identical strategy families across 7 asset classes simultaneously.
Track everything. After 2-4 weeks, the data tells us where to put real money.

---

## Asset Classes & Portfolios

### 1. Stock Index Futures (ES/NQ/CL/ZN/GC)
**Why:** Highest liquidity, 23hr trading, institutional-grade price action
**Symbols:** ES (S&P 500), NQ (Nasdaq 100), CL (Crude Oil), ZN (10Y Note), GC (Gold), SI (Silver)
**Data Source:** yfinance (ES=F, NQ=F, CL=F, ZN=F, GC=F)
**Risk Profile:** -3% SL / +6% TP / 10-day max hold
**Portfolios (10):**

| ID | Strategy Family | Description |
|---|---|---|
| `idx_mean_revert` | Connors RSI-2 adapted | RSI(2) < 10 on ES/NQ (proven 75.7% on SPY) |
| `idx_trend_follow` | EMA stack + ADX | Multi-TF EMA alignment with ADX > 25 filter |
| `idx_momentum` | Cross-sectional momentum | Long strongest / short weakest index |
| `idx_stat_arb` | ES vs NQ spread | Mean reversion on ES/NQ ratio |
| `idx_vol_breakout` | Keltner/ATR expansion | Volatility breakout after compression |
| `idx_regime` | HMM regime-aware | Switch strategies based on regime state |
| `idx_dna_evolved` | DNA genome evolved | Best evolved strategies applied to futures |
| `idx_gp_expression` | Genetic programming | GP-evolved indicator formulas on index data |
| `idx_ensemble_vote` | Multi-model consensus | XGBoost + LightGBM + GRU ensemble |
| `idx_macro_driver` | VIX + DXY + yield curve | Macro-driven position management |

### 2. Individual Stocks (Blue-Chip + Growth)
**Why:** Well-studied, earnings-driven, lower noise than crypto
**Symbols:** AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, JPM, V, UNH, HD, PG, KO, JNJ, WMT (15 blue-chip) + SOFI, PLTR, RIVN, MARA, RIOT (5 growth)
**Data Source:** yfinance
**Risk Profile:** -6% SL / +12% TP / 10-day max hold
**Existing:** `alpha_engine/equity_strategies.py` — 6 strategies already built
**Portfolios (10):**

| ID | Strategy Family | Description |
|---|---|---|
| `stk_connors_rsi2` | Connors RSI-2 | PROVEN on SPY (75.7% WR, p=6×10⁻⁶) — apply per-stock |
| `stk_quality_value` | Quality + Value composite | Dividend aristocrats with factor scoring |
| `stk_momentum_12m` | Jegadeesh-Titman momentum | Top decile 12-month return (skip last month) |
| `stk_earnings_drift` | Post-earnings drift | Trade after earnings surprises |
| `stk_dna_evolved` | DNA genome evolved | Evolved strategies applied to equities |
| `stk_ml_classifier` | XGBoost stock classifier | Retrained crypto ML Edge model on stock features |
| `stk_regime_switch` | Regime-aware selector | HMM regime → pick appropriate strategy |
| `stk_sector_rotation` | Sector ETF rotation | Monthly rebalance to strongest sector |
| `stk_vix_reversal` | VIX spike reversal | PROVEN (72% WR, Sharpe 6.2) — adapted for stocks |
| `stk_intermarket` | SPY/VIX/DXY correlation | Risk-on/risk-off multi-factor |

### 3. Forex (Major + Cross Pairs)
**Why:** $7.5T daily volume, 24hr, highly mathematical, mean-reverting
**Symbols:** EURUSD, USDJPY, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, EURJPY, GBPJPY, AUDJPY
**Data Source:** yfinance (EURUSD=X etc.) + existing findforex2 infrastructure
**Risk Profile:** -2.5% SL / +3% TP / 14-day max hold (tight for FX)
**Existing:** `alpha_engine/forex_strategies.py` — 6 strategies
**Reference:** myfxbook.com verified systems for benchmarking
**Portfolios (10):**

| ID | Strategy Family | Description |
|---|---|---|
| `fx_carry_momentum` | Carry trade + momentum filter | Long high-yield pairs with 20d momentum (Sharpe 0.9-1.2) |
| `fx_london_breakout` | Session breakout | 7am-8am London range breakout (62% WR documented) |
| `fx_mean_revert_200` | 200-day SMA reversion | Anti-trend on extreme SMA distances |
| `fx_jpy_risk_off` | JPY safe-haven | Risk-off reversal detection (USDJPY/EURJPY) |
| `fx_dxy_regime` | Dollar strength rotation | DXY correlation regime switch |
| `fx_dna_evolved` | DNA genome evolved | Evolved strategies on FX pairs |
| `fx_ml_classifier` | LightGBM FX classifier | Retrained from crypto ML Edge features |
| `fx_macro_driver` | Interest rate differential | Central bank policy divergence trades |
| `fx_rsi_reversion` | RSI(2) on FX majors | Connors RSI-2 adapted for currencies |
| `fx_cross_pair_arb` | Cross-pair triangulation | EURUSD × USDJPY vs EURJPY spread |

### 4. ETFs (Sector + Thematic + Bond)
**Why:** Diversified exposure, lower single-stock risk, sector rotation alpha
**Symbols:** XLK, XLV, XLF, XLE, XLU, XLRE, GLD, SLV, TLT, HYG, VNQ, ARKK, QQQ, IWM, EEM
**Data Source:** yfinance
**Risk Profile:** -4% SL / +8% TP / 14-day max hold
**Portfolios (10):**

| ID | Strategy Family | Description |
|---|---|---|
| `etf_sector_momentum` | Sector rotation | Monthly rebalance to top 3 sectors by momentum |
| `etf_risk_parity` | Risk parity allocation | ATR-weighted equal risk across sectors |
| `etf_bond_equity` | TLT/SPY rotation | Classic 60/40 with tactical timing |
| `etf_gold_hedge` | GLD/SLV momentum | Precious metals trend following |
| `etf_value_growth` | Value vs Growth rotation | IWD/IWF relative strength |
| `etf_dna_evolved` | DNA genome evolved | Evolved strategies on ETF data |
| `etf_ml_classifier` | ML-driven sector selection | XGBoost sector scoring |
| `etf_volatility` | VIX/UVXY mean reversion | Volatility selling strategy |
| `etf_dividend_capture` | High-yield ETF rotation | Yield + momentum composite |
| `etf_global_macro` | EEM/EFA/SPY rotation | Regional allocation based on macro |

### 5. Penny Stocks (High-Risk, Potential Moonshots)
**Why:** Low capital at risk, 10-100x upside potential, lottery-ticket allocation
**Symbols:** SOFI, PLTR, NIO, RIVN, LCID, MARA, RIOT, PATH, IONQ, JOBY, DNA, OPEN, WISH, CLOV, BBIG + scanner for new additions
**Data Source:** yfinance + penny stock screeners
**Risk Profile:** -12% SL / +25% TP / 5-day max hold (wider due to volatility)
**Existing:** Penny volume breakout strategy in alpha_engine
**Portfolios (10):**

| ID | Strategy Family | Description |
|---|---|---|
| `penny_volume_spike` | Volume breakout | 3x avg volume + price > VWAP |
| `penny_momentum` | 3-day momentum surge | +10% in 3 days with volume |
| `penny_dip_buy` | RSI capitulation | RSI(14) < 25 with reversal candle |
| `penny_social_velocity` | Social engagement spike | Reddit/Twitter mentions acceleration |
| `penny_insider_follow` | SEC filing tracker | Follow insider buys on penny stocks |
| `penny_dna_evolved` | DNA genome evolved | Evolved strategies for micro-caps |
| `penny_technical_breakout` | Chart pattern breakout | Cup & handle, ascending triangle |
| `penny_ml_pump_detect` | ML pump detector | LightGBM trained on historical pumps |
| `penny_sector_heat` | Sector heat rotation | Rotate to hottest penny stock sectors |
| `penny_short_squeeze` | Short interest tracker | High SI% + volume surge |

### 6. Meme Coins (Similar to Penny Stocks for Crypto)
**Why:** Already have infrastructure, lottery-ticket allocation, community-driven pumps
**Symbols:** DOGEUSDT, SHIBUSDT, PEPEUSDT, FLOKIUSDT, BONKUSDT, WIFUSDT, BRETTUSDT + new additions
**Data Source:** Binance API (existing)
**Risk Profile:** -15% SL / +30% TP / 3-day max hold
**Existing:** Meme coin strategies in alpha_engine, competition data
**Portfolios (5):**

| ID | Strategy Family | Description |
|---|---|---|
| `meme_social_pump` | Social velocity detector | Twitter/Reddit mention spike |
| `meme_whale_follow` | Whale wallet tracker | Large transfers to exchanges |
| `meme_technical` | Classic TA on meme coins | RSI + MACD + volume |
| `meme_dna_evolved` | DNA genome evolved | Evolved specifically for meme coins |
| `meme_momentum_ride` | Momentum with trailing stop | Ride pumps with tight trailing stops |

### 7. Crypto (Existing — Track Record Improvement)
**Already running 26 portfolios.** Focus on fixing what's broken:
- Fix Alpha Engine P&L tracking (currently dead at 0%)
- Reduce portfolio overlap (43 positions but only 6 unique symbols)
- Apply PROVEN strategies only (Connors RSI-2, Funding Rate Carry)
- DNA evolution strategies already generating picks

### 8. Future Considerations
- **Mutual Funds:** Lowest priority. Lock-up periods make active trading impossible.
  Existing infrastructure at findmutualfunds/portfolio1/ — keep for reference.
- **Sports Betting:** Already automated (5x daily via GitHub Actions).
  Track separately — different risk/reward profile.

---

## Position Tracking Schema (All Asset Classes)

Every position across all portfolios will track:

```
{
  // Identity
  "id": "sha256_hash",
  "portfolio_id": "idx_mean_revert",
  "asset_class": "INDEX_FUTURES" | "STOCKS" | "FOREX" | "ETF" | "PENNY" | "MEME_COIN" | "CRYPTO",

  // Entry
  "symbol": "ES=F",
  "direction": "LONG" | "SHORT",
  "entry_price": 5892.50,
  "entry_time_est": "2026-03-11 09:32:15 EST",
  "size_usd": 1200.00,
  "leverage": 1,  // 1x for stocks/ETFs, up to 20x for crypto/forex
  "strategy": "connors_rsi2",
  "source_system": "alpha_engine",
  "confidence": 0.82,

  // Targets
  "take_profit": 6245.00,
  "stop_loss": 5715.00,
  "risk_reward_ratio": 2.05,

  // Live State
  "current_price": 5920.00,
  "unrealized_pnl_pct": 0.47,
  "unrealized_pnl_usd": 5.58,
  "peak_pnl_pct": 1.2,
  "trough_pnl_pct": -0.3,
  "last_updated_est": "2026-03-11 14:00:00 EST",

  // Exit (when closed)
  "exit_price": 6100.00,
  "exit_time_est": "2026-03-13 10:15:00 EST",
  "exit_reason": "TP" | "SL" | "TRAIL" | "TIME_EXIT" | "FORCE_CLOSE",
  "realized_pnl_pct": 3.52,
  "realized_pnl_usd": 42.24,
  "hold_duration_hours": 48.7,

  // Costs
  "commission_entry": 1.80,
  "commission_exit": 1.80,
  "slippage_entry": 0.60,
  "slippage_exit": 0.60,
  "net_pnl_usd": 37.44,  // After ALL costs

  // Status
  "status": "OPEN" | "TP_HIT" | "SL_HIT" | "TRAIL_HIT" | "TIME_EXIT"
}
```

---

## Tournament Design

### Phase 1: Setup (Week 1)
1. Create multi-asset scanner module (`multi_asset_scanner.py`)
   - Extend existing `alpha_engine/scanner.py` pattern
   - Fetch OHLCV data for all 7 asset classes via yfinance + Binance
   - Compute shared features (RSI, MACD, BB, ATR, EMA stack, volume ratios)
   - Apply DNA-evolved strategies from genome engine to each asset class

2. Create 65+ portfolios across all asset classes (defined above)
   - Each starts with $10,000 virtual capital
   - Position sizing: 8-20% per trade depending on asset class
   - Commission model per asset class (IBKR rates)

3. Deploy automated scanning
   - GitHub Actions workflow: every 30 min for crypto/forex, hourly for stocks/ETFs
   - Forward picks generation for all asset classes

### Phase 2: Tournament Run (Weeks 2-4)
4. All 65+ portfolios trade simultaneously on paper
5. Track every position with full schema (above)
6. Daily scoreboard updates to dashboard
7. Weekly asset class rankings published

### Phase 3: Analysis (Week 4+)
8. Compute predictability metrics per asset class
9. Identify winning strategies per asset class
10. Kill losing portfolios, scale winners
11. Decision: where to deploy real capital

---

## Predictability Metrics (Per Asset Class)

For each of the 7 asset classes, we compute:

| Metric | Description | Target |
|---|---|---|
| **Win Rate** | % of trades profitable | > 55% |
| **Profit Factor** | Gross profit / Gross loss | > 1.5 |
| **Sharpe Ratio** | Risk-adjusted returns (annualized) | > 1.5 |
| **Max Drawdown** | Worst peak-to-trough | < 15% |
| **Calmar Ratio** | CAGR / Max Drawdown | > 1.0 |
| **Average PnL/Trade** | Mean realized PnL per trade | > 0.5% |
| **Win Streak** | Longest consecutive wins | > 5 |
| **Recovery Factor** | Net profit / Max drawdown | > 2.0 |
| **Sample Size** | Total trades (statistical significance) | > 30 |
| **P-Value** | Statistical significance of edge | < 0.05 |
| **Consistency Score** | % of weeks profitable | > 60% |

### Predictability Grading Scale

| Grade | Win Rate | Sharpe | P-Value | Verdict |
|---|---|---|---|---|
| **A+** | > 70% | > 2.5 | < 0.001 | DEPLOY REAL CAPITAL |
| **A** | > 65% | > 2.0 | < 0.01 | STRONG CANDIDATE |
| **B** | > 58% | > 1.5 | < 0.05 | PROMISING - MORE DATA |
| **C** | > 52% | > 1.0 | < 0.10 | MARGINAL - KEEP TESTING |
| **D** | > 50% | > 0.5 | > 0.10 | RANDOM NOISE |
| **F** | < 50% | < 0.5 | N/A | KILL IT |

---

## Strategy Recycling Plan

### DNA Evolution → Multi-Asset
The genome engine (5 engines, 1,615 strategies) is currently crypto-only.
Here's how we adapt it:

1. **Feature Engineering is Universal**
   - RSI, MACD, BB, ATR, EMA, volume — works on ANY OHLCV data
   - Just need to swap data source (Binance → yfinance)

2. **Re-evolve per Asset Class**
   - Run `genome/evolve_strategies.py` with stock data → stock-optimized DNA
   - Run with forex data → forex-optimized DNA
   - Run with ETF data → ETF-optimized DNA
   - 4-island model adapts automatically (bear/bull/range/recent)

3. **GP Expression Trees (GENESIS)**
   - `genome/genetic_programmer.py` evolves indicator formulas
   - Feed it stock price data → discovers stock-specific indicators
   - Fed forex data → discovers FX-specific indicators

4. **Ensemble Coevolution (LEGION)**
   - Evolve teams of strategies per asset class
   - Different assets may need different consensus mechanisms

### ML Models → Multi-Asset
1. **Crypto ML Edge** (LightGBM, validated Sharpe 12-40)
   - Retrain on stock/forex/ETF features
   - Same walk-forward CV framework
   - Same DSR/PSR statistical gates

2. **ML Battleground** (XGBoost filter + regime + GRU)
   - System A (filter): Retrain on non-crypto features
   - System B (regime): HMM is already asset-agnostic
   - System C (GRU): Retrain on stock/forex 15m+1h data

3. **Mercury2** (3-ensemble XGBoost)
   - Currently failing on crypto (Sharpe -0.027)
   - May perform better on less volatile assets (stocks/ETFs)

### Proven Strategies → Multi-Asset
| Strategy | Crypto WR | Stock Potential | Forex Potential | Reason |
|---|---|---|---|---|
| Connors RSI-2 | 62.5% | **75.7% (PROVEN on SPY)** | ~60% est. | Mean reversion works best on liquid assets |
| VIX Spike Reversal | N/A | **72% (PROVEN)** | N/A | Equity-specific |
| Carry Trade | N/A | N/A | **70% (PROVEN)** | Interest rate differential |
| Funding Rate | 71% | N/A | N/A | Crypto-specific |
| London Breakout | N/A | N/A | **62% documented** | Session-specific |

---

## Existing Infrastructure to Resurrect

### Stocks (Active but underutilized)
- `STOCKS/competition/run_competition.py` — backtests 12+ strategies on real data
- `alpha_engine/equity_strategies.py` — 6 equity strategies ready
- Last competition run: Mar 8, 2026 ✓

### Forex (Dormant)
- `findforex2/portfolio/` — portfolio tracking HTML (needs data pipeline)
- `alpha_engine/forex_strategies.py` — 6 strategies ready
- Needs: automated scanner for FX pairs

### Penny Stocks (Light activity)
- `findstocks/portfolio2/penny-stocks.html` — dashboard exists
- Volume breakout strategy in alpha_engine
- Needs: dedicated scanner + more strategies

### ML Systems (Mixed state)
- **Active:** ML Battleground, Crypto ML Edge, Claude Gainer ML
- **Stale:** Mercury2 (failing), ML Crypto Predictor (research only)
- **Needs:** Retraining on multi-asset data

### Hub Dashboard (Active — command center)
- `hub/index.html` — 26 systems catalogued
- Perfect place to add multi-asset tournament status

---

## Implementation Phases

### Phase 1: Multi-Asset Scanner (3-5 days)
- [ ] Create `multi_asset_scanner.py` — unified scanner for all asset classes
- [ ] Extend `alpha_engine/config.py` with full symbol universes
- [ ] Add yfinance data fetcher for stocks/ETFs/forex/futures
- [ ] Compute shared features across all asset classes
- [ ] Create portfolio definitions for all 65+ portfolios
- [ ] GitHub Actions workflow for automated scanning

### Phase 2: DNA Evolution Per Asset Class (3-5 days)
- [ ] Modify `genome/dna_backtester.py` to accept yfinance data
- [ ] Run evolution cycles for stocks, forex, ETFs, futures
- [ ] Generate evolved picks per asset class
- [ ] GP expression tree evolution on non-crypto data

### Phase 3: ML Retraining (3-5 days)
- [ ] Retrain Crypto ML Edge models on stock/forex features
- [ ] Retrain ML Battleground System B regime detector on multi-asset
- [ ] Deploy retrained models into scanning pipeline

### Phase 4: Tournament Dashboard (2-3 days)
- [ ] Create tournament dashboard HTML
  - Asset class leaderboard
  - Per-portfolio equity curves
  - Predictability grades (A+ through F)
  - Filter by asset class
- [ ] Deploy to GitHub Pages
- [ ] Link from Hub dashboard

### Phase 5: Tournament Run (2-4 weeks)
- [ ] All 65+ portfolios trading simultaneously
- [ ] Daily automated scoring
- [ ] Weekly asset class reports
- [ ] Identify winners

### Phase 6: Live Deployment Decision
- [ ] Asset classes with Grade A+ or A → real capital candidate
- [ ] Start small ($50-100/trade)
- [ ] Scale with proven track record
- [ ] Kill everything Grade D or below

---

## Expected Predictability Ranking (Hypothesis)

Based on academic research + our existing data:

| Rank | Asset Class | Expected Predictability | Reasoning |
|---|---|---|---|
| 1 | **Stock Index Futures (ES/NQ)** | HIGH | Deep liquidity, Connors RSI-2 PROVEN at 75.7%, institutional patterns |
| 2 | **Individual Stocks** | HIGH | Earnings drift, factor models, years of academic validation |
| 3 | **Forex Majors** | MEDIUM-HIGH | Mean reversion works well, carry trade proven, very liquid |
| 4 | **ETFs** | MEDIUM | Sector rotation has documented alpha, less noise than stocks |
| 5 | **Penny Stocks** | LOW-MEDIUM | High noise, but asymmetric risk/reward (lottery ticket) |
| 6 | **Meme Coins** | LOW | Pure sentiment, keep allocation small |
| 7 | **Crypto (BTC/ETH/Alts)** | LOW | Despite 1,615 strategies, barely beats coin flip |

**Key Insight:** Our BEST strategies (Connors RSI-2, VIX Spike) are already proven on STOCKS, not crypto.
The tournament may confirm that we should SHIFT focus from crypto to equities/forex.

---

## Success Criteria

The tournament is successful if we identify:
- At least 2 asset classes with Grade A+ or A
- At least 5 individual portfolios with Sharpe > 2.0 and WR > 60%
- A clear "best strategy per asset class" winner
- Statistical significance (p < 0.05) on at least 10 portfolios
- A deployment plan for real capital

**The goal is NOT more strategies. The goal is FEWER strategies that ACTUALLY WORK.**

---

## Files to Create

| File | Purpose |
|---|---|
| `multi_asset/scanner.py` | Unified multi-asset scanner |
| `multi_asset/portfolio_defs.py` | All 65+ portfolio definitions |
| `multi_asset/tournament.py` | Tournament scoring engine |
| `multi_asset/data_fetcher.py` | yfinance + Binance unified data layer |
| `multi_asset/feature_engine.py` | Shared feature computation |
| `multi_asset/dashboard.html` | Tournament dashboard |
| `.github/workflows/multi-asset-tournament.yml` | Automated scanning workflow |

---

## References

- Connors RSI-2: Connors & Alvarez (2009) — 75.7% WR on SPY (p=6×10⁻⁶)
- VIX Spike Reversal: 72% WR, Sharpe 6.2 — our own forward test
- Carry Trade: Burnside et al. (2011) — Sharpe 0.9-1.2 with momentum filter
- London Breakout: ~62% WR — documented in forex literature
- Jegadeesh-Titman Momentum: JFE 1993 — foundational factor research
- Cross-Sectional Momentum: Liu et al. (2022) JFE — Sharpe ~2.1 on crypto
- myfxbook.com: Verified forex system performance benchmarks
