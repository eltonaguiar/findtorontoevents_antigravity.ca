# Algorithm Specification — MUTUAL FUNDS

**Asset Class:** MUTUAL FUNDS
**Status:** ZERO COVERAGE — NOT REGISTERED AS ASSET CLASS
**sizing_allowed:** false

---

## 1. Algorithm Specification

Mutual funds are **structurally incompatible** as active picks. No algorithm was built or tested.

### Structural Constraints

| Constraint | Impact on Active Picking |
|------------|-------------------------|
| NAV struck once daily after market close | No intraday TP/SL execution possible |
| Next-NAV execution | Entry/exit at unknown price (next NAV after order) |
| Frequent-trading limits | Discourages/penalizes short-term trading |
| Load fees (front-end/back-end) | Immediate cost drag on any trade |
| 12b-1 fees | Ongoing cost drag |
| Expense ratio (0.015%-0.74%) | Persistent cost drag |
| Minimum initial investment ($0-$3,000+) | Accessibility constraint |
| AUM and turnover reporting | Transparency varies |

### Valid Role: Passive Core Allocation

Mutual funds are valid as **passive core allocation**, not active picks:

| Criterion | Threshold | Purpose |
|-----------|-----------|---------|
| Expense ratio | ≤ 0.09% (index) / ≤ 0.20% (active) | Minimize cost drag |
| Load fee | None | No entry/exit penalty |
| 12b-1 fee | None | No ongoing distribution cost |
| Min initial investment | ≤ $1,000 | Accessibility |
| AUM | ≥ $1B | Institutional scale/liquidity |
| Turnover ratio | ≤ 20% | Low trading cost |
| Tracking error | ≤ 0.25% vs benchmark | Close benchmark tracking |
| Track record | ≥ 10 years | Multiple market cycles |
| NAV freshness | ≤ 24h | Current pricing |

### Starter Universe (Passive Core Only)
VFIAX, VTSAX, FXAIX, SWTSX, VBTLX, VWELX, VGSLX, VTIAX

### Allocation Model
- 60% total US equity index
- 20% total international equity index
- 20% short-duration bond / T-bill index
- Rebalance quarterly or on 5% drift bands

---

## 2. Backtest Results

**None.** Mutual funds are not backtested as active picks because:
1. Daily NAV only — no intraday signal possible.
2. No TP/SL execution — cannot test stop-based strategies.
3. No production infrastructure exists (class id = -1, NOT_BUILT).
4. Zero mutual fund picks in any pipeline.

---

## 3. Pick Justification

**No mutual fund active pick is justified.** Mutual funds are specified as **passive core allocation only** — the highest-probability lower-risk capital deployment vehicle.

**Justification for passive allocation:**
- Captures equity risk premium + bond income over multi-year horizons.
- Low costs (ER ≤ 0.09-0.20%) preserve returns.
- Diversification reduces permanent capital-loss risk.
- Does not require the prediction system to work.
- Positive expected return over multi-year periods (market beta).

---

## 4. Elimination Reason

- **Mutual funds as active picks:** Eliminated — structurally incompatible (daily NAV, no intraday TP/SL, load/12b-1 costs, frequent-trading limits).
- **Mutual funds as passive allocation:** NOT eliminated — recommended as the capital deployment vehicle.

---

## 5. Money-Ready Gate Result

**Not applicable** — mutual funds are not an active pick class. Passive allocation is the recommended deployment vehicle outside the prediction system's gates.
