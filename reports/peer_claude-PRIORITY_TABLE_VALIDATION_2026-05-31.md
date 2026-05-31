# Peer Priority-Table Validation — 2026-05-31

Cross-references incoming 7-row priority action table against today's 12+ independent verifications (PR #318 chain, PR #330, money_ready_verdict.json 2026-05-24, fresh live SQL 2026-05-31 EST).

## Fresh SQL Verifications (live ejaguiar1_stocks.trading_picks, closed_at NOT NULL)

| Strategy | Direction | n | WR | PF |
|---|---|---|---|---|
| mega_mutation | any | **2** | **0.0%** | **0.00** |
| ml_enhanced_DYDXUSDT | LONG | 63 | 63.5% | 0.31 |
| ml_enhanced_INJUSDT | LONG | 45 | 82.2% | 13.48 |
| ml_enhanced_RENDERUSDT | LONG | 74 | 60.8% | 3.06 |

FOREX direction split:
| Direction | n | WR | PF |
|---|---|---|---|
| LONG | 620 | 41.6% | **7.05** |
| SHORT | 1011 | 46.4% | 1.75 |
| BUY | 22 | 68.2% | 0.73 |

## Per-Row Verdict Table

| Row | Verdict | Reasoning |
|---|---|---|
| P0 COMMODITY hard-disable at emission gate | **ACCEPT_pending_operator** | money_ready 2026-05-24 PF 0.31 n=28 FAIL+INSUFF; 57% CT=F concentration. Operator must approve emission-gate change. |
| P0 EQUITY hard-disable at emission gate | **NEEDS_VERIFY / REJECT_full_disable** | money_ready PF 0.62 / 0.16 INSUFF n=33 conflicts with broader 90d EQUITY cohorts (raw PF up to 3.41 in some windows — cohort definition issue). Recommend tighter per-strategy gate, NOT full class disable. |
| P0 FOREX LONG-only block (block all LONG) | **REJECT** | Live SQL shows FOREX LONG PF=**7.05** (WR 41.6%, n=620) vs SHORT PF=1.75. LONG is the WINNER, not the destroyer. Claim is FACTUALLY INVERTED. If anything, demote SHORT-heavy strats. |
| P1 Document & scale mega_mutation as "only proven edge" | **REJECT** | Fresh SQL: n=2, WR=0%, PF=0. DOESNT_REPRODUCE per PR #318 verifier swarm. The +318% 90d cum on /audit TIER-2 is an arithmetic-sum-not-compound artifact, already flagged. Scaling this is a money-losing move. |
| P1 Let small-n ml_enhanced candidates accumulate to n>=50 | **CONDITIONAL_ACCEPT** | DYDX n=63 PF 0.31 — borderline-bad, do NOT accumulate further without gate. RENDER n=74 PF 3.06 — reasonable but original "PF 6.83" doesn't reproduce. INJ n=45 PF 13.48 WR 82.2% — best candidate but small-n outlier risk. Accumulate-only, NO size-up until n>=100 with LB>0.6. |
| P2 Remove WR<15% PF>5.0 strategies from TIER | **ACCEPT** | Classic statistical outlier artifact (single huge winner masking 85%+ losing trades). Safe cleanup. |
| P2 Deploy undeployed backtested strategies on probation | **NEEDS_OPERATOR_APPROVAL** | Overlaps with wkyapjb3g finding: bt_backtest_trades is 25d stale. Deploying off stale backtest data is risky. Operator must approve + freshness gate. |

## Summary Counts

- P0 accept (pending operator): **1** (COMMODITY)
- P0 needs verify / reject: **2** (EQUITY needs cohort reconciliation; FOREX-LONG-block REJECTED — claim inverted)
- P1 reject: **1** (mega_mutation scale)
- P1 conditional: **1** (ml_enhanced accumulate, no size-up)
- P2 accept: **1** (WR<15%+PF>5 outliers)
- P2 needs operator: **1** (deploy backtested, blocked by stale data)

## Key Fabrications Detected

1. **mega_mutation "only proven edge"** — FALSE. n=2, WR=0%, PF=0 live. The 90d cum % is sum-not-compound.
2. **FOREX LONG is destroyer** — INVERTED. LONG PF=7.05 is the *winner*; SHORT (PF=1.75) is the weaker side.
3. **RENDER PF 6.83 / WR 83%** — DOESNT_REPRODUCE (actual 3.06 / 60.8%).
4. **DYDX "shows promise"** — degraded morning→evening (LB 0.81 → 0.52, now PF 0.31).

## Recommendation for Operator (tomorrow)

- Approve P0 COMMODITY emission-gate disable.
- Approve P2 WR<15%+PF>5 outlier purge.
- **Reject mega_mutation scaling.** Add to fabrication-watch registry.
- **Reject FOREX LONG block.** Re-examine the source table that produced this inverted claim.
- Keep EQUITY at tightened per-strategy gate, not class-disable.
- Let ml_enhanced INJ/DYDX/RENDER accumulate to n>=100 with LB>0.6 gate; do NOT scale.

Source verifications: PR #318 (verifier swarm), PR #330 (evening DYDX), money_ready_verdict.json 2026-05-24, live SQL 2026-05-31 EST.
