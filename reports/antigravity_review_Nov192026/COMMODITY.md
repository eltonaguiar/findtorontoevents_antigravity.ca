# COMMODITY — Asset Class Deep-Dive Review

**Report date:** 2026-11-22
**Verdict: KILL** (class aggregate)
**Source surface:** findtorontoevents.ca/audit3 (2026-11-22 build) — cross-checked with local `audit3_ledger.json` (2026-11-20) and `dashboard_data.json`.

---

## 1. Current state

| Metric | Live audit3 (2026-11-22) | Local ledger (2026-11-20) |
|---|---|---|
| n | 50 | 45 |
| Win rate | 20.0% [11.2, 33.0] | 15.6% |
| Net expectancy / trade | −3.57% (n=40) | −3.51% |
| Selection alpha | −2.96% | −3.72% |
| Profit factor | 0.15 | 0.117 |
| DSR | 0.000 | 0.000 |
| Verdict | **KILL** | **KILL** |

Dashboard `asset_class_health` (2026-10-19): status=`thin_sample`, n=18, WR=33.3%, PF=1.32, sizing not allowed.

---

## 2. Statistical gate failure

| Gate | Result | Notes |
|---|---|---|
| G0 | n=50 → passes floor, but thin | only 40/50 priced |
| G1 | ✘ net CI [−5.51, −2.05] entirely < 0 | strong negative |
| G2 | ✘ | 2× cost CI also < 0 |
| G4 | DSR=0.000 — fails | |
| G5 | ✘ split-half unstable | |
| G6 | CT=F concentration — 57% | near concentration boundary |
| G7 | ✘ net < 0 after slippage | |
| G8 | n/a | |

**Root cause:** a single strategy (`futures_momentum`, SHORT) and a highly concentrated CT (57%) drive the aggregate. Class net expectancy −3.57%/trade with PF 0.15 is severe.

---

## 3. Kill list

- **Strategy:** `futures_momentum` (SHORT), n=27, net −4.28%, PF 0.00.
- **Emission gate:** blocked 64 COMMODITY pick attempts (top suppressed: commodity_momentum ×36).

---

## 4. Recency

| Panel | WR | PF |
|---|---|---|
| 14d | (not present; thin sample) | — |
| 48h | — | — |

Class sample is too thin for recency panels; dashboard holds only n=18.

---

## 5. What has promise (audit2)

| Pod | Status | Evidence |
|---|---|---|
| POD-COMMODITY-ROLL-YIELD | observe | Academic factor (Erb–Harvey / Gorton–Rouwenhorst); in-repo emitter dormant (0 rows); needs a second-nearby contract feed |

---

## 6. Recommendation

1. **Kill/cease emitting the class aggregate** — the net-expectancy CI is entirely negative and harm is material (−3.57%/trade).
2. **Do not size up** — below T2, thin sample, sizing disallowed.
3. **Mutate:** `futures_momentum` SHORT is a fade-signal candidate (WR 0%); either invert (LONG) with a second source or retire.
4. **Rescue path:** only the academic roll-yield carry factor has a defensible thesis; build the contract feed, backfill prices, then forward-test with n≥100 before any re-emission.

---
*Not investment advice. Data: audit3 ledger, dashboard asset_class_health, audit2 pods. Generated 2026-11-22.*
