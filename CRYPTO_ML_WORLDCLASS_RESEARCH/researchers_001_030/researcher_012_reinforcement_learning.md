# Researcher Profile: Dr. David Wu

## Persona
- **Title:** Reinforcement Learning for Trading Lead
- **Expertise:** Deep Q-Networks (DQN), Policy Gradient (PPO, A2C, SAC), multi-agent RL
- **Years Experience:** 11
- **Background:** PhD Berkeley RL, former OpenAI, now applies RL to crypto trading at a prop firm.

## Research Scope
**Primary Question:** Can RL agents learn profitable trading policies in crypto markets, and what are the best practices for training stability?

**Target Systems/Areas:**
- DQN for discrete action trading (buy/hold/sell)
- PPO/A2C for continuous position sizing
- SAC for entropy-regularized continuous control
- Multi-agent RL for portfolio management and market simulation
- Imitation learning from expert traders
- Risk-aware RL (CVaR, entropy regularization)

## Methodology
1. **Sources:** OpenAI Gym trading environments (gym-anytrading), FinRL library, academic papers (2022-2026), GitHub RL trading repos, FinRL Contest results (2023-2025).
2. **Extraction:** State space (features), action space (discrete/continuous), reward function design, training stability tricks, sim-to-real transfer.
3. **Analysis:** Compare sample efficiency, robustness to non-stationarity, generalization, and compute requirements.
4. **Validation:** Cross-reference backtest claims vs live/paper trading results; prioritize studies with out-of-sample evidence.

---

## COMPLETE FINDINGS

### 1. Does RL for Crypto Trading Actually Work? (Honest Assessment)

**The short answer: In backtesting, often spectacularly. In live trading, rarely and inconsistently.**

