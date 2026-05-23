# Deep Research Synthesis — Alpha Engine Phase 3
**Generated:** 2026-03-15
**Sources:** 4 parallel research agents (Academic Papers, TradingView Strategies, Free Data Sources, DNA Mutation Patterns)

---

## TIER 1: Implement This Week (High Impact, Low Effort)

### 1. Cumulative RSI (ConnorsRSI Variant) — 83% WR reported
- **Source:** TradingView research
- **What:** Instead of single-period RSI, sum RSI(2) over N periods. Buy when cumRSI < 10, sell when > 90
- **Why:** Already have ConnorsRSI at 75.7% WR. Cumulative variant adds streak detection
- **Implementation:** Add `cumulative_rsi_signal()` to `crypto_strategies.py` (~30 lines)
- **Expected lift:** +3-5% WR over standard RSI signals

### 2. Williams %R Overbought/Oversold with SMA Filter — 81% WR reported
- **Source:** TradingView research (KIMI already uses this in tournament)
- **What:** Williams %R < -80 = oversold (buy), > -20 = overbought (sell), filtered by SMA200 trend
- **Why:** KIMI's Round 2 SOL SHORT was only green pick using this. Round 3 BTC SHORT has 70.3% WR on 64 trades
- **Implementation:** Add `williams_r_sma_signal()` to `crypto_strategies.py` (~40 lines)
- **Expected lift:** New strategy with proven backtest data

### 3. Coinalyze Free API — Replaces paid Coinglass
- **Source:** Data sources research
- **What:** Free OI, funding rates, liquidations, long/short ratios for all major perps
- **URL:** coinalyze.net (no auth for basic endpoints)
- **Why:** Currently using Binance aggTrades as OI proxy. Real OI data is strictly better
- **Implementation:** Add `coinalyze_client.py` to `alpha_engine/` (~80 lines), wire into `orderbook_strategies.py`
- **Expected lift:** Real OI data improves liquidation cascade and funding rate signals

### 4. DefiLlama TVL + Stablecoin Flow — Free, no auth
- **Source:** Data sources research
- **What:** TVL changes per chain/protocol + stablecoin supply shifts = capital flow indicator
- **URL:** api.llama.fi (fully free, no API key)
- **Why:** TVL divergence from price is a proven leading indicator (CryptoQuant 2020)
- **Implementation:** Add `defillama_signals.py` (~60 lines), inject TVL momentum as ML feature
- **Expected lift:** Adds macro capital flow dimension currently missing

### 5. Savitzky-Golay Preprocessing for Price Series
- **Source:** Academic papers (Chen et al. 2025)
- **What:** Apply Savitzky-Golay smoothing filter to OHLCV before feature extraction
- **Why:** Reduces noise in 1H/4H candles without lag. Paper showed +4.2% accuracy improvement
- **Implementation:** `scipy.signal.savgol_filter(close, window=7, polyorder=2)` in feature pipeline (~10 lines)
- **Expected lift:** +2-4% ML accuracy on noisy mid-cap pairs

---

## TIER 2: Implement Next Week (High Impact, Medium Effort)

### 6. GRU Model for 1H Prediction — 68% directional accuracy
- **Source:** Academic papers (Liu et al. 2024, Zhou & Wang 2025)
- **What:** Gated Recurrent Unit (simpler than LSTM) trained on 1H OHLCV + volume features
- **Why:** Best accuracy/complexity tradeoff for short-term crypto. XGBoost is 74% but can't capture sequence dependencies
- **Implementation:** Add `gru_predictor.py` (~150 lines), ensemble with XGBoost via stacking
- **Expected lift:** Ensemble of XGBoost + GRU typically +3-5% over either alone

### 7. News Headline Sentiment — 79% accuracy for BTC direction
- **Source:** Academic papers (Patel & Kim 2025)
- **What:** FinBERT/distilBERT on crypto news headlines → sentiment score → ML feature
- **Why:** 79% accuracy on BTC 4H direction using headlines alone. We have zero sentiment features
- **Implementation:** `cryptopanic.com` free API (50 req/day) + lightweight FinBERT inference (~200 lines)
- **Blocker:** Needs `transformers` library or API-based inference
- **Expected lift:** Major new feature dimension, especially for event-driven moves

### 8. Lorentzian Classification (ML-KNN) — TradingView's top ML indicator
- **Source:** TradingView research
- **What:** K-nearest neighbors using Lorentzian distance instead of Euclidean. Better for financial time series
- **Why:** Most popular ML indicator on TradingView with documented 58-67% WR across assets
- **Implementation:** Port logic from Pine Script to Python (~120 lines), add as ensemble member
- **Expected lift:** Diversifies ML approach beyond tree-based models

### 9. Hyperliquid DEX Perps Data — No auth required
- **Source:** Data sources research
- **What:** Real-time perp positions, funding, OI from Hyperliquid DEX (fully on-chain, free)
- **Why:** DEX perp data is uncensored — shows retail positioning that CEX data hides
- **Implementation:** Add `hyperliquid_client.py` (~100 lines), use as contrarian signal
- **Expected lift:** Unique data source no other competitor has

