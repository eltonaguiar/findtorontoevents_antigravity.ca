# Pick Quality Analysis

**Source:** `alpha_engine/data/smart_picks.json`

## Overview
- Total picks: 7 (all crypto)
- Regime: NEUTRAL, Fear/Greed: 13 (low)
- Asset classes: 100% crypto, 0% non‑crypto
- Scoring: elite scores range 45‑87, smart scores 49‑74
- Pn: 3‑5 swing picks, 1 scalp pick

## Key Findings
| Symbol | Tier | Smart Score | Elite Score | Pn% | Age (h) | R:R |
|--------|------|-------------|-------------|------|--------|-----|
| ETHUSDT | SCALP | 52 | 87 | -1.52 | 1.6 | 5.1 |
| LINKUSDT | SWING | 49 | 45 | -2.21 | 5.5 | 3.9 |
| INJUSDT | SWING | 74 | 72 | 0.25 | 3.0 | 1.35 |
| TRUUSDT | SWING | 72 | 63 | -1.05 | 5.5 | 2.32 |
| REDUSDT | SWING | 56 | 60 | 3.53 | 5.5 | 1.16 |
| ... (2 more swing picks omitted for brevity) | | | | | | |

- **Negative PnL** on 3 of 5 swing picks and the scalp pick.
- **Elite scores** are modest; only ETHUSDT exceeds 80.
- **Risk‑reward ratios** vary widely; many below 2.0, indicating weak upside vs. stop‑loss.
- **Freshness** is good (≤6 h) but signal confidence is low (most "WATCH" tier).

## Recommendations to Reach Hedge‑Fund Quality
1. **Diversify Asset Classes** – Add equities, futures, ETFs, commodities to reduce crypto‑only bias.
2. **Stricter Quality Gate** – Require elite_score ≥ 80 and R:R ≥ 2.5 before inclusion.
3. **Multi‑Model Ensemble** – Combine directional, momentum, and macro models; require at least 2/3 agreement (currently 2/3 for many picks).
4. **Robust Back‑testing** – Run rolling‑window back‑tests on each strategy; discard any with win‑rate < 55 % or Sharpe < 1.0.
5. **Dynamic Position Sizing** – Scale size by Kelly‑criterion or volatility‑adjusted risk, not flat $ per pick.
6. **Risk Management Layer** – Implement portfolio‑level VaR/ES limits; cap exposure per asset class ≤ 10 % of capital.
7. **Signal Validation** – Use out‑of‑sample validation (e.g., walk‑forward) before marking a pick as "validated_score".
8. **Feature Enrichment** – Incorporate macro indicators (interest rates, CPI) and cross‑asset correlation to filter noisy crypto signals.
9. **Transparency & Explainability** – Store full rationale (model weights, feature importance) for each pick to aid audit and compliance.
10. **Continuous Monitoring** – Deploy a real‑time health dashboard (drawdown, turnover) and automatically prune under‑performing strategies.

## Next Steps
- Implement the above quality‑gate thresholds in `alpha_engine/smart_picks_engine.py`.
- Add non‑crypto data pipelines (e.g., `alpha_engine/equity_strategies.py`).
- Create a back‑testing harness (`tools/backtest_equity_catalyst_momentum.py`).
- Generate a weekly audit report summarising portfolio metrics.

*Prepared by Kilo – analysis of current picks and roadmap to hedge‑fund level quality.*