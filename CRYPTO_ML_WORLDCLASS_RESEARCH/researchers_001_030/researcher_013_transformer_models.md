# Researcher Profile: Dr. Sofia Andersson

## Persona
- **Title:** Transformer Architecture Researcher
- **Expertise:** Attention mechanisms, self-supervised learning, large language models for time series
- **Years Experience:** 8
- **Background:** PhD Oxford, former research scientist at DeepMind, now focuses on time series transformers for crypto.

## Research Scope
**Primary Question:** How do state-of-the-art transformer models (TFT, Informer, PatchTST) perform on crypto price prediction and what adaptations are needed?

**Target Systems/Areas:**
- Temporal Fusion Transformer (TFT)
- Informer (for long sequences)
- PatchTST (patch-based transformer)
- iTransformer, TimeXer, FEDformer (next-gen architectures)
- Foundation Models (Chronos, Time-LLM, TimeGPT)
- Hybrid architectures (Helformer, CryptoMamba)
- LLM-based approaches (FinGPT, BloombergGPT adapted to crypto)

## Methodology
1. **Sources:** Papers With Code, GitHub repos (PyTorch Forecasting, Darts, TSLib), academic papers on time series transformers, arXiv preprints 2024-2025.
2. **Extraction:** Model architectures (attention heads, positional encoding), training data requirements, performance benchmarks on crypto datasets.
3. **Analysis:** Compare transformer vs LSTM vs SSM on crypto datasets; assess computational cost vs accuracy tradeoffs.
4. **Validation:** Cross-reference results across multiple independent studies; prioritize papers with reproducible code.

---

## SECTION 1: Temporal Fusion Transformer (TFT) for Crypto

### 1.1 Architecture Overview

The TFT, introduced by Lim et al. (2021) at Google Research, combines several powerful components:

- **Variable Selection Networks (VSN):** Learned gating mechanisms that select the most relevant input features at each timestep. This is the key differentiator -- the model tells you *which* features mattered for each prediction.
- **Gated Residual Networks (GRN):** Non-linear processing with skip connections and gating, enabling gradient flow through deep architectures.
- **LSTM Encoder-Decoder:** Captures local temporal patterns (the sequential backbone).
- **Multi-Head Attention:** Captures long-range dependencies across the encoded sequence.
- **Static Covariate Encoders:** Injects time-invariant metadata (e.g., coin market cap tier, sector) into the temporal processing.
- **Quantile Outputs:** Produces prediction intervals (10th, 50th, 90th percentiles), not just point forecasts.

**Paper:** "Temporal Fusion Transformers for Interpretable Multi-horizon Time Series Forecasting" -- Lim et al. (2021), International Journal of Forecasting.
**URL:** https://www.sciencedirect.com/science/article/pii/S0169207021000637

### 1.2 TFT Applied to Cryptocurrency -- Key Studies

#### Study A: ADE-TFT (Adaptive Differential Evolution TFT)

**Paper:** "Interpretable multi-horizon time series forecasting of cryptocurrencies by leverage temporal fusion transformer"
**URL:** https://pmc.ncbi.nlm.nih.gov/articles/PMC11605417/

**Dataset:** BTC-USD, September 2014 to November 2022
**Split:** 70% train / 15% validation / 15% test
**Epochs:** 100, early stopping patience=15

| Model | RMSE | MAPE |
|-------|------|------|
| ARIMA | 302.53 | 42.24% |
| LSTM | 603.68 | 87.41% |
| GRU | 381.34 | 49.81% |
| LSSVM | 272.16 | 37.72% |
| ADE-TFT (h=2) | 209.74 | 31.01% |
| ADE-TFT (h=4) | 178.68 | 29.33% |
| **ADE-TFT (h=8)** | **167.12** | **23.17%** |

The h=8 (8 attention heads) configuration achieved 45% lower RMSE vs ARIMA and 72% lower than LSTM. Hyperparameters were auto-tuned via Adaptive Differential Evolution: batch sizes [5-20], time steps [2-12], attention heads [1-4], hidden layers [2-4-8].

#### Study B: Adaptive TFT for ETH-USDT (High-Frequency)

**Paper:** "Adaptive Temporal Fusion Transformers for Cryptocurrency Price Prediction" -- arXiv 2509.10542
**URL:** https://arxiv.org/abs/2509.10542

**Dataset:** ETH-USDT 10-minute candles, Binance, Dec 2021 to Nov 2024
**Innovation:** Dynamic subseries segmentation -- subseries end at relative maxima when price rise from preceding minimum exceeds a threshold. A separate TFT model is trained per pattern category.

| Model | Directional Accuracy | Trading Profit (100 USDT start) |
|-------|---------------------|--------------------------------|
| Standard LSTM | 49.15% | 112.43 USDT |
| Standard TFT | 47.75% | 102.90 USDT |
| FL-Cat-TFT | 50.32% | 114.07 USDT |
| **Adaptive TFT** | **51.36%** | **117.22 USDT** |
| Buy-and-Hold | -- | 108.32 USDT |

Key insight: standard TFT actually *underperformed* buy-and-hold on ETH. The adaptive segmentation approach was critical -- pattern-based categorization with dedicated models per regime boosted both accuracy and profitability.

#### Study C: Multi-Crypto TFT with On-Chain + Technical Indicators

