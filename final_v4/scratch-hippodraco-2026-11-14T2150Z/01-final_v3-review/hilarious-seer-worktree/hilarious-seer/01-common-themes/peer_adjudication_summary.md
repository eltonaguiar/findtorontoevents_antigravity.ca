# Common Themes — Peer Adjudication Summary

**Date:** 2026-11-14
**Worktree:** hilarious-seer
**Sources:** All 7 worktrees' final_v2 outputs + quant-audit adjudication

---

## How This Differs from childlike-airport's BUGS.md

childlike-airport produced an excellent 14-bug inventory (`final_v3/00_common_themes/BUGS.md`). This file complements it by documenting the **peer disputes that were ADJUDICATED** during the 2026-11-14 audit cycle — cases where peers disagreed and a resolution was reached. These adjudications are binding for all future work.

---

## Adjudication 1: VWAP Mean Reversion Sharpe 3.76 — REJECTED

**Claimant:** childlike-airport (via quant-audit package)
**Claim:** "Regime-Filtered VWAP MR: Sharpe 3.76, PF 1.21, MDD 10%, PBO 0.489, DSR 1.0 — deploy first"

**Refuters:**
- finpredict-v2 SCORECARD: correct Sharpe ~1.18 (t=0.91, p=0.18), intrabar stops PF 0.81, CSCV PBO 0.84–0.97
- finpredict-v3 quant-audit: "12.7% total over ~22 months implies annualized vol of 1.84% at Sharpe 3.76 — impossible at 40% position size in 4h crypto. Fatal annualization unit error."

**Adjudication:** **REJECTED.** The 3.76 claim is a fatal annualization unit error. Real Sharpe ≈1.18. PBO 0.489 alongside DSR 1.0 are internally inconsistent — a 49% probability of backtest overfitting means at best half the apparent edge is selection. The strategy is NOT deployable.

**Impact:** Highest-consequence bug in the repo. An agent reading only the quant-audit package would deploy a refuted strategy.

**Fix:** Verdict files must carry `evidence_hash` + `generated_at`; CI fails when `VALIDATED`/`PROVEN` appears without matching registry entry.

---

## Adjudication 2: ITERATION-005 CRYPTO Trend "PROVEN" — PARTIALLY SUPPORTED BUT MISLABELLED

**Claimant:** finpredict-v1 (original claim)
**Claim:** "Vol-targeted trend: net Sharpe 2.13, t=5.56, CI [1.25,3.25], OOS 2.06→2.33, 10/10 assets positive — PROVEN"

**Refuters:**
- finpredict-v3 quant-audit: "Partially supported but mislabelled. Significance was tested against zero, not against buy-and-hold. B&H of the same 10 assets had Sharpe ≈2.2. TSMOM365 OOS Sharpe 0.57, null p=0.200 on re-run."
- finpredict-v2: "The trend method is the best genuine edge candidate and should be built, but its claim must be restated as 'risk-adjusted vs B&H on drawdown/vol', not 'outperforms B&H'."

**Adjudication:** **DOWNGRADED from "PROVEN" to "BEST CANDIDATE."** The strategy is internally consistent and shows genuine risk-adjusted improvement (maxDD −17% vs B&H −36%), but the t=5.56 tested absolute return > 0, not > benchmark. The window was bull-flattered. PF was mislabeled. It is the best candidate for deployment AFTER benchmark-relative restatement and fresh data.

**Impact:** Prevents deployment of a strategy that underperforms B&H in bull markets while claiming alpha.

**Fix:** Restate all ITERATION-005 claims vs buy-and-hold benchmark. Add survivorship-adjusted universe. Add taker-cost stress.

---

## Adjudication 3: ML Confidence Inverted = Code Bug — FLAGGED AS CAUTION

**Claimant:** Some peers (narrative that confidence inversion is a pure code bug)
**Claim:** "ML confidence is inverted; flip the threshold and results improve"

**Refuters:**
- scratch-hippodraco: "Data/leakage/label issues more often than the model math alone. Gatekeeper leakage default work must be paired with retrain + parity tests before claiming improvement."
- finpredict-v3: "Merge-safe concerns for gatekeeper flip — not ready to merge as a drop-in prod change without engineering work."

**Adjudication:** **CAUTION — DO NOT FLIP WITHOUT RETRAIN.** The confidence inversion may be a symptom of data/leakage/label issues, not a root cause. Flipping thresholds without retraining risks silent LONG defaults and other pathologies. Any gatekeeper change requires: (1) retrain on clean data, (2) bundle parity tests, (3) A/B sleeve behavior validation, (4) test environment mutation checks.

