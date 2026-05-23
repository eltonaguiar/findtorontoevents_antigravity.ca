# World-Class Signal Provider Benchmarks
## Source: Kimi Deep Research (March 2026)

## Target Metrics for #1 Signal Service

| Metric | Target | Our Current | Status |
|---|---|---|---|
| Win Rate | 65-75% | 66.1% (Keltner BTC, 59 trades) | IN RANGE |
| Risk-Reward | 1:2.5 minimum | 1.3-1.8 avg | BELOW — need wider TPs |
| Sharpe Ratio | >1.4 | Walk-forward validated (p=0.0007) | NEEDS CALCULATION |
| Max Drawdown | <15% | ~5% (battleground) | EXCEEDS TARGET |
| Profit Factor | >1.75 viable, >2.0 strong | 2.5-4.3 (Keltner strategies) | EXCEEDS TARGET |
| ML Filtering Gate | >60% confidence | Heuristic (now fixed to train) | IN PROGRESS |

## The Winning Formula (Signal Composition)

```
World-Class Signals =
    Technical Analysis (30%) → Battleground Keltner/RSI strategies
    On-Chain Analytics (25%) → Alpha Engine MVRV/NVT/Hash Ribbon
    Risk Management (20%) → Portfolio circuit breaker + Kelly sizing
    Sentiment Analysis (15%) → LunarCrush Galaxy Score (Phase 4)
    Machine Learning (10%) → Alpha Engine XGBoost ranker (just fixed)
```

## Industry Benchmarks (Top Providers 2025-2026)

| Provider | Win Rate | Key Strategy |
|---|---|---|
| WallStreet Queen | 88.24% | Multi-timeframe analysis |
| Binance Killers | 85% | Altcoin futures focus |
| Verified Crypto Traders | 86.54% | Multi-strategy approach |
| Industry Average | 73.8% | Mixed strategies |

CRITICAL: Win rate alone is meaningless. Provider A with 80% WR and 1:1 R:R
LOSES money (-$4/trade). Provider B with 55% WR and 3:1 R:R MAKES money (+$60/trade).

## ML Model Performance Benchmarks

| Model Type | Accuracy | Sharpe | Best Use |
|---|---|---|---|
| XGBoost (Gradient Boosting) | 67% | 1.4 | Price prediction |
| Ensemble Methods | 68% | 1.6 | Signal filtering |
| LSTM Networks | 54% | 1.1 | Pattern recognition |

Key insight: Ensemble methods beat complex single models.
Use ML to FILTER signals (confidence >60%) — eliminates ~70% of bad trades.

## Risk Management Standards

- Single trade: 1-2% max risk
- Single asset: 10% max exposure
- Total open risk: 5-10%
- Max drawdown: 20% hard stop (our circuit breaker = 8%, MORE conservative)

## Gaps to Close

1. R:R ratio needs improvement (1.3 avg vs 2.5 target)
   - Action: Widen TPs on proven strategies, especially Keltner
2. Need formal Sharpe ratio calculation on forward-tested trades
3. ML filtering now active but needs first training cycle to verify
4. On-chain strategies (MVRV, NVT) have small sample sizes — need more trades
5. Sentiment (LunarCrush) just added — no forward data yet
6. No third-party verification (MyFXBook equivalent for crypto)

## 12-Month Roadmap to #1

Phase 1 (Months 1-3): Foundation — LARGELY DONE
- Strict risk management (circuit breaker at 8%) ✅
- Signal quality framework (score 0-100 with 25% weights) ✅
- Transparent track record (audit dashboard live) ✅

Phase 2 (Months 4-6): Enhancement — IN PROGRESS
- On-chain analytics (MVRV, NVT, hash ribbon) ✅ deployed
- ML filtering (XGBoost ensemble) ✅ just fixed
- Sentiment analysis (LunarCrush) ✅ just added

Phase 3 (Months 7-12): Excellence — NEXT
- Regime-adaptive strategies (regime_terminal + router exists)
- VIP tiers and API access
- Third-party audit and verification
- Target: 70%+ WR, 1:2.5 R:R, <15% MDD, 1.4+ Sharpe