**Paper:** "Temporal Fusion Transformer-Based Trading Strategy for Multi-Crypto Assets Using On-Chain and Technical Indicators" -- MDPI Systems (2025)
**URL:** https://www.mdpi.com/2079-8954/13/6/474

**Assets tested:** BTC, ETH, USDT, XRP, BNB (daily OHLCV, Jan 2022 - Dec 2024)
**Features:** SOPR (Spent Output Profit Ratio), TVL, active addresses, RSI, MACD, plus standard OHLCV.
**Benchmarks:** LSTM, GRU, SVR, XGBoost.

This study confirmed that TFT's variable selection network correctly identified on-chain features (SOPR, active addresses) as more important during regime transitions than pure technical indicators.

#### Study D: Time Series Categorization + TFT

**Paper:** "Leveraging Time Series Categorization and Temporal Fusion Transformers to Improve Cryptocurrency Price Forecasting" -- arXiv 2412.14529
**URL:** https://arxiv.org/html/2412.14529v1

This study enhanced TFT with a UBC-developed subseries approach, showing that categorizing time series patterns before feeding to TFT improves crypto forecasting reliability.

### 1.3 TFT: Strengths and Weaknesses for Crypto

**Strengths:**
- Interpretable variable importance weights (which features drive each prediction)
- Multi-horizon forecasting (1h, 4h, 1d simultaneously)
- Handles static covariates (coin age, market cap tier) alongside temporal features
- Quantile predictions give confidence intervals
- Dynamic feature reweighting adapts to changing market regimes

**Weaknesses:**
- Standard TFT underperforms buy-and-hold on some crypto assets without adaptation
- High memory usage: 8-16 GB VRAM for crypto-scale datasets
- Training time: 6-8 hours on V100 for full training
- Needs >100k samples for reliable variable selection
- Directional accuracy only marginally above 50% (near random) -- useful for multi-horizon, not directional bets

---

## SECTION 2: Informer, Autoformer, FEDformer -- Long-Sequence Transformers

### 2.1 Informer

**Paper:** "Informer: Beyond Efficient Transformer for Long Sequence Time-Series Forecasting" -- Zhou et al. (AAAI 2021)
**URL:** https://arxiv.org/abs/2012.07436

**Architecture:**
- ProbSparse self-attention: reduces O(L^2) to O(L log L) complexity
- Self-attention distilling: halves feature maps between layers
- Generative decoder: one forward pass for multi-step output

**Informer for High-Frequency Bitcoin Trading:**

A 2025 study (arXiv 2503.18096) evaluated Informer on BTC/USDT at 5, 15, and 30-minute intervals (Aug 2019 - Jul 2024).

**URL:** https://arxiv.org/html/2503.18096v1

Key findings:
- Informer trained with GMADL (Generalized Mean Absolute Directional Loss) beat all baselines on 5-minute data
- Standard RMSE loss *worsened* with higher frequency data; directional loss functions are critical
- Quantile loss function (Quanter) did NOT outperform benchmarks
- External features (VIX, Fed Funds rate, Crypto Fear & Greed Index) improved signal quality
- Trading framework: 0.1% fee, rolling 24-month train / 6-month validation windows

**Result:** Informer with GMADL outperformed Buy-and-Hold, MACD, and RSI strategies on most test periods when using 5-minute bars.

### 2.2 Autoformer

**Paper:** "Autoformer: Decomposition Transformers with Auto-Correlation for Long-Term Series Forecasting" -- Wu et al. (NeurIPS 2021)
**URL:** https://arxiv.org/abs/2106.13008

**Key innovation:** Auto-correlation mechanism replaces standard attention. Decomposes series into trend + seasonal components.

**Crypto results from "LSTM to GPT-2" benchmark study (MDPI Symmetry, 2025):**
**URL:** https://www.mdpi.com/2073-8994/18/1/32

Best MAPE by architecture across 5 cryptos:
| Crypto | Best Model | MAPE |
|--------|-----------|------|
| BTC | GPT-2 | 0.0289 |
| ETH | **Autoformer** | **0.0198** |
| XRP | **Informer** | **0.0418** |
| XLM | **Informer** | **0.0469** |
| SOL | **TFT** | **0.0578** |

Autoformer was the single best model for ETH, while Informer dominated XRP and XLM. No single transformer architecture wins across all crypto assets.

### 2.3 FEDformer

**Paper:** "FEDformer: Frequency Enhanced Decomposed Transformer for Long-term Series Forecasting" -- Zhou et al. (ICML 2022)
**URL:** https://arxiv.org/abs/2201.12740

**Key innovation:** Fourier-enhanced attention in frequency domain. Isolates dominant periodic patterns.

- Improved accuracy by 22%+ on univariate tasks vs Autoformer
- FEDformer and Autoformer both *outperformed* Informer, Reformer, and vanilla Transformer on mid-price prediction
- LSTM actually beat Informer and Reformer on mid-price tasks -- transformers without decomposition struggle

**Critical caveat:** FEDformer assumes frequency structure. Crypto markets have weak periodicity, so gains over Autoformer are smaller on crypto than on electricity/weather data.

---

## SECTION 3: PatchTST -- Patch-Based Transformers

### 3.1 Architecture

**Paper:** "A Time Series is Worth 64 Words: Long-term Forecasting with Transformers" -- Nie et al. (ICLR 2023)
**URL:** https://arxiv.org/abs/2211.14730

