# AI Tournament Pick Quality & Edge Criteria Audit

**Date:** 2026-05-24 | **Source:** `tournament_picks` table (3,149 picks, 9 asset classes)
**Context:** Reviewing SUPREME PLAN 90-day goals, MASTER ACTION PLAN, and current DB state for edge criteria.

---

## 1. Overall Pick Quality

| Asset Class | Picks | WR | Avg PnL | Sharpe | Readiness |
|---|---|---|---|---|---|
| EQUITY | 650 | 52.1% | +0.56% | +0.12 | ✅ n>=100 |
| CRYPTO | 628 | 50.0% | +1.02% | +0.17 | ✅ n>=100 |
| COMMODITY | 470 | 53.9% | +0.21% | +0.06 | ✅ n>=100 |
| FOREX | 454 | 57.3% | -0.39% | -0.22 | ⚠️ Best WR, negative PnL |
| ETF | 453 | 55.0% | +0.17% | +0.05 | ✅ n>=100 |
| BOND | 439 | 53.4% | -0.14% | -0.06 | ⚠️ Negative Sharpe |
| PENNY | 43 | — | — | — | ⏳ No resolved picks yet |
| FUTURES | 11 | — | — | — | ⏳ No resolved picks yet |

**Finding:** FOREX has the best WR (57.3%) but negative avg PnL — suggests many small winners and fewer large losers. CRYPTO has the best risk-adjusted return (Sharpe 0.17) but only 50% WR.

---

## 2. Statistical Edges Found

### Edge A: Regime-Adaptive Persona (Strongest)
| Persona | Asset Class | n | WR | Avg PnL |
|---|---|---|---|---|
| regime_adaptive | ETF | 13 | 84.6% | +2.11% |
| regime_adaptive | COMMODITY | 5 | 80.0% | +0.60% |
| regime_adaptive | CRYPTO | 13 | 76.9% | +4.32% |

**CRITERIA:** `regime_adaptive` persona + CRYPTO/ETF/COMMODITY → Compound WR ~80%, PnL +2-4%
**n is small (5-13)** — needs more data before calling it an edge

### Edge B: Momentum Breakout (Consistent)
| Persona | Asset Class | n | WR | Avg PnL |
|---|---|---|---|---|
| momentum_breakout | FOREX | 9 | 77.8% | +0.85% |
| momentum_breakout | COMMODITY | 13 | 61.5% | -0.29% |
| momentum_breakout | ETF | 46 | 58.7% | +0.17% |

**CRITERIA:** `momentum_breakout` + FOREX → 77.8% WR (n=9, needs more data)

### Edge C: Deep Value (Scalable)
n=60 across EQUITY at 60.0% WR, +1.07% avg PnL — largest sample, consistent positive returns.

### Edge D: Vol Arb (High Return)
CRYPTO + vol_arb: n=9, 66.7% WR, +3.82% PnL — highest return but small sample.

---

## 3. Confidence is NOT Predictive

- **All resolved picks** have confidence = 0 (stored as string "HIGH/MEDIUM/LOW" but ingested as 0)
- Confidence data from our pipeline is NOT flowing to the resolved stats
- The `fmt_conf()` function converts strings but some legacy picks are numeric/zero

---

## 4. Missing Audit Components (Not in tournament_picks)

| Component | Where | Description |
|---|---|---|
| **Verified Alpha** | `/audit/` | Shows "Verified Alpha" strategies with validation results |
| **Smart Picks** | `/audit/` button | "Smart Picks" score vs raw signal toggle |
| **High-Conviction Picks** | `/audit/` | Confidence-filtered picks with quality gates |
| **Edge Stability** | `/audit/edge_stability.html` | Per-class consistency checks |

These exist in the audit dashboard UI but their data comes from the OLD `picks` table (16,213 rows) and `universal_resolved_picks.json`, NOT from our `tournament_picks` table. They should be integrated.

---

## 5. PnL Display Issues (from Audit Stat-Validation)

- The "+1380.78%" and similar numbers are **arithmetic sum of per-trade PnL%** — not compounded returns
- The honest compounded EW figure is ~+50%, not +692%
- This has been partially fixed on the summary page with bold "Compound Return (EW)" labels

---

## 6. What We've Already Built

| Capability | Status |
|---|---|
| DB ingest (deduped, 3,149 picks) | ✅ Clean |
| Kelly position sizing | ✅ |
| Portfolio analytics (Sharpe, VaR, DD) | ✅ |
| Diversification monitor | ✅ |
| Performance reporting | ✅ |
| Research topics with macro data | ✅ |
| Price tracker (PENNY 7d, FUTURES 14d) | ✅ |
| ELI5 explanations | ✅ |

---

## 7. Available Data Sources (wiring plan)

| Source | Status | Picks/Signals | API Key | CI Freq |
|---|---|---|---|---|
| **FRED Macro** | ⚠️ BROKEN | 0 (CI produces nulls/400) | FRED_API_KEY set but fetch fails | 6h |
| **Kalshi** | ✅ Fresh | 9 picks (6 consensus symbols) | No key needed | 30min |
| **Polymarket** | ✅ Fresh | 3 signals + 8 whale profiles | No key needed | 30min |
| **Copy Trader** | ✅ Fresh | 20+ picks (stocks/forex/commodities) | No key needed | 2h |

### What's already wired
- **Research generator** reads FRED/Kalshi/Polymarket → adds macro regime + prediction market topics
- **FRED CI workflow exists** (fred-macro-refresh.yml) but produces all nulls — needs debugging
- **Copy Trader engine** exists (3,519 lines) but NOT wired into tournament pipeline

### What needs wiring
- Copy Trader picks → should be fed into `tournament_picks` as additional model entries
- FRED refresh needs debugging (likely API endpoint / authentication issue)
- Polymarket whale profiles → could inform direction confidence scoring

---

## 8. Open Questions for Swarm

1. Is `regime_adaptive` ETD 84.6% WR real or data leakage? (n=13 is small)
2. FOREX has highest WR (57.3%) but negative PnL — is this a hidden edge (frequent small wins vs occasional large losses)?
3. Should we filter by persona×asset_class pairs with WR>60% and n>=20 as "proven" strategies?
4. What's the right confidence encoding format — float 0-1 or string HIGH/MEDIUM/LOW?
5. How should we integrate the audit dashboard's "Verified Alpha" and "Smart Picks" components into tournament_picks?
6. Should PENNY and FUTURES have default resolution windows or be manually configured?
