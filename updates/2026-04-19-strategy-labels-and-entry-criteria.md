# Audit Dashboard Strategy Labels & Entry Criteria — 2026-04-19

## Summary

Investigated every strategy appearing on `findtorontoevents.ca/audit/` and ensured each has a descriptive label in the dashboard's `_STRATEGY_DESCRIPTIONS` map. Previously 31 of 32 active strategies had no label — they appeared as raw internal names. Now all 32 have descriptions including entry criteria, signal logic, and why each symbol was chosen.

---

## Strategy Reference Table

### Non-Crypto / Multi-Asset Strategies

| Strategy | Category | Entry Criteria | Symbol Selection | Picks |
|----------|----------|----------------|------------------|-------|
| **cftc_cot_commercial_signal** | Commodity | CFTC Socrata API: commercial hedgers net-long >55% + speculators net-short >50% → BUY. Opposite → SELL. Weekly COT divergence. TP=2x ATR, SL=1.5x ATR. | Commodity futures with COT data: ZW=F (wheat), CL=F (crude oil) | 2 |
| **clone_hl_copy_PensionFund_24M** | Crypto (copy trade) | Mirrors OKX top copy trader "PensionFund_24M" (870d, +58.6% PnL, 55.6% WR, 600 copiers). Entry when trader opens new position. Direction matches. | Whatever PensionFund_24M holds: AVAX, LINK, NEAR, SUI, RENDER, HYPE, ONDO | 7 |
| **clone_hl_copy_lb_None** | Crypto (copy trade) | Mirrors OKX leaderboard top traders (highest PnL ratio, >30d track record). Entry when leaderboard trader opens position. | Top OKX leaderboard traders' positions: RENDER, ONDO, BTC, BNB, AVAX, LINK, NEAR, SUI | 11 |
| **cot_positioning** | Commodity | CFTC COT commercial net positioning z-score > +1.5 → BUY (smart money accumulating). Z-score < -1.5 → SELL. Cross-referenced with Binance top trader L/S ratio. | Commodity futures with COT data: ZW=F (wheat), NG=F (natgas), ZS=F (soy), CT=F (cotton) | 4 |
| **cta_commodity_momentum_term** | Commodity/Futures | Momentum ranking across 1/3/6/12 month lookbacks + futures term structure (contango vs backwardation). Long top-ranked in backwardation, short bottom-ranked in contango. TP=2.5x ATR, SL=1.5x ATR. | Futures with momentum + term structure alignment: SI=F (silver), GC=F (gold), ZC=F (corn), ZW=F (wheat) | 4 |
| **cta_cross_asset_tsmom** | Cross-asset | 12-month TSMOM across commodities, FX, equity index futures. Positive 12m momentum → LONG, negative → SHORT. Vol-targeted sizing (10% ann. vol). | Cross-asset: GC=F (gold), CL=F (crude), USDJPY=X (forex) | 3 |
| **forex_carry_momentum** | Forex | Positive carry (long high-yielder) + EMA20 > EMA50 (trend) + RSI < 70 (not overbought) → BUY. Carry > 2% annual + EMA stack aligned. TP=1.5x ATR, SL=1x ATR. | High carry pairs: GBPJPY, USDJPY, CADJPY | 3 |
| **forex_rsi2_mean_reversion** | Forex | Connors RSI(2) < 10 (deep oversold) + price > SMA(200) → BUY. RSI(2) > 90 + price < SMA(200) → SELL. 68%+ WR academic. TP at SMA(5), SL=1.5x ATR. Conf capped 0.70. | RSI2 extremes in trending FX: EURGBP, CADJPY, EURJPY | 3 |
| **futures_bb_mean_reversion** | Futures | Bollinger Bands (20,2): price < lower BB + RSI < 30 + volume > 1.2x avg → BUY. Price > upper BB + RSI > 70 → SELL. TP at BB midline. SL beyond BB by 0.5x ATR. | Overextended futures: NQ=F (Nasdaq), CT=F (cotton) | 2 |
| **futures_momentum** | Futures | EMA12 > EMA26 > EMA50 (full bullish stack) + ADX > 20 → BUY. Bearish stack → SELL. TP=2x ATR, SL=1x ATR. Confidence from ADX + stack alignment. | Trending metals: SI=F (silver), HG=F (copper), PL=F (platinum) | 3 |
| **ig_contrarian_sentiment** | Forex | IG retail client data: >70% retail LONG → SELL (contrarian fade). >70% SHORT → BUY. Confidence from positioning extreme (75%+ = higher). TP=1.5x ATR, SL=1x ATR. | Major FX where retail is extreme: AUDUSD, EURJPY, AUDJPY, EURUSD, GBPUSD, USDCAD, GBPJPY, CADJPY | 8 |
| **myfxbook_retail_contrarian** | Forex | Myfxbook aggregated retail positioning: >65% retail LONG → SELL. >65% SHORT → BUY. Entry at retail extreme + RSI divergence + key level. TP=1.5x ATR, SL=1x ATR. | Major FX with retail extreme: AUDJPY, AUDUSD, EURJPY, EURUSD, GBPUSD, USDCAD, GBPJPY | 8 |
| **regime_mild_bull** | Equity | SPY > SMA50 + VIX < 22 + SPY 5d > 0% (mild bull regime). Buys quality equities in pullback: stock RSI(2) < 20 + SMA(200) uptrend. TP=7-8%, SL=4-5%. | Large-cap growth in regime pullback: GOOGL, SPY, SOFI | 3 |
| **regime_strong_bull** | Equity | SPY > SMA20 + VIX < 18 + SPY 5d > +2% (strong bull). Buys mega-cap tech breaking out. TP=7-8%, SL=4-5%. Conf=0.95 max. | Mega-cap tech leaders: MSFT | 1 |
| **stocks_rsi2_pullback** | Equity | Connors RSI(2) < 10 + price > SMA(200) + S&P 500 quality universe. TP=4%, SL=3%. 88.9% WR on 9 trades. | Blue-chip pullback names: JNJ, KO, MRK, LLY, RIOT | 5 |
| **stocks_rsi2_pullback_fast** | Equity | Same RSI2 < 10 entry as stocks_rsi2_pullback, faster exit: sell RSI(2) > 70 (vs 90). TP=3.5%, SL=3%. | Fast-exit variant on same universe: JNJ | 1 |
| **stocks_rsi2_pullback_slow** | Equity | Same RSI2 < 10 entry, slower exit: hold until RSI(2) > 90 AND price < SMA(5). TP=5%, SL=3%. | Slow-exit variant: JNJ | 1 |
| **stocks_rsi2_pullback_tight** | Equity | Same RSI2 < 10 entry, tight risk: TP=3.5%, SL=2.5%. For conservative entries. | Tight-stop variant: JNJ | 1 |
| **stocks_rsi2_pullback_wide** | Equity | Same RSI2 < 10 entry, wide risk: TP=5.5%, SL=4%. For noisy names. | Wide-stop variant: JNJ | 1 |

