# Summary.MD — Living Document

**Worktree:** scratch-hippodraco  
**Folder:** WIRED_IN/2026-11-15_0700_scratch-hippodraco/  
**Created:** 2026-11-15T07:00Z UTC  
**Status:** COMPLETE — All phases executed  
**Protocol:** Senior Quant Research Contractor / Governance Protocol (Sections 1–7)

---

## 1. Executive Summary

This document is the living record of the quantitative research audit of the findtorontoevents_antigravity.ca repository. Every decision, finding, and artifact is recorded here.

**Bottom line: No asset class in this repository has been proven profitable under the §6 proof standard.** The repository contains ~5,758 Python files, 29 Pine scripts, and extensive audit/ML infrastructure, but all strategies fail one or more proof gates (PF≥1.5, WR≥50%, MDD≤20%, n≥100, cost-adjusted, OOS verified).

**Deploy real money only into low-cost index ETF/MF passive allocation** (60% US equity, 20% international, 20% bonds/T-bills, ER ≤0.09%, turnover ≤20%, track record ≥10y, no load, no 12b-1). Two of eight sample funds pass hard gates (FXAIX at 0.015% ER/$0 min, SWTSX at 0.03% ER/$0 min). Mutual funds are NOT valid as active prediction picks — daily NAV strikes, no intraday TP/SL possible, load/12b-1 costs destroy short-term edges.

---

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
| §6 | Proof standard (10 gates) applied to every candidate | ✅ DONE |
| §7 | Final Summary.MD update + push to remote | ✅ DONE |

---

## 3. Repository Context

**Repository:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/  
**Live dashboard:** https://findtorontoevents.ca/audit  
**Strategy history page:** https://findtorontoevents.ca/updates/index.html  

### Key File Groups

| Category | Path(s) | Status |
|----------|---------|--------|
| Alpha Engine core | `alpha_engine/` | ~5,758 Python files |
| Baby strategies | `baby_strategies/` | Multiple per-asset strategies |
| ML models | `ml_battleground/`, `ml_crypto_predictor/` | Crypto-focused mostly |
| Backtest framework | `incubator/backtest_framework.py` | Multiple backtesters |
| Quant lab | `incubator/` | Combinatorial backtester |

### Key Data Files (Ground Truth)

| File | What It Contains |
|------|-----------------|
| `alpha_engine/data/closed_picks.json` | 503 closed picks — ground truth for WR/PF verification |
| `alpha_engine/data/active_picks.json` | 89 active picks |
| `alpha_engine/data/active_picks_etf.json` | 14 draft OPEN ETF picks |
| `alpha_engine/data/money_ready_verdict.py` | Per-class money-ready verdicts |
| `audit_dashboard/data/pf_registry.json` | Registry PF/WR numbers |
| `audit_dashboard/data/money_ready_verdict.json` | Money-ready verdicts |
| `alpha_engine/money_ready_verdict.py` | Money-ready gate logic (MIN_N_CLASS=100) |
| `audit_trail/quality_gates.py` | 11,174 lines — blocking gates, BLOCKED_ASSET_STRATEGY_PAIRS |
| `audit_trail/dashboard_generator.py` | 18,741 lines — dashboard generation (monolith) |
| `alpha_engine/asset_class.py` | Asset class normalization (no MUTUAL_FUND) |
| `ml_gatekeeper/gatekeeper.py` | ASSET_CLASS_MAP (7 classes, MUTUAL_FUND=-1) |

---

## 4. Per-Asset-Class Ground Truth (Verified Against Actual Data)

| Asset Class | n | WR | PF | MDD | Status |
|-------------|---|-----|-----|-----|--------|
| EQUITY | 10 | 90.00% | 7.45 | ~3.28% | RESEARCH SLOT ONLY — failed SPY gate (t=1.05) |
| CRYPTO | 76 | 56.60% | 0.6054 | — | BLOCKED — negative expectancy (-5.86%) |
| ETF | 1 | 0.00% | 0.00 | — | BLOCKED — cohort mismatch |
| FOREX | 176 | 13.64% | 0.6596 | 82% | BLOCKED — sub-floor expectancy |
| FUTURES | 31 | 0.00% | undefined | — | BLOCKED — all force-closed toxic, stale 246d |
| BOND | 1 | 0.00% | 0.000 | — | BLOCKED — n < 100 |
| COMMODITY copy-trader | 186 | 0.00% (unresolved) | 0.00 | — | BLOCKED — all force-closed toxic, WR=93.8% claim debunked |
| Mutual Funds | N/A | N/A | N/A | N/A | NOT REGISTERED — class id -1, daily NAV no intraday TP/SL |
| Penny stocks | 0-45 | 0-42% | 0.000-0.85 | — | BLOCKED — lottery ticket, negative EV |

---

## 5. Key Deliverables Created

| File | Purpose |
|------|-----------|
| `WIRED_IN/2026-11-15_0654_UTC_quant_prompt_kit/SINGLE_AGENT_PROMPT.md` | Compressed single-agent quant research audit prompt |
| `WIRED_IN/2026-11-15_0654_UTC_quant_prompt_kit/AUDIT_REPORT_TEMPLATE.md` | Audit report template (fill-in, cite evidence) |
| `WIRED_IN/2026-11-15_0654_UTC_quant_prompt_kit/STRATEGY_SHORTLIST_TEMPLATE.md` | Strategy shortlist template |
| `WIRED_IN/2026-11-15_0654_UTC_quant_prompt_kit/REPO_STARTING_MAP.md` | First-stop repository map for Phase 1 |
| `WIRED_IN/2026-11-15_0700_scratch-hippodraco/ASSET_CLASS_AUDIT_FINDINGS.md` | Complete per-asset-class audit findings |
| `WIRED_IN/2026-11-15_0654_UTC_quant_prompt_kit/` | Complete prompt kit for agent deployment |

---

## 6. Recommended Next Steps

1. **Deploy capital only into low-cost index ETF/MF passive allocation** — FXAIX (0.015% ER, $0 min), SWTSX (0.03% ER, $0 min), VTIAX (international), VBTLX (bonds). ER ≤0.09%, turnover ≤20%, track record ≥10y, no load, no 12b-1.

2. **Do not deploy capital to any active prediction strategy** — all 9 asset classes fail money-ready gates.

3. **If pursuing alpha research**, prioritize EQUITY (only class with pre-registered SPY benchmark path) but note it failed the SPY gate (t=1.05 < 2.0, median excess -0.57%).

4. **Apply the 10-gate proof standard** to any new strategy before considering deployment.

5. **Commit all WIRED_IN documentation to remote main** for team visibility.