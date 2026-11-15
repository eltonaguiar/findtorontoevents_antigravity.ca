# Summary.MD — Living Document

**Worktree:** scratch-hippodraco  
**Folder:** WIRED_IN/2026-11-15_0700_scratch-hippodraco/  
**Created:** 2026-11-15T07:00Z UTC  
**Last Updated:** 2026-11-15T07:00Z UTC  
**Status:** Phase 2 — Repo Mining Complete, Phase 3 — Peer Review Complete

---

## 1. Executive Summary

This document is the living record of the quantitative research audit of the findtorontoevents_antigravity.ca repository. Every decision, finding, and artifact is recorded here first and updated at the end of every phase.

**Current state:** No asset class in this repository has been proven profitable under the §6 proof standard. The repository contains ~5,758 Python files, 29 Pine scripts, and extensive audit/ML infrastructure, but all strategies fail one or more proof gates (PF≥1.5, WR≥50%, MDD≤20%, n≥100, cost-adjusted, OOS verified).

## 2. Protocol Compliance Checklist

| Section | Requirement | Status |
|---------|-------------|--------|
| §1 | Workspace protocol — WIRED_IN/<timestamp>_<unique-id>/ created | ✅ DONE |
| §1 | Summary.MD created FIRST | ✅ DONE |
| §2 | Layer A — Regex archaeology across whole repo | ✅ DONE |
| §2 | Layer B — Semantic mapping of flagged files | ✅ DONE |
| §2 | harvested_ideas/00_inventory.csv | ✅ DONE |
| §2 | harvested_ideas/01_failures_taxonomy.md | ✅ DONE |
| §2 | harvested_ideas/02_methods_catalogue.md | ✅ DONE |
| §2 | One .md per asset class in harvested_ideas/ | ✅ DONE |
| §3 | Plan/<asset_class>/PLAN.md per new experiment | ✅ DONE |
| §4 | tracker/predictions_tracker.csv + HTML viewer | ✅ DONE |
| §6 | Proof standard (10 gates) applied to every candidate | ⏳ PENDING |
| §7 | Final Summary.MD update + push to remote | ⏳ PENDING |

---

## 3. Repository Context (Initial Scan)

**Repository:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/  
**Live dashboard:** https://findtorontoevents.ca/audit  
**Strategy history page:** https://findtorontoevents.ca/updates/index.html (3.9MB)

### Key File Groups Identified

| Category | Path(s) | Status |
|----------|---------|--------|
| Alpha Engine core | `alpha_engine/` | ~5,758 Python files |
| Baby strategies | `baby_strategies/` | Multiple per-asset strategies |
| ML models | `ml_battleground/`, `ml_crypto_predictor/` | Crypto-focused mostly |
| Backtest framework | `incubator/backtest_framework.py`, `alpha_engine/backtest/` | Multiple backtesters |
| Quant lab | `incubator/` | Combinatorial backtester, permutation portfolio |
| Audit dashboard | `audit_dashboard/` | Dashboard data JSONs, HTML pages |
| Money-maker skills | `.claude/skills/money-maker-ready*` | v1, v2, June11, July11 editions |
| Peer reviews | `reports/peer_claude-phase10b-money-maker-*` | Per-asset-class peer reviews |
| Kimi agent | `kimi_claw_pro.pine`, `deploy_kimis_claw_production.py` | Pine Script + Python deploy |
| Audit trail | `audit_trail/` | Resolver, dashboard generator, quality gates |
| Tools | `tools/` | Various utilities including backtest, sync, freshness |

### Known Problem Areas (from prior audits)

| Issue | Evidence | Impact |
|-------|----------|--------|
| 851 active picks with no `current_price` | dashboard_data.json inspection | Shows as 0% PnL, corrupts aggregates |
| 25.5% of EQUITY picks have pnl_pct=0 | money_ready_verdict.json | Dilutes WR/PF |
| CRYPTO has genuine negative expectancy | 61.4% negative picks | Strategy issue, not data issue |
| No class passes all T2 gates | money_ready_verdict.json | n<100, PF<1.5, WR<50% for most |
| No walk-forward OOS validation on any strategy | Prior audit findings | Cannot prove edge |

---

## 4. Phase Plan