### ML-Enhanced Per-Symbol Strategies

| Strategy | Model Type | Timeframe | Symbol | Entry Logic | Confidence |
|----------|-----------|-----------|--------|-------------|------------|
| **ml_enhanced_APEUSDT_1d_D_ensemble_stack** | Ensemble (LGBM+XGB+RF) | 1d | APE/USDT | Ensemble majority vote, >55% prob → SHORT | 0.40 |
| **ml_enhanced_DYDXUSDT_15m_D_ensemble_stack** | Ensemble stack | 15m | DYDX/USDT | Short-term momentum + orderflow features → LONG | 0.40 |
| **ml_enhanced_FETUSDT_1d_B_lightgbm** | LightGBM | 1d | FET/USDT | Technical features (RSI, MACD, BB, vol z-score) → LONG | 0.80 |
| **ml_enhanced_HBARUSDT_1d_D_ensemble_stack** | Ensemble stack | 1d | HBAR/USDT | Momentum + mean-reversion + regime features → LONG | 0.40 |
| **ml_enhanced_INJUSDT_1d_B_lightgbm** | LightGBM | 1d | INJ/USDT | RSI, MACD, volume, BB features → LONG | 0.60 |
| **ml_enhanced_JTOUSDT_1d_B_lightgbm** | LightGBM | 1d | JTO/USDT | Momentum + volatility regime → LONG | 0.40 |
| **ml_enhanced_POLUSDT_1d_B_lightgbm** | LightGBM | 1d | POL/USDT | RSI, MACD, volume z-score, BB → LONG | 0.40 |
| **ml_enhanced_RENDERUSDT_1h_D_ensemble_stack** | Ensemble stack | 1h | RENDER/USDT | Orderflow + momentum features → LONG | 0.80 |
| **ml_enhanced_STRKUSDT_15m_D_ensemble_stack** | Ensemble stack | 15m | STRK/USDT | Micro-momentum + volume profile → LONG | 0.40 |
| **ml_enhanced_TONUSDT_4h_D_ensemble_stack** | Ensemble stack | 4h | TON/USDT | Momentum regime + volume → LONG | 0.40 |
| **ml_enhanced_TRXUSDT_1d_B_lightgbm** | LightGBM | 1d | TRX/USDT | RSI, MACD, BB, volume z-score → LONG | 0.40 |
| **ml_enhanced_ZKUSDT_4h_D_ensemble_stack** | Ensemble stack | 4h | ZK/USDT | Momentum + mean-reversion regime → LONG | 0.40 |