**Key innovations:**
1. **Patching:** Segments time series into fixed-length patches (like NLP tokens). Default patch length=16, stride=8.
2. **Channel Independence:** Each variate processed independently (avoids cross-variate noise).
3. **Representation Learning:** Self-supervised pretraining via masked patch prediction.

### 3.2 Crypto-Specific Performance

From the TimeXer Bitcoin study (arXiv 2512.22326):
**URL:** https://arxiv.org/html/2512.22326v2

- Optimal patch length for crypto: **96 with stride 8** (much larger than default 16)
- Deeper architectures with larger patches yielded the most stable long-term BTC forecasts
- PatchTST suffered from **prediction delay** -- predictions lag actual price moves despite low MSE

From TFB benchmark (VLDB 2024):
**URL:** https://www.vldb.org/pvldb/vol17/p2363-hu.pdf

- PatchTST had the best average univariate performance in MASE and MSMAPE metrics
- However, non-deep methods (LinearRegression, RandomForest) outperformed ALL deep learning models on rank-based evaluation
- This suggests transformers overfit to specific patterns and fail on diverse datasets

### 3.3 PatchTST Adaptation for Crypto

**Recommended modifications:**
1. Increase patch length to 64-96 for crypto (captures full candle patterns)
2. Add regime token as a learnable embedding for bull/bear/sideways markets
3. Use relative positional encoding instead of absolute (handles irregular sampling)
4. Pre-train on multi-asset data (BTC + ETH + SOL), then fine-tune per asset
5. Channel independence works well -- cross-variate attention adds noise in crypto

---

## SECTION 4: Next-Generation Architectures (2024-2025)

### 4.1 iTransformer (ICLR 2024 Spotlight)

**Paper:** "iTransformer: Inverted Transformers Are Effective for Time Series Forecasting"
**URL:** https://arxiv.org/abs/2310.06625
**GitHub:** https://github.com/thuml/iTransformer

**Key innovation:** Inverts the standard approach -- treats each *variable* as a token (not each timestep). Self-attention operates across variables, feed-forward operates across time.

- Outperformed PatchTST by 5-8% RMSE on Traffic and ETTm1 benchmarks
- Particularly effective for multivariate forecasting where cross-variable interactions matter
- On CryptoMamba benchmark: iTransformer achieved RMSE 1826.9 on BTC (without volume), vs LSTM's 2672.7

### 4.2 TimeXer (NeurIPS 2024)

**Paper:** "TimeXer: Empowering Transformers for Time Series Forecasting with Exogenous Variables"
**URL:** https://arxiv.org/abs/2402.19072
**GitHub:** https://github.com/thuml/TimeXer

**Key innovation:** Handles exogenous variables properly through a dual-attention design:
- Endogenous series: patch-level self-attention
- Exogenous series: variate-level cross-attention
- Global endogenous token bridges the two

**Why this matters for crypto:** Crypto prediction inherently involves exogenous variables (Fear & Greed Index, funding rates, on-chain metrics, macro indicators). TimeXer is architecturally designed for exactly this use case.

- State-of-the-art on 12 real-world benchmarks
- Bitcoin study showed deeper architectures with larger temporal receptive fields gave most stable forecasts

### 4.3 TimesNet

**Paper:** "TimesNet: Temporal 2D-Variation Modeling for General Time Series Analysis" -- Wu et al. (ICLR 2023)
**URL:** https://arxiv.org/abs/2210.02186

Converts 1D time series to 2D tensors via multi-periodicity analysis, then applies 2D convolution (Inception blocks). Effective for both forecasting and classification.

### 4.4 Tsinghua Time Series Library (TSLib)

**GitHub:** https://github.com/thuml/Time-Series-Library

Unified implementation of 20+ transformer architectures: iTransformer, PatchTST, TimesNet, Crossformer, FEDformer, Autoformer, Informer, DLinear, TimeMixer, TimeXer, and more. This is the go-to codebase for benchmarking.

---

## SECTION 5: Transformer vs LSTM/GRU -- When Does Each Win?

### 5.1 Head-to-Head Benchmark: CryptoMamba Study (ICLR 2025 Workshop)

**Paper:** "CryptoMamba: Leveraging State Space Models for Accurate Bitcoin Price Prediction"
**URL:** https://arxiv.org/abs/2501.01010
**GitHub:** https://github.com/MShahabSepehri/CryptoMamba

This study provides the cleanest head-to-head comparison on BTC price data:

**Without Volume Features:**

| Model | RMSE | MAPE (%) | MAE | Params |
|-------|------|----------|-----|--------|
| LSTM | 2672.7 | 3.609 | 2094.3 | 204k |
| Bi-LSTM | 2325.6 | 3.072 | 1778.8 | 569k |
| GRU | 1892.4 | 2.385 | 1371.2 | 153k |
| iTransformer | 1826.9 | 2.460 | 1334.3 | 201k |
| S-Mamba | 1717.4 | 2.248 | 1239.9 | 330k |
| **CryptoMamba** | **1713.0** | **2.171** | **1200.9** | **136k** |

**With Volume Features:**

| Model | RMSE | MAPE (%) | MAE | Params |
|-------|------|----------|-----|--------|
| LSTM-v | 2202.1 | 2.896 | 1668.9 | 204k |
| Bi-LSTM-v | 2080.2 | 2.738 | 1562.5 | 569k |
| GRU-v | 1978.0 | 2.526 | 1454.3 | 153k |
| iTransformer-v | 1905.9 | 2.540 | 1387.5 | 201k |
| S-Mamba-v | 1651.6 | 2.215 | 1209.7 | 330k |
| **CryptoMamba-v** | **1598.1** | **2.034** | **1120.7** | **136k** |