| Phase | Task | Deliverable | Status |
|-------|------|-------------|--------|
| 1 | Workspace setup + Summary.MD | `WIRED_IN/2026-11-15_0700_scratch-hippodraco/` | ✅ DONE |
| 2 | Layer A — Regex archaeology | `harvested_ideas/00_inventory.csv` | ✅ DONE |
| 3 | Layer B — Semantic mapping | `harvested_ideas/00_inventory.csv` | ✅ DONE |
| 4 | Failure taxonomy + methods catalogue | `harvested_ideas/01_failures_taxonomy.md`, `02_methods_catalogue.md` | ✅ DONE |
| 5 | Per-asset-class MD files | `harvested_ideas/{stocks,crypto,forex,bonds,etfs,mutual_funds,multi_asset}.md` | ✅ DONE |
| 6 | Per-asset-class PLAN.md files | `Plan/<asset_class>/PLAN.md` | ✅ DONE |
| 7 | Prediction tracker | `tracker/predictions_tracker.csv` + HTML viewer | ✅ DONE |
| 8 | Experiments + proof validation | `experiments/`, `proof/` | ⏳ PENDING |
| 9 | Final Summary.MD + commit | `Summary.MD` (finalized) | ⏳ PENDING |

---

## 5. Key Decisions Log

| # | Decision | Rationale | Timestamp |
|---|----------|-----------|-----------|
| 1 | Workspace name: `2026-11-15_0700_scratch-hippodraco` | Follows protocol: UTC timestamp + worktree name | 2026-11-15T07:00Z |
| 2 | Asset classes for analysis: EQUITY, CRYPTO, FOREX, BONDS, ETFs, MUTUAL_FUNDS, MULTI_ASSET | Covers all classes in repo | 2026-11-15T07:00Z |
| 3 | Primary candidate: EQUITY (highest WR at 59.2%) | Best starting point despite PF<1.5 | 2026-11-15T07:00Z |
| 4 | Secondary candidate: ETF (cleanest OOS profile historically) | n=45, needs expansion | 2026-11-15T07:00Z |
| 5 | CRYPTO blocked: Needs OHLCV backfill ≥180 days 1h | Intrabar truth gap (26.4% false TP_HITs) | 2026-11-15T07:00Z |
| 6 | FOREX blocked: Drift alert active (KS_D=6.6×) | Do not unblock while drift alert TRUE | 2026-11-15T07:00Z |
| 7 | BOND/COMMODITY/FUTURES/BOND blocked: n too small, no real feed | Structural blockers | 2026-11-15T07:00Z |
| 8 | MUTUAL_FUNDS blocked: Not a class (class id -1) | Not a prediction target; allocation only | 2026-11-15T07:00Z |

---

## 6. Key Decisions Log

| # | Decision | Rationale | Timestamp |
|---|----------|-----------|-----------|
| 1 | Workspace name: `2026-11-15_0700_scratch-hippodraco` | Follows protocol: UTC timestamp + worktree name | 2026-11-15T07:00Z |
| 2 | Asset classes for analysis: EQUITY, CRYPTO, FOREX, BONDS, ETFs, MUTUAL_FUNDS, MULTI_ASSET | Covers all classes in repo | 2026-11-15T07:00Z |
| 3 | Primary candidate: EQUITY (highest WR at 59.2%) | Best starting point despite PF<1.5 | 2026-11-15T07:00Z |
| 4 | Secondary candidate: ETF (cleanest OOS profile historically) | n=45, needs expansion | 2026-11-15T07:00Z |
| 5 | CRYPTO blocked: Needs OHLCV backfill ≥180 days 1h | Intrabar truth gap (26.4% false TP_HITs) | 2026-11-15T07:00Z |
| 6 | FOREX blocked: Drift alert active (KS_D=6.6×) | Do not unblock while drift alert TRUE | 2026-11-15T07:00Z |
| 7 | BOND/COMMODITY/FUTURES/BOND blocked: n too small, no real feed | Structural blockers | 2026-11-15T07:00Z |
| 8 | MUTUAL_FUNDS blocked: Not a class (class id -1) | Not a prediction target; allocation only | 2026-11-15T07:00Z |

---

## 7. Key Findings from Repo Mining

### Asset Class Verdicts

| Asset Class | n | WR | PF | MDD | Verdict | Primary Blocker |
|-------------|-----|-----|-----|-----|---------|-----------------|
| EQUITY | 250 | 59.2% | 0.94 | 33.04% | NOT_READY | PF < 1.5; MDD > 20% |
| CRYPTO | 3,705 | 35.87% | 0.92 | N/A | NOT_READY | WR < 50%; PF < 1.5 |
| FOREX | 612 | 32.2% | 0.66 | N/A | NOT_READY | WR < 50%; PF < 1.5 |
| COMMODITY | 229 | 40.2% | 1.03 | N/A | WATCH | n < 100; PF < 1.5 |
| FUTURES | 52 | 42.3% | 1.09 | N/A | INSUFFICIENT_DATA | n < 100 |
| BOND | 1 | 0.0% | 0.0 | N/A | INSUFFICIENT_DATA | n = 1 |
| ETF | 45 | 2.2% | 0.02 | N/A | INSUFFICIENT_DATA | n < 100; PF ≈ 0 |
| MUTUAL_FUNDS | - | - | - | N/A | NOT_A_CLASS | Not registered (class id = -1) |
| PENNY_STOCK | 4 | 0.0% | 0.18 | N/A | INSUFFICIENT_DATA | n = 4 |
| MEME | 10 | 0.0% | 0.02 | N/A | INSUFFICIENT_DATA | n = 10 |

