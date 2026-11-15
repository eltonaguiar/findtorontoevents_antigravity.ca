# Finpredict Summary — 2026-11-15

## Approach Overview

Forensic, multi-agent audit of the finpredict project's multi-year attempts to build a profitable trading system across all asset classes (stocks, crypto, forex, bonds, ETFs, commodities, mutual funds). The project has consistently failed to produce statistically valid, benchmark-beating edges.

## Core Finding

**No asset class has shown proven alpha** after clean out-of-sample testing. 0/23 hypotheses survived peer final review. Repeated contamination bugs (TIME_EXIT forging, stale prices, direction-sign mismatches, non-unique IDs, ghost/duplicate rows) contaminated every verdict.

## Asset-Class Results (OOS last-40%, weekly, 10bp costs, wealth gate vs same-asset B&H)

| Asset | Sharpe (vs B&H) | Final wealth (vs B&H) | Proof gates | Verdict |
|-------|-----------------|----------------------|-------------|---------|
| BTC sma200 | 0.57 vs 0.46 | **1.94 vs 1.67** | 0/11 | PROMISING (wealth beat; not protocol-proven) |
| GLD sma200 | 1.14 vs 0.93 | 2.12 vs 2.01 (window-sensitive) | 0/11 | window-sensitive; re-run w/ 1% margin |
| SPY/QQQ/VTI sma200 | better | **lose wealth** | 0/11 | REJECT (DD overlay only) |
| TLT/BND sma200 | negative | lose wealth | N/A | REJECT |
| IWM sma200 | 0.31 vs 0.49 | lose wealth | N/A | REJECT |
| ETH sma200 | 0.28 vs 0.29 | wins wealth but fails Sharpe | N/A | REJECT |
| FOREX | | WR 6.82% / DSR fail | N/A | REJECT |
| COT 93.8% claim | — | contaminated (post-dedup WR~40% PF~0.17) | REJECT |

## Proof Standard (10 gates, non-negotiable)

1. Temporal discipline 2. Walk-forward optimization 3. Multiple-testing correction (Bonferroni/Holm, deflated Sharpe, White's RC) 4. Monte Carlo block-bootstrap 5. Full friction model (spread/commission/slippage/funding/tax; breakeven) 6. Bootstrap CI for excess return excluding zero + t-stat + p 7. Regime robustness 8. Shuffle control 9. Pre-registered forward test 10. Reproducibility.

## Recommendation

- Keep paper-trading adapter (`faber_model_emitter`) as paper-only plumbing.
- Do not enable live emission (NO-GO).
- Run full proof-protocol on BTC sma200 (only wealth-beating candidate).
- If nothing passes, pivot audit dashboard to a rule-based passive allocation strategy with explicit benchmark.

## Files in This Folder

- Summary.MD (this)
- harvested_ideas/ (00_inventory.csv, 01_failures_taxonomy.md, 02_methods_catalogue.md)
- Plan/{equities,crypto,forex,bonds}/PLAN.md
- AUDIT_REPORT.md
- STRATEGY_SHORTLIST.md
- SINGLE_AGENT_PROMPT.md
- negative_result_diagnosis.md