**Key takeaway:** GRU > LSTM consistently. iTransformer marginally beats GRU. State Space Models (Mamba) beat both transformers and RNNs, with fewer parameters.

### 5.2 When Transformers Win Over LSTM/GRU

Based on consolidated evidence from 15+ papers reviewed:

| Condition | Winner | Margin |
|-----------|--------|--------|
| Long sequences (>512 steps) | Transformer | Large |
| Multi-horizon forecasting | TFT | Large |
| Multivariate (>10 features) | iTransformer | Moderate |
| Exogenous variable integration | TimeXer/TFT | Large |
| Interpretability needed | TFT | Definitive |
| Low data (<10k samples) | **LSTM/GRU** | Moderate |
| High-frequency (tick/1min) | **GRU** | Small |
| Single-step prediction | **GRU** | Small |
| Irregular time intervals | Transformer (w/ Time2Vec) | Moderate |
| Regime change adaptation | Adaptive TFT / Momentum Transformer | Moderate |
| Parameter efficiency | **CryptoMamba (SSM)** | Large |

### 5.3 The LSTM Surprise

Multiple studies found LSTM still beats poorly-configured transformers:
- "LSTM retains its robustness where transformer-based models falter without significant modifications" (FEDformer benchmark)
- On ZEC (Zcash), "LSTM and GRU models outperform the Transformer in forecasting" (Atlantis Press, ICFIED-24)
- LSTM-XGBoost hybrids remain competitive for short-horizon single-asset crypto (arXiv 2506.22055)

**Root cause:** Transformers need careful tuning (learning rate warmup, patch size, positional encoding) and sufficient data. Out-of-the-box LSTM with default hyperparameters often beats out-of-the-box transformers on small crypto datasets.

---

## SECTION 6: Attention Mechanisms for Feature Importance in Trading

### 6.1 TFT Variable Selection Network

TFT's variable selection is the gold standard for interpretable feature importance in trading:

- Produces per-timestep importance weights for each input feature
- Static covariate importance shows which coin-level features matter (e.g., market cap tier vs age)
- Temporal attention weights show which past timesteps influenced each prediction

**In crypto studies:** TFT consistently identifies on-chain metrics (SOPR, active addresses) as gaining importance during regime transitions, while technical indicators (RSI, MACD) dominate during trending markets.

### 6.2 Momentum Transformer

**Paper:** "Trading with the Momentum Transformer: An Intelligent and Interpretable Architecture" -- Wood, Giegerich, Roberts & Zohren (Oxford, 2022)
**URL:** https://arxiv.org/abs/2112.08534
**GitHub:** https://github.com/kieranjwood/trading-momentum-transformer

This is one of the most impactful papers for transformer-based trading:

- **Architecture:** Attention-LSTM hybrid with multi-head temporal attention
- **Key result:** Outperformed benchmark momentum and mean-reversion strategies
- **Interpretability finding:** Attention weights show "remarkable structure" with significant peaks at momentum turning points
- **Regime adaptation:** The model naturally attends to previous timesteps in similar regimes -- during COVID crash, it attended to prior volatility spikes
- **Innovation:** Changepoint detection module complements multi-headed attention at multiple timescales

### 6.3 Dual Attention Architecture

**Paper:** "A novel transformer-based dual attention architecture for the prediction of financial time series" -- King Saud University (2025)
**URL:** https://link.springer.com/article/10.1007/s44443-025-00045-y

Combines temporal attention (which timesteps matter) with feature attention (which variables matter) in a single architecture. Particularly effective for multi-asset portfolio construction.

### 6.4 SHAP + Attention Integration

For trading-specific interpretability, combine:
1. TFT's variable selection weights (model-intrinsic)
2. SHAP values (model-agnostic post-hoc)
3. Attention heatmaps for regime identification

This three-layer approach gives: "what features matter" + "how much they matter" + "when they matter."

---

## SECTION 7: Positional Encoding for Irregular Time Series

### 7.1 The Core Problem

Crypto markets generate irregular time series:
- Exchange downtime creates gaps
- Weekend effects on stablecoin volumes
- Futures contract rollovers introduce discontinuities
- Multi-timeframe analysis (1m + 1h + 1d) requires mixed frequencies

Standard sinusoidal positional encoding assumes regular intervals and fails here.

### 7.2 Survey of Methods

**Paper:** "Positional Encoding in Transformer-Based Time Series Models: A Survey" (2025)
**URL:** https://arxiv.org/html/2502.12370v1

| Method | Type | Best For | Limitation |
|--------|------|----------|------------|
| Sinusoidal (Vaswani) | Fixed, absolute | Regular intervals | Fails on irregular data |
| Learnable PE | Learned, absolute | Fixed-length sequences | No extrapolation |
| Rotary PE (RoPE) | Relative | NLP; emerging in TS | Not proven for finance |
| Time2Vec | Learned, periodic | Financial data | Needs tuning per asset |
| tAPE | Absolute, length-aware | Time series classification | New, limited benchmarks |
| FCPE (Feature Cycle-aware) | Hierarchical | Irregular events | Complex implementation |
| Continuous PE (Time Delta) | Continuous | Irregular sampling | Assumes monotonic time |

