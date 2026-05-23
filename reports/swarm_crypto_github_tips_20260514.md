# Swarm Round A: Crypto GitHub Tips & Free Data Sources — 2026-05-14

**Engines:** deepseek (deepseek-v4-flash), xai (grok-3), cerebras (gpt-oss-120b)
**Status:** 3/3 OK — deepseek 11.9KB, cerebras 2.9KB (raw 6.5KB, JSON fence stripped), xai 6.4KB
**Briefing:** `swarm_runs/briefing_crypto_github_tips_20260514.md`
**Raw outputs:** `swarm_runs/crypto_github_tips_20260514/`

---

## Top GitHub Repos (ranked by expected impact)

| # | Name | URL | Use Case | Effort | Impact |
|---|------|-----|----------|--------|--------|
| 1 | **freqtrade** | https://github.com/freqtrade/freqtrade | Crypto backtesting bot with look-ahead bias prevention, hyperopt, live execution | medium | High — validates strategies with realistic slippage/fees; directly reduces backtest-to-live PF gap (all 3 engines agree) |
| 2 | **mlfinlab** | https://github.com/MLFinLab/mlfinlab | Triple-barrier labeling, fractional differencing, entropy features | medium | High — addresses labeling leakage root cause; fractional differencing retains price memory while achieving stationarity |
| 3 | **ruptures** | https://github.com/deepcharles/ruptures | Offline change-point detection for regime shifts | low | High — detects the KS_D drift events early; enables proactive model retraining before performance collapse (2 of 3 engines) |
| 4 | **alibi-detect** | https://github.com/SeldonIO/alibi-detect | KS test, MMD, out-of-distribution drift detection | medium | High — automates retraining triggers tied directly to our KS_D=0.312 alert threshold |
| 5 | **cryptofeed** | https://github.com/bmoscon/cryptofeed | Real-time order-book, trades, funding rates across exchanges | low | High — provides live microstructure data (funding rates, OI) not in current OHLCV-only feature set |
| 6 | **vectorbt** | https://github.com/polakowo/vectorbt | Fast pandas-native backtesting with walk-forward + Monte Carlo | low | Medium-High — eliminates look-ahead bias, quantifies signal decay under execution costs |
| 7 | **pytorch-forecasting** | https://github.com/jdb78/pytorch-forecasting | Temporal Fusion Transformer (TFT) for multivariate time-series | medium | Medium — captures long-range dependencies and attention-based feature importance |
| 8 | **river** | https://github.com/online-ml/river | Online learning (Hoeffding Adaptive Tree) — incremental model updates | medium | Medium — continuous drift adaptation without full retraining; reduces confidence-band inversion lag |
| 9 | **ccxt** | https://github.com/ccxt/ccxt | Unified API for 100+ exchanges — order book, funding rates, OHLCV | low | Medium — already part of failover chain; extend to pull funding rates + open interest |
| 10 | **gplearn** | https://github.com/trevorstephens/gplearn | Genetic programming for automated feature discovery | medium | Medium — discovers non-linear RSI/MACD/volume combinations; estimated +0.1–0.2 PF |
| 11 | **dune-client** | https://github.com/duneanalytics/dune-client | Python wrapper for Dune Analytics on-chain queries | low | Medium — whale holdings, liquidation events without running a node |
| 12 | **blockchain-etl** | https://github.com/blockchain-etl/blockchain-etl | Batch extraction of ERC-20 transfers, liquidations, whale wallets | medium | Medium — granular on-chain whale flow and liquidation signals |
| 13 | **ta** | https://github.com/bukosabino/ta | Expanded technical indicators beyond RSI/MACD | low | Low-Medium — broadens feature set cheaply |

---

## Top Free Data Sources

| Name | URL | Data Type | Use Case |
|------|-----|-----------|----------|
| **CoinGlass** | https://coinglass.com/api | order-flow | Funding rates, open interest, liquidation data — primary perp intelligence feed (all 3 engines) |
| **Glassnode Free Tier** | https://api.glassnode.com/v1/metrics | on-chain | Whale flows, exchange net inflows, MVRV ratio, active addresses for BTC/ETH |
| **Binance Futures Funding API** | https://fapi.binance.com/fapi/v1/fundingRate | order-flow | Direct funding rate history for all perpetual pairs — zero friction, already in failover chain |
| **Bybit Open Interest & Funding** | https://api.bybit.com/v2/public/tickers | order-flow | Cross-exchange OI confirmation; divergence from Binance = regime signal |
| **Whale Alert Free Tier** | https://api.whale-alert.io/v1/transactions | on-chain | Large-wallet transfers (>$10M) on BTC, ETH, BNB — precedes major moves |
| **Santiment Free Tier** | https://api.santiment.net/ | sentiment | Social volume, dev activity, exchange inflow/outflow for top coins |
| **CryptoFear & Greed Index** | https://alternative.me/crypto/fear-and-greed-index/ | sentiment | Daily macro sentiment regime indicator — trivially integrable as a binary feature |
| **CryptoPanic News API** | https://cryptopanic.com/api/v1/posts/ | sentiment | Aggregated headlines with bullish/bearish polarity — LunarCrush alternative |
| **CoinMetrics Community** | https://coinmetrics.io/community-edition/ | on-chain | Realized price, MVRV, supply metrics — institutional-grade on-chain, free tier |
| **The Graph Subgraphs** | https://thegraph.com/explorer | on-chain | Uniswap/Aave liquidity, swap volume, borrow data — DeFi regime signal |
| **Dune Analytics Free** | https://dune.com/ | on-chain | Custom SQL on-chain queries for whale wallets, liquidation cascades |
| **Messari Free Tier** | https://messari.io/ | macro | Token unlocks, governance data, fundamental metrics for altcoins |

