# Part 2 · P2-1: Forward-Clock Deep-Dive

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 03:30 EST
**Source:** `reports/forward_observations.jsonl` (430 rows) · `audit_dashboard/data/audit2_forward.json` · `audit3_ledger.json` `forward_gate`

---

## 1. What the forward clock is

Forward rows are real, closed picks dated **after** a hypothesis's registration. Per the tribunal's G8 gate, **a pod can reach PROVEN_T2 only on its own forward rows closed after registration.** The forward clock is the only promotion path.

---

## 2. Current clock state

| Metric | Value |
|---|---|
| Total forward rows | **430** |
| Asset classes | 100% CRYPTO (n=430) |
| Hypothesis | 100% **H-119** (orphan — owned by no pod) |
| Direction | LONG 226 / SHORT 204 |
| Intrabar first-touch | 430/430 (100%) |
| Regime-ok | 430/430 (100%) |
| Benchmark leg coverage | 343/430 (79.8%) |
| Selection alpha (gross_mismatch_pp) | mean **+1.79%** |
| Alpha win-rate | **315/430 = 73.3%** |
| Benchmark-leg return | mean −0.92% |
| Distinct symbols | 109 (top: JUP, AVAX, RENDER, ADA, ETH…) |
| Slippage | mean 16 bps |

---

## 3. The critical finding

**All 430 forward rows belong to hypothesis H-119 — which has NO registered pod.** The audit2 forward clock labels H-119 an **orphan hypothesis**: "these rows cannot promote anything." Registered pods all have **0 forward rows** (POD-EQUITY-BREAKOUT, POD-FOREX-USDJPY-MOMENTUM, POD-COMMODITY-ROLL-YIELD, POD-CRYPTO-BTC4H-RSIMACD, POD-CRYPTO-POSITION, POD-FABER-TAA).

So despite a **genuine +1.79% selection alpha on n=430 (73.3% alpha WR)** — the strongest out-of-sample signal in the entire book — **nothing can promote**, because H-119 is not attached to a pod that can certify it.

This is a **structural bug in the pod registry / hypothesis linkage**, not a market signal problem.

---

## 4. Why the alpha is credible (but unconfirmed)

- 100% intrabar first-touch resolution (no lookahead).
- 100% regime-ok rows.
- Benchmark leg coverage 79.8%; when present, benchmark return is negative (−0.92%) while picks returned +1.79% alpha — i.e., picks **beat a falling market**.
- Alpha WR 73.3% across 109 distinct symbols → low concentration risk for the aggregate.

**Caveats:** all rows are CRYPTO; the hypothesis is single-family; and because it's orphaned there is no pre-registered confirmatory status — so statistically it counts as discovery-only, not confirmatory.

---

## 5. Actionable recommendation

1. **Register/adopt H-119 into a pod (or create `POD-H119-FORWARD-ALPHA`)** so these 430 real forward rows can count toward a promotion decision. This is the single highest-leverage fix in the whole system — it would immediately give the book its first *testable* confirmatory cohort.
2. Fix the **6 pods with 0 forward rows** (data blockers / winner-stays bugs) so their registration isn't moot.
3. Until adopted, treat the +1.79% alpha as **discovery evidence** — promising but not eligible to certify PROVEN.

---
*Not investment advice. Data: forward_observations.jsonl, audit2_forward.json, audit3_ledger.json.*