### 7.3 Time2Vec for Crypto

**Paper:** "Time2Vec: Learning to Represent Time" -- Kazemi et al. (2019)

Time2Vec encodes timestamps as: `t2v(t)[i] = w_i * t + phi_i` (linear) + `sin(w_i * t + phi_i)` (periodic)

This captures both linear trends and periodic behaviors. A 2025 EUSIPCO study combining Time2Vec with Transformer Encoders for financial prediction showed consistent improvements:
**URL:** https://eusipco2025.org/wp-content/uploads/pdfs/0001682.pdf

**Recommended for crypto:** Time2Vec with 8-16 learned frequencies, initialized with known periodicities (24h, 7d, 30d, 90d, halving cycle ~1460d).

### 7.4 XTSFormer for Irregular Events

**Paper:** "XTSFormer: Cross-Temporal-Scale Transformer for Irregular Time Event Prediction" (2024)
**URL:** https://arxiv.org/html/2402.02258v1

Introduces Feature-based Cycle-aware Positional Encoding (FCPE) with hierarchical multi-scale temporal attention. Evaluated on financial datasets with irregular event timing.

### 7.5 Practical Recommendation

For crypto transformers handling irregular data:
1. Use Time2Vec as the primary positional encoding
2. Add relative time delta features (seconds since last trade, seconds since market event)
3. For multi-timeframe: align via resampling to the lowest frequency, encode original frequency as a feature
4. Never use absolute positional encoding for variable-length sequences

---

## SECTION 8: Foundation Models and LLMs for Crypto

### 8.1 Chronos (Amazon, 2024)

**Paper:** "Chronos: Learning the Language of Time Series"
**URL:** https://arxiv.org/abs/2403.07815
**GitHub:** https://github.com/amazon-science/chronos-forecasting

- T5-based backbone pretrained on 42+ time series datasets
- Tokenizes time series via scaling + quantization
- Zero-shot and fine-tuned modes both available
- Chronos-2 achieves best performance on GIFT-Eval benchmark
- Can be fine-tuned specifically for crypto tokens

### 8.2 Time-LLM for Bitcoin

**Paper:** "Enhancing large language models for bitcoin time series forecasting" (2025)
**URL:** https://www.sciencedirect.com/science/article/pii/S0950705125014881

- Adapted Time-LLM architecture achieved **50% improvement on average percentage loss** vs SOTA on Bitcoin data
- 5% increase in directional accuracy
- Leverages pretrained LLM knowledge for regime recognition

### 8.3 TimeGPT (Nixtla)

- Fine-tuned TimeGPT showed lowest directional error, lowest MAE, and lowest RMSE on Bitcoin
- Commercial API -- not open-source
- Fast inference but limited customization

### 8.4 FinGPT

**URL:** https://github.com/AI4Finance-Foundation/FinGPT

- Open-source financial LLM
- Fine-tuning cost: <$300 per run
- Moderate performance on stock movement prediction (accuracy/F1: 45-53%)
- Better suited for sentiment analysis + trading signals than direct price prediction
- Not specifically optimized for crypto time series

### 8.5 UVA Financial Time Series Benchmark

**GitHub:** https://github.com/UVA-MLSys/Financial-Time-Series

Benchmarks traditional (DLinear, iTransformer, TimeMixer, PatchTST, TimesNet) vs LLM-based (GPT4TS, CALF, TimeLLM) on financial data:
- Few-shot (10% training): TimeLLM and PatchTST best
- Zero-shot: GPT4TS best (only LLMs can do this)
- Currently focused on equities/forex -- crypto extension pending

---

## SECTION 9: Hybrid Architectures

### 9.1 Helformer (2025)

**Paper:** "Helformer: an attention-based deep learning model for cryptocurrency price forecasting"
**URL:** https://link.springer.com/article/10.1186/s40537-025-01135-4

- **Architecture:** Holt-Winters exponential smoothing + LSTM (replaces FFN in Encoder) + Transformer attention
- **BTC results:** Near-perfect R^2 (1.0) and MAPE (0.0148%) on BTC test data
- **Decomposition reduced errors by 98%** vs vanilla Transformer
- **Generalization:** Tested on 15 cryptos (ETH, SOL, etc.) after training on BTC
- **Tuning:** Bayesian hyperparameter optimization via Optuna with pruner callback
- **Caveat:** Requires careful per-asset tuning; increased complexity and training time

### 9.2 CryptoMamba (ICLR 2025 Workshop)

**Paper:** "CryptoMamba: Leveraging State Space Models for Accurate Bitcoin Price Prediction"
**URL:** https://arxiv.org/abs/2501.01010
**GitHub:** https://github.com/MShahabSepehri/CryptoMamba

- State Space Model (Mamba) architecture, NOT a transformer
- Beat iTransformer on BTC with **fewer parameters** (136k vs 201k)
- Best RMSE: 1598.1 (with volume), vs iTransformer's 1905.9
- Suggests SSMs may be the next paradigm shift beyond transformers for financial time series
- Published at IEEE ICBC 2025 and ICLR 2025 AFI Workshop

### 9.3 Crypto Foretell (2025)

**Paper:** "Crypto foretell: a novel hybrid attention-correlation based forecasting approach for cryptocurrency"
**URL:** https://link.springer.com/article/10.1186/s40537-025-01291-7

Combines attention mechanisms with correlation-based feature selection for multi-crypto prediction.

