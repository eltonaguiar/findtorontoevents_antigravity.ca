# Algorithm Specification — COMMODITY / FUTURES

**Asset Class:** COMMODITY / FUTURES
**Status:** WATCH — LOW-FREQUENCY ONLY, NOT MONEY-READY
**sizing_allowed:** false

---

## 1. Algorithm Specification

No Commodity/Futures strategies were backtested in this simulation.

### Known Data
- **Historical PF:** 1.78 (better than crypto/forex, but low n)
- **Recent PF:** 1.026 (barely above break-even)
- **Win rate:** ~40-47%
- **Sample size:** n=7-229 (insufficient for statistical inference)

### Strategies Previously Tested
- CTA trend following
- COT (Commitment of Traders) contrarian — GATE FAILED 4/4
- Multi-asset strategies

### Cost Model (Not Applied)
Commodity/futures costs (roll yield, contango/backwardation, commission, slippage, contract identity) were not modeled due to low n and data quality issues.

---

## 2. Backtest Results

**None.** Commodity/Futures was not backtested in this simulation because:
1. Sample size n=7-229 — insufficient for statistical inference.
2. COT contrarian backtest failed its gate 4/4 checks (OOS n=30, PF 0.861, mean net -0.45%/trade).
3. 422% cost ratio for commodity — costs exceed average PnL.
4. No reliable contract identity / roll data pipeline.

---

## 3. Pick Justification

**No Commodity/Futures pick is justified for deployment.**

**Reasoning:**
1. **Low n (7-229)** — cannot support statistical inference.
2. **COT contrarian gate failed** 4/4 — the one strategy tested did not pass.
3. **422% cost ratio** — costs are 4.22× the average PnL. Structurally unprofitable.
4. **Registry mismatch** — official PF 1.026 vs registry PF 0.172. Cannot trust numbers.
5. **No real feed / contract identity** — execution quality unknown.

---

## 4. Elimination Reason

- **All Commodity/Futures strategies:** Eliminated — blocked until data quality clears (real feed, contract identity, n ≥ 100). COT contrarian specifically failed gate.

---

## 5. Money-Ready Gate Result

**Not applicable** — Commodity/Futures is blocked. Cannot evaluate gates without reliable data and sufficient sample.
