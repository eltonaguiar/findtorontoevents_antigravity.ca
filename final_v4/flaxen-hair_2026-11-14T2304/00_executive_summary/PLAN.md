# FINALIZED PLAN — Executive Summary

**Worktree:** flaxen-hair_2026-11-14T2304 | **Date:** 2026-11-14T23:04Z | **Repo:** findtorontoevents_antigravity.ca

---

## Bottom Line

**No approach is proven profitable.** 0/23 hypotheses across 4 protocol versions survived clean-OOS + effective-N + capital + execution gates. **Do not deploy capital today.**

The only defensible path forward is:

1. **Fix measurement infrastructure** (PnL calculation, blank fields, stale data, promotion gates)
2. **Build mutual fund + ETF infrastructure from scratch** (zero coverage currently)
3. **Run pre-registered benchmark tests** for EQUITY (slot 1) and CRYPTO (slot 2 conditional)
4. **Implement comprehensive risk management** with separate webpage review
5. **Only promote to live capital** after meeting all go/no-go criteria

---

## Current State: 24-Hour Review Findings

### Local Files Modified (Last 24h)

| File | Type | Finding |
|------|------|---------|
| `dashboard/live_picks.json` | Data | 6 active picks, many PnL=0.0, JNK bond pick with current_price=266.66 (wrong asset price) |
| `mercury2/data/metrics_report.json` | Data | 40.09% win rate, IC≈0 (Pearson 0.0391, Spearman 0.1046) |
| `MARKET_BEATING_REPORT.md` | Report | 58.3% accuracy (below 60% target), only ADA-USD ✅ at 66.7% |
| `research/profitability/HYPOTHESES.md` | Research | 23 hypotheses, ALL NOT_PROVED |
| `research/profitability/SCORECARD.md` | Scorecard | 0/10 proof score, 7.0/10 overall |
| `research/profitability/forward/ledger.csv` | Forward | 1 row only (started 2026-11-13), needs 90 days or 30 round trips |
| `quick_wins/shared/daily_tracker_log.jsonl` | Data | New untracked file |
| `quick_wins/shared/gated_picks.jsonl` | Data | New untracked file |

### Remote GitHub Commits (Last 24h)

~60 automated commits, all `[skip ci]`, including:
- Alpha Engine scans, conviction scans, smart picks batches
- Live PnL refreshes, signal recorder updates
- Dashboard pick trader updates
- Mega mutation tracker hourly updates
- Gainer scans, momentum tracker scans
- CI failures: Python 3.11 and 3.12 jobs failing (run 43644095951)

### Peer Review Contradictions Found

| Issue | Contradiction | Severity |
|-------|--------------|----------|
| ETF win rate | 2.22% vs 68.42% across files | HIGH |
| CRYPCO count | 3,705 vs 22,055 | HIGH |
| VWAP claim | Claimed Sharpe 3.76, actual ~1.18 | CRITICAL (falsified) |
| Mega-mutation | 21/50 forward picks may be synthetic/replay | HIGH |
| Promotion gates | Both FDR and single-source default OFF | CRITICAL |
| Cost gate | Fail-open on missing evidence | CRITICAL |

---

## Research Priority (Not Deployment)

| Priority | Asset Class | Basis | Status |
|----------|-------------|-------|--------|
| **Slot 1** | EQUITY | Only class with positive cost margin (3.23×, mean +0.323%, n=738) | Pre-registered test vs SPY total return |
| **Slot 2** | CRYPTO | Only class with diagnosed fixable defect (fill issue) | Conditional: fix fills first, forward-test n≥100 |
| **Deferred** | ETF, FOREX, COMMODITY, BOND, FUTURES, MUTUAL FUNDS | Blocked by arithmetic or insufficient data | Do not prioritize |

---

## Go/No-Go Criteria (Must ALL Pass Before Live Capital)