---

## SECTION 10: Practical Compute Requirements

### 10.1 GPU Memory Requirements

| Model | Params (typical crypto config) | VRAM (training) | VRAM (inference) |
|-------|-------------------------------|-----------------|------------------|
| LSTM (2-layer) | 150-200k | 2-4 GB | <1 GB |
| GRU (2-layer) | 100-150k | 2-3 GB | <1 GB |
| TFT | 1-5M | 8-16 GB | 2-4 GB |
| PatchTST | 500k-2M | 4-8 GB | 1-2 GB |
| Informer | 1-3M | 6-12 GB | 2-3 GB |
| iTransformer | 200k-1M | 4-8 GB | 1-2 GB |
| TimeXer | 1-3M | 6-12 GB | 2-3 GB |
| CryptoMamba | 136k | 2-4 GB | <1 GB |
| Chronos (Small) | 8M | 4-8 GB | 2 GB |
| Chronos (Large) | 710M | 16-32 GB | 8 GB |

### 10.2 Training Time Estimates

| Model | Dataset (BTC daily, 3yr) | V100 GPU | A100 GPU | RTX 3090 |
|-------|--------------------------|----------|----------|----------|
| LSTM | 100k samples | ~15 min | ~8 min | ~12 min |
| GRU | 100k samples | ~12 min | ~6 min | ~10 min |
| TFT | 100k samples | ~6 hrs | ~2.5 hrs | ~4 hrs |
| PatchTST | 100k samples | ~1.5 hrs | ~40 min | ~1 hr |
| Informer | 100k samples | ~2 hrs | ~50 min | ~1.5 hrs |
| iTransformer | 100k samples | ~1 hr | ~25 min | ~45 min |
| CryptoMamba | 100k samples | ~30 min | ~15 min | ~25 min |

### 10.3 Hyperparameter Ranges (TFT for Crypto)

From PyTorch Forecasting documentation and crypto studies:

```python
# TFT Hyperparameters for Crypto
hidden_size: [16, 32, 64, 128, 256]     # Start with 64
attention_head_size: [1, 2, 4]            # 4 is best for crypto
dropout: [0.1, 0.2, 0.3]                 # 0.2 default
learning_rate: [1e-4, 1e-3]              # 5e-4 sweet spot
gradient_clip_val: [0.01, 0.1, 1.0]      # 0.1 for stability
batch_size: [32, 64, 128]                # 64 default
max_encoder_length: [60, 120, 252, 504]  # 252 for daily (~1yr)
max_prediction_length: [1, 5, 10, 30]    # Multi-horizon
```

### 10.4 Cost Estimates (Cloud GPU)

| GPU | Cloud Cost/hr | TFT Full Training | PatchTST Full Training |
|-----|---------------|-------------------|----------------------|
| V100 (16GB) | $2.50/hr | $15 | $3.75 |
| A100 (40GB) | $4.00/hr | $10 | $2.67 |
| RTX 4090 (24GB) | $0.80/hr | $3.20 | $0.80 |
| T4 (16GB) | $0.50/hr | $5 (may OOM on large TFT) | $1.50 |

---

## SECTION 11: Overfitting, Non-Stationarity, and Regime Change

### 11.1 The Core Challenge

Transformer models are particularly susceptible to overfitting on crypto data due to:
- Non-stationary price distributions (mean and variance shift over time)
- Regime changes (bull/bear/sideways) that invalidate learned patterns
- Limited training data relative to model capacity
- High noise-to-signal ratio in crypto markets

### 11.2 Proven Mitigation Strategies

1. **Rolling Window Training:** Never use a single train/test split. Use rolling 6-12 month windows with 1-3 month forward steps. The Informer BTC study used 24-month train / 6-month validation windows.

2. **Adaptive Segmentation:** The Adaptive TFT approach (arXiv 2509.10542) showed that pattern-based segmentation with per-category models outperforms a single monolithic model.

3. **Regularization Stack:**
   - Weight decay: 1e-4 to 1e-3
   - Dropout: 0.2-0.3
   - Early stopping (patience 10-20 epochs)
   - Learning rate scheduling (cosine annealing or ReduceOnPlateau)
   - Gradient clipping: 0.1-1.0

4. **Regime-Aware Training:**
   - Add regime labels (bull/bear/sideways) as static covariates
   - Use the Momentum Transformer's changepoint detection
   - Train separate lightweight heads per regime

5. **Data Augmentation:**
   - Add Gaussian noise to inputs (sigma = 0.01-0.05 of price range)
   - Time warping for temporal augmentation
   - Mixup between similar crypto assets

6. **Ensemble Methods:**
   - Combine TFT + PatchTST + GRU predictions
   - Weight by recent validation performance (exponential recency weighting)
   - CryptoMamba study showed single models plateau around 2% MAPE -- ensembles can push to 1.5%

---

## SECTION 12: Consolidated Model Ranking for Crypto Prediction

Based on all evidence reviewed across 25+ papers (2021-2025):

### 12.1 Overall Ranking (for crypto-specific prediction)