**Evidence FOR:**
- A 2025 DQN study on Bitcoin (2022 to mid-2025) reported 120x growth in NAV from $1M, vastly outperforming buy-and-hold ([Cogent Economics, 2025](https://www.tandfonline.com/doi/full/10.1080/23322039.2025.2594873)).
- Multi-agent RL systems claim 142% annual returns vs 12% for rule-based bots, with a reported +4.7% during a November 2025 market crash where markets fell -11% ([NeuralArb, 2025](https://www.neuralarb.com/2025/11/20/reinforcement-learning-in-dynamic-crypto-markets/)).
- SAC and DDPG agents outperformed equal-weighted and mean-variance portfolio baselines ([arxiv: 2511.20678](https://arxiv.org/html/2511.20678v1)).

**Evidence AGAINST:**
- Over 90% of academic trading strategies (including RL) fail when implemented with real capital. Standard backtesting suffers from multiple testing bias and overfitting ([Portfolio Optimization Backtesting](https://portfoliooptimizationbook.com/slides/slides-backtesting.pdf)).
- Simpler models (Naive, buy-and-hold) have consistently outperformed more complex ML/DL models in multiple comparative studies ([Springer, 2025](https://link.springer.com/article/10.1007/s44163-025-00519-y)).
- A key 2022 study in Expert Systems with Applications demonstrated that supervised learning (ResNet-LSTM) outperformed classical RL techniques (DQN, A2C, recurrent RL) on six cryptocurrencies ([ScienceDirect, 2022](https://www.sciencedirect.com/science/article/abs/pii/S0957417422006339)).
- FinRL contest organizers themselves acknowledge: "the lack of standardised task definitions, real-time high-quality datasets, close-to-real market environments and robust baselines has hindered consistent reproduction" ([FinRL Contests, 2025](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/aie2.12004)).

**Honest verdict:** RL produces impressive backtest numbers that almost never survive contact with live markets at the same level. The 120x claims should be treated with extreme skepticism. The technology is promising but immature for production crypto trading. Most real-world success stories involve RL as one component in a hybrid system, not as a standalone agent.

---

### 2. PPO vs SAC vs DQN for Crypto Trading

| Aspect | DQN | PPO | SAC |
|---|---|---|---|
| **Action space** | Discrete (buy/hold/sell) | Both (best for continuous) | Continuous (position sizing) |
| **Training stability** | Moderate (replay buffer helps) | High (clipped updates prevent catastrophic drops) | High (entropy regularization) |
| **Sample efficiency** | Better (off-policy, replay) | Lower (on-policy) | Better (off-policy) |
| **Exploration** | Epsilon-greedy (crude) | Entropy bonus (tunable) | Maximum entropy (principled) |
| **Compute cost** | Lowest | Moderate | Highest |
| **Best use case** | Strategy selection, discrete signals | Multi-asset allocation, cross-exchange | Portfolio management, continuous sizing |
| **Crypto-specific results** | 0.48% cumulative return, Sharpe 0.21, max DD -0.98% (conservative) | Most popular in 2025 production systems | Outperformed DDPG; more stable in noisy conditions |

**Recommendation for our systems:**
- **DQN** is closest to what we already do (discrete signal generation). Easiest migration path.
- **PPO** is the industry default for multi-asset trading. Most tutorials, most stable training.
- **SAC** is theoretically superior for continuous position sizing but requires more compute and tuning.
- For our use case (signal generation, not continuous position sizing), **DQN or PPO** would be the appropriate choice.

---

### 3. FinRL Library: Practical Results and Limitations

**What FinRL provides:**
- Pre-built environments for stock/crypto/forex trading
- Integration with DQN, PPO, SAC, A2C, TD3, DDPG
- Data pipelines for Yahoo Finance, Alpaca, Binance
- Standardized benchmarking via FinRL Contests (2023-2025)

**Practical limitations (confirmed by 2025 contest organizers):**
1. **Policy instability:** Small changes in training settings or market environment cause large performance variations.
2. **Sampling bottleneck:** Collecting high-quality trajectories is expensive and limited by data access.
3. **Engineering-heavy:** "Applying RL strategies to real-world trading tasks remains error-prone and engineering-heavy" for individuals.
4. **Reproducibility crisis:** Lack of standardized benchmarks means results are hard to compare.
5. **Unrealistic assumptions:** Most FinRL examples assume zero or minimal transaction costs, unlimited liquidity, and instant fills.

**FinRL Contest evolution (2023-2025):**
- 2023: Basic stock trading benchmarks
- 2024: Added crypto trading, order execution
- 2025: FinRL-AlphaSeek for crypto trading, factor mining, LLM-engineered signal integration

**Our assessment:** FinRL is useful as a research/prototyping tool but NOT production-ready. You would need to build significant infrastructure around it for live trading. The library teaches concepts well but the gap between its demos and production systems is enormous.

---

### 4. Reward Function Design: Sharpe-Based vs PnL-Based

This is one of the most critical and underappreciated aspects of RL for trading.

**Pure PnL reward (r_t = portfolio_return_t):**
- Pros: Simple, directly optimizes what you want (money)
- Cons: Encourages extreme risk-taking, ignores volatility, leads to boom/bust policies
- Result: Agents learn to maximize leverage in trending markets, get destroyed in reversals

**Sharpe-ratio reward (r_t = rolling_sharpe):**
- Pros: Balances return vs risk, produces smoother equity curves
- Cons: Non-stationary (rolling window changes), can lead to inaction (Sharpe maximized by not trading)
- Performance: Sharpe-TD3 achieved 91.7% cumulative return with Sharpe >1.51, volatility 13.4%, max DD -14% ([Springer, 2025](https://link.springer.com/article/10.1007/s44196-025-00875-8))

**Composite reward (2025 state-of-the-art):**
- Formula: `Reward = alpha * Return - beta * DownsideRisk + gamma * DifferentialReturn - delta * Turnover`
- Combines annualized return, downside risk, differential return, and Treynor ratio
- Modular and weighted to encode diverse investor preferences
- Avoids "reward hacking" that single-metric objectives encourage

**Risk-aware reward with CVaR:**
- Formula: `Reward = Profit - Costs - lambda * CVaR`
- CVaR is the most adopted risk measure in RL-based portfolio optimization
- Critical for crypto: tail risk is much larger than traditional markets
- Key finding: Early CVaR research "completely disregarded transaction costs" -- must include them

**Practical recommendation for our systems:**
- If we adopt RL, use composite reward: `r_t = log_return - 0.5 * drawdown_penalty - transaction_cost - lambda * tail_risk`
- Never use pure PnL reward -- it is a trap that leads to overfitting on trending regimes

---

### 5. State Space Design for Crypto Trading Agents

**Best practices from 2025 research:**

| Category | Features | Count |
|---|---|---|
| Price/Volume | OHLCV, returns, log-returns, normalized price | 8-12 |
| Technical indicators | RSI, MACD, Bollinger Bands, ATR, OBV, Stochastic | 15-25 |
| On-chain metrics | Active addresses, NVT, MVRV, exchange netflow, hash rate | 8-12 |
| Sentiment | Fear & Greed Index, social volume, funding rates | 3-6 |
| Market microstructure | Bid-ask spread, order book imbalance, liquidation data | 4-8 |
| Account state | Unrealized PnL, available balance, current position | 2-4 |
| Cross-asset | BTC dominance, DXY, VIX, correlation matrix | 4-8 |
| **Total typical state space** | | **50-75 features** |

**Key finding:** XGBoost feature selection BEFORE feeding into RL significantly improves performance. A 2025 study combining XGBoost feature selection with DDQN "improves all key trading performance metrics" ([ScienceDirect, 2025](https://www.sciencedirect.com/science/article/abs/pii/S1568494625003400)).

**LSTM-encoded observations:** Rather than raw features, passing data through an LSTM encoder first (learned representations) then feeding to PPO produces more stable training. The observation space becomes a latent representation rather than raw market data.

**For our systems specifically:** We already compute most of these features for XGBoost/GRU-Attention. The state space design is NOT a barrier to RL adoption -- we could reuse our existing feature pipeline.

---

### 6. Sample Efficiency: How Much Data Does RL Need?

**The bad news:** Deep RL models need MORE training data than traditional ML for comparable performance. This is a fundamental limitation.

| Method | Minimum Data (1h bars) | Typical Training | Notes |
|---|---|---|---|
| XGBoost (our current) | 5,000-10,000 samples | Minutes on CPU | Can work with 6 months of hourly data |
| DQN | 50,000-200,000 steps | Hours on GPU | Off-policy helps; replay buffer |
| PPO | 500,000-2,000,000 steps | Hours-days on GPU | On-policy; needs fresh rollouts |
| SAC | 100,000-500,000 steps | Hours on GPU | Off-policy; best sample efficiency among policy gradient |
| Multi-agent | 1,000,000+ steps | Days on multi-GPU | Exponential with number of agents |

**Compute requirements (2025 benchmarks):**
- Single-asset DQN: 1-4 GPU hours (consumer GPU sufficient)
- PPO portfolio (5 assets): 8-24 GPU hours
- SAC with LSTM encoder: 12-48 GPU hours
- Multi-agent system: 100+ GPU hours
- GPU training is 100-1000x faster than CPU for RL

**For our context:** We currently train XGBoost in minutes on CPU. Moving to RL would require GPU infrastructure and 10-100x longer training cycles. This is a significant operational cost increase for uncertain benefit.

---

### 7. Sim-to-Real Gap: Why RL Backtests Well But Fails Live

This is the CENTRAL problem of RL for trading and the primary reason for caution.

**Root causes of the gap:**

1. **Overfitting to historical patterns:** RL agents memorize specific market sequences that are unlikely to recur. Standard backtesting inflates performance through in-sample optimization and multiple testing bias.

2. **Market impact not modeled:** Backtests assume orders fill at observed prices. In reality, your orders move the market, especially in crypto where liquidity is thin.

3. **Non-stationarity:** Crypto market regimes change dramatically (bull/bear/crab). An agent trained on 2021 bull market will fail in 2022 bear market. The environment distribution shifts constantly.

4. **Latency and execution:** RL assumes instant execution. Real-world latency (50-500ms) means the state observed at decision time differs from the state at execution time.

5. **Liquidity assumptions:** Most studies "operate under near-perfect fill and unlimited liquidity assumptions" which are completely unrealistic for crypto, especially altcoins.

6. **Reward hacking:** Agents find unintended loopholes in the reward function that score well in simulation but are meaningless in practice (e.g., rapid trading to accumulate tiny rewards that would be eaten by real fees).

**Quantified gap:** A PPO system reported Sharpe 1.8 in backtest but only 1.2 in live trading -- a 33% degradation. This is actually one of the BETTER outcomes; many systems lose money entirely when going live.

**Mitigation strategies (2025 best practices):**
- Walk-forward validation with rolling windows across multiple independent test periods
- Domain randomization: train with randomized transaction costs, slippage, and latency
- Ensembles of agents trained on different time periods
- Conservative position sizing (1/3 to 1/2 of backtest-optimal)
- Mandatory 3-month paper trading before live deployment
- Continuous monitoring for regime drift

---

### 8. RL vs Supervised ML for Crypto Trading (Critical Comparison)

**Direct head-to-head evidence:**

A peer-reviewed study in Expert Systems with Applications (2022) directly compared supervised learning (ResNet-LSTM) against RL techniques (DQN, A2C, recurrent RL) on six cryptocurrencies. **Result: Supervised learning outperformed RL** ([ScienceDirect, 2022](https://www.sciencedirect.com/science/article/abs/pii/S0957417422006339)).

**Why supervised learning can be superior for crypto trading:**

The key theoretical insight: In crypto trading, the market state does NOT transition based on a single agent's actions. Unlike games (where RL excels because the agent's actions change the game state), one trader's buys/sells do not meaningfully change BTC's price. This removes the core theoretical advantage of RL (learning to influence state transitions) and reduces the problem to a standard pattern recognition task -- which is exactly what supervised learning excels at.

| Dimension | Supervised ML (XGBoost/GRU) | Reinforcement Learning |
|---|---|---|
| **Signal generation** | Excellent (direct probability estimation) | Indirect (learns policy, not probabilities) |
| **Sample efficiency** | High (5K-10K samples) | Low (100K-2M steps) |
| **Training time** | Minutes (CPU) | Hours-days (GPU) |
| **Interpretability** | Good (feature importance, SHAP) | Poor (black box policy) |
| **Robustness** | Moderate (can overfit, but well-understood) | Poor (reward hacking, policy instability) |
| **Position sizing** | Manual rules on top of signals | Can learn directly (continuous action) |
| **Regime adaptation** | Requires retraining/online learning | Can adapt during episodes (in theory) |
| **Production reliability** | High (deterministic inference) | Low (stochastic policies, exploration noise) |
| **Compute cost** | Low | 10-100x higher |
| **Maintenance** | Standard ML ops | Complex (reward tuning, environment maintenance) |

**Where RL has genuine advantages:**
1. Position sizing and portfolio allocation (continuous actions)
2. Multi-step sequential decisions (when to enter, when to add, when to exit)
3. Adapting to changing conditions within an episode (in theory)
4. Learning to coordinate multiple strategies

**Where supervised ML wins:**
1. Signal generation (buy/sell probability)
2. Feature importance and interpretability
3. Sample efficiency and training speed
4. Production stability and reliability
5. Debugging and maintenance

**Industry trend (2025):** Hybrid approach adoption increased from 15% (2020) to 42% (2025), while pure RL decreased from 85% to 58%. The field is maturing toward combining XGBoost/gradient boosting for feature selection and signal generation with RL for execution and portfolio optimization.

---

### 9. Multi-Agent RL for Portfolio Management

**Architecture patterns:**

1. **Specialist agents:** Each agent trades one asset; a meta-agent allocates capital.
2. **Collaborative MARL:** Agents share information and jointly optimize portfolio return. Outperformed single-agent and non-cooperative models on futures commodities ([ACM, 2025](https://dl.acm.org/doi/10.1145/3746709.3746915)).
3. **Hierarchical RL:** High-level agent selects regime/strategy; low-level agents execute.
4. **LLM-powered multi-agent:** LLM orchestrates multiple RL agents for crypto portfolio; outperformed single-agent models and market benchmarks ([arxiv: 2501.00826](https://arxiv.org/abs/2501.00826)).
5. **Correctable MARL:** Agents can override each other's bad decisions; showed superiority over standard RL portfolio management ([MDPI, 2025](https://www.mdpi.com/2673-4591/120/1/11)).

**Practical results:**
- SAC outperformed DDPG for portfolio management, with greater stability in noisy conditions
- Multi-agent systems showed +4.7% during a -11% market crash (November 2025)
- Hierarchical approaches handle regime changes better than flat architectures

**Compute cost:** Multi-agent systems require 10-100x more compute than single-agent. This is the main barrier.

**For our context:** Multi-agent is the most promising RL application for us since we already run 100+ strategies. An RL meta-agent that allocates capital across our existing supervised ML signals could add value without replacing our core signal generation.

---

### 10. Practical Implementation Challenges and Compute Requirements

**Engineering challenges:**
1. **Environment design:** Building a realistic trading simulator with accurate order execution, fees, slippage, and market impact is harder than the RL algorithm itself.
2. **Reward engineering:** Small changes in reward function produce wildly different policies. This requires extensive experimentation.
3. **Hyperparameter sensitivity:** RL is notoriously sensitive to learning rate, discount factor, clip ratio (PPO), entropy coefficient, etc.
4. **Reproducibility:** Same code with different random seeds can produce Sharpe ranging from -1 to +3. Must train multiple seeds and ensemble.
5. **Data pipeline:** Need real-time data feeds, historical data management, and feature computation -- all synchronized.
6. **Monitoring:** Need to detect policy degradation, regime changes, and reward hacking in production.

**Minimum viable compute:**
- Development/experimentation: 1x consumer GPU (RTX 3080+), ~$500
- Serious training: 1x A100 or equivalent cloud, ~$2-4/hour
- Multi-agent production: 4-8 GPUs, ~$10-20/hour
- FinRL-style full pipeline: Estimated $50-200/month cloud compute for ongoing training

**Timeline for implementation:**
- Learning curve: 2-4 weeks for experienced ML engineer
- Environment + reward design: 2-4 weeks
- Training + tuning: 2-4 weeks
- Paper trading validation: 12 weeks (non-negotiable)
- Total: 4-6 months before any live trading

---

## Comparison to Our Current Systems

### What We Have Now
- **XGBoost classification** for signal generation (buy/sell/hold)
- **GRU-Attention** for sequential pattern recognition
- **100+ strategies** in Alpha Engine running every 30 minutes
- **Rule-based position sizing** and risk management
- CPU-only training, minutes per retrain cycle
- Proven results: Connors RSI-2 at 75.7% WR, VIX Spike Reversal at 72% WR

### What RL Would Add
- Potentially better position sizing (continuous action space)
- Meta-strategy allocation (which of our 100 strategies to weight)
- Adaptive risk management
- Potentially better handling of multi-step trade management

### What RL Would Cost
- GPU infrastructure ($50-200/month minimum)
- 4-6 month development timeline
- Significant engineering complexity
- Ongoing maintenance burden
- Reduced interpretability
- Higher risk of catastrophic failure (policy instability)

### What RL Would NOT Fix
- Our core signal quality (supervised ML is already good or better at this)
- Data quality issues
- Market regime changes (RL struggles with these too)
- Execution/slippage (this is an infrastructure problem, not an algorithm problem)

---

## GO/NO-GO RECOMMENDATION

### VERDICT: CONDITIONAL NO-GO (for now) -- with one targeted exception

**Do NOT replace XGBoost/GRU-Attention with RL for signal generation.** The evidence clearly shows:
1. Supervised learning outperforms RL for signal generation in crypto
2. Our current WR (62-75%) is competitive with the best RL backtest results
3. RL would add 10-100x compute cost for uncertain improvement
4. The sim-to-real gap means RL backtest gains will degrade significantly live
5. Engineering and maintenance burden would be substantial

**ONE exception worth exploring: RL Meta-Allocator**

Use RL (specifically PPO or DQN) as a capital allocation layer ON TOP of our existing 100+ strategy signals:

```
[Our existing supervised ML signals] --> [RL Meta-Allocator] --> [Position sizes per strategy]
```

This is the lowest-risk, highest-potential-value application because:
- It leverages our existing signal quality (no replacement needed)
- The action space is well-defined (allocate across known strategies)
- We have plenty of training data (100+ strategies x daily signals)
- It addresses a real gap (we currently use equal weighting or manual rules)
- If it fails, we fall back to current allocation without losing signal quality

**Implementation path for Meta-Allocator:**
1. Use DQN (simplest) with discrete allocation buckets (0%, 25%, 50%, 100% per strategy)
2. State: recent performance of each strategy, market regime indicators, correlation matrix
3. Reward: portfolio Sharpe ratio minus transaction cost penalty
4. Train on our own historical signal data (we have months of Alpha Engine output)
5. Paper trade for 3 months before any live use

**Estimated effort:** 4-6 weeks development, minimal additional compute (DQN on CPU is feasible for this scale).

**Revisit full RL adoption when:**
- We have 12+ months of historical signal data for meta-allocator training
- GPU infrastructure is already available for other reasons
- The RL research community solves the sim-to-real gap more convincingly
- Our supervised ML signal quality plateaus and we need a new approach

---

## Key References

### Core Papers
- Rodinos et al., "A Sharpe Ratio Based Reward Scheme in Deep RL for Financial Trading" ([Springer, 2023](https://link.springer.com/chapter/10.1007/978-3-031-34111-3_2))
- "Outperforming Algorithmic Trading RL Systems: A Supervised Approach" ([Expert Systems with Applications, 2022](https://www.sciencedirect.com/science/article/abs/pii/S0957417422006339))
- "Deep RL for Cryptocurrency Trading: Practical Approach to Address Backtest Overfitting" ([arxiv: 2209.05559](https://arxiv.org/abs/2209.05559))
- Bandarupalli, "Risk-Aware Deep RL for Crypto and Equity Trading Under Transaction Costs" ([SSRN, 2025](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5662930))
- "RL in Financial Decision Making: A Systematic Review" ([arxiv: 2512.10913](https://arxiv.org/html/2512.10913v1))
- "Cryptocurrency Futures Portfolio Trading System Using RL" ([Applied Sciences, 2025](https://www.mdpi.com/2076-3417/15/17/9400))

### Frameworks and Tools
- FinRL Library ([GitHub](https://github.com/AI4Finance-Foundation/FinRL)) -- research/prototyping, not production
- FinRL Contests 2023-2025 ([Wiley, 2025](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/aie2.12004))
- AgileRL ([agilerl.com](https://agilerl.com/)) -- evolutionary hyperparameter optimization for RL
- CFA Institute Practitioner's Guide, Ch. 6: RL and Inverse RL ([CFA, 2025](https://rpc.cfainstitute.org/research/foundation/2025/chapter-6-reinforcement-learning-inverse-reinforcement-learning))

### Algorithm-Specific
- "RL-Based Crypto Portfolio Management Using SAC and DDPG" ([arxiv: 2511.20678](https://arxiv.org/html/2511.20678v1))
- "Collaborative Multi-Agent RL for Portfolio Management" ([ACM, 2025](https://dl.acm.org/doi/10.1145/3746709.3746915))
- "LLM-Powered Multi-Agent System for Automated Crypto Portfolio Management" ([arxiv: 2501.00826](https://arxiv.org/abs/2501.00826))
- "Risk-Adjusted Deep RL for Portfolio Optimization: Multi-reward Approach" ([Springer, 2025](https://link.springer.com/article/10.1007/s44196-025-00875-8))
- "Designing a Crypto Trading System with DRL Utilizing LSTM + XGBoost" ([ScienceDirect, 2025](https://www.sciencedirect.com/science/article/abs/pii/S1568494625003400))

### Industry and Practical
- "Machine Learning in Trading: The CPU-GPU Latency Problem" ([QuantBlog, 2025](https://quantblog.wordpress.com/2025/10/05/machine-learning-in-trading-the-cpu-gpu-latency-problem/))
- "RL in Dynamic Crypto Markets: Future of Intelligent Arbitrage" ([NeuralArb, 2025](https://www.neuralarb.com/2025/11/20/reinforcement-learning-in-dynamic-crypto-markets/))
- Henderson et al., "Deep Reinforcement Learning that Matters" (reproducibility crisis in RL)
- Moody & Saffell, "Reinforcement Learning for Trading" (foundational)

---
*Researcher ID: 012* | *Status: COMPLETE* | *Last Updated: 2026-02-24*
