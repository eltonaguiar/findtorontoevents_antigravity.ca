# FINAL V4 — Final Review and Plan

**Worktree:** flaxen-hair_2026-11-14T2304 | **Date:** 2026-11-14T23:04Z | **Repo:** findtorontoevents_antigravity.ca

This is the final review stage, incorporating final_v3 peer reviews, local uncommitted files from the last 24 hours, remote GitHub financial files, SubQ workflow status, and money-maker-readyv2 skill results.

## Bottom Line

**No asset class is established as reliably profitable.** The combined evidence from local final_v3 reports, remote GitHub financial files, source-code audits, and the background review package all converge on the same conclusion: **0/23 profitability hypotheses PROVED**, **0/10 proof score** on actual profitability, and multiple critical measurement defects that invalidate even the apparent positive signals.

### Research Priority (Not Deployment)

| Priority | Asset Class | Basis | Status |
|----------|-------------|-------|--------|
| **Slot 1** | EQUITY | Only class with positive cost margin (3.23×, mean +0.323%, n=738) | Pre-registered benchmark test vs SPY total return |
| **Slot 2** | CRYPTO | Only class with diagnosed fixable defect (kimi_riseoftheclaw stop-fill, 98.8% of class loss) but fix → breakeven (PF≈1.00), not profit | Conditional: fix fills first, then forward-test POSITION horizon n≥100 |
| **Deferred** | ETF, FOREX, COMMODITY, BOND, FUTURES, MUTUAL FUNDS | Blocked by arithmetic or insufficient data | Do not prioritize |

### SubQ Status

**NOT_RUN.** No verifiable SubQ provider invocation, response artifact, or raw request metadata exists. Peer documents referencing SubQ are comparison documents, not verified model output.

### Money-Maker-Ready Status

**NOT MONEY-READY.** All nine asset classes return `sizing_allowed: false` from `readiness.by_class`. Promotion gates default to OFF. The cost gate has fail-open paths. After-cost stamping errors are suppressed.

---

## Files in This Package

| Folder | Contents |
|--------|----------|
| `00_executive_summary/` | This summary + PLAN.md |
| `01_proposed_edits/` | PROPOSED_EDITS.md — 15 specific code edits |
| `02_qa_plan/` | QA_PLAN.md — PnL=0% validation, blank field flags, open/recently closed items, mutual funds + ETFs |
| `03_mutual_fund_etf/` | MF_ETF_PLAN.md — Mutual fund + ETF infrastructure plan |
| `04_risk_management/` | RISK_MANAGEMENT_PLAN.md — Risk management + separate webpage design |
| `05_peer_review_results/` | PEER_REVIEW_RESULTS.md — Subagent cross-check results |

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
| CI workflows failing | 2/2 | Python 3.11 and 3.12 jobs failed |
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
| Add mutual funds as prediction class | Equity risk premium, not signal; structurally untradeable as picks |
| Mine more strategies | 170 ledgers already sampled; 4 pass at 95% vs 8.5 by chance |
| Fix FOREX entries to close 16pp gap | Structural problem; entry timing won't close it |
| Turn on more emitting systems | Sizing disabled everywhere for a reason; emission is the loss source |
| Re-enable push trigger on audit-dashboard.yml | Known cancel-cascade risk (removed 2026-05-19) |

---
