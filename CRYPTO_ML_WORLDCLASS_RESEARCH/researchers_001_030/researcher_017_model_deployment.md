# Researcher Profile: Dr. Robert Kim

## Persona
- **Title:** ML Ops and Deployment Architect
- **Expertise:** Model serving, CI/CD, monitoring, scalability, low-latency inference
- **Years Experience:** 14
- **Background:** PhD Stanford CS, former AWS SageMaker team, now leads MLOps at a crypto trading firm.

## Research Scope
**Primary Question:** How do world-class trading firms deploy and monitor ML models in production with high reliability and low latency?

**Target Systems/Areas:**
- Model serving frameworks (TensorFlow Serving, TorchServe, KServe)
- Real-time inference pipelines (WebSocket, gRPC)
- A/B testing and canary deployments
- Model monitoring (data drift, concept drift, performance)
- Scalability (horizontal scaling, autoscaling)
- Disaster recovery and rollback

## Methodology
1. **Sources:** MLOps best practices, cloud provider docs (AWS, GCP), Kubernetes patterns, case studies from tech/finance.
2. **Extraction:** Architecture diagrams, deployment workflows, monitoring metrics, SLA targets.
3. **Analysis:** Compare on-prem vs cloud; assess tradeoffs (latency vs cost).
4. **Validation:** Design deployment pipeline for sample crypto model; measure inference latency and uptime.

---

## COMPLETE RESEARCH FINDINGS

### 1. CI/CD for ML Trading Models (GitHub Actions-Based Pipelines)

#### 1.1 Why ML CI/CD Differs from Traditional Software CI/CD

Traditional CI/CD pipelines test code correctness and deploy binaries. ML CI/CD adds three additional dimensions: **data validation**, **model training/evaluation**, and **continuous training (CT)**. Unlike a web app where a passing test suite means "ship it," an ML model must also prove its statistical performance has not degraded before promotion to production.

ML workflows involve GPU/TPU-intensive tasks that can take hours or days, making pipeline efficiency and cost management critical. A trading model CI/CD pipeline must validate not just code correctness but also prediction quality, latency compliance, and risk constraints.

#### 1.2 GitHub Actions Pipeline Architecture for Crypto ML

A production-grade GitHub Actions pipeline for crypto ML models consists of three layered workflows:

**Layer 1 -- Code Pipeline (triggered on push/PR):**
```yaml
name: ML Code CI
on: [push, pull_request]
jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Lint
        run: flake8 src/ && mypy src/
      - name: Unit tests
        run: pytest tests/unit/ -v --tb=short
      - name: Integration tests
        run: pytest tests/integration/ -v
```

**Layer 2 -- Model Training Pipeline (scheduled + on-demand):**
```yaml
name: Model Training CT
on:
  schedule:
    - cron: '0 2 * * *'    # Daily at 2 AM UTC
  workflow_dispatch:         # Manual trigger
jobs:
  train:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Cache training data
        uses: actions/cache@v4
        with:
          path: data/
          key: training-data-${{ hashFiles('data/manifest.json') }}
      - name: Train model
        run: python train.py --config configs/production.yaml
      - name: Evaluate model
        run: python evaluate.py --threshold 0.55 --max-drawdown 0.15
      - name: Upload model artifact
        uses: actions/upload-artifact@v4
        with:
          name: model-${{ github.sha }}
          path: models/latest/
```

**Layer 3 -- Deployment Pipeline (triggered by successful training):**
```yaml
name: Model Deploy
on:
  workflow_run:
    workflows: ["Model Training CT"]
    types: [completed]
jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - name: Download model artifact
        uses: actions/download-artifact@v4
      - name: Run shadow validation (paper trading)
        run: python shadow_test.py --duration 1h --model models/latest/
      - name: Deploy to canary (5% traffic)
        run: python deploy.py --target canary --percentage 5
      - name: Monitor canary for 30 min
        run: python monitor_canary.py --duration 30m --alert-on-degradation
      - name: Promote to production
        run: python deploy.py --target production --percentage 100
```

**Key scheduling best practices:**
- Stagger multiple daily jobs (e.g., 1:00 AM, 1:15 AM, 1:30 AM) to avoid resource bottlenecks.
- GitHub Actions does not guarantee exact cron execution times; build tolerance into your pipeline.
- Use `workflow_dispatch` for emergency retraining after market regime changes.
- Cache datasets aggressively to reduce training wall-clock time.

#### 1.3 Trading-Specific CI/CD Gates

Beyond standard ML evaluation, crypto trading pipelines need these gates before promotion:

| Gate | Metric | Threshold | Action on Fail |
|------|--------|-----------|----------------|
| Backtest quality | Sharpe ratio | > 1.0 | Block deployment |
| Drawdown limit | Max drawdown | < 15% | Block deployment |
| Win rate | Win rate | > 52% | Warning |
| Latency | P99 inference | < 100ms | Block deployment |
| Data freshness | Last data timestamp | < 5 min old | Block deployment |
| Risk check | Position sizing | Within limits | Block deployment |

