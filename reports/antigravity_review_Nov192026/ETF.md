# ETF — Asset Class Deep-Dive Review

**Report date:** 2026-11-22
**Verdict: WEAK** (keep observing)
**Source surface:** findtorontoevents.ca/audit3 (2026-11-22 build) — cross-checked with local ledger and dashboard.

---

## 1. Current state

| Metric | Live audit3 (2026-11-22) | Local ledger (2026-11-20) |
|---|---|---|
| n | 590 | 590 |
| Win rate | 43.0% [39.1, 47.1] | 42.9% |
| Net expectancy / trade | −0.10% (n=539) | −0.004% |
| Selection alpha | −0.01% | −0.12% |
| Profit factor | 0.99 | 0.996 |
| DSR | 0.001 | 0.001 |
| Verdict | **WEAK** | **WEAK** |

Dashboard `asset_class_health` (2026-10-19): status=`thin_sample`, n=15, WR=73.3%, PF=1.83, sizing not allowed.

> ⚠ Note: dashboard shows a small, *very* different cohort (n=15, WR 73%, PF 1.83). The audit3 ledger (n=590) is the trustworthy view. All 18 ETF bars measured (full coverage).

---

## 2. Statistical gate status

| Gate | Result | Notes |
|---|---|---|
| G0 | ✔ n=590 | |
| G1 | ⚠ net CI [−0.31, +0.10] straddles 0 | |
| G2 | ⚠ | |
| G4 | DSR~0.001 — fails | |
| G5 | ⚠ | |
| G6 | ✔ | |
| G7 | ⚠ **slippage 234% of per-trade PnL** | cost is the killer |
| G8 | n/a | |

**Key insight:** ETF is structurally a cost problem. Measured ETF slippage ≈234% of per-trade PnL (from the monthly cadence), so a nominally-neutral pick is deeply negative net. This is a measurement/cadence artifact more than a signal problem.

---

## 3. Kill list (symbol)

| Symbol | n | WR | Net expectancy | PF |
|---|---|---|---|---|
| IWM | 66 | 31.8% | −0.49% | 0.53 |

---

## 4. Recency

| Panel | WR | PF |
|---|---|---|
| 14d | 3.5% | 0.05 |
| 48h | — | 0.00 |

⚠ 14d WR 3.5% / PF 0.05 is severe. Most ETF closes in the last 14d lost.

---

## 5. What has promise (audit2)

| Pod | Status | Evidence |
|---|---|---|
| POD-ETF-DUAL-MOMENTUM | observe | 12-1 sector-vs-SPY dual momentum — only ETF sleeve with lab WF PASS (OOS PF 2.75); 0 forward closes (winner-stays bug) |
| POD-FABER-TAA | observe | SPY/QQQ B-tier Sharpe ~1.65–1.74; 0 ETF closes in forward pilot |
| POD-EQUITY-BREAKOUT | pre_registered | ETF OOS Sharpe +0.21 (53 folds) |

---

## 6. Recommendation

1. **Keep observing; fix the cost model.** The 234% slippage-vs-PnL ratio means no ETF strategy can pass G7 until cadence/execution is fixed or backtests model realistic fills.
2. **Do not size up** — below T2, thin dashboard cohort, negative 14d.
3. **Rescue:** fix the winner-stays bug stopping DUAL-MOMENTUM forward closes; it's the most defensible ETF thesis (lab WF PASS). ETF shares the pre_registered EQUITY-BREAKOUT pod's long path.
4. **Recency flag:** 14d WR 3.5% is a red flag — if it persists one more build, elevate to WATCH.

---
*Not investment advice. Data: audit3 ledger, dashboard panels, audit2 pods. Generated 2026-11-22.*
