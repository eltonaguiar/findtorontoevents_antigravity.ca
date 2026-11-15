# PROFITABILITY FRAMEWORK — Complete Asset Class Analysis & Profit Path

**Worktree:** flaxen-hair_2026-11-15T0020 | **Date:** 2026-11-15T00:27Z | **Repo:** findtorontoevents_antigravity.ca

This document synthesizes ALL findings from:
- ALL_STRATEGIES.md (700+ strategies across 12 asset class categories)
- money-maker-ready / money-maker-readyv2 / money-maker-ready-June112026edition / money-maker-ready-July112026edition skills
- 2026-05-13-money-maker-action-plan.md
- 2026-05-11-money-maker-master-plan.html
- All 16 peer_claude-phase10b-money-maker reports (EQUITY, ETF, FOREX, BOND, COMMODITY, CRYPTO, FUTURES, PENNY)
- All previous final_v2/final_v4 audit findings
- Current local + remote GitHub state (2026-11-14)

## Bottom Line

**No asset class is proven profitable.** 0/23 hypotheses across 4 protocol versions.

**Only ONE approach shows genuine forward-validated risk-adjusted performance:** ETF Tactical Asset Allocation (TAA) — matches market return with ~half the drawdown (Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs SPY −51%, Calmar 0.48 vs 0.21, validated 2007-2026 including 2008 GFC).

**Research priorities (not deployment):**
1. **ETF TAA** — slot 1: forward-track the 50/50 blend (momentum rotation + VAA-G4), Sharpe 0.89, MaxDD −16%
2. **EQUITY** — slot 2: pre-registered benchmark test vs SPY total return (n≥500, PF≥1.15, Sharpe≥SPY)
3. **CRYPTO** — slot 3 conditional: fix `kimi_riseoftheclaw` fill bug first, then forward-test POSITION horizon n≥100
4. **All other classes** — blocked by arithmetic

**Do not deploy capital.** System is not money-ready — all 9 classes return `sizing_allowed: false`, promotion gates default OFF, cost gate has fail-open paths.

---

## Files in This Package

| Folder | Contents |
|--------|----------|
| README.md | This summary |
| 01_asset_class_plans/ | PROFITABILITY_FRAMEWORK.md — per-asset-class profitability plans ranked by probability |
| 02_holding_period_analysis/ | HOLDING_PERIOD_TRADING_STYLE_ANALYSIS.md — per-class analysis by holding period vs trading style |
| 03_proven_algorithms/ | PROVEN_ALGORITHMS.md — top algorithms from TradingView contests (Hoffman, etc.) |
| 04_subq_decision_support/ | SUBQ_DECISION_SUPPORT.md — SubQ API key usage + fact-checking protocol + Kalshi/Polymarket + copy trading analysis + AI coding agent prompts |
| 05_framework_answers/ | FRAMEWORK_ANSWERS.md — answers to the 6 detailed framework questions |
| 06_essential_questions/ | ESSENTIAL_QUESTIONS.md — essential questions for finding profitable algorithms |
| 07_company_turnarounds/ | TURNAROUNDS.md — financial prediction/risk management company turnarounds |
| 08_key_metrics/ | KEY_METRICS.md — key metrics from different perspectives (Sharpe, pro investor, mutual fund manager, bank trader) |

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