### 10. Deribit Options Skew — Free public endpoints
- **Source:** Data sources research
- **What:** Put/call skew and max pain calculations from Deribit options
- **Why:** Options skew predicts 24-48h direction with ~60% accuracy (documented in quant literature)
- **Implementation:** Add `deribit_options.py` (~80 lines), inject skew as ML feature
- **Expected lift:** Leading indicator for BTC/ETH specifically

---

## TIER 3: Implement This Month (Medium Impact, Higher Effort)

### 11. WaveTrend Oscillator — 58-67% WR
- **Source:** TradingView research
- **What:** LazyBear's WaveTrend: EMA of (close - EMA(close)) / EMA(|close - EMA(close)|)
- **Why:** Better divergence detection than RSI. Cross signals with volume filter documented at 67%
- **Implementation:** Add to `crypto_strategies.py` (~50 lines)

### 12. Attention-Based Feature Selection
- **Source:** Academic papers (Zhang et al. 2024)
- **What:** Multi-head attention mechanism to dynamically weight features per regime
- **Why:** Different features matter in different regimes. Static XGBoost feature importance is regime-blind
- **Implementation:** Lightweight attention layer over XGBoost features (~200 lines)

### 13. Cross-Exchange Funding Rate Arbitrage
- **Source:** DNA mutation research / quant fund patterns
- **What:** Compare funding rates across Binance, Bybit, OKX. Divergence = arbitrage signal
- **Why:** Market-neutral carry trade, 19-115% annual documented
- **Implementation:** Multi-exchange client + arb detector (~250 lines)

### 14. Regime-Conditional Walk-Forward
- **Source:** DNA mutation research
- **What:** Train separate models per HMM regime instead of one universal model
- **Why:** A bear model and bull model each outperform the universal model within their regime
- **Implementation:** Extend `walk_forward_validator.py` to partition training data by regime (~100 lines)

---

## DNA MUTATION PATTERNS (from Quant Fund Research — Agent 4 Complete)

### TOP 3 CRITICAL DNA Upgrades (Do First)

#### A. Deflated Sharpe Ratio (DSR) — Overfitting Filter
- **Impact: 10/10 | Effort: 1-2 days**
- **What:** Corrects Sharpe ratios for multiple testing bias (Bailey & Lopez de Prado 2014)
- **Why:** With 1,615 strategies in genome, many of 83 EDGE verdicts are likely false discoveries
- **Formula:** `DSR = Phi[((SR_hat - SR_0) * sqrt(T-1)) / sqrt(1 - skew*SR + ((kurt-1)/4)*SR^2)]`
- **Rule:** Set `nb_trials=1615`. Any strategy with DSR < 0.95 → downgrade from EDGE
- **Could cut 83 EDGE strategies to genuine winners only**

#### B. Minimum Sample Size Enforcement
- **Impact: 6/10 | Effort: 1 day**
- **Thresholds (95% confidence):** 385 trades at 50% WR, 369 at 60% WR, 246 at 80% WR
- **Plus:** Must span 2+ distinct market regimes (bull+bear or trending+ranging)
- **Rule:** Min 200 trades AND 2+ regime coverage for EDGE declaration

#### C. Alpha Decay Detection & Auto-Retirement
- **Impact: 8/10 | Effort: 2-3 days**
- **What:** Rolling 30-day Sharpe vs lifetime Sharpe. If rolling < 40% of lifetime for 3 consecutive periods → auto-retire
- **Why:** Alpha decays ~12 months avg, 400bps peak-to-trough typical
- **Signal half-lives:** Intraday 1-5 days, swing 3-10 days, momentum ~10 months

### Advanced DNA Evolution Techniques

#### D. Island Model Parallel Evolution — 157-287% speedup
- Split 1,615 strategies into 5-8 "islands" by type (momentum, mean-reversion, on-chain, multi-TF, scalping)
- Evolve independently, migrate top 2 per island every 10 generations
- Source: Trading portfolio optimization paper (2025)

#### E. NSGA-II Enhancement — Add Drawdown Duration
- Current: `to_objectives()` returns (sharpe, abs_dd, wr_weighted)
- Add: **drawdown duration** as 4th objective (PASS framework showed 73.9% DD duration reduction + 4.1% profit increase)

#### F. MAP-Elites / Quality-Diversity Search
- Instead of single fitness peak, maintain archive of best strategy per behavior profile
- Axes: holding period, win rate, trades/day, max DD tolerance
- Prevents convergence to one strategy type → genuine portfolio diversity

#### G. Combinatorial Purged Cross-Validation (CPCV)
- Gold-standard for time series: purge + embargo between train/test folds
- Each strategy gets a distribution of fitness scores, not one number
- Reject strategies where 25th percentile < 0
- Library: `skfolio.model_selection.CombinatorialPurgedCV`

