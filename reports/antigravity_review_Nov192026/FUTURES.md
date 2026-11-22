# FUTURES — Asset Class Deep-Dive Review

**Report date:** 2026-11-22
**Verdict: INSUFFICIENT_N** (no claim — too little data)
**Source surface:** findtorontoevents.ca/audit3 (2026-11-22 build) — cross-checked with local ledger and dashboard.

---

## 1. Current state

| Metric | Live audit3 (2026-11-22) | Local ledger (2026-11-20) |
|---|---|---|
| n | 4 | 4 |
| Win rate | 50.0% [15.0, 85.0] | 50.0% |
| Net expectancy / trade | +1.34% (n=4) | +1.29% |
| Selection alpha | +1.29% | +1.34% |
| Profit factor | 1.87 | 1.87 |
| DSR | — (n<20, no cell score) | — |
| Verdict | **INSUFFICIENT_N** | **INSUFFICIENT_N** |

Dashboard `asset_class_health` (2026-10-19): status=`thin_sample`, n=12, WR=8.3%, PF=0.45, sizing not allowed.

> ⚠ n=4 is far below even the G0 sample floor (n=20). The +1.3% expectancy and PF 1.87 are meaningless at this sample size. Do not read anything into them.

---

## 2. Statistical gate status

| Gate | Result | Notes |
|---|---|---|
| G0 | ✘ n=4 < 20 | no verdict possible |
| G1–G8 | not scored | no DSR, no CI, no split-half |
| G6 | — | 4/4 instruments measured |

---

## 3. Recency

| Panel | WR | PF |
|---|---|---|
| 14d | 60.7% | 2.72 |
| 48h | 77.6% | 5.35 |

These 14d/48h numbers (from the recency panels) are attractive but come from a tiny cohort and are not gated by the tribunal. Treat as noise until n grows.

---

## 4. What has promise (audit2)

No FUTURES-specific pod is registered in audit2. FUTURES is not a tracked forward sleeve.

---

## 5. Recommendation

1. **No action possible.** n=4 is insufficient to claim or deny edge. Keep collecting rows.
2. **Do not size up** — below T2, thin sample.
3. **Low priority** — FUTURES is not a registered forward pod; if futures work matters, register a hypothesis/pod first (M-107 pre-registration) before growing the sample.

---
*Not investment advice. Data: audit3 ledger, dashboard panels. Generated 2026-11-22.*