**Impact:** Prevents a potentially destructive "quick fix" that could make the system worse.

**Fix:** Full retrain pipeline with parity tests before any threshold flip.

---

## Adjudication 4: flaxen-hair CRYPTO Production Readiness — INTERNAL CONTRADICTION, VETOED

**Claimant:** flaxen-hair
**Claim A:** `production_enable=true, promotion_ready=true, no blockers` (TRUE_PROFITABILITY_VALIDATED.md)
**Claim B:** `production_enable=false, promotion_ready=false, blocked by pf_drift>30%` (PROFITABLE_APPROACH_PROVEN.md)

**Refuters:**
- scratch-hippodraco: "No asset class is money-ready today under stated thresholds."
- hilarious-seer: "Data layer is 172d stale; forward PF (8.32) is 3x lab PF (2.79) — pf_drift >30% is a genuine overfitting signal."

**Adjudication:** **VETOED.** The same worktree gives contradictory production readiness statuses. Positive drift treated as "confirmation" is statistical malpractice. The mega_mutation MACD+RSI strategy remains a high-risk secondary sleeve only, not primary deployment.

**Impact:** Prevents deployment based on internally inconsistent claims.

---

## Adjudication 5: finpredict-v4 Destructive Fixes — VETOED

**Claimant:** finpredict-v4
**Claim:** Proposed SQL DELETE/UPDATE/INSERT OR REPLACE operations, mass row deletions, unblocking FUTURES/COMMODITY without feed

**Refuters:**
- scratch-hippodraco: "Discard 'unblock now', 'delete rows', 'fabricate rows'. Keep policy + observability + tests + alignment."
- finpredict-v2: Veto list established for destructive fixes.

**Adjudication:** **VETOED.** All destructive SQL operations, mass deletes, row fabrications, and blind unblocks are rejected. Only policy-clean, observability, test-driven, and alignment-focused fixes are accepted.

**Impact:** Prevents data destruction that would destroy audit trails.

---

## Adjudication 6: CRYPTO Stop Fill Slippage — FIXED TODAY (B3)

**Finding:** CRYPTO stop loss realized 2.956% vs planned 1.919% — a 1.54× overshoot totaling +832.4pp against a class total of −837.8pp. One system (`kimi_riseoftheclaw`) accounts for 94% of the leak.

**Resolution:** Fixed today via gap-aware fill in `audit_trail/stop_fill.py`, wired into `universal_pick_resolver._check_tp_sl_intrabar`. Replay tool measures the effect.

**Expected outcome:** Breakeven, not profit. The fix turns an unmeasurable class into a measurable one.

**Impact:** This is the single biggest PnL fix in the repo. It reframes CRYPTO from "anti-skill" to "potentially fixable."

---

## Summary Table: All Adjudications

| # | Dispute | Claim | Verdict | Impact |
|---|---------|-------|---------|--------|
| 1 | VWAP Sharpe 3.76 | childlike-airport: deploy first | **REJECTED** — fatal annualization error | Highest-consequence bug |
| 2 | ITERATION-005 PROVEN | finpredict-v1: proven alpha | **DOWNGRADED** — best candidate, not proven | Prevents B&H underperformance in bull |
| 3 | ML confidence flip | Some peers: flip threshold | **CAUTION** — retrain required first | Prevents destructive quick fix |
| 4 | flaxen-hair CRYPTO ready | flaxen-hair: production_ready=true | **VETOED** — internal contradiction | Prevents inconsistent deployment |
| 5 | Destructive SQL fixes | finpredict-v4: mass deletes/unblocks | **VETOED** — dry-run/archive only | Prevents audit trail destruction |
| 6 | CRYPTO stop fills | Measured: 1.54× overshoot | **FIXED TODAY** — gap-aware fill | Biggest PnL fix in repo |

---

## Cross-Cutting Themes (All Peers Agree After Adjudication)

1. **No asset class is money-ready today** (0/166 cells, 0/9 strategies)
2. **Fix data first** — no gate, benchmark, or PnL claim is trustworthy on broken prices/units/phantoms
3. **Benchmark-relative measurement** — absolute Sharpe in a bull window is beta, not alpha
4. **One clean strategy per class, not 683** — the signal zoo is the enemy
5. **Risk premia are modest** — expect Sharpe 0.3–1.0 net; do not chase PF 10–56 fantasies
6. **Trial counts must be tracked** — every forward test pre-registered with trial ID; pass threshold |t| ≥ 3.5
