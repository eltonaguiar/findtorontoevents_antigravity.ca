# Algorithm Specification — ETF

**Asset Class:** ETF
**Status:** BLOCKED — COHORT MISMATCH / INSUFFICIENT DATA
**sizing_allowed:** false

---

## 1. Algorithm Specification

No active ETF strategy was backtested in this simulation due to the cohort mismatch blocker.

### Planned Strategies (Not Tested)

| Strategy | Type | Reason Not Tested |
|----------|------|-------------------|
| Dual MA Crossover | Trend following | ETF cohort mismatch blocks all ETF strategies |
| Sector Rotation | Tactical | No reliable ETF sector data pipeline |
| Bond/Equity Rotation | Tactical | Insufficient ETF data quality |

### Known Data Issue
- **Cohort mismatch:** Official ETF PF = 0.022 (n=45) vs Registry PF = 1.788 — 6×+ discrepancy. Cannot trust either number without row-level reconciliation.
- **Zero live ETF picks** currently emitted by the system.
- **SPY miscategorized** as equity in some pipelines.

---

## 2. Backtest Results

**None.** ETF strategies were not backtested because:
1. The ETF cohort mismatch (official vs registry) is a blocker.
2. No reliable ETF data pipeline exists for backtesting.
3. All ETF hypotheses are NOT_PROVED (H5-H19 in peer review).

---

## 3. Pick Justification

**No ETF pick is justified for deployment.**

**Reasoning:**
1. **Zero live ETF picks** exist in the system.
2. **Cohort mismatch** makes any ETF performance number untrustworthy.
3. **267% of ETF average PnL is cost** — ETF cannot win as currently configured.
4. **No backtestable ETF strategy** with clean data exists.

**Deployment path for ETF:** Only as passive core allocation (low-cost broad-market ETFs like VTI, VXUS, BND), not as active picks.

---

## 4. Elimination Reason

- **All ETF active strategies:** Eliminated — blocked by cohort mismatch and zero live data. Not testable until data pipeline fixed.

---

## 5. Money-Ready Gate Result

**Not applicable** — ETF is blocked. Cannot evaluate gates without reliable data.