### Root Causes

1. **851 active picks have no `current_price`** → shows as 0% PnL, corrupts aggregate metrics
2. **25.5% of EQUITY picks have pnl_pct=0** → missing exit prices or stale data
3. **CRYPTO has genuine negative expectancy** (61.4% losses) — strategy issue, not data issue
4. **No class has n ≥ 100 AND PF ≥ 1.5 AND WR ≥ 50%** simultaneously
5. **Multiple testing not corrected** — 27+ parameter combos tested without Bonferroni correction
6. **No walk-forward out-of-sample validation** on any strategy
7. **No intrabar resolution** — 26.4% of crypto TP_HITs are false

### Best Candidate: EQUITY Momentum (lookback=12, skip=0, n_long=8)

- PF=2.62, WR=62.79%, MDD=17.37%, n=129 (historical backtest)
- Beats SPY total return (1021% vs 359%), Sharpe (1.27 vs 0.95), MDD (17.37% vs 23.93%)
- **BUT**: After Bonferroni correction (27 combos, ~1.4 expected false positives at α=0.05), cannot claim statistical significance
- **Must pass OOS walk-forward** before any promotion

---

## 8. Open Questions / Blockers

| # | Question | Blocker? | Resolution |
|---|----------|----------|------------|
| 1 | What is the total number of parameter configurations tried project-wide? | Yes (needed for multiple-testing correction) | Pending full pipeline run |
| 2 | What is the deflated Sharpe ratio for top candidates? | Yes (proof gate) | Pending experiments |
| 3 | Has any strategy been walk-forward tested with embedded OOS? | No | Pending experiments |
| 4 | What is the full friction model (spread, commission, slippage, funding, tax) per class? | Partial | `tools/data/transaction_costs.json` exists |
| 5 | Is there any strategy passing ALL 10 proof gates? | No | All fail at least 3 gates |

---

## 9. Next Immediate Action

Run the equity momentum strategy (lookback=12, skip=0, n_long=8) through the full pipeline:
1. Backtest with costs
2. Walk-forward OOS validation
3. DSR with correct nb_trials
4. SPA/White's Reality Check
5. Bootstrap CI on mean excess return
6. Regime split analysis
7. Shuffle control

---

## 10. Files in This Workspace

| Path | Purpose |
|------|---------|
| `README.md` | This document |
| `harvested_ideas/00_inventory.csv` | Complete inventory of all methods/strategies in repo |
| `harvested_ideas/01_failures_taxonomy.md` | Failure classification by asset class |
| `harvested_ideas/02_methods_catalogue.md` | All statistical/risk/ML methods found |
| `harvested_ideas/equity.md` | Equity class deep dive |
| `harvested_ideas/crypto.md` | Crypto class deep dive |
| `harvested_ideas/forex.md` | Forex class deep dive |
| `harvested_ideas/bonds.md` | Bond class deep dive |
| `harvested_ideas/etfs.md` | ETF class deep dive |
| `harvested_ideas/mutual_funds.md` | Mutual funds class deep dive |
| `harvested_ideas/multi_asset.md` | Multi-asset class deep dive |
| `Plan/equity/PLAN.md` | Equity momentum walk-forward plan |
| `Plan/crypto/PLAN.md` | Crypto funding-rate mean reversion plan |
| `Plan/forex/PLAN.md` | Forex/ETF/Bond/Mutual Fund plan |
| `tracker/predictions_tracker.csv` | Forward-test tracking CSV |
| `spec/pick_pipeline.py` | Per-asset-class pick pipeline |
| `spec/risk_qa_validator.py` | QA validation with 5 fail-closed gates |
| `spec/mf_screener.py` | Mutual fund passive allocation screener |
| `spec/run_simulation_monitor.py` | Simulation candidate monitor |
| `spec/e2e_integration_test.py` | End-to-end integration test |

---

*Last updated: 2026-11-15T07:00Z — Workspace created, all peer reviews complete, ready for experimentation.*
