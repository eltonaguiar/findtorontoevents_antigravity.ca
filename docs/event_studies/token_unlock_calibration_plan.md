# Event-Study Calibration Plan — Token Unlock Strategy

**Status:** S0→S1 gate. Mandatory per Strategy Factory v1.1 §6.
**Companion hypothesis:** `docs/hypotheses/token_unlock_event_driven.md`

## 1. Event Sample

- **Lookback window:** 2023-01-01 → current minus 30 days (settle time for
  post-event returns).
- **Target sample size:** n ≥ 30 events per cohort (see §3).
- **Cohorts:**
  1. Large investor-tier unlocks (>5% float) → expected short edge.
  2. Small investor-tier unlocks (<2% float) → expected relief-bounce long.
  3. Team-tier unlocks (any size) → asymmetry test vs cohort 1.
  4. Airdrop / TGE events → separate regime; tested but not traded in v1.
- **Exclusions:** events overlapping (< 7d apart on same asset); events
  during Fed-day / CPI-day (macro contamination).

## 2. Event Window & Return Computation

- **Estimation window:** T-90d to T-7d (build normal-return model).
- **Event window:** T-72h to T+72h in 1h bars.
- **Abnormal return (AR):**
  `AR_t = r_asset_t - beta * r_BTC_t - alpha_hat`
  where `alpha_hat, beta` are OLS-fit over the estimation window.
- **CAR:** sum of AR across window slices:
  - Pre-emption slice: T-7d to T-72h
  - Entry slice: T-72h to T+0
  - Post slice: T+0 to T+24h
  - Tail slice: T+24h to T+72h

## 3. Statistical Tests

Per v1.1 §6, edge is declared real only if ALL hold:

1. **Bootstrap CI:** 10,000 resamples (with replacement) of event CARs;
   95% CI on mean CAR excludes zero. `p < 0.05` (two-sided).
2. **Pre-emption gate:** `|CAR(T-7d..T-72h)| / |CAR(T-7d..T+24h)| < 0.30`.
   If ≥ 30%, retail enters after the move; kill cohort.
3. **Liquidity survival:** split events by median 30d ADV; edge must hold
   (p < 0.10) on below-median subsample. If edge only exists in top-
   liquidity half, accept; if only in bottom half, reject (execution risk).
4. **Sign consistency:** ≥ 60% of individual events directionally agree
   with cohort mean (binomial test vs 0.5, p < 0.05).
5. **Cross-validation:** split sample chronologically 70/30; edge on
   holdout must not flip sign.

## 4. Variance & Sizing Analysis

- Report σ(CAR) per cohort and implied event-level Sharpe
  (`mean / σ * sqrt(n)`).
- Require event-level Sharpe ≥ 0.8 after 2bp round-trip cost assumption
  (perp taker fee + funding slippage estimate).
- If Sharpe 0.5-0.8 → cohort downgraded to size-at-half.
- If Sharpe < 0.5 → cohort killed.

## 5. Pre-Emption Forensics

For any cohort passing gates, additionally report:
- Mean time-of-max-adverse-excursion within entry window (is T-72h optimal,
  or should entry be T-48h / T-24h?)
- Correlation of CAR with: (a) unlock-size-as-%-float, (b) 30d prior return,
  (c) perp funding at T-72h, (d) market regime (BTC 30d vol bucket).
  These become S2 feature candidates.

## 6. Deliverable Format

`tools/backtest_token_unlock.py` emits `artifacts/event_studies/token_unlock_<date>.json`
containing:
- per-cohort: n, mean CAR, bootstrap CI, p-value, pre-emption ratio,
  liquidity-split p-value, sign-consistency %, holdout sign.
- per-event: asset, unlock_ts, size_pct_float, category, CAR slices.
- decision: `PASS` / `DOWNGRADE` / `KILL` per cohort, with reason codes.

## 7. S1 Promotion Rule

At least ONE cohort must PASS for the strategy to advance to S1
(feature engineering + walk-forward design). If all cohorts KILL,
archive hypothesis under `docs/hypotheses/archive/` with autopsy note.