---

## Top Quant Tips for Crypto Prediction (P0 first)

**P0 — Address Immediately**

1. **[labeling] Use triple-barrier labeling.** Replace fixed-horizon return labels with profit-take / stop-loss / time-out exits via mlfinlab's `TripleBarrierLabeling`. Fixed-horizon labels cause severe class imbalance during volatility spikes and inflate backtest PF while degrading live performance. Rationale from all 3 engines: our current labeling is the most likely root cause of confidence-band inversion.

2. **[validation] Walk-forward validation with purge buffer.** Replace any static train/test split with rolling walk-forward windows (minimum 30-day train, 7-day hold-out) and purge 1–2 weeks between windows. Rationale: with KS_D=0.312 (6.6× critical), static splits guarantee overfitting to a regime that no longer exists.

3. **[regime] Implement change-point detection for proactive retraining.** Use ruptures on a composite vector (ATR + funding rate divergence) to detect regime boundaries. Train separate sub-models per regime. Rationale: our drift_alert=True flag is reactive; ruptures gives us 2–5 day advance warning before PF collapses.

4. **[execution] Monitor KS-test on live features weekly; auto-trigger retraining.** Wire alibi-detect or a rolling KS check into the scoring pipeline. When KS_D breaches threshold, halt new signals from the affected sub-source and trigger retraining. Rationale: the quan_engine (PF 0.70) and unknown (PF 0.35) sub-sources are almost certainly operating on stale distributions.

**P1 — High Priority**

5. **[feature_engineering] Add funding rate + open interest as first-class features.** Pull from Binance Futures API and CoinGlass for all 13 pairs. Extreme funding rates (>0.1% per 8h) predict mean reversion; OI divergence predicts squeeze direction. Expected lift: 5–10% WR improvement per deepseek.

6. **[feature_engineering] Apply time-decay weighting to training samples.** Use exponential decay with half-life ≈14 days. Weight recent samples 3× older ones. Rationale: our KS_D severity means features from 90 days ago are measured on a different distribution; decay weighting prevents those from dominating the loss function.

7. **[labeling] Use volatility-adjusted (ATR-based) label thresholds.** Replace fixed-% win/loss thresholds with 1.5× ATR boundaries. Rationale: in low-vol periods, noise overwhelms fixed thresholds, biasing the model toward small-edge trades.

8. **[feature_engineering] Add whale-flow and liquidation-risk features.** A binary "liquidation-pressure" flag when OI exceeds N× recent volume predicts cascade direction. Whale Alert + Glassnode provide this free. Rationale: liquidation cascades drive the largest short-term directional moves in crypto, currently absent from our feature set.

9. **[execution] Calibrate confidence scores with isotonic regression.** Train calibration on out-of-sample data. Map raw >0.85 confidence to calibrated values before applying the PR #1000 block. Rationale: the block may be discarding genuinely high-edge signals that are merely miscalibrated, not actually overconfident.

**P2 — Improvement**

10. **[feature_engineering] Multi-horizon ensemble (1h, 4h, 1d).** Train separate models per horizon, combine via rank averaging. Reduces single-timeframe overfitting.

11. **[feature_engineering] Apply fractional differencing (mlfinlab).** Makes price series stationary while preserving memory. Reduces the autocorrelation that inflates backtest PF vs live.

12. **[execution] Use online learning (River) for final ensemble layer.** Incremental per-tick adaptation reduces the lag between regime change and model response — directly addresses quan_engine degradation.

---

## Concerns About Current Approach

- **quan_engine (18% volume, PF 0.70) is the single largest drag** — if not retrained or disabled within one week, it will continue degrading system PF. All 3 engines flagged this independently.
- **Confidence band inversion (blocking >0.85)** indicates model miscalibration, not true overconfidence. The block is correct as a safety measure but is almost certainly discarding edge — calibration is the fix, not permanent suppression.
- **KS_D=0.312 vs critical=0.047 (6.6× severity)** — the model is very likely fit to a regime that no longer exists. Full retraining on the last 60 days only (not historical corpus) is likely needed before feature additions will show improvement.
- **104 closed trades out of 8,162 total** — suspiciously low close rate suggests open-position bloat from stale signals or execution gaps. This inflates apparent n while understating real WR. Resolve before promoting CRYPTO to T2.
- **Small-n sub-symbols (DYDX PF 58, BNB PF 56)** — extreme PF on tiny n is overfitting, not edge. Do not use these to justify CRYPTO class health until n >= 30 clean closed trades per symbol.
- **Missing on-chain features** — current feature set (RSI, MACD, SMA, Bollinger, ATR, volume, kimi sentiment) has zero market microstructure. Funding rates, OI, and whale flows are well-established crypto alpha sources not yet integrated.
- **Label leakage risk** — if targets use any forward price information that is also present in features (e.g., end-of-bar close), backtest PF will be inflated vs live. Triple-barrier labeling eliminates this.

---

## Synthesis Verdict

All three engines converge on the same root causes: severe concept drift (KS_D 6.6× critical) combined with stale sub-source models (quan_engine, unknown) is the primary obstacle to reaching PF 2.0+, and no amount of new GitHub repo integration will overcome it until retraining on recent data with walk-forward validation is in place. The highest-ROI next steps — in order — are: (1) retrain or disable quan_engine immediately, (2) implement rolling walk-forward validation with a drift-triggered retraining pipeline using ruptures + alibi-detect, (3) add funding rate and open interest as features via the Binance Futures API and CoinGlass, and (4) adopt triple-barrier labeling from mlfinlab to fix confidence miscalibration at the source. The free data and repos listed above provide a clear, low-cost path from PF 1.26 toward PF 2.0+ — but the critical path is drift remediation first, then feature expansion.
