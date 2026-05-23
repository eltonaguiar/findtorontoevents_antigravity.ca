# Audit Dashboard: Evaluation Framework Mapping

Maps our audit dashboard scoring system to the 15 criteria from the
**Comprehensive Framework for Evaluating Trading Prediction Quality** (Kimi Agent review).

## Performance Benchmarks (Industry Standard)

| Metric | Minimum | Good | Excellent | Our Dashboard Usage |
|--------|---------|------|-----------|---------------------|
| Sharpe Ratio | 0.5 | 1.0 | 1.5+ | Not directly computed; PF used as proxy |
| Profit Factor | 1.2 | 1.5 | 2.0+ | `pfScore` in forward component: PF 1.2=47, 1.5=67, 2.0=100 |
| Win Rate | 40% | 50% | 60%+ | `wrScore` in forward component; >80% flagged as suspect |
| Max Drawdown | <40% | <25% | <15% | `recent_max_dd` column; used in strategy health |
| Recovery Factor | 2.0 | 3.0 | 5.0+ | Not tracked |
| Expectancy | >$0 | >$10 | >$50 | `expScore` in forward component |

## Statistical Significance Requirements

| Level | Min Trades | Framework Says | Our Implementation |
|-------|-----------|----------------|-------------------|
| No data | 0 | Not assessable | Trust tier: UNPROVEN (0.10x multiplier) |
| Minimal | 1-4 | Not significant | Trust tier: UNPROVEN (0.15x), fwdScore capped at 30 |
| Basic | 5-29 | Preliminary only | Full forward score computed; no sample bonus |
| Moderate | 30-99 | Basic significance | Full forward score; approaching significance |
| Significant | 100+ | Statistically valid | fwdScore gets 1.1x bonus at 50+ trades |
| **Gap** | — | Framework wants 100+ min | We grant full scoring at 5+; should tighten |

## 15 Criteria Mapping

### A. Performance Verification (Criteria 1-5)

| # | Criterion | What We Track | Score Component | Gap / Priority |
|---|-----------|---------------|-----------------|----------------|
| 1 | **Verified Track Record** | Forward-test results from closed picks per system; win_rate, profit_factor, expectancy from `D.systems` | `forward` (15%) + Trust Tier gating | We track real forward results, not 3rd-party verified. **LOW priority** — we are the system, not evaluating an external provider. |
| 2 | **Statistical Robustness** | WR, PF, expectancy, trade count; health status (healthy/watch/degraded) | `strategy` (25%) + `forward` (15%) | Missing: formal p-value / t-test calculation. **MEDIUM priority** — add t-test to system stats generator. |
| 3 | **Risk Metrics** | `recent_max_dd`, PnL distribution, entry drift penalty | `forward` (15%) + `entryDrift` multiplier | Missing: Sharpe ratio, Calmar ratio, recovery factor. **HIGH priority** — Sharpe is the most-cited benchmark. |
| 4 | **Out-of-Sample Validation** | Walk-forward insight badges (GOLDEN/STRONG/WARNING/DANGER) from `_signalInsight`; backtest vs forward WR comparison | `insightMult` multiplier (0.35x to 1.15x) | Well covered. Walk-forward is our primary validation. **DONE.** |
| 5 | **Market Regime Performance** | Direction bias penalty (bearish/choppy/bullish regime detection); conflict ratio scoring | `dirPenalty` multiplier + `noConflict` (10%) + `consensus` (15%) | Missing: formal regime classification (bull/bear/sideways stats per strategy). **MEDIUM priority.** |

### B. Transparency & Methodology (Criteria 6-9)

| # | Criterion | What We Track | Score Component | Gap / Priority |
|---|-----------|---------------|-----------------|----------------|
| 6 | **Clear Strategy Explanation** | Strategy name shown; insight badge with WR/trade count on hover | Display only (not scored) | Not applicable for scoring — we are the system. Strategy code is open. **N/A.** |
| 7 | **Trade Details Provided** | Entry price, SL, TP, R:R ratio, direction, timeframe, entry type (LIMIT/MARKET) | `signal` (20%) — R:R score + confidence | Well covered. All picks have entry/SL/TP. **DONE.** |
| 8 | **Cost Transparency** | Not applicable — no subscription/fee model | — | **N/A** for our internal system. |
| 9 | **Risk Disclosure** | Tooltips warn about failing strategies; trust tier warnings; meme coin warnings | Display only | **N/A** for scoring; covered in UX. |

### C. Operational Quality (Criteria 10-12)

| # | Criterion | What We Track | Score Component | Gap / Priority |
|---|-----------|---------------|-----------------|----------------|
| 10 | **Signal Delivery** | `freshness` component (age_hours); time decay multiplier; real-time timestamp | `freshness` (15%) + `timeDecay` multiplier | Well covered. Stale picks are aggressively penalized. **DONE.** |
| 11 | **Customer Support** | Not applicable — internal system | — | **N/A.** |
| 12 | **Provider Credentials** | Not applicable — we are the provider | — | **N/A.** |

### D. Red Flag Assessment (Criteria 13-15)

| # | Criterion | What We Track | Score Component | Gap / Priority |
|---|-----------|---------------|-----------------|----------------|
| 13 | **Marketing Tactics** | N/A (internal tool) | — | **N/A.** |
| 14 | **Review Authenticity** | N/A (internal tool) | — | **N/A.** |
| 15 | **Withdrawal/Access** | N/A (internal tool) | — | **N/A.** |

## Statistical Methods Coverage

| Method | Framework Recommendation | Our Status | Priority |
|--------|--------------------------|------------|----------|
| **Monte Carlo Simulation** | Shuffle trade order 1000x, check if 95% of simulations remain profitable | **NOT IMPLEMENTED** | HIGH — would validate that system edge is not sequence-dependent |
| **Bootstrapping** | Resample trades 10,000x with replacement, compute CI for WR/PF/Sharpe/MDD | **NOT IMPLEMENTED** | HIGH — would give confidence intervals on all key metrics |
| **T-Test** | t = mean_return / (stdev / sqrt(n)), require p < 0.05 | **NOT IMPLEMENTED** | MEDIUM — straightforward to add to system stats |
| **Walk-Forward Analysis** | Optimize on period A, test on period B, compare | **IMPLEMENTED** via insight badges (GOLDEN = walk-forward proven) | DONE |
| **Confusion Matrix** | Precision, Recall, F1 for directional predictions | **NOT IMPLEMENTED** | LOW — WR is a simpler proxy for our use case |

## Priority Summary

| Priority | Item | Impact |
|----------|------|--------|
| **HIGH** | Add Sharpe ratio to system stats + forward scoring | Most-cited industry benchmark; currently absent |
| **HIGH** | Monte Carlo simulation for strategy validation | Would prove edge is not luck/sequence-dependent |
| **HIGH** | Bootstrapping for confidence intervals | Would give error bars on WR, PF, MDD claims |
| **MEDIUM** | T-test for statistical significance | Quick win: reject null hypothesis per strategy |
| **MEDIUM** | Tighten min trade threshold (5 -> 30 for full scoring) | Framework says 100+; we currently allow 5+ |
| **MEDIUM** | Formal market regime classification per strategy | Know which strategies work in which conditions |
| **LOW** | Confusion matrix / F1 score | Overkill for current use case |
| **LOW** | Recovery factor (CAGR / MDD) | Nice-to-have alongside Sharpe |

---

*Framework source: trading_prediction_evaluation_framework.md (Kimi Agent Crypto Picks Audit Review)*
*Dashboard: audit_dashboard/template.html — computeScore() function*
*Last updated: 2026-03-15*
