# Asset-Class Smoking-Gun Analysis + High-Conviction Methodology (PR-Ready)

Date: 2026-04-30
Author: GitHub Copilot (GPT-5.3-Codex)
Scope: findtorontoevents.ca/audit performance improvement plan across CRYPTO, FOREX, COMMODITY, EQUITY, ETF, BOND

## Goal Alignment

This report is focused on Goal #1 from project instructions: phenomenal performance on /audit across all asset classes, with Tier 2 as minimum target and Tier 1 as long-run target.

## Evidence Base Used

1. reports/asset_class_independent_recompute_2026_04_27_mercury2_copilot.md
2. reports/action_B_resolver_2026_04_27.md
3. reports/SESSION_WRAP_2026_04_29.md
4. Last-week commit stream (`git log --since="7 days ago"`)

## Smoking-Gun Findings

### 1) Measurement contamination was real and must be fixed before strategy conclusions

- The closed-history publication path in dashboard generation allowed banned rows into recent_closed.
- This contaminates class-level PF/WR/MaxDD interpretation and model feedback loops that rely on dashboard-derived cohorts.
- Immediate fix applied in this session: filter out banned source tiers and banned trust_tier rows before reservation/capping logic.

### 2) Resolver noise dominates FOREX and COMMODITY win labels

From the independent recompute and resolver deep-dive:

- FOREX noise-win share: 63.25%
- COMMODITY noise-win share: 66.79%

Interpretation:

- Current FOREX/COMMODITY WR and PF are partially artifacts of close-time spot drift and ultra-tight outcome thresholding.
- Any class-level optimization for these two classes before resolver hardening is statistically fragile.

### 3) Drawdown, not hit rate, is the current CRYPTO failure mode

- CRYPTO in the recompute had positive aggregate PnL and PF > 1, but MaxDD was catastrophic.
- This is consistent with concentration in high-vol symbols and insufficient per-symbol poison-set suppression.

### 4) EQUITY and ETF show the strongest path to Tier 2 first

- EQUITY/ETF quality is materially better than FOREX/COMMODITY under current data quality constraints.
- Recent commit history includes HC gate tuning for EQUITY and strong documentation pushes around edge isolation.
- UEPS/long_term_value + PEAD wiring exists; the bottleneck is calibration/verification depth, not missing integration.

## Asset-Class Diagnosis and Priority Order

## 1. EQUITY (Priority: Highest near-term upside)

Current signal:

- Best path to stable Tier 2 candidate once HC filters and calibration settle.
- Less affected by resolver noise than FOREX/COMMODITY.

Suggested improvements:

1. Promote EQUITY-specific HC thresholds (already moving via scoreFloor/compound floor tuning) and stop using broad cross-class defaults.
2. Add PEAD quality guardrails:
   - earnings freshness window
   - liquidity floor
   - spread/slippage proxy cap
   - post-earnings gap regime tagging
3. Add long-horizon segmentation dashboard fields:
   - holding-period buckets (1-3d, 4-10d, >10d)
   - gap-adjusted entry quality
   - earnings-event proximity score

Mutation plan (baby strategies + DNA):

- Create PEAD micro-variants with one-axis mutations only:
  - entry delay mutation (T+0 open, T+1 open, VWAP-first-hour)
  - TP/SL ladder mutation (fixed RR vs ATR-adaptive)
  - volatility veto mutation (skip top-decile realized vol)
- Keep each mutation family isolated and report with matched-control cohort.

## 2. ETF (Priority: High)

Current signal:

- Positive edge signs but sample depth still thinner.

Suggested improvements:

1. Reduce concentration risk from single dominant source families.
2. Add source diversity quota for ETF picks in high-conviction feeds.
3. Add ETF-specific market-regime tags:
   - risk-on/risk-off
   - rates-volatility proxy
   - sector concentration cap

Mutation plan:

- Build ETF rotation baby variants:
  - trend-follow + regime filter
  - mean-reversion-on-overshoot only in low-vol regime
  - event-aware variants for macro announcement weeks

## 3. CRYPTO (Priority: High, but risk-first)

Current signal:

- Edge exists, but drawdown makes headline PF operationally unsafe.

Suggested improvements:

1. Hard gate poison symbols with n>10 and WR<30% cohorts.
2. Add volatility-targeted position sizing sidecar in production path (not doc-only).
3. Add drawdown-aware exposure throttles:
   - per-symbol max concurrent exposures
   - class-level kill-switch when rolling MDD exceeds threshold
