# Researcher Profile: Dr. Rachel Green

## Persona
- **Title:** Generative AI for Financial Data
- **Expertise:** GANs, VAEs, diffusion models for synthetic data and scenario generation
- **Years Experience:** 9
- **Background:** PhD Stanford AI, former research scientist at NVIDIA, now applies generative models to crypto market simulation.

## Research Scope
**Primary Question:** How can generative models (GANs, diffusion) augment crypto ML training, stress-test strategies, and create synthetic data for rare events?

**Target Systems/Areas:**
- TimeGAN for synthetic crypto price sequences
- Conditional GANs for regime-specific generation
- Diffusion models for volatility surfaces
- VAEs for latent space interpolation
- Augmenting training data to improve robustness

## Methodology
1. **Sources:** Papers on generative time series (TimeGAN, Diffusion models), GitHub implementations, finance applications.
2. **Extraction:** Model architectures, training stability tricks, evaluation metrics (TSTR - Train on Synthetic, Test on Real).
3. **Analysis:** Compare synthetic data fidelity (statistical moments, autocorrelation) and utility (improved model performance when trained on augmented data).
4. **Validation:** Generate 2022-like bear market scenarios; test strategy resilience.

---

## Key Findings

### 1. TimeGAN: The Gold Standard for Synthetic Time Series

**Source:** Yoon et al., "Time-series Generative Adversarial Networks" (NeurIPS 2019)

**Architecture — Four Core Components:**
TimeGAN combines an autoencoder with an adversarial network, using four interacting networks:

| Component | Role | Implementation |
|---|---|---|
| **Embedder** | Maps input time series into a lower-dimensional latent space, capturing temporal dynamics | RNN (typically GRU layers) |
| **Recovery** | Decodes latent representations back to original feature space | Feedforward network |
| **Generator** | Produces synthetic latent sequences from random noise | RNN with noise input |
| **Discriminator** | Distinguishes real from synthetic latent sequences | RNN classifier |

**Three-Phase Training Protocol:**
1. **Autoencoder Pretraining:** Embedding and recovery networks trained to minimize reconstruction loss, ensuring the latent space faithfully represents real data.
2. **Supervised Pretraining:** Generator is supervised to approximate next-time-step transitions in the latent space, capturing the stepwise conditional distribution p(s_t | s_{t-1}).
3. **Adversarial Joint Training:** Full min-max game across all four networks under a combined objective:
   - **Reconstruction Loss:** Measures fidelity of encode-decode roundtrip vs. original data.
   - **Supervised Loss:** Encourages generator to capture time-conditional distributions (the key innovation over standard GANs).
   - **Adversarial (Unsupervised) Loss:** Standard GAN objective pushing synthetic sequences toward indistinguishability from real ones.

**Application to Crypto Markets:**
- Generate BTC/ETH 1h OHLCV sequences with realistic volatility clustering, fat tails, and mean-reversion patterns.
- Condition on market regime labels (bull, bear, sideways) for targeted scenario generation.
- TSTR evaluation shows synthetic-trained models achieve approximately 85% of real-data model performance.
- Typical hyperparameters: GRU layers, dropout regularization, batch sizes 64-128, sequence lengths 24-168 steps (1-7 days of hourly data).

**Strengths:** Temporal coherence far superior to vanilla GANs; supervised loss prevents the generator from taking temporal shortcuts.

**Weaknesses:**
- Mode collapse remains a challenge, especially for extreme tail events.
- Struggles to reproduce the full severity of black swan events (e.g., LUNA/UST collapse magnitude).
- Training instability requires careful hyperparameter tuning.
- Computationally expensive for high-frequency data (tick-level).

