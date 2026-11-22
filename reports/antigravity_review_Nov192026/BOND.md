# BOND — Asset Class Deep-Dive Review

**Report date:** 2026-11-22
**Verdict: WEAK** (keep observing)
**Source surface:** findtorontoevents.ca/audit3 (2026-11-22 build) — cross-checked with local ledger and dashboard.

---

## 1. Current state

| Metric | Live audit3 (2026-11-22) | Local ledger (2026-11-20) |
|---|---|---|
| n | 37 | 35 |
| Win rate | 43.2% [28.7, 59.1] | 40.0% |
| Net expectancy / trade | −0.05% (n=35) | −0.18% |
| Selection alpha | −0.10% | −0.11% |
| Profit factor | 0.81 | 0.65 |
| DSR | 0.000 | 0.000 |
| Verdict | **WEAK** | **WEAK** |

Dashboard `asset_class_health` (2026-10-19): status=`insufficient_data`, n=0, WR=0%, PF=null, sizing not allowed.

> ⚠ The dashboard's `asset_class_health` shows **n=0** for BOND (insufficient data). The audit3 ledger (n=37) is the only usable view. All 37 rows have measured bars (2/2 coverage panel).

---

## 2. Statistical gate status

| Gate | Result | Notes |
|---|---|---|
| G0 | ⚠ n=37 — above 20 floor, below 100 stability | thin |
| G1 | ⚠ net CI [−0.40, +0.30] straddles 0 | |
| G2 | ⚠ | |
| G4 | DSR=0.000 — fails | |
| G5 | ⚠ | |
| G6 | ✔ | |
| G7 | ⚠ | |
| G8 | n/a | |

**Key insight:** BOND has near-zero activity (n=37 across the whole book) and no signal. The CI straddles zero; there is simply not enough data to claim or deny edge.

---

## 3. Kill list

No BOND strategy or symbol cells killed in the current tribunal. BOND has no kills — it simply has too little data to judge.

---

## 4. Recency

BOND does not appear in the 14d/48h recency panels (insufficient closes). No recency signal available.

---

## 5. What has promise (audit2)

No BOND pod is registered in audit2. There is no active BOND thesis.

---

## 6. Recommendation

1. **Keep observing.** BOND is insufficient-information, not harmful (unlike CRYPTO/COMMODITY).
2. **Do not size up** — below T2, n<100.
3. **Low priority rescue** — there is no active BOND emitter/thesis; if bond work is desired, the only defensible academic sleeve is duration rotation / TLT-IEF (dashboards show `bond_tlt_ief_*` backtests exist), but those are not registered as forward pods. Register a hypothesis/pod before spending effort.

---
*Not investment advice. Data: audit3 ledger, dashboard panels. Generated 2026-11-22.*
