# Quant-Driven Roadmap: 12 Steps to World-Class Crypto Prediction

Source: User research compilation (2026-04-06)
Reference for all agents working on scoring/prediction improvements.

## Quick Checklist (Priority Implementation Order)

1. Data pipeline & versioning (Day 1-7)
2. Baseline statistical filters + performance audit (Day 8-14)
3. Feature store & first ML model (XGBoost) (Day 15-30)
4. Walk-forward backtest framework (Day 31-45)
5. Risk-budget engine (Day 46-60)
6. Live monitoring & alerts (Day 61-75)
7. Governance docs & public methodology (Day 76-90)

## Current Status vs Blueprint

| Step | Blueprint | Our Status |
|------|-----------|------------|
| 1. Diagnose | Data + perf + infra audit | DONE (this session: 3485 closed picks audited) |
| 2. Data Pipeline | Clean feeds, normalize, feature store | PARTIAL (Binance+CoinGecko, no InfluxDB/DVC) |
| 3. Signal Framework | TP/SL methodology, risk budget | DONE (ATR-based, per-portfolio risk rules) |
| 4. Feature Engineering | Tech + on-chain + sentiment + cross-asset | PARTIAL (120+ strategies but ML features sparse) |
| 5. Model Development | Baseline→ML→ensemble | PARTIAL (logistic reg exists, 1/46 features active) |
| 6. Backtesting | Walk-forward, realistic slippage | PARTIAL (parameter sweep done, full framework pending) |
| 7. Performance Scoring | Sharpe/Sortino/Calmar/PF scorecard | PARTIAL (PF computed, Sharpe in sweep, no Calmar) |
| 8. Risk Management | Dynamic sizing, portfolio caps | PARTIAL (per-trade risk, no portfolio-level optimization) |
| 9. Monitoring | Live dashboard, drift detection | PARTIAL (dashboard exists, no Prometheus/drift alerts) |
| 10. Governance | Methodology page, audit | PARTIAL (SCORING_ROADMAP_2026-04-06.md published) |
| 11. User Enhancements | Signal UI, historical view | DONE (findtorontoevents.ca/audit) |
| 12. Iteration | Feedback loop, A/B testing | IN PROGRESS (multi-agent feedback loop active) |

## Key Metrics Targets

| Metric | Target | Current |
|--------|--------|---------|
| Sharpe | > 1.0 | ~2.95 (but may include FETUSDT concentration) |
| Win Rate | > 55% | 41.7% overall, 73.4% on filtered (ml>=60) |
| Profit Factor | > 1.5 | 0.90 (PF<1.0 = SL too tight) |
| Max Drawdown | < 20% | Unknown (not tracked per-portfolio) |
| Confidence Calibration (Brier) | < 0.1 | Not measured yet |

See full blueprint in user message 2026-04-06T03:30Z.