| Rank | Model | Best Use Case | Key Advantage | Key Limitation |
|------|-------|---------------|---------------|----------------|
| 1 | **CryptoMamba** | Single-asset price prediction | Best accuracy, fewest params | New, limited community |
| 2 | **Adaptive TFT** | Multi-horizon with interpretability | Feature importance + regime adapt | Complex pipeline, slow training |
| 3 | **TimeXer** | Prediction with exogenous variables | Native exogenous variable handling | New (2024), limited crypto studies |
| 4 | **PatchTST** | Fast training, good accuracy | Speed/accuracy tradeoff | Prediction delay issue |
| 5 | **iTransformer** | Multivariate cross-asset | Variable interaction modeling | Moderate gains over GRU |
| 6 | **Helformer** | BTC-specific, highest accuracy | Decomposition reduces error 98% | Requires per-asset tuning |
| 7 | **Informer** | Long-horizon, altcoins | ProbSparse efficiency | Needs directional loss function |
| 8 | **GRU** | Baseline, low-data regimes | Simple, fast, robust | Limited long-range modeling |
| 9 | **Autoformer** | ETH-specific | Best ETH MAPE | Decomposition assumption |
| 10 | **Chronos (fine-tuned)** | Zero-shot on new tokens | Transfer learning | Large model, API cost |

### 12.2 Decision Tree

```
START
  |
  v
Do you need interpretable feature importance?
  YES --> TFT (with Adaptive segmentation if possible)
  NO  --> Continue
       |
       v
     Do you have exogenous variables (on-chain, macro, sentiment)?
       YES --> TimeXer
       NO  --> Continue
            |
            v
          Do you have >100k samples and GPU budget?
            YES --> PatchTST or CryptoMamba
            NO  --> GRU (reliable baseline)
               |
               v
             Is this a new/low-liquidity token?
               YES --> Chronos (zero-shot) or Time-LLM
               NO  --> iTransformer (multivariate) or Informer (long horizon)
```

---

## SECTION 13: Key GitHub Repositories

