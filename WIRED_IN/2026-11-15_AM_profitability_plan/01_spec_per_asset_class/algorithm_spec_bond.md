# Algorithm Specification — BOND

**Asset Class:** BOND
**Status:** INSUFFICIENT DATA — NOT MONEY-READY
**sizing_allowed:** false

---

## 1. Algorithm Specification

No Bond strategies were backtested in this simulation.

### Known Data
- **Official n:** 1 (cannot support statistical inference)
- **Registry n:** 35 (marginal, below floor)
- **Official PF:** 0.000
- **Registry PF:** 0.586
- **Official WR:** 0.00%
- **Registry WR:** 37.1%

### Strategies Previously Tested
- Bond duration rotation
- Bond credit spread overlay
- Yield curve strategies (FRED data)

### Cost Model (Not Applied)
Bond costs (bid-ask spread, commission, roll-down) were not modeled due to insufficient data.

---

## 2. Backtest Results

**None.** Bond was not backtested in this simulation because:
1. Official n=1 — statistically meaningless.
2. Registry n=35 — below minimum floor (n≥100 required).
3. No yield/duration data pipeline for backtesting.
4. Exit semantics broken (per asset class fixes).

---

## 3. Pick Justification

**No Bond pick is justified for deployment.**

**Reasoning:**
1. **n=1 official** — cannot draw any conclusion.
2. **n=35 registry** — below minimum sample for statistical inference.
3. **PF 0.000-0.586** — below break-even.
4. **WR 0-37%** — below 50%.
5. **No data pipeline** for bond backtesting.

---

## 4. Elimination Reason

- **All Bond strategies:** Eliminated — insufficient data. Blocked until yield/duration data acquired and n ≥ 100.

---

## 5. Money-Ready Gate Result

**Not applicable** — Bond is blocked. Cannot evaluate gates without data and sufficient sample.