### ML Naming Convention

ML-enhanced strategy names follow the pattern: `ml_enhanced_{SYMBOL}_{TIMEFRAME}_{GRADE}_{MODEL}`

- **SYMBOL**: Trading pair (e.g., FETUSDT, HBARUSDT)
- **TIMEFRAME**: Candle interval (1d, 4h, 1h, 15m)
- **GRADE**: Model quality grade (A/B/C/D) — D=low confidence, B=moderate, A=high
- **MODEL**: Model architecture — `lightgbm` (single model) or `ensemble_stack` (multi-model vote)

All ML strategies use TP=2x ATR, SL=1.5x ATR with confidence derived from model probability + walk-forward validation.

---

## Already-Labeled Strategies (39 existing in _STRATEGY_DESCRIPTIONS)

These were already present before this update:

| Strategy | Short Description |
|----------|-------------------|
| antigravity_breakout | Antigravity breakout detection |
| antigravity_momentum | Antigravity momentum strategy |
| antigravity_reversal | Antigravity reversal detection |
| bollinger_breakout | Bollinger Band breakout |
| bollinger_squeeze | Bollinger squeeze momentum |
| connors_rsi2 | Connors RSI(2) mean reversion |
| cta_tsmom_blend | Blended CTA TSMOM across assets |
| divergence_detector | RSI/MACD divergence detection |
| elliott_wave | Elliott wave counting |
| ema_cross | EMA crossover strategy |
| ema_stack | EMA stack trend alignment |
| funding_rate_arb | Funding rate arbitrage |
| hyrotrader_elite | Hyrotrader elite scoring |
| ichimoku_cloud | Ichimoku cloud breakout |
| macd_histogram | MACD histogram momentum |
| mean_reversion_vwap | VWAP mean reversion |
| ml_conservative_boosted | ML conservative with boost |
| ml_moderate_boosted | ML moderate with boost |
| ml_aggressive_boosted | ML aggressive with boost |
| momentum_roc | Rate of change momentum |
| obv_divergence | OBV divergence detection |
| rsi_divergence | RSI divergence detection |
| rsi_oversold_overbought | RSI extreme levels |
| smart_money_divergence | Smart money divergence |
| stoch_rsi | Stochastic RSI |
| supertrend | Supertrend trend-following |
| swing_failure | Swing failure pattern |
| vpin_mean_reversion | VPIN mean reversion |
| vwap_reversion | VWAP reversion |
| williams_vix_fix | Williams VIX fix |
| wyckoff_accumulation | Wyckoff accumulation |
| wyckoff_distribution | Wyckoff distribution |
| zls_haguchi | Zero-lag Haguchi |
| tsmom_volscaled | Time-series momentum with vol scaling |
| *+ 4 more existing entries* | |

---

## Changes Made

1. **`audit_dashboard/template.html`** — Added 31 strategy descriptions to `_STRATEGY_DESCRIPTIONS`:
   - 19 non-crypto/multi-asset strategies (forex, commodity, futures, equity, copy-trader, sentiment)
   - 12 ML-enhanced per-symbol strategies (LightGBM and ensemble stack variants)

2. **`tools/add_strategy_descriptions.py`** — One-time insertion script (can be reused when new strategies are added)

3. **`updates/2026-04-19-strategy-labels-and-entry-criteria.md`** — This documentation file

---

## How the Dashboard Strategy Label System Works

1. `_STRATEGY_DESCRIPTIONS` (JS object in template.html) maps strategy names to human-readable descriptions
2. `_lookupMappedDescription(name, [_STRATEGY_DESCRIPTIONS])` looks up the description, with fallback to `_humanizeExportKey(name)` for unlabeled strategies
3. `_humanizeExportKey` converts `ml_enhanced_FETUSDT_1d_B_lightgbm` → `ML Enhanced FETUSDT 1d B Lightgbm` (camelCase split)
4. Descriptions appear in:
   - Active picks table (strategy column tooltip)
   - Score report (strategy descriptions)
   - Strategy breakdown panel
   - Per-pick drill-down modal

The fix ensures all 32 currently active strategies now have rich descriptions instead of raw internal names.