| Criterion | Threshold |
|-----------|-----------|
| Profit factor | ≥ 1.5 |
| Sharpe ratio | ≥ 1.0 |
| Win rate | ≥ 50% |
| Sortino ratio | ≥ 1.0 |
| Calmar ratio | ≥ 0.5 |
| Deflated Sharpe Ratio | ≥ 0.95 at N≥38 |
| DSR after best day removal | ≥ 0.95 |
| 2-day-lag Sharpe | ≥ 1.0 |
| Max drawdown | < 15% |
| Daily loss cap | -2% |
| Monthly loss cap | -10% |
| Expectancy | > 0 (positive) |
| Forward sample | n ≥ 100 closed picks |
| Kelly fraction | > 0 after shrinkage |

---

## 90-Day Execution Roadmap

| Weeks | Work | Decision Point |
|-------|------|----------------|
| **Week 1** | PnL validation, blank field flags, promotion gates fail-closed, QA infrastructure | Measurement fixed |
| **Weeks 2-4** | Mutual fund + ETF infrastructure (NAV cache, ranker, backtest tools) | MF/ETF ready for testing |
| **Weeks 4-8** | EQUITY 24-month benchmark test vs SPY; CRYPTO forward test post-fill-fix | Alpha vs beta determination |
| **Weeks 9-13** | Review forward data against gates; publish trial count | Scale or wind down |

**Success at day 90 is NOT "profitable."** It is one class with a pre-registered, benchmark-relative result and a known trial count — the first point at which "is this profitable?" becomes answerable.

---

## Risk Management Summary

| Component | Status | Key Thresholds |
|-----------|--------|---------------|
| Position sizing | Needs implementation | 1-2% risk per trade, Kelly quarter |
| Stop loss | Needs standardization | ATR-based, 1.0× SL, 1.5× TP |
| Drawdown controls | Partial (daily only) | Add weekly (-5%), monthly (-10%) |
| Correlation limits | Partial | Max 3 per group, 0.70 threshold |
| Risk-adjusted metrics | Partial | Sharpe > 0.5, Sortino > 1.0, Calmar > 0.5 |
| Probability framework | Missing | Expectancy, Kelly, ruin probability |
| Risk dashboard webpage | Missing | Separate HTML page with Chart.js |
| QA validation | Missing | PnL=0%, blank fields, open items |

---

## Files in This Plan Package

```
final_v4/flaxen-hair_2026-11-14T2304/
├── 00_executive_summary/PLAN.md          ← This document
├── 01_proposed_edits/PROPOSED_EDITS.md   → 15 specific code edits
├── 02_qa_plan/QA_PLAN.md                 → QA: PnL=0%, blank fields, MF/ETF
├── 03_mutual_fund_etf/MF_ETF_PLAN.md     → MF + ETF infrastructure plan
├── 04_risk_management/RISK_MANAGEMENT_PLAN.md → Risk mgmt + separate webpage
└── 05_peer_review_results/               → Subagent cross-check results
```

---

## Immediate Next Steps (This Week)

1. **Enable promotion gates** — Change `MONEY_READY_FDR_GATE` and `MONEY_READY_SINGLE_SOURCE_GATE` defaults from `"0"` to `"1"` in `alpha_engine/money_ready_verdict.py`
2. **Close cost gate fail-open** — Change `per_class_cost_gate.py` to fail-closed on missing/stale evidence
3. **Create QA validator** — Build `alpha_engine/risk_qa_validator.py` with PnL=0%, blank field, open item checks
4. **Build mutual fund infrastructure** — Create `alpha_engine/mutual_fund_ranker.py`, metadata CSV, NAV cache directory
5. **Register MUTUAL_FUND class** — Add to `asset_class.py`, `gatekeeper.py`, `dashboard_generator.py`
6. **Create risk thresholds config** — Build `alpha_engine/risk_thresholds.json`
7. **Create risk dashboard** — Build `risk_dashboard.html` with Chart.js visualizations

---
