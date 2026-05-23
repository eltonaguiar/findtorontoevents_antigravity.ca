# Asset-Class Edge + Drift Diagnosis (Last 5 Populated Hours)

Generated: 2026-04-11 UTC
Inputs:
- `tmp/hourly_5h_assetclass_realized_unrealized.json`
- `tmp/backtest_forward_drift_analysis.json`
- `audit_dashboard/data/dashboard_data.json`

## 1) Where edge is missing right now

### CRYPTO (unstable, negative cluster)
- 2026-04-11 00:00: 11 picks, WR 36.36%, P/L -2.1684%, PF 0.6192
- 2026-04-11 01:00: 12 picks, WR 0.00%, P/L -10.8166%, PF 0.0000
- 2026-04-11 02:00: 11 picks, WR 0.00%, P/L -16.1881%, PF 0.0000
- 2026-04-11 03:00 (unrealized): 2 picks, WR 50.0%, P/L -0.08%, PF 0.1111

Interpretation:
- Short-term CRYPTO edge decayed hard after 23:00 and stayed negative for multiple consecutive hours.
- This is not only win-rate drift; payoff quality collapsed (PF near zero).

### EQUITY (payoff asymmetry failure)
- 2026-04-10 23:00 (unrealized): 8 picks, WR 37.5%, P/L -2.27%, PF 0.5668
- 2026-04-11 02:00 (realized): 4 picks, WR 50.0%, P/L -17.271%, PF 0.3629

Interpretation:
- Even when WR reached 50%, losers were materially larger than winners.
- Edge is weak by expectancy/PF, not just by WR.

### COMMODITY (weak, low sample)
- 2026-04-10 23:00: 6 picks, WR 33.33%, P/L -2.7136%, PF 0.7866

Interpretation:
- Weak edge signal, but sample is too small for strong conclusions.

### FOREX (current strength)
- 2026-04-10 23:00: 19 picks, WR 47.37%, P/L +3.3752%, PF 1.5655
- 2026-04-11 02:00: 25 picks, WR 44.0%, P/L +203.1656%, PF 2.9234

Interpretation:
- FOREX is currently carrying the edge in this horizon.

## 2) Backtest-vs-forward drift status

### Important data quality finding
- `tmp/backtest_forward_drift_analysis.json` has `bt_wr=0` and `bt_n=0` almost everywhere.
- Therefore, its per-strategy `wr_gap` is not reliable as a true backtest-vs-forward measure.

### What is still usable from current data
- The same drift file still identifies forward underperformers by forward WR/PnL (usable for triage):
  - `claude_gainer`: 347 trades, WR 32.0%, P/L -772.12
  - `stocks_competition`: 397 trades, WR 33.0%, P/L -437.67
  - `institutional_picks_engine`: WR 14.3%, P/L -108.82
  - multiple CRYPTO mutation/AI challenge families with WR 0-33% and negative P/L.

### Dashboard-level drift context
- In `audit_dashboard/data/dashboard_data.json`, `forward_degradation.aggregate` reports:
  - source_wr: 42.5
  - realized_wr: 49.2
  - delta_pp: +6.7 (labelled `LIFTING`)
- So aggregate system-level drift is not universally negative, but specific strategy clusters are clearly failing.

## 3) Why edge is disappearing

Most likely contributors (from observed pattern + existing protocol docs):
1. Regime mismatch in CRYPTO around 00:00-02:00 UTC (edge flips from strong to strongly negative).
2. Payoff asymmetry in EQUITY (WR can be acceptable while PF/expectancy fail).
3. Promotion/monitoring still too WR-centric in some flows; insufficient PF/expectancy gating.
4. Drift analysis plumbing issue (missing backtest join) masks true backtest-vs-forward decay per strategy.

## 4) Protocol improvements (priority order)

1. Fix drift telemetry integrity first.
- Rebuild the backtest join used by drift analyzer so `bt_wr` and `bt_n` are populated.
- Block deployment decisions if drift report has null/zero backtest fields for >20% of active strategies.

2. Add hard decay gates for forward promotion/probation.
- Trigger rehab if forward decay > 15pp vs backtest with resolved >= 20.
- Trigger rehab if forward PF < 1.0 over last 20 resolved trades (even if WR >= 45%).
- Trigger rehab if expectancy < 0 over last 20 resolved.

3. Enforce execution realism in backtests.
- Next-bar-open entries only.
- Asset-specific fees/slippage model required in metadata for every run.
- Reject runs lacking cost model metadata.

4. Tighten walk-forward protocol freshness and breadth.
- Purged walk-forward with embargo.
- Refresh cadence <= 7 days.
- Cover >= 3 asset classes for any strategy marketed as multi-asset.

5. Regime-stratified acceptance.
- Require positive expectancy in >= 2 regime buckets (trend/volatility + FGI bucketing).
- For CRYPTO, add hour-of-day regime validation; explicitly test 00:00-03:00 UTC slice.

6. Separate Realized vs Unrealized in gating.
- Use realized trades for pass/fail.
- Keep unrealized metrics as early warning only; do not promote on unrealized edge.

7. Add asset-class-specific gates.
- EQUITY: enforce minimum PF threshold > 1.15 due to observed payoff asymmetry.
- CRYPTO: require both PF and WR stability across at least 2 recent hourly buckets.
- FOREX: keep as active priority but add concentration controls to avoid single-regime overfitting.

## 5) Recommended immediate actions (today)

1. Route CRYPTO underperformers from the drift triage list to rehab (do not kill).
2. Put EQUITY strategies with PF < 1 into probation pending mutation/regime-filter variants.
3. Increase FOREX allocation in paper/test portfolios while monitoring concentration risk.
4. Patch drift report generator to correctly populate backtest baselines, then rerun comparison.

---

Conclusion:
- Missing edge is concentrated in CRYPTO (recent hours) and EQUITY (payoff asymmetry).
- FOREX currently shows strongest live edge.
- Backtest-vs-forward drift machinery needs a data integrity fix before strategy-level decay claims are considered authoritative.