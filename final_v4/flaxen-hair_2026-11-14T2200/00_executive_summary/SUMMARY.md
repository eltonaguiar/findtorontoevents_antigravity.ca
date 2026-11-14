# FINAL V4 — Final Review and Findings

**Worktree:** flaxen-hair_2026-11-14T2200 | **Date:** 2026-11-14T22:00Z | **Repo:** findtorontoevents_antigravity.ca

This is the final review stage, incorporating final_v3 peer reviews, local uncommitted files from the last 24 hours, remote GitHub financial files, SubQ workflow status, and money-maker-readyv2 skill results.

---

## Executive Summary

### Bottom Line

**No asset class is established as reliably profitable.** The combined evidence from local final_v3 reports, remote GitHub financial files, source-code audits, and the background review package all converge on the same conclusion: **0/23 profitability hypotheses PROVED**, **0/10 proof score** on actual profitability, and multiple critical measurement defects that invalidate even the apparent positive signals.

### Research Priority (Not Deployment)

| Priority | Asset Class | Basis | Status |
|----------|-------------|-------|--------|
| **Slot 1** | EQUITY | Only class with positive cost margin (3.23×, mean +0.323%, n=738) but conflicts with official verdict/registry | Pre-registered benchmark test vs SPY total return |
| **Slot 2** | CRYPTO | Only class with diagnosed fixable defect (kimi_riseoftheclaw stop-fill, 98.8% of class loss) but fix → breakeven (PF≈1.00), not profit | Conditional: fix fills first, then forward-test POSITION horizon n≥100 |
| **Deferred** | ETF, FOREX, COMMODITY, BOND, FUTURES, MUTUAL FUNDS | Blocked by arithmetic or insufficient data | Do not prioritize |

### SubQ Status

**NOT_RUN.** No verifiable SubQ provider invocation, response artifact, or raw request metadata exists. Peer documents referencing SubQ are comparison documents, not verified model output. All findings in this review are based on direct source inspection and peer report synthesis, not SubQ output.

### Money-Maker-Ready Status

**NOT MONEY-READY.** All nine asset classes return `sizing_allowed: false` from `readiness.by_class`. Promotion gates (`MONEY_READY_FDR_GATE`, `MONEY_READY_SINGLE_SOURCE_GATE`) default to OFF (`"0"`) in `alpha_engine/money_ready_verdict.py`. The cost gate (`tools/per_class_cost_gate.py`) has fail-open paths for missing/stale evidence. After-cost stamping errors are suppressed in `audit_trail/dashboard_generator.py`.

---

## Coverage and Limitations

- **Local final_v3 reports:** Reviewed common themes, deep-investigation, plan, GHA fixes, asset-class fixes, backtest simulations, SubQ coverage, focus decision, mutual-fund screen, and evidence index.
- **Background review package:** `final_v3/feat-stop-fill-cost-gate-final-v3/` (11 files) — adjudication, scope/coverage, improvement plans, focus decision, mutual-fund screen, SubQ status, evidence index.
- **Remote GitHub:** `final_v3/finpredict` commit `d18adb510ab1` (6 files read), `final_v2`/`final_2026_11_14` at commit `086f410713ecd6cb3feec2735b224670418c0588` (470 Markdown paths, 309 unique Git blob SHAs; selected documents reviewed, not all 309).
- **Local uncommitted files (last 24h):** MARKET_BEATING_REPORT.md, dashboard/live_picks.json, mercury2/data/metrics_report.json, research/profitability/* (23 hypotheses v1-v4), research/asset_class/equity/* (multiple backtest runs).
- **Remote GitHub financial files:** money_ready_verdict.json, pick_summary_stats_48h.json, pick_summary_stats_14d.json — all class verdicts FAIL gates.
- **No tests, backtests, model training, or database writes were run** in this review.
- **No verifiable SubQ invocation** was available.

---

## Files in This Package

```
final_v4/flaxen-hair_2026-11-14T2200/
├── 00_executive_summary/         ← this file
├── 01_common_themes_bugs/        Measurement, gating, exit, and workflow defects
├── 02_local_uncommitted/         Local files from last 24h
├── 03_remote_github/             Remote GitHub financial files and state
├── 04_subq_workflow/             SubQ status: NOT_RUN
├── 05_money_maker_readyv2/       Skill invocation results
├── 06_per_class_profitability/   Per-class assessment matrix
├── 07_proof_assessment/          0/23 hypotheses PROVED breakdown
├── 08_execution_roadmap/         90-day plan with go/no-go criteria
├── 09_risk_management/           Risk rules and emergency stops
└── 10_peer_work_review/          Peer agent synthesis
```

---

## Key Numbers That Matter

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Hypotheses tested | 23 | Across crypto, equity, ETFs, bonds, forex, commodities, futures |
| Hypotheses PROVED | 0 | None survive clean-OOS + effective-N + capital + execution gates |
| Proof score | 0/10 | Actual profitability proof |
| CRYPCO intrabar PF | 0.9196 | Below 1.0 (not profitable) |
| CRYPCO intrabar WR | 0.3587 | Below 50% |
| CRYPCO policy_clean PF | 0.2617 | Severe PF inflation (0.28× factor) |
| ETF WR range across files | 2.22% → 68.42% | 85× spread on same class |
| CRYPCO count range across files | 3,705 → 22,055 | 6× difference |
| Gates failing closed | 0/2 | FDR and single-source gates default OFF |
| CI workflows failing | 2/2 | Python 3.11 and 3.12 jobs failed (run 43644095951) |
| Mutual funds in ledger | 0 | Not a prediction class |

---

## Go / No-Go Decision

**NO-GO for live capital deployment.**

### Conditions to revisit:
1. **Measurement gates pass:** cohort_id, filter hash, source timestamp, row-level denominator reconciled across all reports
2. **Promotion gates fail closed:** MONEY_READY_FDR_GATE and MONEY_READY_SINGLE_SOURCE_GATE enabled and validated
3. **EQUITY pre-registered test:** vs SPY total return, n≥500, OOS Sharpe ≥ SPY Sharpe AND PF ≥ 1.15, stability both halves
4. **CRYPTO post-fix forward test:** POSITION horizon n≥100, PF ≥ 1.3, WR ≥ 55%, after fill fix for kimi_riseoftheclaw
5. **CI failure resolved:** Python 3.11/3.12 test failures diagnosed and fixed

If both EQUITY and CRYPTO fail pre-registered tests, the correct decision is to keep both blocked and preserve a passive benchmark sleeve.

---

## What NOT to Do

| Tempting Action | Why Not |
|-----------------|---------|
| Deploy mega-mutation crypto forward picks | 21/50 reported forward picks may be synthetic/replay; aggregate uses different row sets than per-symbol table |
| Tune commodity COT until it passes | Failed all 4 pre-registered checks; re-fitting = false positives |
| Add mutual funds as prediction class | Equity risk premium, not signal; structurally untradeable as picks (daily NAV, no intraday TP/SL) |
| Mine more strategies | 170 ledgers already sampled; 4 pass at 95% vs 8.5 by chance |
| Fix FOREX entries to close 16pp gap | Structural problem; entry timing won't close it |
| Turn on more emitting systems | Sizing disabled everywhere for a reason; emission is the loss source |
| Re-enable push trigger on audit-dashboard.yml | Known cancel-cascade risk (removed 2026-05-19) |

---
