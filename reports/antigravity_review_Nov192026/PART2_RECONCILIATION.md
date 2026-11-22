# Part 2 · P2-2: Cross-Source Reconciliation Matrix

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 03:30 EST
**Sources:** `audit3_ledger.json` (authoritative, 2026-11-20 build) vs `dashboard_data.json` `performance.by_asset_class` + `readiness.by_class` (2026-10-19 snapshot)

---

## 1. The problem

The audit ledger and the publishing dashboard report **different numbers for the same class**. This is not a rounding issue — it is a denominator/method mismatch. Since the ledger uses the canonical resolved view (intrabar truth, integrity-excluded rows removed), it is the trustworthy source.

---

## 2. Reconciliation matrix

| Class | Ledger n | Ledger WR | Ledger PF | Dashboard by_class WR/PF | Readiness n/PF/WR | Verdict |
|---|---|---|---|---|---|---|
| CRYPTO | 6,874 | 40.2% | 0.83 | 45.8% / 1.29 | 19,621 / 0.29 / 45.7% | KILL |
| EQUITY | 942 | 45.0% | 1.08 | 45.5% / 11.91 | 463 / 0.88 / 55.3% | WEAK |
| ETF | 590 | 42.9% | 1.00 | 30.0% / 0.57 | 15 / 1.83 / 73.3% | WEAK |
| FOREX | 279 | 36.6% | 0.67 | 16.1% / 0.42 | 374 / 0.31 / 32.9% | WEAK |
| COMMODITY | 45 | 15.6% | 0.12 | 75.0% / **5,624.67** | 18 / 1.32 / 33.3% | KILL |
| BOND | 35 | 40.0% | 0.65 | 50.0% / 217.33 | 0 / — / 0% | WEAK |
| FUTURES | 4 | 50.0% | 1.87 | 0.0% / 0.0 | 12 / 0.45 / 8.3% | INSUFFICIENT_N |

---

## 3. Divergence analysis

**Worst offender — COMMODITY:** dashboard `by_asset_class` shows WR 75% / PF **5,624** — an absurd, clearly-wrong number — while the ledger shows a KILL (WR 15.6%, PF 0.12). The dashboard number is driven by a tiny, non-representative subset and must be ignored. Anyone reading `/audit` headline COMMODITY stats is being misled.

**CRYPTO:** dashboard `by_class` PF 1.29 vs ledger 0.83; readiness n=19,621 vs ledger 6,874. The dashboard counts rows that the ledger integrity-excludes; and the raw PF doesn't reflect intrabar truth (Part 1: 0.29× inflation). Verdict (KILL) is unchanged, but the *magnitude* of the problem is understated on the dashboard.

**FUTURES:** dashboard shows WR 0% / PF 0 (all losses) while ledger shows WR 50% / PF 1.87. n=4 both ways — both are meaningless, but they *disagree* on direction. Classic small-sample flip.

**BOND:** dashboard readiness n=0 but `by_class` shows WR 50% / PF 217. Contradictory within the same dashboard.

---

## 4. Recommendation

1. **The dashboard and ledger must share one denominator.** The `asset_class_health` / `by_asset_class` block should be regenerated from the canonical resolved view, not a raw DB slice.
2. **Surface the ledger verdict on `/audit`** so KILL/WEAK is visible next to the headline WR/PF (currently the verdict lives only on `/audit3`).
3. **Hide/flag absurd PF values** (PF > 50 at n < 100) to prevent misreading.
4. **Part 2's core ask:** fix the freshness — `dashboard_data.json` is 2026-10-19 while the ledger is 2026-11-20; they're a month apart and out of sync.

---
*Not investment advice. Reconciliation is based on the two committed JSON files cited above.*
