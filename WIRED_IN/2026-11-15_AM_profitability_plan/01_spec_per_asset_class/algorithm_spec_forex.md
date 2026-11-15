# Algorithm Specification — FOREX

**Asset Class:** FOREX
**Status:** MUTATION-BEFORE-KILL — NOT MONEY-READY
**sizing_allowed:** false

---

## 1. Algorithm Specification

No Forex strategies were backtested in this simulation. Forex is on mutation protocol.

### Known Data
- **Historical PF:** 0.27 (sub-floor, below 1.0 break-even)
- **Recent PF:** 0.85 (still below 1.0)
- **Win rate:** ~32-40%
- **Sample size:** High n but negative expectancy

### Strategies Previously Tested
- Copy-trader paths
- CTA paths
- G10 carry basket (proposed, not tested)

### Cost Model (Not Applied)
Forex costs (spread + commission + swap) were not modeled in this simulation due to the class being blocked.

---

## 2. Backtest Results

**None.** Forex was not backtested in this simulation because:
1. Forex is on mutation-before-kill protocol.
2. Historical PF 0.27 — sub-floor, structurally unprofitable.
3. Recent PF 0.85 — still below break-even.
4. No clean data pipeline for Forex backtesting.

---

## 3. Pick Justification

**No Forex pick is justified for deployment.**

**Reasoning:**
1. **Historical PF 0.27** — gross losses exceed gross profits by nearly 4×.
2. **Recent PF 0.85** — still below 1.0 break-even after costs.
3. **Win rate 32-40%** — below 50%, requires very high R:R to survive.
4. **High n but negative expectancy** — more data confirms the losing edge, not refutes it.
5. **Already on mutation protocol** — class is being restructured, not deployed.

---

## 4. Elimination Reason

- **All Forex strategies:** Eliminated — mutation-before-kill. Historical and recent PF both below break-even. No path to profitability identified.

---

## 5. Money-Ready Gate Result

**Not applicable** — Forex is blocked on mutation protocol. Cannot evaluate gates.
