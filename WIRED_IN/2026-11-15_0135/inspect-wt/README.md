# WIRED_IN / 2026-11-15_0135 / inspect-wt

**Author:** inspect-wt (deepAI quantitative audit, worktree `.inspect-wt`, branch `audit/live-audit-2026-11-14`)
**Date:** 2026-11-15 01:35 UTC
**Status:** research-complete; two deployable candidates under pre-registered forward gates — no capital claims

---

## Contents

| Folder | File | Purpose |
|--------|------|---------|
| `algorithm_specifications/` | `ALGORITHM_SPECIFICATIONS.md` | Exact algorithm per asset class (reproducible spec) |
| `pick_justifications/` | `PICK_JUSTIFICATION.md` | Why these picks / asset classes, with probabilities |
| `backtest_research/` | `BACKTEST_AND_RESEARCH.md` | What was backtested and researched, with numbers |
| `elimination_rationale/` | `ELIMINATION_RATIONALE.md` | How the other classes, strategies and claims were eliminated |

---

## Summary

- **Picks (in priority order):** (1) **MF/ETF allocation sleeve** — monthly 12-1 momentum
  rotation with absolute-momentum filter and inverse-vol weights; (2) **variant-C strategy
  selection** — monthly reselect of top-6 strategies by trailing profit factor (the only
  procedure that beats random selection at Bonferroni-corrected p<0.005); (3) **equity
  RSI(2) trial** and (4) **crypto vol-targeted trend** as pre-registered conditional trials.
- **Backtest proof:** variant-C walk-forward n=237, PF 1.26, +98.7pp over 8 true OOS months,
  randomization 0/800 (p<0.0013), reproduced independently twice; MF/ETF sleeve 166-month
  backtest (2013-01→2026-10): CAGR 8.2% / Sharpe 0.53 / MDD −20.4% vs 60/40 7.3% / 0.54 /
  −21.0% and SPY 12.8% / 0.75 / −24.8% (price-only, conservative), with 2022 +2.3% vs SPY
  −19.5% and COVID −0.8% vs −19.9%.
- **Eliminated:** intraday/day-trading in every class, FOREX as a prediction class
  (PF 0.27 on honest n), BOND as prediction (n=18–35 vs floor 100), COMMODITY emission
  (422% cost/PnL; COT test failed 4/4), EQUITY as a *current* edge source (NO_ALPHA_BETA),
  single-cell mining (46 cells, zero survivors; 170 ledgers vs 8.5 by chance), the
  alive-filter refinement, `mega_mutation` (VETOED, single-source), VWAP (refuted twice),
  prediction-market copy-trading (7 structural reasons), and display-tier curation as evidence.

---

## The core claim

Nothing in this system is certified money-ready today (0/9 surfaces, fleet PF 0.80). But two
things survive every audit: a **benchmark-relative allocation sleeve that needs no alpha**
(reproducible backtest in-repo), and a **strategy-selection procedure whose edge over random
is statistically demonstrated** (p<0.005 Bonferroni-surviving, forward pilot running).
Everything else was eliminated under pre-registered gates, not vibes.

---

*inspect-wt / 2026-11-15 · companion packages: `final_2026_11_14/inspect-wt/`, `final_v4/inspect-wt/`,
`2026-11-14＊7PM＊plan/inspect-wt/`*
