# Part 2 · P2-5: Pod-to-PROVEN Acceptance Checklist

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 03:30 EST
**Source:** `audit_dashboard/data/audit2_pods.json` · `audit3_ledger.json` `forward_gate`

---

## What a pod needs to reach PROVEN_T2

1. **n ≥ 100** closed forward rows dated AFTER registration.
2. **Net-expectancy bootstrap CI lower bound > 0 at 2× class slippage.**
3. **IR ≥ 0.5** vs a matched index/benchmark leg.
4. **Split-half stable** (both halves net mean > 0).
5. Own a **registered pod** (not orphan H-119).

---

## Per-pod status

| Pod | Class | Status | Forward rows | Blocker to PROVEN |
|---|---|---|---|---|
| POD-EQUITY-BREAKOUT | EQUITY/ETF | **pre_registered** | 0 | 0 forward rows — needs n≥100 |
| POD-FOREX-USDJPY-MOMENTUM | FOREX | observe | 0 | fx_prices stale to 2026-02-09 |
| POD-COMMODITY-ROLL-YIELD | COMMODITY | observe | 0 | emitter dormant (0 rows), needs contract feed |
| POD-CRYPTO-BTC4H-RSIMACD | CRYPTO | observe | 0 | fails 2× cost stress; needs n≥100 |
| POD-CRYPTO-POSITION | CRYPTO | observe | 0 | needs forward rows closed after 2026-11-19 |
| POD-FABER-TAA | EQUITY/ETF | observe | 0 | forward pilot has 0 ETF closes |
| POD-CRYPTO-VWAP-REVERSION | CRYPTO | observe | 0 | contested (lag drops PF); needs replay |
| POD-CRYPTO-BOLLINGER-MR | CRYPTO | observe | 0 | n<100; never merged to production |
| POD-ETF-DUAL-MOMENTUM | ETF | observe | 0 | winner-stays bug → 0 closes |

---

## The paradox (and the fix)

**Every registered pod has 0 forward rows, and all 430 existing forward rows belong to orphan H-119.**

- The system is gated on forward evidence, but none of the registered pods have any — so **nothing can ever promote**.
- Meanwhile the strongest forward evidence (H-119, +1.79% alpha, n=430) is orphaned and unusable.

**Recommended action:** create/adopt `POD-H119-FORWARD-ALPHA` (CRYPTO), which would make 430 real, intrabar-resolved forward rows eligible for a confirmatory decision — immediately giving the book its first testable certification path. Secondary: fix the 6 pods' data blockers (FX backfill, contract feed, winner-stays bug, merge-to-production).

---
*Not investment advice. Pod registry & forward gate cited above.*
