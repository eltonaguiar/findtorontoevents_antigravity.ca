Use a **pre-registered, hash-locked weekly protocol**: data window, baseline model, tests, thresholds, score mapping, and tie-break are fixed before the run.

### 1) Mechanical 0–3 rubric per focus class

| Hypothesis | Test | Score |
|---|---|---|
| **H1 measurement-error** | Reconciliation error rate + MAPE vs trusted source | 0: bad rows ≤0.5% and MAPE ≤1%; 1: ≤2% or ≤3%; 2: ≤5% or ≤10%; 3: >5% or >10% or unreconciled |
| **H2 backtest-only** | Live IC/Sharpe decay vs backtest | 0: decay ≤20% and live t-stat >2; 1: 20–40% or t 1–2; 2: 40–70% or t 0–1; 3: >70% or sign flip/live t <0 |
| **H3 data-scarcity** | Effective sample size + missingness | 0: N_eff ≥500 and missing ≤5%; 1: 250–500 or 5–15%; 2: 100–250 or 15–30%; 3: <100 or >30% missing |
| **H4 external-signal-quality** | Agreement with independent source + IC + latency | 0: agreement ≥90%, IC ≥0.03, SLA met; 1: 80–90% or IC .015–.03; 2: 60–80% or IC 0–.015; 3: <60%, negative IC, or stale |
| **H5 coverage-gaps** | Uncovered exposure in focus class | 0: ≤5% uncovered; 1: 5–15%; 2: 15–30%; 3: >30% or any key risk bucket >20% uncovered |

Top lever only if top score ≥2; otherwise no new lever.

### 2) Prevent steering

- Scoring is a **deterministic script**, not the builder-agent.
- Scorer receives **no lever roadmap, no intervention names, no expected uplift**.
- Protocol hash is committed before data access.
- Builder only sees final hypothesis score after lock.
- Any override requires reviewer sign-off with reason code.
- Weekly shadow-score by second agent/model; disagreement triggers audit.

### 3) Tie-break minimizing regret

If two hypotheses tie, choose the one with the largest **conservative regret of inaction**:

`R = exposure-weighted PnL-at-risk × lower-bound failure probability − fix cost`

Use lower 80% confidence bound. If still tied, choose the **cheapest reversible fix**. If still tied, prioritize **H1/H5 over H2/H4**, because data integrity and coverage failures can poison all downstream decisions.