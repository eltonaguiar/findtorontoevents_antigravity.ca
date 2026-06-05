# Agent-UPDATES Findings Report — 2026-06-05

## Executive Summary
As of June 5, 2026, the system has **0/9 asset classes** that are "money-ready" for live capital allocation based on the policy-clean production audit. While research-tier data (HF_STATS) shows potential edge in COMMODITY, EQUITY, and ETF, these have not yet passed the strict institutional-grade gates (n≥100, PF≥1.5, WR≥50%, DSR≥0.95, PBO≤0.05).

## 1. Money-Ready Verdict
- **Production Verdict**: 0/9 asset classes are money-ready.
- **Status**: The production `/audit` dashboard is the only source of truth for capital allocation. All other surfaces (Smart Picks, AI tournament, research-tier) are for paper-trading or shadow-pilot purposes only.
- **Key Bottleneck**: The primary constraint is not a lack of strategy edge, but **plumbing and data integrity** (resolver staleness, ghost rows, label pollution).

## 2. Asset Class Performance (HF_STATS Recent Data)
The following table summarizes the research-tier edge (recent data, not yet production-gated):

| Class | n | WR% | PF | Sharpe | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **COMMODITY** | 74 | 54.05 | 2.26 | 5.81 | Strongest edge |
| **EQUITY** | 271 | 52.40 | 1.82 | 3.67 | Strong edge |
| **ETF** | 104 | 58.65 | 1.49 | 2.70 | Marginal |
| **CRYPTO** | 2891 | 44.34 | 1.25 | 1.26 | Kelly-negative (avoid LONG) |
| **FOREX** | 148 | 30.41 | 1.31 | 1.35 | Kelly-negative |
| **BOND** | 12 | 0.5 | 0.66 | -2.72 | No edge |

## 3. Trustworthiness Assessment
- **Marketing vs. Reality**: Many "best picks" or high-WR claims in the system are artifacts of over-fitting, look-ahead bias, or resolver pollution (e.g., phantom wins, mislabeled exits).
- **Trustworthy Indicators**:
    - **Policy-clean net**: The only layer that should drive real-money sizing.
    - **Walk-forward OOS**: Essential for validating edge durability.
    - **n≥100**: Minimum sample size for statistical significance.
- **Untrustworthy Indicators**:
    - **All-time PF**: Often inflated by legacy artifacts (e.g., COT dedup).
    - **Tournament/Shadow PnL**: Useful for paper-learning, but not deployable production edge.
    - **Single-symbol concentration**: Strategies that profit from only one symbol (e.g., CT=F) are fragile and not class-wide edges.

## 4. Recommendations
1. **Do not size** production Smart Picks or policy-clean aggregate books.
2. **Focus on plumbing**: Prioritize resolver hygiene, data integrity, and walk-forward validation over adding new strategies.
3. **Shadow Pilot**: Treat `etf_verified_dual_momentum` as the best candidate for the first money-ready promotion, pending successful forward-pilot results.
4. **Enforce Gates**: Maintain the current threshold freeze and do not promote any class until it passes the canonical Tier-2 gates.
