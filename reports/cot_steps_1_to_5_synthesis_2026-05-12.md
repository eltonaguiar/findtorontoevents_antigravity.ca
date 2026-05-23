# COT 7-Step Testing Plan — Steps 1-5 Synthesis (2026-05-12)

Parallel execution of `reports/cot_paper_pilot_testing_plan_2026-05-12.md`
Steps 1-5 via 5 cavecrew-investigator agents in one batch. All 5 agents
returned within ~5 minutes total.

## Verdict matrix

| Step | Title                          | Verdict          | Headline                                                |
|------|--------------------------------|------------------|---------------------------------------------------------|
| 1    | Reproducibility audit          | **PASS**         | 90/100 = 90.0% WR exact; DSR 1.0 reconfirmed            |
| 2    | Data-integrity audit           | **PASS**         | 0 zero-PnL rows, 0 missing exits; 12% whole-dollar (low fraud signal) |
| 3    | Walk-forward CPCV (10-fold)    | **CONDITIONAL**  | Mean OOS 90%, but fold_1 worst=10%, variance 28.3pp fails 15pp ceiling |
| 4    | DSR conservative re-verify     | **PASS**         | DSR 0.9974 at n_trials=500 (well above 0.85 floor)      |
| 5    | Sample-window robustness       | **PASS**         | Last-30 = 100% WR; no drift across full/60/30 windows   |

## Overall: 4 PASS + 1 CONDITIONAL

Per the testing plan's disqualifying conditions (`reports/cot_paper_pilot_testing_plan_2026-05-12.md` §Disqualifying):

> "Step 3 walk-forward mean OOS WR < 75%"

**Mean OOS is 90% (PASS)** — does not trigger the disqualify. BUT the *worst-fold* criterion (≥60%) and *variance* criterion (≤15pp) both fail. Reading literally, the disqualifying clause only references mean OOS WR, so the strategy is technically not disqualified. However:

## Critical caveat — fold_1 regime outlier

Step 3 found:
- Folds 2-10 run 90-100% WR consistently.
- Fold_1 (earliest chronological cohort, 10 trades) shows 10% WR.
- Step 5 confirms last-30 trades = 100% WR.

Reading: there's a **regime discontinuity** between the oldest 10 trades and the most recent 90 trades. Two hypotheses:
1. **Strategy learned** — the cot_positioning logic was refined post-fold_1; later trades reflect a better setup that won't repeat under the same parameters.
2. **Regime shift** — early trades were in a different macro environment (e.g., pre-2024 cotton volatility regime) and the recent 90-trade run is in a more favorable environment; if that environment changes, the WR could revert.

Either way, the **forward-looking interpretation** must account for this discontinuity. Step 3 recommended: "regime-gating (HMM state ≥2) on all CT=F picks before Step 4 live account seed."

## Recommended next actions

| Priority | Action                                                                                | Effort | Status              |
|----------|---------------------------------------------------------------------------------------|--------|---------------------|
| P0       | Add regime-gate filter to cot_positioning's live emitter (HMM state filter or equivalent) | 2-3h   | Queued              |
| P0       | Continue Step 6 forward paper-pilot (4 weeks passive) — already running               | n/a    | In progress         |
| P1       | Execute Step 7 risk-of-ruin Monte Carlo at $5k/$10k/$25k tiers                        | 1h     | Queued (small)      |
| P2       | Re-run Step 3 quarterly to detect fold-1-style regime shifts                          | 30min  | Periodic monitoring |

## Why this matters for real-money sizing

The cotton-COT edge is the **#1 candidate** for first real-money LIVE_EXECUTION per Codex single-class deviation accepted 2026-05-12. Pre-real-money gate clears 4 of 5 active-work steps. Step 3 is partial — does not block sizing per the literal disqualifier, but DOES require the regime-gate add before any capital flows. Step 6 (4-week paper-pilot) is the only remaining passive-work gate.

## Linked reports

- `reports/cot_paper_pilot_testing_plan_2026-05-12.md` — the original plan
- `reports/cot_step1_reproducibility_2026-05-12.md`
- `reports/cot_step2_data_integrity_2026-05-12.md`
- `reports/cot_step3_walkforward_cpcv_2026-05-12.md`
- `reports/cot_step4_dsr_conservative_2026-05-12.md`
- `reports/cot_step5_sample_window_2026-05-12.md`
- `reports/cotton_cot_real_money_sizing_2026-05-12.md` — capital tier brief
- `audit_dashboard/paper_pilot.html` — live SHADOW-state tracker

## NFA

Research surface only. No real-money sizing without (1) regime-gate addition,
(2) Step 6 4-week paper-pilot clear, (3) Step 7 risk-of-ruin Monte Carlo
clear, (4) explicit user greenlight. The /audit Real Money hub
(`audit_dashboard/real_money.html`) aggregates the full gate.