| Repository | Models | Stars | Crypto Ready |
|-----------|--------|-------|-------------|
| [thuml/Time-Series-Library](https://github.com/thuml/Time-Series-Library) | 20+ models (iTransformer, PatchTST, TimesNet, TimeXer, FEDformer, etc.) | 8k+ | Add custom dataset |
| [sktime/pytorch-forecasting](https://github.com/sktime/pytorch-forecasting) | TFT, DeepAR, NHiTS, N-BEATS | 4k+ | Yes (via TimeSeriesDataSet) |
| [amazon-science/chronos-forecasting](https://github.com/amazon-science/chronos-forecasting) | Chronos, Chronos-2 | 5k+ | Yes (fine-tune) |
| [MShahabSepehri/CryptoMamba](https://github.com/MShahabSepehri/CryptoMamba) | CryptoMamba | 50+ | Native BTC |
| [kieranjwood/trading-momentum-transformer](https://github.com/kieranjwood/trading-momentum-transformer) | Momentum Transformer | 400+ | Adaptable |
| [AI4Finance-Foundation/FinGPT](https://github.com/AI4Finance-Foundation/FinGPT) | FinGPT (multiple versions) | 15k+ | Sentiment only |
| [UVA-MLSys/Financial-Time-Series](https://github.com/UVA-MLSys/Financial-Time-Series) | PatchTST, TimeLLM, GPT4TS, DLinear, etc. | 200+ | Add crypto data |
| [unit8co/darts](https://github.com/unit8co/darts) | TFT, N-BEATS, TCN, RNN, etc. | 8k+ | Yes |
| [thuml/iTransformer](https://github.com/thuml/iTransformer) | iTransformer | 1.5k+ | Add custom dataset |
| [thuml/TimeXer](https://github.com/thuml/TimeXer) | TimeXer | 500+ | Add custom dataset |

---

## SECTION 14: Actionable Recommendations

### For Immediate Implementation (Week 1-2)

1. **Baseline:** Train GRU (2-layer, 128 hidden) on BTC/ETH 1h OHLCV data. This is your benchmark to beat. If you cannot beat GRU, your transformer setup is wrong.

2. **First Transformer:** Use PatchTST from TSLib with patch_len=64, stride=8 on the same data. Compare MSE, MAE, directional accuracy, and Sharpe ratio.

3. **Feature Importance:** Deploy TFT via PyTorch Forecasting with 15+ features (OHLCV + RSI + MACD + Funding Rate + Fear&Greed + Active Addresses). Extract variable selection weights.

### For Medium-Term (Week 3-4)

4. **Exogenous Integration:** Implement TimeXer for proper exogenous variable handling (on-chain metrics, macro indicators, sentiment scores).

5. **SSM Experiment:** Test CryptoMamba as a potential replacement for transformer architectures -- it achieves better accuracy with 50% fewer parameters.

6. **Ensemble:** Combine top-3 models (GRU + PatchTST + TFT) with exponential recency-weighted averaging.

### For Long-Term (Month 2+)

7. **Foundation Model:** Fine-tune Chronos-Small on multi-asset crypto data for zero-shot prediction on new tokens.

8. **Regime-Aware Pipeline:** Implement Momentum Transformer's changepoint detection + per-regime model heads.

9. **Production Deployment:** Use ONNX export for inference optimization. Target <100ms latency for 1-minute bar predictions.

### Critical Warnings

- **Do NOT use vanilla Transformer for crypto** -- it consistently underperforms LSTM without extensive modification
- **Do NOT trust single train/test splits** -- always use rolling window validation
- **Do NOT ignore prediction delay** -- PatchTST and other models may appear to have low MSE while simply lagging the price by 1-2 steps
- **Do NOT skip the GRU baseline** -- if your transformer cannot beat a 2-layer GRU, something is wrong with your data pipeline or hyperparameters
- **Do NOT assume more parameters = better** -- CryptoMamba (136k params) beats iTransformer (201k params) and Bi-LSTM (569k params)

---

## References (Complete List)

1. Lim, B. et al. (2021). "Temporal Fusion Transformers for Interpretable Multi-horizon Time Series Forecasting." *International Journal of Forecasting*. https://www.sciencedirect.com/science/article/pii/S0169207021000637

2. Nie, Y. et al. (2023). "A Time Series is Worth 64 Words: Long-term Forecasting with Transformers." *ICLR 2023*. https://arxiv.org/abs/2211.14730

3. Zhou, H. et al. (2021). "Informer: Beyond Efficient Transformer for Long Sequence Time-Series Forecasting." *AAAI 2021*. https://arxiv.org/abs/2012.07436

4. Wu, H. et al. (2021). "Autoformer: Decomposition Transformers with Auto-Correlation for Long-Term Series Forecasting." *NeurIPS 2021*. https://arxiv.org/abs/2106.13008

5. Zhou, T. et al. (2022). "FEDformer: Frequency Enhanced Decomposed Transformer for Long-term Series Forecasting." *ICML 2022*. https://arxiv.org/abs/2201.12740

6. Liu, Y. et al. (2024). "iTransformer: Inverted Transformers Are Effective for Time Series Forecasting." *ICLR 2024 Spotlight*. https://arxiv.org/abs/2310.06625

7. Wang, Y. et al. (2024). "TimeXer: Empowering Transformers for Time Series Forecasting with Exogenous Variables." *NeurIPS 2024*. https://arxiv.org/abs/2402.19072

8. Wu, H. et al. (2023). "TimesNet: Temporal 2D-Variation Modeling for General Time Series Analysis." *ICLR 2023*. https://arxiv.org/abs/2210.02186

9. Sepehri, M.S. et al. (2025). "CryptoMamba: Leveraging State Space Models for Accurate Bitcoin Price Prediction." *IEEE ICBC 2025 / ICLR 2025 AFI Workshop*. https://arxiv.org/abs/2501.01010

10. Wood, K. et al. (2022). "Trading with the Momentum Transformer: An Intelligent and Interpretable Architecture." *arXiv*. https://arxiv.org/abs/2112.08534

11. "Adaptive Temporal Fusion Transformers for Cryptocurrency Price Prediction." *arXiv 2509.10542*. https://arxiv.org/abs/2509.10542

12. "Interpretable multi-horizon time series forecasting of cryptocurrencies by leverage temporal fusion transformer." *Heliyon / PMC (2024)*. https://pmc.ncbi.nlm.nih.gov/articles/PMC11605417/

13. "Leveraging Time Series Categorization and Temporal Fusion Transformers to Improve Cryptocurrency Price Forecasting." *arXiv 2412.14529*. https://arxiv.org/html/2412.14529v1

14. "Temporal Fusion Transformer-Based Trading Strategy for Multi-Crypto Assets Using On-Chain and Technical Indicators." *MDPI Systems (2025)*. https://www.mdpi.com/2079-8954/13/6/474

15. "Informer In Algorithmic Investment Strategies on High Frequency Bitcoin Data." *arXiv 2503.18096*. https://arxiv.org/html/2503.18096v1

16. "From LSTM to GPT-2: Recurrent and Transformer-Based Deep Learning Architectures for Multivariate High-Liquidity Cryptocurrency Price Forecasting." *MDPI Symmetry (2025)*. https://www.mdpi.com/2073-8994/18/1/32

17. "Helformer: an attention-based deep learning model for cryptocurrency price forecasting." *Journal of Big Data (2025)*. https://link.springer.com/article/10.1186/s40537-025-01135-4

18. "Comparative Analysis of LSTM, GRU and Transformer Deep Learning Models for Cryptocurrency ZEC Price Prediction Performance." *Atlantis Press, ICFIED-24*. https://www.atlantis-press.com/proceedings/icfied-24/125999624

19. Ansari, A.F. et al. (2024). "Chronos: Learning the Language of Time Series." *arXiv*. https://arxiv.org/abs/2403.07815

20. "Enhancing large language models for bitcoin time series forecasting." *Knowledge-Based Systems (2025)*. https://www.sciencedirect.com/science/article/pii/S0950705125014881

21. "Positional Encoding in Transformer-Based Time Series Models: A Survey." *arXiv (2025)*. https://arxiv.org/html/2502.12370v1

22. Kazemi, S.M. et al. (2019). "Time2Vec: Learning to Represent Time." *arXiv*. https://arxiv.org/abs/1907.05321

23. "Expert System for Bitcoin Forecasting: Integrating Global Liquidity via TimeXer Transformers." *arXiv 2512.22326*. https://arxiv.org/html/2512.22326v2

24. "TFB: Towards Comprehensive and Fair Benchmarking of Time Series Forecasting." *VLDB 2024*. https://www.vldb.org/pvldb/vol17/p2363-hu.pdf

25. "Intriguing Properties of Positional Encoding in Time Series Forecasting." *arXiv (2024)*. https://arxiv.org/abs/2404.10337

---

*Researcher ID: 013* | *Status: COMPLETE* | *Last Updated: 2026-02-24* | *Papers Reviewed: 25+* | *Models Benchmarked: 15*