**Sources:**
- [CI/CD for Machine Learning: End-to-End Guide on GitHub Actions (Medium, Feb 2026)](https://medium.com/@orbinsunny/ci-cd-for-machine-learning-an-end-to-end-guide-on-github-actions-4c4b95df4025)
- [Implementing CI/CD Pipelines with GitHub Actions for MLOps (Victoria Lo)](https://lo-victoria.com/implementing-cicd-pipelines-with-github-actions-for-mlops)
- [CI/CD for Machine Learning (Made With ML)](https://madewithml.com/courses/mlops/cicd/)
- [Implementing MLOps with GitHub Actions (DEV Community)](https://dev.to/craftworkai/implementing-mlops-with-github-actions-1knm)

---

### 2. Model Versioning and Rollback Strategies

#### 2.1 Model Registry Architecture

A model registry is the central artifact store that tracks every model version with its metadata, lineage, and lifecycle stage. For crypto trading, the registry must track not just the model weights but also the exact training data snapshot, feature pipeline version, and hyperparameters.

**MLflow Model Registry** is the dominant open-source solution (2025-2026). Key capabilities:
- **Version tracking:** Each registered model gets auto-incrementing version numbers.
- **Stage transitions:** Models move through `None -> Staging -> Production -> Archived`.
- **Aliasing:** Named aliases (e.g., `champion`, `challenger`) point to specific versions.
- **Metadata tagging:** Attach Sharpe ratio, backtest period, training data hash.
- **Lineage:** Connect models to exact code versions, prompt configs, evaluation runs, and deployment metadata.

**MLflow 3.0 (2025)** extended the registry to handle generative AI applications and AI agents, with built-in monitoring, automated promotion, and rollback capabilities.

#### 2.2 Versioning Schema for Trading Models

Recommended versioning convention for trading models:

```
{strategy_name}/v{major}.{minor}.{patch}-{data_date}
```

Example: `connors_rsi2/v2.1.0-20260224`

| Component | Meaning | Triggers |
|-----------|---------|----------|
| major | Architecture change (new model type) | Manual promotion |
| minor | Retraining with new data | Automated CT pipeline |
| patch | Hyperparameter tuning | Experiment tracking |
| data_date | Training data cutoff date | Appended automatically |

#### 2.3 Rollback Strategies

**Strategy 1 -- Instant Rollback (Blue/Green):**
- Keep the previous production model loaded in memory alongside the current one.
- On degradation detection, swap traffic instantly (< 1 second).
- Cost: 2x memory/compute for serving infrastructure.

**Strategy 2 -- Automated Rollback on Metric Degradation:**
```python
# Pseudo-code for automated rollback
def check_and_rollback(current_metrics, baseline_metrics):
    if current_metrics['sharpe'] < baseline_metrics['sharpe'] * 0.8:
        # Sharpe dropped more than 20%
        rollback_to_version(baseline_metrics['model_version'])
        alert_team("Model rolled back: Sharpe degradation")
    if current_metrics['max_drawdown'] > 0.15:
        # Drawdown exceeded 15%
        rollback_to_version(baseline_metrics['model_version'])
        alert_team("Model rolled back: Drawdown exceeded threshold")
```

**Strategy 3 -- Gradual Traffic Rollback:**
- Production model receives decreasing traffic share (100% -> 50% -> 0%).
- Previous stable version receives increasing traffic share.
- Rollback duration: 15-60 minutes depending on trading volume.

**Strategy 4 -- Registry-Based Rollback:**
- MLflow aliases make rollback declarative: move the `champion` alias back to the previous version.
- All serving infrastructure points to the `champion` alias, so rollback is a single API call.

```python
import mlflow
client = mlflow.tracking.MlflowClient()

# Rollback: move champion alias to previous version
client.set_registered_model_alias(
    name="connors_rsi2",
    alias="champion",
    version=previous_version
)
```

**Critical principle:** Organizations should automate model registration, promotion, and rollback by integrating the registry with CI/CD pipelines, allowing data scientists to experiment rapidly while ensuring only validated models reach production.

**Sources:**
- [Model Versioning Infrastructure: Managing ML Artifacts at Scale (Introl, 2025)](https://introl.com/blog/model-versioning-infrastructure-mlops-artifact-management-guide-2025)
- [MLflow Model Registry (Official Docs)](https://mlflow.org/docs/latest/ml/model-registry/)
- [How to Build Model Versioning (OneUptime, Jan 2026)](https://oneuptime.com/blog/post/2026-01-30-model-versioning/view)
- [MLflow in 2025: The New Backbone of Enterprise MLOps (Sparity)](https://www.sparity.com/blogs/mlflow-3-0-enterprise-mlops/)
- [How Do You Manage Model Versioning and Rollback in Production? (Medium)](https://medium.com/@sharetonschool/how-do-you-manage-model-versioning-and-rollback-in-production-4cec6166a0f6)

---

### 3. A/B Testing for Trading Strategies in Production

#### 3.1 Why A/B Testing Matters for Trading

Deploying an ML model directly into a production trading environment is high-risk. A model that achieves 0.82 MAP in offline evaluation can fail online due to distribution shift, feedback loops, or training-serving skew -- causing up to 15% accuracy drops. A/B testing provides statistical evidence that a new model is quantifiably better before full deployment.

#### 3.2 A/B Testing Architecture for Trading

**Traffic Splitting Approaches:**

| Approach | Description | Best For |
|----------|-------------|----------|
| Capital-based split | Allocate X% of capital to new strategy | Portfolio managers |
| Symbol-based split | Route specific symbols to new model | Diversified portfolios |
| Time-based split | Alternate time windows between models | Single-asset strategies |
| Shadow + live | New model runs shadow; old model executes | Risk-averse deployment |

**Capital-Based A/B Test Example:**
```
Total Portfolio: $100,000
├── Model A (champion): $90,000 (90% capital)
│   └── Strategy: Connors RSI-2 v2.0
└── Model B (challenger): $10,000 (10% capital)
    └── Strategy: Connors RSI-2 v2.1 (new features)
```

#### 3.3 Statistical Rigor for Trading A/B Tests

Standard A/B testing assumes independent, identically distributed (IID) observations. Trading returns violate this assumption due to autocorrelation, regime dependence, and fat tails. Required adaptations:

- **Minimum sample size:** At least 100 trades per model variant (not page views -- trades).
- **Duration:** Minimum 30 trading days to capture multiple market regimes.
- **Metric selection:** Sharpe ratio (risk-adjusted), not just raw returns.
- **Statistical test:** Welch's t-test on daily returns, or bootstrap confidence intervals.
- **Correction for multiple testing:** Bonferroni or Holm-Bonferroni if testing multiple strategy variants.

**Decision Framework:**
```
IF challenger_sharpe > champion_sharpe * 1.1 (10% improvement)
AND p_value < 0.05
AND max_drawdown_challenger < max_drawdown_champion
THEN promote challenger to champion
ELSE keep champion; archive challenger
```

#### 3.4 Combining Canary with A/B Testing

The recommended deployment sequence combines both strategies:

1. **Canary phase (1-4 hours):** Route 5% of traffic to new model. Monitor for crashes, latency spikes, and error rates. This is a **technical stability** check.
2. **A/B test phase (7-30 days):** If canary passes, expand to 10-20% of traffic. Collect enough trades for statistical significance. This is a **performance quality** check.
3. **Full rollout:** If A/B test shows statistically significant improvement, promote to 100%.

**Sources:**
- [Canary Deployments and A/B Testing for Safer Model Rollouts (Medium)](https://medium.com/@sebuzdugan/day-60-100-canary-deployments-and-a-b-testing-safer-smarter-model-rollouts-d9245042baf9)
- [A/B Testing and Canary Deployments for Models (APXML)](https://apxml.com/courses/advanced-ai-infrastructure-design-optimization/chapter-4-high-performance-model-inference/ab-testing-canary-deployments-models)
- [A/B Testing ML Models in Production (Qwak)](https://www.qwak.com/academy/ab-testing-ml-models)
- [AWS Well-Architected Machine Learning Lens: Deployment Strategies (MLREL-11)](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlrel-11.html)

---

### 4. Shadow Mode / Paper Trading Before Live Deployment

#### 4.1 The Shadow Deployment Pattern

Shadow deployment (also called "dark launching") runs the new model in parallel with the production model on live market data, but only the production model's predictions are executed as real trades. The shadow model's predictions are logged for comparison.

**Architecture:**
```
Live Market Data (WebSocket/REST)
       │
       ├──► Production Model ──► Order Execution (REAL trades)
       │         │
       │         └──► Metrics Logger
       │
       └──► Shadow Model ──► Paper Trading Engine (SIMULATED trades)
                  │
                  └──► Metrics Logger
                            │
                            └──► Comparison Dashboard
```

#### 4.2 Paper Trading Implementation

Paper trading simulates order execution against live market data without risking capital. It is the single most important pre-deployment validation step for trading models.

**What paper trading catches that backtesting misses:**
- **Slippage:** Real order book depth means large orders move the price.
- **Latency effects:** Model predicts "buy" but by execution time, price has moved.
- **Data pipeline issues:** Missing data, delayed feeds, format changes.
- **API rate limits:** Exchange throttling during high-volatility periods.
- **Fill probability:** Limit orders that never fill in real markets.

**Realistic Paper Trading Engine Requirements:**
```python
class PaperTradingEngine:
    def __init__(self):
        self.slippage_model = SlippageModel(basis_points=5)  # 5bps slippage
        self.commission_model = CommissionModel(maker=0.02, taker=0.04)  # %
        self.latency_simulator = LatencySimulator(mean_ms=50, std_ms=20)
        self.fill_probability = FillModel(method='orderbook_depth')

    def simulate_order(self, signal, current_orderbook):
        # Add realistic latency
        delayed_price = self.latency_simulator.apply(current_orderbook)
        # Apply slippage based on order size vs book depth
        fill_price = self.slippage_model.apply(delayed_price, signal.size)
        # Check if order would actually fill
        if not self.fill_probability.would_fill(signal, current_orderbook):
            return OrderResult(status='unfilled')
        # Apply commissions
        net_result = self.commission_model.apply(fill_price, signal.size)
        return OrderResult(status='filled', price=net_result)
```

#### 4.3 Staged Capital Deployment Timeline

Based on practitioner experience with 7+ years of production crypto trading, the recommended progression:

| Phase | Duration | Capital | Purpose | Exit Criteria |
|-------|----------|---------|---------|---------------|
| Shadow mode | 2-4 weeks | $0 | Verify predictions match expectations | Prediction accuracy within 5% of backtest |
| Paper trading | 1-3 months | $0 | Validate execution simulation | Sharpe > 1.0 in paper trading |
| Micro-live | 1-3 months | $1,000 | Learn real execution mechanics | Still profitable after fees/slippage |
| Small-live | 3-6 months | $10,000 | Validate at meaningful scale | Sharpe > 1.0, max DD < 10% |
| Production | Ongoing | $50,000+ | Full deployment | Continuous monitoring |

**Critical rule:** Never skip stages. A model that looks great in backtesting but has not survived 30+ days of paper trading is not ready for live capital.

**Sources:**
- [Machine Learning Models That Actually Work in Crypto Trading (Medium)](https://medium.com/@laostjen/machine-learning-models-that-actually-work-in-crypto-trading-78a6735b5639)
- [Machine Learning in Trading 2025: Smarter Crypto Strategies (DarkBot)](https://darkbot.io/blog/machine-learning-in-trading-2025-smarter-crypto-strategies)
- [Understanding Machine Learning in Crypto Trading: 2025 Guide (3Commas)](https://3commas.io/blog/understanding-machine-learning-algorithms-in-crypt)

---

### 5. Model Monitoring and Alerting (Performance Degradation Detection)

#### 5.1 The Scale of the Problem

A landmark MIT research study examining 32 datasets across four industries revealed that **91% of machine learning models experience degradation over time**. More critically, research on production ML systems found that **41% of critical model degradations went undetected for over a week** when using only traditional monitoring practices.

For crypto trading, undetected model degradation translates directly to capital losses. Monitoring is not optional -- it is the most critical component of production MLOps.

#### 5.2 Three Layers of Monitoring

**Layer 1 -- Infrastructure Monitoring (seconds-level):**
| Metric | Tool | Alert Threshold |
|--------|------|-----------------|
| Inference latency P99 | Prometheus + Grafana | > 100ms |
| Memory usage | Prometheus | > 85% |
| GPU utilization | NVIDIA DCGM | > 95% sustained |
| Error rate | Prometheus | > 0.1% |
| Throughput (QPS) | Prometheus | < 80% of baseline |
| Data pipeline lag | Custom exporter | > 30 seconds |

**Layer 2 -- Data Drift Monitoring (minutes-to-hours level):**

Data drift occurs when the statistical properties of input features change over time. For crypto, this happens constantly due to regime changes, exchange API changes, and market structure evolution.

**Detection methods (Evidently AI provides 20+ built-in methods):**
- **Kolmogorov-Smirnov (KS) test:** Compares distributions; good for continuous features (price, volume).
- **Population Stability Index (PSI):** Industry standard for financial models. PSI > 0.2 = significant drift.
- **Jensen-Shannon divergence:** Symmetric measure; works for categorical and continuous data.
- **Wasserstein distance:** Measures "earth mover's distance" between distributions; robust to outliers.

**Trading-specific drift signals:**
```python
# Example: Monitor for regime change using Evidently
from evidently.metrics import DataDriftTable
from evidently.report import Report

drift_report = Report(metrics=[
    DataDriftTable(
        columns=['btc_return_1h', 'volume_24h', 'funding_rate',
                 'fear_greed_index', 'rsi_14', 'volatility_30d'],
        stattest='ks',           # Kolmogorov-Smirnov test
        stattest_threshold=0.05  # 5% significance level
    )
])

drift_report.run(reference_data=training_window, current_data=live_window)

if drift_report.as_dict()['metrics'][0]['result']['drift_share'] > 0.5:
    alert("CRITICAL: >50% of features drifting -- consider retraining")
```

**Layer 3 -- Model Performance Monitoring (hours-to-days level):**

This is the most important layer for trading, but also the hardest because ground truth (whether a trade was profitable) is only known after position close.

| Metric | Calculation | Alert Condition | Action |
|--------|-------------|-----------------|--------|
| Rolling Sharpe (7d) | annualized(mean/std of daily returns) | < 0.5 | Warning |
| Rolling Sharpe (30d) | Same, 30-day window | < 0.0 | Critical - halt trading |
| Win rate (rolling 50 trades) | wins / total | < 45% | Warning |
| Max drawdown (rolling) | peak-to-trough | > 10% | Critical - reduce position size |
| Prediction confidence | mean(model probability) | Drops > 20% from baseline | Investigate |
| Signal frequency | signals per day | Deviates > 2 std from baseline | Investigate |

#### 5.3 Alerting Architecture

```
Model Predictions ──► Metrics Collector ──► Prometheus
                                                │
                                    ┌───────────┼───────────┐
                                    │           │           │
                                Grafana    AlertManager   PagerDuty
                              (dashboard)  (rules)     (on-call)
                                                │
                                    ┌───────────┼───────────┐
                                    │           │           │
                                 Slack      Email      Auto-Rollback
                              (warnings)  (daily)     (critical)
```

**Alert severity levels for trading:**
- **INFO:** Feature drift detected in non-critical features.
- **WARNING:** Win rate below threshold, Sharpe declining, minor drift in key features. Action: Increase monitoring frequency.
- **CRITICAL:** Max drawdown exceeded, Sharpe negative, majority of features drifting. Action: Reduce position sizes to 50%.
- **EMERGENCY:** Model producing erratic signals, data pipeline broken, exchange API failure. Action: Halt all trading immediately, roll back to last known good model.

**Key finding:** Teams using dedicated ML observability tools (Evidently, WhyLabs, Arize) responded to critical issues **2.7x faster** than those using general-purpose monitoring solutions (Datadog, Prometheus alone).

**Sources:**
- [Model Monitoring for ML in Production: Comprehensive Guide (Evidently AI)](https://www.evidentlyai.com/ml-in-production/model-monitoring)
- [ML Model Monitoring Prevents Model Decay (Krasamo)](https://www.krasamo.com/ml-model-monitoring/)
- [Advanced ML Model Monitoring: Drift Detection and Automated Retraining (Enhanced MLOps)](https://enhancedmlops.com/advanced-ml-model-monitoring-drift-detection-explainability-and-automated-retraining/)
- [Machine Learning Model Monitoring Best Practices (Datadog)](https://www.datadoghq.com/blog/ml-model-monitoring-in-production-best-practices/)
- [How to Build Data Drift Detection (OneUptime, Jan 2026)](https://oneuptime.com/blog/post/2026-01-30-data-drift-detection/view)
- [Evidently AI GitHub (Open-Source ML Observability)](https://github.com/evidentlyai/evidently)

---

### 6. Canary Deployments for Strategy Updates

#### 6.1 Why Canary is Essential for Trading Models

Canary deployment introduces a new model to a small portion of traffic before system-wide rollout. For trading systems, "traffic" translates to either capital allocation or symbol coverage.

ML models are especially suited to canary because they can pass offline validation but fail online due to:
- **Distribution shift:** Live data differs from training data.
- **Feedback loops:** Model predictions influence the data it later trains on (e.g., front-running your own signals).
- **Training-serving skew:** Differences between training feature pipeline and production feature pipeline.

#### 6.2 Canary Architecture for Trading

**Approach 1 -- Capital-Weighted Canary:**
```
Phase 1 (0-4h):   Canary gets 2% of capital ($2,000 of $100,000)
Phase 2 (4-24h):  Canary gets 10% if Phase 1 passes health checks
Phase 3 (1-7d):   Canary gets 25% if Phase 2 performance is acceptable
Phase 4 (7-14d):  Canary gets 50% -- now a formal A/B test
Phase 5 (14d+):   Canary promoted to 100% if statistically significant improvement
```

**Approach 2 -- Symbol-Weighted Canary:**
```
Phase 1: Canary handles 3 low-volume symbols (e.g., DOT, LINK, AVAX)
Phase 2: Canary adds 5 medium-volume symbols (e.g., SOL, ADA, XRP)
Phase 3: Canary handles all symbols except BTC and ETH
Phase 4: Canary handles full portfolio including BTC and ETH
```

#### 6.3 Canary Health Checks

Automated health checks run continuously during canary phases:

```python
def canary_health_check(canary_metrics, baseline_metrics, phase):
    checks = {
        'error_rate': canary_metrics['error_rate'] < 0.01,
        'latency_p99': canary_metrics['latency_p99'] < 100,  # ms
        'prediction_distribution': ks_test(
            canary_metrics['predictions'],
            baseline_metrics['predictions']
        ).pvalue > 0.01,  # Not wildly different
        'signal_frequency': abs(
            canary_metrics['signals_per_hour'] -
            baseline_metrics['signals_per_hour']
        ) / baseline_metrics['signals_per_hour'] < 0.5,  # Within 50%
    }

    if phase >= 2:  # After initial stability check
        checks['sharpe_ratio'] = canary_metrics['sharpe_7d'] > 0
        checks['max_drawdown'] = canary_metrics['max_drawdown'] < 0.10

    if phase >= 3:  # During A/B comparison
        checks['outperforms'] = (
            canary_metrics['sharpe_7d'] > baseline_metrics['sharpe_7d'] * 0.9
        )

    all_passed = all(checks.values())
    if not all_passed:
        failed = [k for k, v in checks.items() if not v]
        trigger_rollback(reason=f"Canary failed checks: {failed}")

    return all_passed
```

#### 6.4 Rollback Triggers

| Trigger | Threshold | Response Time |
|---------|-----------|---------------|
| Error rate spike | > 1% | Immediate (< 1 min) |
| Latency P99 spike | > 200ms | Immediate (< 1 min) |
| Prediction distribution anomaly | KS p < 0.01 | Within 5 min |
| Negative Sharpe (24h rolling) | < 0 | Within 1 hour |
| Max drawdown exceeded | > 8% of canary capital | Immediate |
| No signals generated | 0 signals in 4 hours | Within 30 min |

**Sources:**
- [Canary Deployments and A/B Testing (Medium)](https://medium.com/@sebuzdugan/day-60-100-canary-deployments-and-a-b-testing-safer-smarter-model-rollouts-d9245042baf9)
- [A/B Testing, Canary and Shadow Deployments for ML Models (Qwak/LinkedIn)](https://www.linkedin.com/pulse/ab-testing-canary-shadow-deployments-ml-models-qwak-com)
- [Trade-offs: Canary vs Blue/Green vs Shadow Deployment (SystemOverflow)](https://www.systemoverflow.com/learn/ml-ab-testing/ramp-up-strategies/trade-offs-canary-vs-blue-green-vs-shadow-deployment)

---

### 7. Infrastructure: Cloud vs Local for Crypto ML

#### 7.1 The Latency-Cost Spectrum

True microsecond performance often exceeds **$200,000 annually** including infrastructure, development, and maintenance. Most profitable crypto trading operations use enterprise cloud infrastructure rather than co-location, focusing on strategy quality over pure speed.

| Infrastructure Tier | Latency | Annual Cost | Best For |
|---------------------|---------|-------------|----------|
| Co-located FPGA (Jump Trading style) | < 1 microsecond | > $500K | HFT market making |
| Dedicated bare metal, exchange co-lo | 1-5 ms | $50-200K | Low-frequency HFT |
| Cloud VPS near exchange (AWS Tokyo for Binance) | 5-20 ms | $5-20K | Medium-frequency algos |
| Standard cloud VM (any region) | 20-100 ms | $1-5K | Swing trading, 1h+ timeframes |
| GitHub Actions / serverless | 100-500 ms | $0-1K | Daily signals, scanning |
| Local machine | Variable (ISP-dependent) | $0 + hardware | Development, backtesting |

#### 7.2 Practical Recommendation by Strategy Type

**For strategies operating on 15min+ timeframes (most retail crypto ML):**
- **Cloud VPS** is optimal: AWS t3.medium ($30/month) or Hetzner AX41 ($40/month).
- Latency of 20-100ms is irrelevant when signals change every 15-60 minutes.
- Focus budget on data quality (CoinGecko Pro, CryptoQuant API) rather than infrastructure speed.

**For strategies operating on 1-15min timeframes:**
- **Cloud VPS near exchange** is recommended: AWS Tokyo (ap-northeast-1) for Binance, AWS Virginia for Coinbase.
- Consider dedicated instances (not shared) for consistent latency.
- Budget: $100-500/month.

**For strategies operating on sub-1min timeframes:**
- **Co-located infrastructure** required: Equinix or exchange-provided co-location.
- Custom networking (kernel bypass, DPDK).
- Budget: $5,000-50,000/month.
- Note: This tier is rarely justified for ML-based strategies; the edge usually comes from speed, not prediction quality.

#### 7.3 GitHub Actions as ML Infrastructure

For scanning-type crypto ML systems (like the Alpha Engine in this repo), GitHub Actions provides a surprisingly effective infrastructure:

**Advantages:**
- Zero infrastructure management.
- Built-in scheduling (cron), secret management, and artifact storage.
- Free tier: 2,000 minutes/month for public repos.
- Parallel job execution for multi-strategy scanning.

**Limitations:**
- 6-hour maximum job duration (training large models may not fit).
- No GPU runners on free tier (self-hosted runners needed for deep learning).
- Cold start: ~30-60 seconds for runner provisioning.
- Scheduled workflows not guaranteed exact time.
- Network latency to exchanges is unpredictable.

**Optimal use pattern:**
```yaml
# Good: Periodic scanning, signal generation, data collection
on:
  schedule:
    - cron: '*/30 * * * *'  # Every 30 minutes

# Bad: Real-time trading execution (latency too variable)
```

#### 7.4 Hybrid Architecture (Recommended for This Project)

```
┌─────────────────────────────────────────────────────────┐
│ GitHub Actions (Free Tier)                               │
│ ├── Model training (daily cron, 2 AM UTC)               │
│ ├── Strategy scanning (every 30 min)                    │
│ ├── Signal generation → active_picks.json               │
│ └── Model evaluation and A/B test analysis              │
└─────────────────────┬───────────────────────────────────┘
                      │ Pushes signals to repo
                      ▼
┌─────────────────────────────────────────────────────────┐
│ Cloud VPS ($30-100/month)                                │
│ ├── Signal consumer (watches repo / webhook)            │
│ ├── Order execution engine (low-latency to exchange)    │
│ ├── Paper trading engine (shadow mode)                  │
│ ├── Real-time monitoring (Prometheus + Grafana)         │
│ └── MLflow model registry (local SQLite or Postgres)    │
└─────────────────────┬───────────────────────────────────┘
                      │ Executes trades
                      ▼
┌─────────────────────────────────────────────────────────┐
│ Exchange APIs (Binance, Coinbase, etc.)                  │
└─────────────────────────────────────────────────────────┘
```

**Cost breakdown for this architecture:**
- GitHub Actions: $0 (free tier, public repo)
- Cloud VPS: $30-100/month
- Data APIs (CoinGecko Pro, etc.): $50-200/month
- Domain + dashboard hosting: $5-10/month
- **Total: $85-310/month** -- accessible for individual traders

**Sources:**
- [High-Frequency Trading in Crypto: Latency and Infrastructure (Medium)](https://medium.com/@laostjen/high-frequency-trading-in-crypto-latency-infrastructure-and-reality-594e994132fd)
- [Ultra-Low Latency Crypto Trading on Cloud (Alibaba Cloud)](https://www.alibabacloud.com/blog/a-guide-to-ultra-low-latency-crypto-trading-on-the-cloud-part-1---infrastructure-fundamentals_601851)
- [Optimize Tick-to-Trade Latency for Digital Assets on AWS](https://aws.amazon.com/blogs/web3/optimize-tick-to-trade-latency-for-digital-assets-exchanges-and-trading-platforms-on-aws/)
- [Best VPS for Algorithmic Trading (QuantVPS)](https://www.quantvps.com/blog/best-vps-algorithmic-trading)
- [MLOps for Low-Latency Applications (CloudFactory)](https://www.cloudfactory.com/blog/mlops-for-low-latency)

---

### 8. Model Serving Frameworks for Trading

#### 8.1 Framework Comparison

| Framework | Latency (tree models) | Latency (LSTM/DL) | GPU Support | Auto-scaling | Best For |
|-----------|----------------------|-------------------|-------------|-------------|----------|
| TensorFlow Serving | P50 < 5ms | P50 < 30ms | Yes | Via K8s HPA | TF/Keras models |
| TorchServe | P50 < 5ms | P50 < 30ms | Yes | Via K8s HPA | PyTorch models |
| NVIDIA Triton | P50 < 3ms | P50 < 20ms | Yes (optimized) | Built-in | Multi-framework, GPU |
| KServe (K8s) | P50 < 10ms | P50 < 50ms | Yes | Built-in | K8s-native deployments |
| ONNX Runtime | P50 < 2ms | P50 < 15ms | Yes | Manual | Cross-framework, edge |
| FastAPI + pickle | P50 < 5ms | P50 < 30ms | Manual | Via K8s HPA | Simple deployments |
| Direct Python (no server) | P50 < 1ms | P50 < 10ms | Manual | N/A | GitHub Actions scanning |

#### 8.2 Optimization Techniques

**Model compression for lower latency:**
- **Quantization:** FP32 -> INT8 reduces model size 4x, inference 2-3x faster, < 1% accuracy loss for tree models.
- **Knowledge distillation:** Train a smaller "student" model to mimic the larger "teacher" -- dramatically reduces inference latency.
- **ONNX export:** Convert models to ONNX format for optimized cross-platform inference.
- **Feature store caching:** Pre-compute expensive features (e.g., on-chain metrics) and serve from Redis/DynamoDB.

**For the Alpha Engine's use case (30-minute scanning cycle):**
Direct Python execution within GitHub Actions is sufficient. Model serving infrastructure is only needed when moving to real-time execution (sub-minute signals).

---

## Key Findings Summary (Template Entries)

### System: Kubernetes-Based Model Serving
- **Source:** Two Sigma (internal), public MLOps patterns
- **Architecture:** Models containerized; served via KServe; ingress via gRPC
- **Latency:** P50 < 5ms, P99 < 20ms for tree models; 50ms for LSTM
- **Scalability:** Autoscale based on request rate (HPA)
- **Monitoring:** Prometheus metrics (latency, error rate, QPS); Grafana dashboards; Evidently for drift
- **Innovation:** Model warm-up to avoid cold start latency; automated rollback on Sharpe degradation
- **Weaknesses:** Complexity; requires SRE expertise; overkill for < 1 QPS workloads

### System: Edge Deployment for HFT
- **Source:** Jump Trading, Citadel Securities
- **Architecture:** FPGA-accelerated inference; colocated with exchange matching engine
- **Latency:** < 1 microsecond
- **Use Case:** Ultra-low latency signal generation
- **Weaknesses:** Extremely expensive (>$500K/year); only for top-tier firms; not ML-friendly

### System: GitHub Actions + Cloud VPS Hybrid (Recommended for This Project)
- **Source:** Practitioner community, this research
- **Architecture:** GitHub Actions for training/scanning; Cloud VPS for execution/monitoring
- **Latency:** 100-500ms for signal generation (acceptable for 30min+ strategies)
- **Cost:** $85-310/month total
- **Scalability:** Add more GitHub Actions workflows; upgrade VPS as needed
- **Monitoring:** Evidently for drift detection; custom Sharpe/drawdown alerting
- **Innovation:** Zero-cost training infrastructure; model versioning via git
- **Weaknesses:** Not suitable for sub-minute strategies; GitHub Actions scheduling not exact

### System: Shadow + Canary Progressive Deployment
- **Source:** Industry best practices (AWS ML Lens, Qwak, Evidently AI)
- **Architecture:** Shadow model runs alongside production; canary gets 2-25% capital
- **Validation:** Paper trading (1-3 months) -> Micro-live ($1K, 1-3 months) -> Production
- **Statistical rigor:** Minimum 100 trades per variant; 30+ trading days; Welch's t-test
- **Monitoring:** 91% of ML models degrade over time (MIT study); dedicated ML observability tools respond 2.7x faster
- **Innovation:** Capital-weighted canary phases with automated rollback triggers
- **Weaknesses:** Slow to promote (weeks-months); requires discipline to not skip stages

---

## Actionable Insights for This Project

### Immediate (Week 1)
- [x] Containerize models (Docker) for reproducibility -- *already using GitHub Actions runners*
- [ ] Add model versioning to `active_picks.json` output (include model version, training date)
- [ ] Implement basic drift monitoring: compare last 7 days of feature distributions to training baseline
- [ ] Add Sharpe ratio and max drawdown tracking to Alpha Engine dashboard

### Short-Term (Month 1)
- [ ] Set up MLflow tracking server (local SQLite backend, zero cost)
- [ ] Implement shadow mode: new strategy versions generate signals but don't affect `active_picks.json`
- [ ] Add automated rollback: if 7-day rolling Sharpe < 0, revert to previous strategy parameters
- [ ] Create canary deployment workflow: new strategies start with 2% capital allocation

### Medium-Term (Month 2-3)
- [ ] Deploy Evidently AI for automated drift detection on all feature pipelines
- [ ] Implement A/B testing framework: capital-weighted split between champion and challenger models
- [ ] Set up Prometheus + Grafana monitoring on a $30/month VPS
- [ ] Create automated retraining pipeline triggered by drift alerts

### Long-Term (Month 4-6)
- [ ] Migrate to hybrid architecture: GitHub Actions (training) + Cloud VPS (execution)
- [ ] Implement ONNX model export for faster inference
- [ ] Build feature store for pre-computed on-chain metrics (Redis-backed)
- [ ] Statistical validation framework: require p < 0.05 Sharpe improvement before any promotion

---

## References

### Academic / Research
- MIT study on ML model degradation (91% of models degrade over time)
- Liu et al. 2022, Journal of Financial Economics -- cross-sectional momentum
- Mahmudov & Puell 2018 -- MVRV ratio as valuation metric

### Industry / Practitioner
- [CI/CD for Machine Learning (Made With ML)](https://madewithml.com/courses/mlops/cicd/)
- [MLflow Model Registry (Official)](https://mlflow.org/docs/latest/ml/model-registry/)
- [Evidently AI: Model Monitoring Guide](https://www.evidentlyai.com/ml-in-production/model-monitoring)
- [AWS Well-Architected ML Lens](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/mlrel-11.html)
- [MLOps for Low-Latency Applications (CloudFactory)](https://www.cloudfactory.com/blog/mlops-for-low-latency)
- [Model Versioning Infrastructure (Introl, 2025)](https://introl.com/blog/model-versioning-infrastructure-mlops-artifact-management-guide-2025)
- [MLflow 3.0 Enterprise MLOps (Sparity)](https://www.sparity.com/blogs/mlflow-3-0-enterprise-mlops/)

### Books
- "Building Machine Learning Powered Applications" (Emmanuel Ameisen)
- "Designing Machine Learning Systems" (Chip Huyen, O'Reilly 2022)
- "Machine Learning Design Patterns" (Lakshmanan, Robinson, Munn -- O'Reilly 2020)

### Tools Documentation
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [TensorFlow Serving Guide](https://www.tensorflow.org/tfx/guide/serving)
- [NVIDIA Triton Inference Server](https://developer.nvidia.com/triton-inference-server)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Prometheus Monitoring](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)

---
*Researcher ID: 017* | *Status: Complete* | *Last Updated: 2026-02-24*