**GitHub Implementations:** [stefan-jansen/machine-learning-for-trading](https://github.com/stefan-jansen/machine-learning-for-trading) Chapter 21; [YData TimeGAN integration](https://docs.synthetic.ydata.ai/1.3/synthetic_data/time_series/timegan_example/).

---

### 2. QuantGAN: Temporal Convolutional Networks for Financial Fidelity

**Source:** Wiese et al., "Quant GANs: Deep Generation of Financial Time Series" (2019)

**Architecture:**
Unlike TimeGAN's RNN approach, QuantGAN employs **Temporal Convolutional Networks (TCNs)** for both generator and discriminator. TCNs use dilated causal convolutions that are well-suited to capture long-range dependencies in continuous sequential data, such as volatility clusters that persist over weeks or months.

**Key Capabilities — Stylized Facts Reproduction:**
| Financial Property | QuantGAN Fidelity |
|---|---|
| Fat-tailed return distributions | Excellent |
| Volatility clustering | Excellent |
| Leverage effects (negative returns increase vol) | Good |
| Serial autocorrelation in absolute returns | Excellent |
| Long-range dependence | Good (via dilated convolutions) |

**Distributional properties for both small and large lags show excellent agreement** with real data, making QuantGAN particularly suited for risk modeling and options pricing where tail behavior matters.

**Regime-Specific Extension — RSQGAN:**
Koshiyama et al. (2023) extended QuantGAN into the **Regime-Specific Quant GAN (RSQGAN)**, a conditional GAN that:
- Uses a structural breakpoint algorithm to segment financial time series into distinct market regime classes (crisis, recovery, bull, consolidation).
- Generates class-conditional synthetic return data matching the statistical properties of each regime.
- Outperforms unconditional GANs trained on crisis-only data for risk estimation.
- Includes a user-controlled hyperparameter for adjusting the fidelity-variety tradeoff.

**Application to Crypto:**
- Generate regime-specific altcoin return distributions for stress testing.
- Produce realistic "crypto winter" scenarios for strategy robustness evaluation.
- TCN architecture handles the long memory in crypto volatility better than RNN-based approaches.

**Source:** [RSQGAN paper (MDPI Applied Sciences 2023)](https://www.mdpi.com/2076-3417/13/19/10639); [QuantGAN GitHub](https://github.com/KseniaKingsep/quantgan).

---

### 3. Diffusion Models for Financial Time Series Generation

**Source:** Multiple 2024-2025 papers; Song & Ermon, "Score-Based Generative Models"

Diffusion models have emerged as the strongest challenger to GANs for synthetic financial data, with several purpose-built architectures appearing in 2024-2025.

#### 3a. FTS-Diffusion (ICLR 2024)

**Source:** "Generative Learning for Financial Time Series with Irregular and Scale-Invariant Patterns" (ICLR 2024)

**Three-Module Architecture:**
1. **Pattern Recognition:** Scale-invariant algorithm extracts recurring patterns that vary in duration and magnitude (e.g., the "double bottom" appearing at 4h, daily, and weekly scales).
2. **Diffusion-Based Generative Network:** Synthesizes new pattern segments using denoising diffusion probabilistic models (DDPMs).
3. **Temporal Transition Module:** Models pattern sequencing to aggregate generated segments into coherent full time series.

**Key Result:** Augmenting real-world data with FTS-Diffusion synthetic data **reduces stock prediction error by up to 17.9%** across datasets. This is the strongest published evidence for synthetic data utility in financial ML.

**Why it matters for crypto:** Crypto markets exhibit extreme scale-invariant patterns (pump-dump cycles at every timeframe). FTS-Diffusion's explicit handling of these patterns makes it uniquely suited.

#### 3b. Wavelet-Based Diffusion (2025)

**Source:** "Generation of Synthetic Financial Time Series by Diffusion Models" (Quantitative Finance, 2025)

Uses wavelet transformation to convert multiple time series (prices, volumes, spreads) into images, then generates synthetic images via DDPM, and applies inverse wavelet transform to recover realistic time series. This approach naturally preserves cross-asset correlations and multi-scale dependencies.

#### 3c. Emerging Diffusion Architectures (2025)

| Model | Innovation | Application |
|---|---|---|
| **TRADES** | Full market simulation with diffusion | Strategy backtesting with realistic microstructure |
| **CoFinDiff** | Controllable generation via cross-attention conditioning on volatility/trend | Targeted scenario generation |
| **InterDiff** | Classifier-free guided diffusion preserving inter-stock correlations | Portfolio-level synthetic data |
| **DHMoE** | Hierarchical multi-granular mixture of experts | Multi-timeframe stock prediction |

**Diffusion vs. GAN Tradeoffs:**

| Dimension | GANs (TimeGAN/QuantGAN) | Diffusion Models |
|---|---|---|
| Training stability | Fragile (mode collapse risk) | Stable (no adversarial training) |
| Sample quality | Good for returns/vol | Superior for complex patterns |
| Sampling speed | Fast (single forward pass) | Slow (iterative denoising, 50-1000 steps) |
| Controllability | Limited (conditional GAN) | Excellent (classifier-free guidance) |
| Tail event fidelity | Moderate | Better (score matching captures tails) |
| Compute cost | Moderate | High (training and inference) |

---

### 4. VAEs for Market Scenario Simulation and Stress Testing

**Source:** Hull & White, "Variational Autoencoders: A Hands-Off Approach to Volatility" (Quantitative Finance, 2021); "Towards Causal Market Simulators" (2025)

**Core Mechanism:**
VAEs learn a probabilistic latent space of market states, enabling:
- **Monte Carlo scenario generation:** Sample from the learned latent distribution to generate thousands of plausible market trajectories.
- **Interpolation:** Smoothly interpolate between known market states (e.g., blend a 2020 COVID crash with a 2022 crypto winter).
- **Extrapolation:** Push latent variables beyond observed ranges to simulate unprecedented stress events.

**Key Applications:**

| Use Case | Technique | Value |
|---|---|---|
| **Volatility surface completion** | VAE fills missing strikes/maturities | Arbitrage-free surface for options pricing |
| **Stress testing** | Sample from tail regions of latent space | Probabilistic exploration of extreme scenarios |
| **Counterfactual analysis** | TNCM-VAE (causal VAE) | "What if BTC fell 80% but ETH held?" scenarios |
| **Portfolio risk modeling** | Generate correlated multi-asset paths | Realistic drawdown estimation |

**TNCM-VAE (2025) — Causal Market Simulator:**
The Time-series Neural Causal Model VAE combines variational autoencoders with structural causal models:
- Enforces causal constraints through directed acyclic graphs (DAGs) in the decoder architecture.
- Generates counterfactual financial time series preserving both temporal dependencies and causal relationships.
- Enables questions like: "If the Fed raised rates by 200bps instead of 50bps, how would BTC/ETH correlation change?"

**Crypto-Specific Application:**
- Encode the latent representation of market regimes (DeFi summer, NFT mania, exchange collapse).
- Generate plausible "what-if" trajectories for strategy stress testing.
- VAE latent space provides natural dimensionality reduction for high-frequency feature sets.

**Weakness:** VAEs tend to produce blurrier (smoother) outputs than GANs, potentially underestimating spike severity. Hybrid VAE-GAN architectures (e.g., VAEGAN) address this.

---

### 5. Synthetic Data to Augment Small Training Sets

**Critical Problem in Crypto ML:**
Many altcoins have less than 2 years of reliable data. Low-cap tokens may have only months. Rare events (exchange hacks, depegs) occur a handful of times in history. This data scarcity is the primary bottleneck for robust ML model training.

#### 5a. TSTR Framework (Train on Synthetic, Test on Real)

**The standard evaluation protocol for synthetic data utility:**

| Step | Description |
|---|---|
| 1. Train generative model | Fit TimeGAN/Diffusion on real data |
| 2. Generate synthetic dataset | Produce N synthetic sequences |
| 3. Train downstream model on synthetic | E.g., LSTM classifier or XGBoost predictor |
| 4. Evaluate on real holdout | Measure MAE, accuracy, Sharpe on real test set |
| 5. Compare to TRTR baseline | Model trained and tested on real data |

**Key Published Results:**
- TSTR on financial fraud detection: **79.75% accuracy** with synthetic-only training; adding just **20% real data raises to 88.1%**, approaching real-only performance (ACM ICAIF 2025).
- Notably, simple Gaussian sampling sometimes outperforms deep generative models, challenging the assumption that complexity equals utility.
- FTS-Diffusion augmentation: **17.9% reduction in prediction error** vs. real-only training (ICLR 2024).

#### 5b. Optimal Mixing Ratios

Research consensus from CFA Institute (2025) and multiple studies:

| Synthetic:Real Ratio | Typical Effect |
|---|---|
| 100:0 (synthetic only) | 75-85% of real-only performance |
| 80:20 (mostly synthetic) | 85-92% of real-only performance |
| 50:50 (equal mix) | 95-100% of real-only performance |
| 20:80 (augmentation) | 100-105% of real-only performance (best) |
| 0:100 (real only) | Baseline |

**The sweet spot is 10-30% synthetic augmentation** — enough to improve generalization without introducing distributional drift.

#### 5c. Danger: Synthetic-Only Training Collapse

Training exclusively on synthetic data leads to progressive performance degradation:
- Generator artifacts accumulate across training epochs.
- Stylized facts (autocorrelation structure, tail heaviness) drift from real distributions.
- Models learn to exploit generator-specific patterns rather than market structure.

**Mitigation:** Always maintain a real-data holdout; use TSTR scores as a quality gate; implement periodic re-calibration of generators against fresh real data.

---

### 6. Data Augmentation Techniques for Crypto ML

Beyond generative models, simpler augmentation techniques provide substantial value with minimal computational cost.

#### 6a. Transformation-Based Augmentations

| Technique | Description | Best For | Crypto Notes |
|---|---|---|---|
| **Jittering** | Add Gaussian noise (mean=0, std=0.01-0.05 of feature range) to each timestep | Regularization, noise robustness | Use smaller std for price, larger for volume |
| **Magnitude Warping** | Multiply time series by smooth cubic spline curve | Scale invariance | Simulates varying volatility regimes |
| **Time Warping** | Stretch/compress time axis via smooth warping function | Temporal invariance | Models varying trade intensity |
| **Window Slicing** | Crop to 90% of original length from random start | Data volume increase | Creates overlapping training windows |
| **Window Warping** | Select a slice and speed up (2x) or slow down (0.5x) | Temporal distortion robustness | Simulates fast/slow market phases |
| **Rotation** | Apply rotation matrix to multivariate features | Feature interaction robustness | Use only for derived features, not raw OHLCV |
| **Scaling** | Multiply entire series by random factor (0.8-1.2) | Magnitude invariance | Simulates different price levels |
| **Permutation** | Randomly shuffle segments within a window | Order invariance (limited use) | Not recommended for price series; useful for feature vectors |

**Performance Evidence (Iwana & Uchida, 2021):**
- Positive correlations observed for **Jittering, Scaling, and Magnitude Warping** across MLP and LSTM-FCN architectures.
- As class imbalance rises, magnitude-domain augmentations become increasingly beneficial.
- Window Slicing is the simplest technique with consistent positive results.

#### 6b. Crypto-Specific Augmentation Strategies

| Strategy | Implementation | Rationale |
|---|---|---|
| **Regime-conditional jittering** | Higher noise std during high-vol periods, lower during calm | Preserves signal-to-noise ratio per regime |
| **Cross-asset warping** | Apply BTC's temporal pattern to ETH's magnitude | Tests strategy robustness to correlation changes |
| **Volume profile perturbation** | Jitter volume while preserving VWAP | Simulates different liquidity conditions |
| **Spread injection** | Add realistic bid-ask spread noise to mid-price | Tests execution sensitivity |
| **Fee-adjusted returns** | Augment return series with varying fee structures | Tests strategy viability across exchanges |
| **Funding rate scenarios** | Warp funding rate series to simulate extreme carry | Stress tests funding-rate-dependent strategies |

#### 6c. Recommended Augmentation Pipeline for Crypto ML

```
Raw OHLCV Data (real)
    |
    +---> Window Slicing (5-10x volume increase)
    |         |
    |         +---> Jittering (Gaussian noise, std=0.02)
    |         |
    |         +---> Magnitude Warping (cubic spline, knots=4)
    |         |
    |         +---> Time Warping (smooth warping, sigma=0.2)
    |
    +---> TimeGAN / FTS-Diffusion (regime-conditional generation)
    |         |
    |         +---> TSTR quality gate (reject if TSTR < 0.80)
    |
    +---> Merge: 70-80% real + 20-30% synthetic
    |
    +---> Train downstream model
    |
    +---> Evaluate on pure real holdout
```

---

### 7. Realistic Simulation of Market Conditions for Strategy Testing

#### 7a. CTBench: The Crypto-Specific Benchmark (2025)

**Source:** Ang et al., "CTBench: Cryptocurrency Time Series Generation Benchmark" (NeurIPS 2025)

The first open benchmark tailored to cryptocurrency market generation:

| Dimension | Details |
|---|---|
| **Dataset** | 452 cryptocurrencies, all USDT pairs, Jan 2020 - Dec 2024 |
| **Coverage** | Bull runs, crashes, consolidation, DeFi summer, LUNA collapse |
| **Evaluation Tasks** | (1) Predictive Utility, (2) Statistical Arbitrage profitability |
| **Metrics** | 13 metrics across 6 dimensions: error, rank, trading performance, risk assessment, efficiency, visualization |
| **Models Benchmarked** | 8 TSG models from 5 families |

**Key Finding:** No single generative model dominates all metrics. There are fundamental trade-offs between statistical fidelity and real-world trading profitability in generated data. Models that perfectly match statistical moments may not produce profitable synthetic scenarios, and vice versa.

#### 7b. Agent-Based Simulation Augmentation

**Source:** AWS HPC Blog, "Enhancing Equity Strategy Backtesting with Synthetic Data: An Agent-Based Model Approach" (2024)

Rather than purely statistical generation, agent-based models simulate market participants:
- Market makers providing liquidity.
- Momentum traders following trends.
- Mean-reversion traders fading moves.
- Noise traders adding randomness.

This produces synthetic order flow with realistic microstructure (bid-ask bounce, temporary impact, information asymmetry) that statistical generators miss.

#### 7c. Black Swan and Tail Risk Generation

**Approaches for generating extreme scenarios:**

| Method | How It Works | Realism |
|---|---|---|
| **Historical replay with perturbation** | Take real crashes, warp magnitude/duration | High (based on real events) |
| **EVT-calibrated Monte Carlo** | Fit Generalized Pareto Distribution to tails, sample extremes | Good for tail shape |
| **Conditional GAN (crisis mode)** | RSQGAN conditioned on crisis regime label | Good regime properties |
| **Latent space extrapolation (VAE)** | Push VAE z-vectors beyond training distribution | Creative but may be unrealistic |
| **Contagion simulation** | Model cross-asset correlation breakdown during stress | Essential for portfolio testing |

**Critical insight from crypto risk research (2025):** Standard Monte Carlo simulations ignore tail risk and volatility clustering prevalent in crypto. Rolling correlation models are needed to capture regime-dependent contagion spillovers (e.g., stablecoin depeg causing exchange token collapse).

#### 7d. Practical Simulation Framework for Strategy Robustness

```
For each strategy under test:
    1. Backtest on real historical data (baseline)
    2. Generate N=100 synthetic scenarios per regime:
       - Bull market (TimeGAN conditioned on regime)
       - Bear market / crypto winter
       - Black swan / flash crash (EVT + conditional GAN)
       - Sideways / low-vol consolidation
       - Liquidity crisis (agent-based with reduced market makers)
    3. Run strategy across all synthetic scenarios
    4. Compute:
       - Worst-case drawdown across scenarios
       - Sharpe ratio distribution (not just mean)
       - Tail risk metrics (CVaR at 1%, 5%)
       - Strategy decay rate under regime change
    5. Accept strategy only if:
       - Median synthetic Sharpe > 0.5
       - Worst-case drawdown < 2x historical max drawdown
       - Profitable in ≥60% of bear market scenarios
```

---

## Actionable Insights for Production Systems

### Immediate Implementation (Low Effort, High Value)
- [x] **Window slicing + jittering augmentation** — 5-10x training data increase with zero model training. Apply to all existing crypto ML pipelines immediately.
- [x] **Magnitude warping for regime robustness** — Simulate volatile/calm conditions by warping existing data with cubic splines.
- [x] **TSTR evaluation protocol** — Implement as standard quality gate before accepting any synthetic data into training.

### Medium-Term (Moderate Effort)
- [ ] **TimeGAN for regime-conditional generation** — Train separate TimeGAN models for bull/bear/sideways regimes using labeled historical data. Use for augmenting rare regime samples (e.g., only 2 bear markets in crypto history).
- [ ] **FTS-Diffusion for pattern augmentation** — Leverage scale-invariant pattern extraction to generate realistic pump-dump and accumulation-distribution sequences at multiple timeframes.
- [ ] **VAE latent space for strategy stress testing** — Train VAE on multi-asset crypto data; use latent interpolation to generate "corridor" scenarios between known crisis events.

### Advanced (High Effort, Strategic Value)
- [ ] **RSQGAN for regime-specific risk modeling** — Conditional generation per regime for sophisticated risk estimation. Especially valuable for options-like strategies and leveraged positions.
- [ ] **CTBench integration** — Evaluate all generative models against the 452-token benchmark before deployment. Use dual-task evaluation (predictive utility + statistical arbitrage profitability).
- [ ] **Agent-based microstructure simulation** — For strategies sensitive to execution (e.g., funding rate arb, cross-exchange), generate synthetic order books with realistic market maker behavior.
- [ ] **Causal VAE (TNCM-VAE) for counterfactual analysis** — Generate "what-if" scenarios preserving causal structure for portfolio-level stress testing.

### Critical Guardrails
- **Never train exclusively on synthetic data** — Always maintain ≥70% real data in training mix.
- **Monitor for generator drift** — Re-calibrate generative models quarterly against fresh real data.
- **TSTR score threshold** — Reject synthetic batches where TSTR accuracy < 80% of TRTR baseline.
- **Tail event validation** — Verify that generated extreme events match empirical tail indices (kurtosis, GPD shape parameter).
- **Cross-validate augmentation benefit** — Not all strategies benefit from augmentation. Measure marginal Sharpe improvement per synthetic data percentage.

---

## Key Quantitative Benchmarks

| Metric | Value | Source |
|---|---|---|
| TimeGAN TSTR performance vs real | ~85% | Yoon et al. 2019 |
| FTS-Diffusion prediction error reduction | 17.9% | ICLR 2024 |
| Synthetic-only fraud detection accuracy | 79.75% | ACM ICAIF 2025 |
| +20% real data accuracy boost | 88.1% | ACM ICAIF 2025 |
| CTBench tokens evaluated | 452 | NeurIPS 2025 |
| CTBench metrics | 13 across 6 dimensions | NeurIPS 2025 |
| QuantGAN stylized facts fidelity | Excellent (vol clustering, fat tails, leverage) | Wiese et al. 2019 |

---

## References

### Foundational Papers
- Yoon, J., Jarrett, D., & van der Schaar, M. "Time-series Generative Adversarial Networks." NeurIPS 2019. [(link)](https://www.researchgate.net/publication/344464212_Time-series_Generative_Adversarial_Networks)
- Wiese, M., Knobloch, R., Korn, R., & Kretschmer, P. "Quant GANs: Deep Generation of Financial Time Series." 2019. [(link)](https://www.semanticscholar.org/paper/Quant-GANs:-deep-generation-of-financial-time-Wiese-Knobloch/3cf57cad75d71bffac9fc4589d7b294d90558a13)
- Song, Y. & Ermon, S. "Score-Based Generative Modeling through Stochastic Differential Equations."
- Dhariwal, P. & Nichol, A. "Diffusion Models Beat GANs on Image Synthesis." NeurIPS 2021.

### Financial Applications (2024-2025)
- "Generative Learning for Financial Time Series with Irregular and Scale-Invariant Patterns" (FTS-Diffusion). ICLR 2024. [(link)](https://openreview.net/forum?id=CdjnzWsQax)
- "Generation of Synthetic Financial Time Series by Diffusion Models." Quantitative Finance, 2025. [(link)](https://www.tandfonline.com/doi/full/10.1080/14697688.2025.2528697)
- Koshiyama et al. "Regime-Specific Quant Generative Adversarial Network." Applied Sciences 2023. [(link)](https://www.mdpi.com/2076-3417/13/19/10639)
- "Deep Generative Models for Synthetic Financial Data." arXiv 2024. [(link)](https://arxiv.org/html/2512.21798)
- "Towards Causal Market Simulators" (TNCM-VAE). arXiv 2025. [(link)](https://arxiv.org/abs/2511.04469)
- Hull & White. "Variational Autoencoders: A Hands-Off Approach to Volatility." 2021. [(link)](https://arxiv.org/pdf/2102.03945)

### Crypto-Specific
- Ang et al. "CTBench: Cryptocurrency Time Series Generation Benchmark." NeurIPS 2025. [(link)](https://arxiv.org/abs/2508.02758)
- "New Money: A Systematic Review of Synthetic Data Generation for Finance." arXiv 2025. [(link)](https://arxiv.org/html/2510.26076v1)
- CFA Institute. "Synthetic Data in Investment Management." July 2025. [(link)](https://rpc.cfainstitute.org/sites/default/files/docs/research-reports/tait_syntheticdataininvestmentmanagement_online.pdf)
- "TSTR for Financial Fraud." ACM ICAIF 2025. [(link)](https://dl.acm.org/doi/10.1145/3768292.3770393)

### Data Augmentation
- Iwana, B.K. & Uchida, S. "An Empirical Survey of Data Augmentation for Time Series Classification with Neural Networks." PLOS ONE 2021. [(link)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0254841)
- Um et al. "Data Augmentation of Wearable Sensor Data for Parkinson's Disease Monitoring using Convolutional Neural Networks." 2017.
- "Data Augmentation Techniques in Time Series Domain: A Survey and Taxonomy." Neural Computing and Applications, 2023. [(link)](https://link.springer.com/article/10.1007/s00521-023-08459-3)

### Implementations
- [stefan-jansen/synthetic-data-for-finance](https://github.com/stefan-jansen/synthetic-data-for-finance) — TimeGAN and GAN implementations for finance
- [KseniaKingsep/quantgan](https://github.com/KseniaKingsep/quantgan) — QuantGAN PyTorch implementation
- [uchidalab/time_series_augmentation](https://github.com/uchidalab/time_series_augmentation) — Comprehensive augmentation methods
- [YData TimeGAN](https://docs.synthetic.ydata.ai/1.3/synthetic_data/time_series/timegan_example/) — Production-ready TimeGAN

---
*Researcher ID: 014* | *Status: Complete*
