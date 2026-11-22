# FOREX — Asset Class Deep-Dive Review

**Report date:** 2026-11-22
**Verdict: WEAK** (keep observing)
**Source surface:** findtorontoevents.ca/audit3 (2026-11-22 build) — cross-checked with local ledger and dashboard.

---

## 1. Current state

| Metric | Live audit3 (2026-11-22) | Local ledger (2026-11-20) |
|---|---|---|
| n | 264 | 279 |
| Win rate | 36.4% [30.8, 42.3] | 36.6% |
| Net expectancy / trade | −0.07% (n=132) | −0.14% |
| Selection alpha | −0.04% | −0.06% |
| Profit factor | 0.85 | 0.665 |
| DSR | 0.000 | 0.000 |
| Verdict | **WEAK** | **WEAK** |

Dashboard `asset_class_health` (2026-10-19): status=`stressed`, n=374, WR=32.9%, PF=0.31, sizing not allowed. Only 12/17 instruments measured (AUDJPY, CHF, JPY, NZDJPY, USDZAR flagged).

---

## 2. Statistical gate status

| Gate | Result | Notes |
|---|---|---|
| G0 | ✔ n=264 | |
| G1 | ✘ net CI [−0.15, +0.01] not excluded | mostly below 0 |
| G2 | ✘ | 2× cost also <0 |
| G4 | DSR=0.000 — fails | |
| G5 | ⚠ | |
| G6 | ⚠ top source/symbol concentration | USDJPY historically ~55% |
| G7 | ✘ | |
| G8 | n/a | |

**Key insight:** FOREX is honest-exhausted per the audit2 doctrine (H-121 REFUTED) and the data layer cannot measure it fully — `fx_prices` is stale to 2026-02-09. Net expectancy is slightly negative; no edge.

---

## 3. Kill list

**Strategies:**
| Strategy | Dir | n | WR | Net expectancy | PF |
|---|---|---|---|---|
| Breakout Momentum | LONG | 37 | 40.5% | −0.46% | 0.40 |
| MeanReversionBB | SHORT | 29 | 0% | −0.02% | 0.00 |

**Symbols:** EURUSDT (n=20, WR 10%, net −1.65%, PF 0.15).

---

## 4. Recency

| Panel | WR | PF |
|---|---|---|
| 14d | 7.1% | 0.09 |
| 48h | 4.8% | 0.04 |

⚠ Recency is catastrophic (14d WR 7%, PF 0.09). FOREX is the worst 14d/48h class in the book after COMMODITY.

---

## 5. What has promise (audit2)

| Pod | Status | Evidence |
|---|---|---|
| POD-FOREX-USDJPY-MOMENTUM | observe | FXMom USDJPY n=42, Sharpe 2.02, PF 2.03, MC p=0.48; **data blocker: fx_prices stale to 2026-02-09** |

---

## 6. Recommendation

1. **Keep observing but do not size up.** FOREX is below T2, data-limited, and recency is deeply negative.
2. **Fix the data blocker first** — backfill FX price history; nothing can be forward-tested until then. This is the single highest-leverage fix for the class.
3. **Mutate:** the two killed strategies are fade-signal candidates (WR 0–40%). Invert or require a second source.
4. **Anchor on USDJPY momentum** (the only defensible thesis, Sharpe 2.02) once prices are backfilled; gate on own forward rows n≥100.

---
*Not investment advice. Data: audit3 ledger, dashboard panels, audit2 pods. Generated 2026-11-22.*