4. Add slippage-adjusted PnL audit columns for high-vol assets.

Mutation plan:

- CRYPTO DNA should mutate risk controls first, entry logic second.
- Required mutation axes:
  - vol-target multiplier
  - max-hold duration by volatility regime
  - TP compression under adverse volatility expansion

## 4. FOREX (Priority: Blocked until resolver hardening)

Current signal:

- Reported edge is not currently reliable due to resolver-noise contamination.

Suggested improvements:

1. Implement OHLC touch-based exit replay for non-crypto closure logic.
2. Raise non-crypto noise threshold floor from micro-bp to realistic values.
3. Recompute 30-day/90-day metrics after resolver fix, then retune HC thresholds.

Mutation plan:

- Freeze broad FOREX strategy expansion until post-resolver clean baseline.
- Allow only low-risk mutations on already-profitable subfamilies after rebaseline.

## 5. COMMODITY (Priority: Blocked + selective)

Current signal:

- Similar resolver noise issue plus weak sub-classes (agro/oil/silver/gold kills already in recent changes).

Suggested improvements:

1. Keep metals-focused selective cohorts where validated.
2. Avoid broad commodity family relaunch before clean resolver baseline.
3. Add contract-specific liquidity and roll-friction features in scorecards.

Mutation plan:

- Use narrow commodity mutation bands by contract family (no pooled mutation across heterogeneous contracts).

## 6. BOND/FUTURES/UNKNOWN (Priority: Data sufficiency)

Current signal:

- Insufficient sample depth for confidence.

Suggested improvements:

1. Repair/verify routing and taxonomy before optimization.
2. Enforce minimum-n thresholds for any promotion claims.

## Missing Industry-Standard Datapoints (Should be added to /audit)

1. Turnover-adjusted return and implementation shortfall proxy.
2. Tail metrics: CVaR, downside deviation, ulcer index.
3. Exposure concentration metrics:
   - top-symbol contribution
   - top-source contribution
4. Regime-stratified performance:
   - trend/range
   - high/low volatility
5. Time-to-recovery and rolling worst-window stats.
6. Slippage-sensitive PF and WR (stress-adjusted).
7. Capacity flags: liquidity/volume stress on fill assumptions.

## PR Proposal (Implementation Sequence)

### PR A (P0): Data Integrity + Resolver Foundation

- Keep this session's banned-row closed-history fix.
- Add resolver non-crypto OHLC-touch replay and realistic non-crypto thresholding.
- Add post-fix recompute script output artifact.

Acceptance criteria:

1. FOREX/COMMODITY noise-win share materially reduced from current 63-67% zone.
2. No banned source/tier rows published in recent_closed.
3. Recompute outputs produced and versioned.

### PR B (P1): Asset-Class Specific HC Calibration

- Introduce class-specific HC thresholds and rationale fields.
- EQUITY/ETF first, then CRYPTO.

Acceptance criteria:

1. HC pass-rate no longer over-filtered by class.
2. Class-level PF/WR and MDD improve on clean baseline.

### PR C (P1): Mutation Lab for Baby Strategies

- Add controlled mutation harness per class with one-axis mutation sweeps.
- Save per-mutation cohort outputs and promote only with minimum sample thresholds.

Acceptance criteria:

1. Mutation reports include matched-control comparisons.
2. No strategy promotion without minimum-n and drawdown constraints.

## Long-Term Equity / PEAD Verdict

Verdict: Wiring is real and active, but quality is in building/proving phase, not yet "proven edge" at institutional confidence levels.

Implication:

- Treat long-term equity/PEAD as the leading candidate to scale, but keep claims conservative until post-resolver clean baselines and larger sample validation are complete.

## Methodology Standard Going Forward

1. Fix measurement path before changing alpha logic.
2. Recompute independently on dashboard payload after each P0 data-path change.
3. Tune by asset class, never global default first.
4. Use mutation sweeps with single-axis changes and control cohorts.
5. Require minimum-n + drawdown constraints before promotion.

## Immediate Next Actions

1. Merge the recent_closed banned-filter fix and regression test from this session.
2. Open PR A for resolver hardening and rebaseline metrics.
3. Run post-resolver class recompute and update /audit scorecards.
4. Launch class-specific HC calibration for EQUITY and ETF first.
5. Start controlled CRYPTO risk-first mutation sweep.
