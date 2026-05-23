# Swarm consult: next-best research/backtest harvest

## Session-state recap (2026-05-13)

After 14 swarm rounds + 10 backtests + 6 merged exec-gate PRs, evidence-based pattern recognition:

### Strategies that WORK (TIER-1 or near)
1. **EQUITY top-5 momentum + VIX<22 filter** — PF 4.55 / Sharpe 1.98 / MDD 16.8% (TIER-1 PF+Sharpe)
2. **ETF sector top-3 + VIX<22 filter** — PF 3.32 / Sharpe 1.68 / MDD 11.8% (TIER-1 PF)
3. **FUTURES TS-momentum long-only** (Moskowitz-Ooi-Pedersen) — Sharpe 0.86 / MDD 6.57% (NEAR-TIER-1 MDD)
4. **WTI-Brent → refiner event** (spread Δ < -$3, hold 10d) — PF 2.26 / Sharpe 1.03 (TIER-2 provisional, n=45)

### Strategies that FAILED
- BOND credit-spread overlay (yfinance price-delta proxy too noisy)
- BOND duration rotation (10y-5y curve never inverted in sample)
- Gasoline → XLP/XLY lag rotation (peak corr at lag 0, not 10-15)
- Donchian + VIX overlay (breakout signal already captures regime)

### Refined pattern
- **Regime-GATE on monthly-rebalance momentum: 4/5 work** (EQUITY×2, ETF×2; Donchian fails)
- **Lead-LAG-correlation strategies: 0/4 work** (gasoline, BOND, Donchian-VIX, WTI-Brent continuous)
- **Event-based threshold strategies: WTI-Brent works**, momentum + threshold sometimes works
- **Free-tier yfinance fundamentals**: structural look-ahead bias (Piotroski F-score backtest invalid)

## Question to engines

Pick the next 3 highest-leverage research/backtest paths from the following candidates. Rank by expected risk-adjusted edge per dev hour. Strict JSON only:

### Candidate paths

**A. LowVol compounders + VIX overlay** — 5th regime-gate test. Already TIER-2 Sharpe 0.88 baseline; does VIX-skip lift to TIER-1?

**B. CRYPTO momentum + BTC-regime overlay** (not BTC strategy itself — apply BTC4h regime as a filter on existing CRYPTO momentum). Analogous to VIX-on-EQUITY pattern.

**C. EQUITY momentum + yield-curve (10y-2y) regime overlay** — second-regime gate variant. 10y-2y goes inverted = recession signal; skip momentum entries during inversion.

**D. WTI-Brent refiner — friction-adjusted backtest + walkforward OOS validation** — already PF 2.26 found; add 10bp/leg friction + 2024-2026 OOS split.

**E. Mining-capex → copper lead** (Thread J from DAILY_IDEAS) — CAT earnings guidance / Baker Hughes rig count → HG=F directional bias. Cross-correlation untested.

**F. China/Hong Kong premium-discount stat-arb** (Thread F) — KWEB vs ADR basket (BABA/JD/PDD) cross-listed pair trade.

**G. Polymarket prediction-market data correlation** (Thread H) — election odds → small-cap risk-on tilt (R) or healthcare bias (D).

**H. EQUITY moving-average crossover + VIX overlay** (50d/200d golden-cross filtered by VIX). Different signal modality than top-5 momentum.

**I. Crypto Bitcoin sentiment funding-rate divergence** — when funding-rate stays positive but BTC drops, take SHORT. Free Binance funding data.

**J. Sector-specific seasonality (Halloween → April rally)** — buy XLY/XLK Oct 31, sell Apr 30. 60y academic edge ("Sell in May").

Return strict JSON ONLY:

```json
{
  "top_3_ranked": [
    {"id": "<A-J>", "rank": <1-3>, "expected_sharpe_lift": <number>,
     "dev_hours": <integer>, "why_now": "<1 sentence>",
     "falsifiability_risk": "<low | medium | high>"}
  ],
  "lowest_value_pick": {"id": "<A-J>", "why_skip": "<1 sentence>"},
  "single_riskiest_to_falsify": "<id + reason>",
  "expected_tier_outcome_for_top_pick": "<TIER-1 | TIER-2 | TIER-3 | NO_EDGE>"
}
```

## Constraints

- Avoid candidates needing paid feeds (no Bloomberg, no Compustat point-in-time)
- Prefer regime-gate paths (per track record: 4/5 hit rate)
- Reject lead-lag-correlation paths unless cross-correlation matrix prep is included
- Prefer ≤8 dev hours per backtest tool

## Bias check

This session has been a 50% swarm hit-rate on projections. Don't fall for "obvious economic theory" claims without falsification design.
