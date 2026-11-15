# WIRED_IN / 2026-11-15_0125 / finpredict-v4

**Author:** finpredict-v4
**Date:** 2026-11-15
**Status:** Live — picks feeding findtorontoevents.ca/audit

---

## Contents

| Folder | File | Purpose |
|--------|------|---------|
| `algorithm_specifications/` | `ALGORITHM_SPECIFICATIONS.md` | Exact algorithm per asset class |
| `pick_justifications/` | `PICK_JUSTIFICATION.md` | Why these picks / asset classes |
| `backtest_research/` | `BACKTEST_AND_RESEARCH.md` | What was backtested/researched |
| `elimination_rationale/` | `ELIMINATION_RATIONALE.md` | How the others were eliminated |
| root | `RECONCILING_PICKS_VS_PROVEN.md` | Explains why picks can be emitted even though no asset class is *proven* profitable (beta vs alpha) |

---

## Summary

- **Live picks:** VTI / TLT / SGOV / BND (Faber 200d MA + defens rotation).
- **Backtest proof:** Faber 7.39× vs B&H 7.93× (2008–2026), but Sharpe 1.01 vs 0.79 and maxDD -18.8% vs -46.3% — risk-adjusted win.
- **Eliminated:** all intraday scalping/day-trading, FOREX intraday, COT, VWAP, ETF intraday, prediction-market copy-trading, meta-permutations.

---

## The core claim

The only deployable, grounded, backtest-proven path is **trend-aware, low-cost index allocation**. Everything else was eliminated under the four-gate protocol (economic mechanism, benchmark-relative OOS performance, effective N, 90-day forward test).

---

*finpredict-v4 / 2026-11-15*