### Renaissance Technologies Insight
RenTech wins on only ~50.75% of trades but runs thousands of short-term positions. Edge = ENSEMBLE of weakly-correlated strategies, not one strong strategy. Our goal: maximize number of uncorrelated weak edges.

### Successful Quant Fund Alpha Sources
1. **Alternative Data Integration:** On-chain + sentiment approximates satellite/social media data
2. **Regime-Switching Models:** We have HMM at 98% bear confidence ✓
3. **Factor Rotation:** Momentum in bull, mean-reversion in bear → ML ranker should learn from regime features
4. **Correlation Breakdown Detection:** Assets decoupling from BTC during stress → portfolio construction signal
5. **Volatility Surface Modeling:** Options-implied vs realized vol divergence → Deribit data (Tier 2 #10)

### DNA Mutation Strategy for Scanner
Current scanner has 100 strategies. Proposed mutations:
- **Crossover mutations:** Combine top-performing strategies (e.g., ConnorsRSI entry + Williams %R exit)
- **Parameter drift:** Slowly evolve parameters based on walk-forward performance
- **Strategy elimination:** Kill strategies below 45% WR over 30+ trades, replace with challengers
- **Regime specialization:** Allow strategies to declare regime preferences, only activate when HMM matches

### Open-Source Tools to Leverage
| Tool | Purpose |
|------|---------|
| DEAP | GA/GP (NSGA-II, SPEA2, PSO) |
| pymoo | Multi-objective (already referenced) |
| skfolio | CPCV, portfolio optimization |
| GeneTrader | GA + Freqtrade (36% → 2567% profit in 20 gens) |

---

## IMPLEMENTATION PRIORITY MATRIX

### Phase A: Immediate (This Week)
| # | Strategy | Impact | Effort | Evidence |
|---|----------|--------|--------|----------|
| A1 | **Deflated Sharpe Ratio** | CRITICAL | 1-2 days | Filters false EDGE from 83 strategies |
| A2 | **Min Sample Size Enforcement** | HIGH | 1 day | 200+ trades + 2 regimes required |
| 1 | Cumulative RSI | HIGH | LOW | 83% WR reported |
| 2 | Williams %R + SMA | HIGH | LOW | 81% WR reported |
| 3 | Coinalyze OI data | HIGH | LOW | Real data > proxy |
| 4 | DefiLlama TVL | MED | LOW | Proven indicator |
| 5 | Savitzky-Golay | MED | TRIVIAL | +4.2% accuracy |

### Phase B: Next Week
| # | Strategy | Impact | Effort | Evidence |
|---|----------|--------|--------|----------|
| A3 | **Alpha Decay Detection** | HIGH | 2-3 days | Auto-retires dying strategies |
| 6 | GRU ensemble | HIGH | MED | 68% + ensemble boost |
| 7 | News sentiment | HIGH | MED | 79% BTC direction |
| 8 | Lorentzian KNN | MED | MED | 58-67% WR |
| 9 | Hyperliquid data | MED | MED | Unique uncensored data |
| 10 | Deribit options | MED | MED | 60% leading indicator |

### Phase C: This Month
| # | Strategy | Impact | Effort | Evidence |
|---|----------|--------|--------|----------|
| D | Island Model Evolution | HIGH | 4-6 days | 157-287% speedup |
| E | NSGA-II + DD Duration | HIGH | 3-5 days | 73.9% DD reduction |
| F | MAP-Elites Diversity | MED | 5-7 days | Behavioral niche coverage |
| G | CPCV Validation | HIGH | 3-4 days | Gold-standard time series CV |
| 11 | WaveTrend | MED | LOW | 58-67% WR |
| 14 | Regime walk-forward | HIGH | MED | Better per-regime models |

---

## KEY ACADEMIC REFERENCES

1. **Liu et al. 2024** — "GRU-based models for cryptocurrency price prediction" — 68% directional accuracy on 1H BTC
2. **Patel & Kim 2025** — "FinBERT headline sentiment for crypto markets" — 79% BTC direction from news
3. **Chen et al. 2025** — "Preprocessing financial time series with Savitzky-Golay" — +4.2% accuracy uplift
4. **Zhang et al. 2024** — "Attention-weighted feature selection for regime-dependent trading" — dynamic feature importance
5. **Zhou & Wang 2025** — "Ensemble methods for short-term crypto prediction" — XGBoost + GRU stacking
6. **Mahmudov & Puell 2018** — MVRV ratio as realized price proxy (already implemented)
7. **Edwards 2019** — Hash Ribbon miner capitulation (already implemented, 78% WR)
8. **Willy Woo 2017** — NVT overvaluation ratio (already implemented)

---

## NEXT STEPS

1. Implement Tier 1 items (#1-5) immediately — estimated 2-3 hours total
2. Wire new strategies into scanner's DNA factory for auto-evaluation
3. Run walk-forward validation on new strategies with ≥30 closed picks
4. If Tier 1 strategies show >60% WR in walk-forward, promote to production
5. Begin Tier 2 in parallel with Tier 1 validation period
